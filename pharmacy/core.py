"""Database and transaction boundary. Amounts are integer paisa, quantities whole units."""
from __future__ import annotations
import sqlite3, os, hashlib, hmac, secrets, json, shutil
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from contextlib import contextmanager

SCHEMA = '''
CREATE TABLE IF NOT EXISTS meta(version INTEGER NOT NULL);
INSERT INTO meta SELECT 1 WHERE NOT EXISTS(SELECT 1 FROM meta);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT CHECK(role IN ('Admin','Cashier')) NOT NULL, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,sku TEXT UNIQUE NOT NULL,name TEXT NOT NULL,barcode TEXT UNIQUE,category TEXT NOT NULL DEFAULT '',price INTEGER NOT NULL CHECK(price>=0),reorder INTEGER NOT NULL DEFAULT 5 CHECK(reorder>=0),active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS parties(id INTEGER PRIMARY KEY,kind TEXT CHECK(kind IN ('Customer','Supplier')) NOT NULL,name TEXT NOT NULL,phone TEXT NOT NULL DEFAULT '',address TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY,created TEXT NOT NULL,supplier_id INTEGER NOT NULL REFERENCES parties(id),reference TEXT NOT NULL,total INTEGER NOT NULL CHECK(total>=0),paid INTEGER NOT NULL CHECK(paid>=0 AND paid<=total));
CREATE TABLE IF NOT EXISTS batches(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL REFERENCES products(id),purchase_id INTEGER REFERENCES purchases(id),batch TEXT NOT NULL,expiry TEXT NOT NULL,quantity INTEGER NOT NULL CHECK(quantity>=0),cost INTEGER NOT NULL CHECK(cost>=0),original_quantity INTEGER NOT NULL CHECK(original_quantity>0));
CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY,created TEXT NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id),customer_id INTEGER REFERENCES parties(id),subtotal INTEGER NOT NULL,discount INTEGER NOT NULL CHECK(discount>=0),total INTEGER NOT NULL CHECK(total>=0),paid INTEGER NOT NULL CHECK(paid>=0 AND paid<=total),status TEXT NOT NULL DEFAULT 'Posted');
CREATE TABLE IF NOT EXISTS sale_lines(id INTEGER PRIMARY KEY,sale_id INTEGER NOT NULL REFERENCES sales(id),batch_id INTEGER NOT NULL REFERENCES batches(id),quantity INTEGER NOT NULL CHECK(quantity>0),price INTEGER NOT NULL,cost INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,created TEXT NOT NULL,party_id INTEGER NOT NULL REFERENCES parties(id),amount INTEGER NOT NULL CHECK(amount>0),note TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY,created TEXT NOT NULL,category TEXT NOT NULL,note TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0));
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,created TEXT NOT NULL,user_id INTEGER REFERENCES users(id),action TEXT NOT NULL,detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS imports(id INTEGER PRIMARY KEY,digest TEXT UNIQUE NOT NULL,created TEXT NOT NULL,rows INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS batch_product ON batches(product_id,expiry);
CREATE INDEX IF NOT EXISTS sale_created ON sales(created);
'''

def now(): return datetime.now().isoformat(timespec='seconds')
def money(value):
    try:
        d=Decimal(str(value))
        if not d.is_finite() or d<0 or d>Decimal('1000000000'): raise ValueError('Amount out of range')
        if d.as_tuple().exponent < -2: raise ValueError('Use at most two decimal places')
        return int((d*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    except InvalidOperation: raise ValueError('Enter a valid amount')
def fmt(paisa): return f'{Decimal(paisa)/100:,.2f}'
def integer(value, minimum=0):
    s=str(value)
    if not s.isdigit() or int(s)<minimum: raise ValueError(f'Enter a whole number >= {minimum}')
    return int(s)
def valid_date(value): return date.fromisoformat(str(value)).isoformat()
def hash_password(password):
    if len(password)<10: raise ValueError('Password must contain at least 10 characters')
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
def verify(password, encoded):
    salt,digest=encoded.split(':')
    return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex(),digest)
def data_directory():
    return Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))/'PharmacyDesktop'

class Store:
    def __init__(self,path=None):
        self.path=Path(path or data_directory()/'pharmacy.sqlite3')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript(SCHEMA)
        if self.db.execute('SELECT version FROM meta').fetchone()[0]!=1: raise ValueError('Unsupported database schema')
        self.user=None
    def rows(self,sql,args=()): return [dict(r) for r in self.db.execute(sql,args)]
    def scalar(self,sql,args=()): return self.db.execute(sql,args).fetchone()[0]
    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK'); raise
    def authorize(self,admin=False):
        if not self.user: raise PermissionError('Please sign in')
        current=self.rows('SELECT * FROM users WHERE id=? AND active=1',(self.user['id'],))
        if not current or (admin and current[0]['role']!='Admin'): raise PermissionError('Admin access required')
    def audit(self,action,detail=''):
        self.db.execute('INSERT INTO audit(created,user_id,action,detail) VALUES(?,?,?,?)',(now(),self.user['id'] if self.user else None,action,str(detail)))
    def setup(self,username,password):
        username=username.strip()
        if not username: raise ValueError('Username required')
        encoded=hash_password(password)
        with self.transaction():
            if self.scalar('SELECT count(*) FROM users'): raise ValueError('Already configured')
            self.db.execute('INSERT INTO users(username,password,role) VALUES(?,?,?)',(username,encoded,'Admin'))
            self.audit('Initial setup',username)
    def login(self,username,password):
        self.user=None
        found=self.rows('SELECT * FROM users WHERE username=? AND active=1',(username.strip(),))
        if not found or not verify(password,found[0]['password']): raise ValueError('Incorrect username or password')
        self.user={k:v for k,v in found[0].items() if k!='password'}
        self.audit('Login'); return self.user
    def add_user(self,username,password,role):
        self.authorize(True)
        if role not in ('Admin','Cashier') or not username.strip(): raise ValueError('Invalid user')
        with self.transaction():
            self.db.execute('INSERT INTO users(username,password,role) VALUES(?,?,?)',(username.strip(),hash_password(password),role))
            self.audit('Create user',username)
    def change_password(self,old,new):
        self.authorize()
        row=self.rows('SELECT password FROM users WHERE id=?',(self.user['id'],))[0]
        if not verify(old,row['password']): raise ValueError('Old password incorrect')
        with self.transaction():
            self.db.execute('UPDATE users SET password=? WHERE id=?',(hash_password(new),self.user['id']))
            self.audit('Change password')
    def save_product(self,sku,name,barcode,category,price,reorder,product_id=None):
        self.authorize(True)
        if not sku.strip() or not name.strip(): raise ValueError('SKU and name required')
        args=(sku.strip(),name.strip(),barcode.strip() or None,category.strip(),money(price),integer(reorder))
        with self.transaction():
            if product_id:
                self.db.execute('UPDATE products SET sku=?,name=?,barcode=?,category=?,price=?,reorder=? WHERE id=?',(*args,product_id))
            else: product_id=self.db.execute('INSERT INTO products(sku,name,barcode,category,price,reorder) VALUES(?,?,?,?,?,?)',args).lastrowid
            self.audit('Save product',product_id)
        return product_id
    def add_party(self,kind,name,phone='',address=''):
        self.authorize(kind=='Supplier')
        if kind not in ('Customer','Supplier') or not name.strip(): raise ValueError('Party name required')
        with self.transaction():
            ident=self.db.execute('INSERT INTO parties(kind,name,phone,address) VALUES(?,?,?,?)',(kind,name.strip(),phone,address)).lastrowid
            self.audit('Create '+kind,ident)
        return ident
    def _party(self,ident,kind):
        if not self.rows('SELECT id FROM parties WHERE id=? AND kind=?',(ident,kind)): raise ValueError(kind+' required')
    def purchase(self,supplier,reference,lines,paid):
        self.authorize(True); self._party(supplier,'Supplier')
        if not reference.strip() or not lines: raise ValueError('Vendor bill reference and items required')
        normalized=[]
        for line in lines:
            p=integer(line['product_id'],1); q=integer(line['quantity'],1); c=money(line['cost'])
            expiry=valid_date(line['expiry']); batch=str(line['batch']).strip()
            if not batch: raise ValueError('Batch required')
            if expiry<date.today().isoformat(): raise ValueError('Cannot receive expired stock')
            if not self.rows('SELECT id FROM products WHERE id=? AND active=1',(p,)): raise ValueError('Unknown product')
            normalized.append((p,batch,expiry,q,c))
        total=sum(q*c for p,b,e,q,c in normalized); paid=money(paid)
        if paid>total: raise ValueError('Paid exceeds bill total')
        with self.transaction():
            ident=self.db.execute('INSERT INTO purchases(created,supplier_id,reference,total,paid) VALUES(?,?,?,?,?)',(now(),supplier,reference,total,paid)).lastrowid
            for p,b,e,q,c in normalized:
                self.db.execute('INSERT INTO batches(product_id,purchase_id,batch,expiry,quantity,cost,original_quantity) VALUES(?,?,?,?,?,?,?)',(p,ident,b,e,q,c,q))
            self.audit('Purchase',ident)
        return ident
    def sell(self,cart,customer=None,paid='0',discount='0'):
        self.authorize()
        if customer: self._party(customer,'Customer')
        if not cart: raise ValueError('Cart is empty')
        discount=money(discount); paid=money(paid)
        # Merge duplicate scans, allocate earliest expiring batches under the write lock.
        wanted={}
        for item in cart:
            pid=integer(item['product_id'],1); wanted[pid]=wanted.get(pid,0)+integer(item['quantity'],1)
        with self.transaction():
            allocations=[]; subtotal=0
            for pid,requested in wanted.items():
                product=self.rows('SELECT * FROM products WHERE id=? AND active=1',(pid,))
                if not product: raise ValueError('Unknown product')
                price=product[0]['price']; remaining=requested
                for b in self.rows('SELECT * FROM batches WHERE product_id=? AND expiry>=? AND quantity>0 ORDER BY expiry,id',(pid,date.today().isoformat())):
                    take=min(remaining,b['quantity'])
                    if take:
                        allocations.append((b['id'],take,price,b['cost'])); remaining-=take
                    if remaining==0: break
                if remaining: raise ValueError('Insufficient unexpired stock: '+product[0]['name'])
                subtotal+=requested*price
            if discount>subtotal: raise ValueError('Discount exceeds subtotal')
            total=subtotal-discount
            if paid>total or (customer is None and paid!=total): raise ValueError('Walk-in sales require exact full payment; named customer required for credit')
            ident=self.db.execute('INSERT INTO sales(created,user_id,customer_id,subtotal,discount,total,paid) VALUES(?,?,?,?,?,?,?)',(now(),self.user['id'],customer,subtotal,discount,total,paid)).lastrowid
            for bid,q,p,c in allocations:
                self.db.execute('UPDATE batches SET quantity=quantity-? WHERE id=?',(q,bid))
                self.db.execute('INSERT INTO sale_lines(sale_id,batch_id,quantity,price,cost) VALUES(?,?,?,?,?)',(ident,bid,q,p,c))
            self.audit('Sale',ident)
        return ident
    def void_sale(self,ident):
        self.authorize(True)
        with self.transaction():
            s=self.rows('SELECT * FROM sales WHERE id=? AND status=?',(ident,'Posted'))
            if not s: raise ValueError('Sale not found or already void')
            if s[0]['created'][:10]!=date.today().isoformat(): raise ValueError('Only same-day sale cancellations are supported; historical returns require a separate return workflow')
            if s[0]['customer_id']:
                balance=self.balance(s[0]['customer_id'])
                if balance < s[0]['total']-s[0]['paid']: raise ValueError('Customer has later payments; settle/refund separately before voiding')
            for line in self.rows('SELECT * FROM sale_lines WHERE sale_id=?',(ident,)):
                self.db.execute('UPDATE batches SET quantity=quantity+? WHERE id=?',(line['quantity'],line['batch_id']))
            self.db.execute("UPDATE sales SET status='Void' WHERE id=?",(ident,)); self.audit('Void sale',ident)
    def balance(self,party_id):
        party=self.rows('SELECT kind FROM parties WHERE id=?',(party_id,))
        if not party: raise ValueError('Unknown party')
        table,col,extra=('sales','customer_id'," AND status='Posted'") if party[0]['kind']=='Customer' else ('purchases','supplier_id','')
        owed=self.scalar(f'SELECT coalesce(sum(total-paid),0) FROM {table} WHERE {col}=?{extra}',(party_id,))
        return owed-self.scalar('SELECT coalesce(sum(amount),0) FROM payments WHERE party_id=?',(party_id,))
    def payment(self,party_id,amount,note):
        self.authorize(True); amount=money(amount)
        with self.transaction():
            if amount<=0 or amount>self.balance(party_id): raise ValueError('Payment must be positive and cannot exceed outstanding balance')
            self.db.execute('INSERT INTO payments(created,party_id,amount,note) VALUES(?,?,?,?)',(now(),party_id,amount,note)); self.audit('Payment',party_id)
    def expense(self,category,note,amount):
        self.authorize(True); amount=money(amount)
        if not category.strip() or amount<=0: raise ValueError('Category and positive amount required')
        with self.transaction():
            self.db.execute('INSERT INTO expenses(created,category,note,amount) VALUES(?,?,?,?)',(now(),category,note,amount)); self.audit('Expense',category)
    def inventory(self,query=''):
        return self.rows('''SELECT p.*,coalesce(sum(b.quantity),0) stock,coalesce(sum(CASE WHEN b.expiry>=date('now','localtime') THEN b.quantity ELSE 0 END),0) sellable FROM products p LEFT JOIN batches b ON b.product_id=p.id WHERE p.active=1 AND (p.name LIKE ? OR p.sku LIKE ? OR p.barcode LIKE ?) GROUP BY p.id ORDER BY p.name''',tuple('%'+query+'%' for _ in range(3)))
    def get_setting(self,key,default=''): return next((r['value'] for r in self.rows('SELECT value FROM settings WHERE key=?',(key,))),default)
    def settings(self,values):
        self.authorize(True)
        with self.transaction():
            for k,v in values.items(): self.db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,str(v)))
            self.audit('Settings updated',','.join(values))
    def backup(self,destination):
        self.authorize(True); destination=Path(destination)
        if destination.resolve()==self.path.resolve(): raise ValueError('Choose a different file')
        if destination.exists(): raise ValueError('Backup destination already exists; use a new filename')
        out=sqlite3.connect(destination)
        try: self.db.backup(out)
        finally: out.close()
        self.audit('Backup',destination.name)
    def restore(self,source):
        self.authorize(True); source=Path(source)
        if source.resolve()==self.path.resolve(): raise ValueError('Choose a backup file')
        check=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)
        try:
            if check.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Damaged backup')
            if check.execute('SELECT version FROM meta').fetchone()[0]!=1: raise ValueError('Unsupported backup version')
            if check.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Invalid backup relationships')
            # Ensure all required tables/columns exist before touching current data.
            for table in ('users','products','parties','purchases','batches','sales','sale_lines','payments','expenses','audit','imports','settings'):
                actual={r[1] for r in check.execute(f'PRAGMA table_info({table})')}
                expected={r[1] for r in self.db.execute(f'PRAGMA table_info({table})')}
                if actual!=expected: raise ValueError('Invalid backup schema: '+table)
            if not check.execute("SELECT id FROM users WHERE role='Admin' AND active=1").fetchone(): raise ValueError('Backup has no active admin')
            safety=self.path.parent/('before-restore-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
            self.backup(safety)
            check.backup(self.db)
        finally: check.close()
        self.user=None
    def close(self): self.db.close()
