"""Tk desktop UI. All writes pass through Store authorization/transaction methods."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import date, datetime, timedelta
import os, traceback
from .core import Store, fmt, money, integer, data_directory
from . import excel, printing, reports

class App(tk.Tk):
    def __init__(self,store):
        super().__init__(); self.store=store; self.title('Pharmacy Desktop'); self.geometry('1240x780'); self.minsize(980,640)
        style=ttk.Style(self); style.theme_use('clam'); style.configure('Treeview',rowheight=28); style.configure('TButton',padding=7); style.configure('TNotebook.Tab',padding=(14,9))
        self.protocol('WM_DELETE_WINDOW',self.shutdown); self.report_callback_exception=self.callback_error
        self.login_screen()
    def shutdown(self): self.store.close(); self.destroy()
    def callback_error(self,typ,value,tb):
        path=self.store.path.parent/'error.log'
        with path.open('a',encoding='utf-8') as f: traceback.print_exception(typ,value,tb,file=f)
        messagebox.showerror('Operation failed',str(value),parent=self)
    def clear(self):
        for child in self.winfo_children(): child.destroy()
    def safe(self,callback):
        def run():
            try: return callback()
            except Exception as e: messagebox.showerror('Please check',str(e),parent=self)
        return run
    def button(self,parent,label,callback):
        b=ttk.Button(parent,text=label,command=self.safe(callback)); b.pack(side='left',padx=4,pady=6); return b
    def login_screen(self):
        self.clear(); self.store.user=None
        first=self.store.scalar('SELECT count(*) FROM users')==0
        frame=ttk.Frame(self,padding=35); frame.place(relx=.5,rely=.45,anchor='center')
        ttk.Label(frame,text='Pharmacy Desktop',font=('Segoe UI',24,'bold')).pack(pady=15)
        ttk.Label(frame,text='Create your administrator account' if first else 'Sign in • Offline workstation').pack(pady=8)
        variables={}
        for label in ['Username','Password']+(['Confirm password'] if first else []):
            ttk.Label(frame,text=label).pack(anchor='w'); v=tk.StringVar(); variables[label]=v
            entry=ttk.Entry(frame,textvariable=v,width=36,show='*' if 'assword' in label else ''); entry.pack(pady=6)
            if label=='Username': entry.focus_set()
        self.failed_logins=0
        def submit():
            if first:
                if variables['Password'].get()!=variables['Confirm password'].get(): raise ValueError('Passwords do not match')
                self.store.setup(variables['Username'].get(),variables['Password'].get())
            try: self.store.login(variables['Username'].get(),variables['Password'].get())
            except ValueError:
                self.failed_logins+=1
                if self.failed_logins>=5:
                    login.configure(state='disabled'); self.after(30000,lambda: login.configure(state='normal') if login.winfo_exists() else None)
                raise
            self.main()
        login=ttk.Button(frame,text='Create account' if first else 'Sign in',command=self.safe(submit)); login.pack(pady=15)
        self.bind('<Return>',lambda e: login.invoke())
    def form(self,title,fields,callback):
        """fields: (key,label,default[, choices]). Choice labels start with database ID."""
        d=tk.Toplevel(self); d.title(title); d.transient(self); d.grab_set(); d.geometry('580x'+str(min(720,100+len(fields)*56)))
        content=ttk.Frame(d,padding=18); content.pack(fill='both',expand=True); values={}
        for key,label,default,*options in fields:
            ttk.Label(content,text=label).pack(anchor='w')
            v=tk.StringVar(value=str(default)); values[key]=v
            if options: widget=ttk.Combobox(content,textvariable=v,values=options[0],state='readonly')
            else: widget=ttk.Entry(content,textvariable=v,show='*' if 'password' in label.lower() else '')
            widget.pack(fill='x',pady=(1,6))
        def save(): callback({k:v.get() for k,v in values.items()}); d.destroy()
        ttk.Button(content,text='Save',command=self.safe(save)).pack(pady=10)
        return d
    def table(self,parent,columns):
        wrap=ttk.Frame(parent); wrap.pack(fill='both',expand=True,padx=8,pady=4)
        tree=ttk.Treeview(wrap,columns=columns,show='headings',selectmode='browse')
        for col in columns: tree.heading(col,text=col); tree.column(col,width=130,minwidth=65,stretch=True)
        ys=ttk.Scrollbar(wrap,orient='vertical',command=tree.yview); xs=ttk.Scrollbar(wrap,orient='horizontal',command=tree.xview)
        tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set); tree.grid(row=0,column=0,sticky='nsew'); ys.grid(row=0,column=1,sticky='ns'); xs.grid(row=1,column=0,sticky='ew'); wrap.rowconfigure(0,weight=1); wrap.columnconfigure(0,weight=1)
        return tree
    def fill(self,tree,rows):
        tree.delete(*tree.get_children())
        for i,row in enumerate(rows): tree.insert('',tk.END,iid=str(i),values=row)
    def selected(self,tree):
        if not tree.selection(): raise ValueError('Select a row first')
        return tree.item(tree.selection()[0],'values')
    def pickid(self,text): return int(text.split(' | ')[0]) if text else None
    def parties_options(self,kind): return [f"{p['id']} | {p['name']}" for p in self.store.rows('SELECT * FROM parties WHERE kind=? ORDER BY name',(kind,))]
    def product_options(self): return [f"{p['id']} | {p['sku']} | {p['name']}" for p in self.store.inventory()]
    def main(self):
        self.unbind('<Return>'); self.clear(); self.cart=[]; self.purchase_lines=[]
        top=ttk.Frame(self,padding=10); top.pack(fill='x')
        ttk.Label(top,text=self.store.get_setting('name','Pharmacy Desktop'),font=('Segoe UI',20,'bold')).pack(side='left')
        ttk.Label(top,text=f"  PKR • {self.store.user['username']} ({self.store.user['role']})").pack(side='left')
        self.button(top,'Change password',self.password_form); self.button(top,'Sign out',self.login_screen)
        self.notebook=ttk.Notebook(self); self.notebook.pack(fill='both',expand=True,padx=10,pady=5)
        self.tabs={}
        names=['Counter','Stock','Customers','Sales']
        if self.store.user['role']=='Admin': names+=['Purchases','Suppliers','Expenses','Reports','Administration']
        for name in names:
            f=ttk.Frame(self.notebook); self.notebook.add(f,text=name); self.tabs[name]=f
        self.counter_ui(); self.stock_ui(); self.party_ui('Customer'); self.sales_ui()
        if 'Purchases' in self.tabs:
            self.purchases_ui(); self.party_ui('Supplier'); self.expenses_ui(); self.reports_ui(); self.admin_ui()
        ttk.Label(self,text='Offline local database • Save backups to a separate drive • Barcode scanner: keyboard mode + Enter',padding=6).pack(fill='x')
    def counter_ui(self):
        f=self.tabs['Counter']; bar=ttk.Frame(f); bar.pack(fill='x'); self.search=tk.StringVar()
        ttk.Label(bar,text='Scan barcode / search medicine').pack(side='left',padx=8)
        entry=ttk.Entry(bar,textvariable=self.search,width=40); entry.pack(side='left',padx=5)
        self.button(bar,'Search',self.counter_search); self.button(bar,'Add selected',self.cart_add)
        entry.bind('<Return>',self.safe_event(self.scan))
        self.lookup=self.table(f,['ID','SKU','Medicine','Price PKR','Sellable','Barcode'])
        self.lookup.bind('<Double-1>',self.safe_event(self.cart_add))
        self.cart_tree=self.table(f,['ID','Medicine','Quantity','Unit PKR','Total PKR'])
        actions=ttk.Frame(f); actions.pack(fill='x'); self.total_label=ttk.Label(actions,text='Cart total PKR 0.00',font=('Segoe UI',13,'bold')); self.total_label.pack(side='left',padx=10)
        self.button(actions,'Change quantity',self.cart_quantity); self.button(actions,'Remove line',self.cart_remove); self.button(actions,'Clear cart',self.cart_clear); self.button(actions,'Checkout',self.checkout)
        self.counter_search()
    def safe_event(self,fn): return lambda e:self.safe(fn)()
    def counter_search(self):
        self.fill(self.lookup,[(p['id'],p['sku'],p['name'],fmt(p['price']),p['sellable'],p['barcode'] or '') for p in self.store.inventory(self.search.get())])
    def scan(self):
        exact=self.store.rows('SELECT id FROM products WHERE active=1 AND (barcode=? OR sku=?)',(self.search.get(),self.search.get()))
        if len(exact)==1: self.add_cart_product(exact[0]['id']); self.search.set(''); self.counter_search()
        else: self.counter_search()
    def cart_add(self): self.add_cart_product(int(self.selected(self.lookup)[0]))
    def add_cart_product(self,pid):
        for item in self.cart:
            if item['product_id']==pid: item['quantity']+=1; break
        else: self.cart.append({'product_id':pid,'quantity':1})
        self.refresh_cart()
    def refresh_cart(self):
        rows=[]; total=0
        for item in self.cart:
            p=self.store.rows('SELECT * FROM products WHERE id=?',(item['product_id'],))[0]; subtotal=p['price']*item['quantity']; total+=subtotal
            rows.append((p['id'],p['name'],item['quantity'],fmt(p['price']),fmt(subtotal)))
        self.fill(self.cart_tree,rows); self.total_label.configure(text='Cart total PKR '+fmt(total)); self.cart_total=total
    def cart_quantity(self):
        pid=int(self.selected(self.cart_tree)[0])
        def save(v):
            q=integer(v['quantity'],1)
            for item in self.cart:
                if item['product_id']==pid: item['quantity']=q
            self.refresh_cart()
        self.form('Change quantity',[('quantity','Whole sale units',1)],save)
    def cart_remove(self):
        pid=int(self.selected(self.cart_tree)[0]); self.cart=[x for x in self.cart if x['product_id']!=pid]; self.refresh_cart()
    def cart_clear(self): self.cart=[]; self.refresh_cart()
    def checkout(self):
        if not self.cart: raise ValueError('Cart is empty')
        def save(v):
            ident=self.store.sell(self.cart,self.pickid(v['customer']),v['paid'],v['discount'])
            self.cart_clear(); self.refresh_all(); self.print_dialog(*reports.receipt(self.store,ident),self.store.get_setting('thermal','80mm'))
        self.form('Complete sale — enter amount applied, after giving change',[('customer','Customer (blank for walk-in)','',['']+self.parties_options('Customer')),('discount','Discount PKR','0.00'),('paid','Payment applied PKR (exact net total for walk-in)',f'{self.cart_total/100:.2f}')],save)
    def stock_ui(self):
        f=self.tabs['Stock']; bar=ttk.Frame(f); bar.pack(fill='x'); self.stock_search=tk.StringVar()
        ttk.Entry(bar,textvariable=self.stock_search).pack(side='left',padx=8); self.button(bar,'Refresh / search',self.refresh_stock); self.button(bar,'Batch details',self.batch_details)
        if self.store.user['role']=='Admin':
            self.button(bar,'Add medicine',lambda:self.product_form()); self.button(bar,'Edit medicine',lambda:self.product_form(int(self.selected(self.stock_tree)[0])))
            self.button(bar,'Excel template',self.export_template); self.button(bar,'Import opening stock',self.import_excel)
        self.stock_tree=self.table(f,['ID','SKU','Medicine','Category','Price PKR','Total stock','Sellable','Reorder','Alert']); self.refresh_stock()
    def refresh_stock(self): self.fill(self.stock_tree,[(p['id'],p['sku'],p['name'],p['category'],fmt(p['price']),p['stock'],p['sellable'],p['reorder'],'LOW / OUT' if p['sellable']<=p['reorder'] else '') for p in self.store.inventory(self.stock_search.get())])
    def product_form(self,pid=None):
        p=self.store.rows('SELECT * FROM products WHERE id=?',(pid,))[0] if pid else dict(sku='',name='',barcode='',category='',price=0,reorder=5)
        fields=[('sku','Unique SKU',p['sku']),('name','Medicine / unit name',p['name']),('barcode','Unique barcode (keep leading zeros)',p['barcode'] or ''),('category','Category',p['category']),('price','Selling price PKR',f"{p['price']/100:.2f}"),('reorder','Low stock threshold',p['reorder'])]
        def save(v): self.store.save_product(**v,product_id=pid); self.refresh_all()
        self.form('Medicine',fields,save)
    def batch_details(self):
        pid=int(self.selected(self.stock_tree)[0]); d=tk.Toplevel(self); d.title('Batch and expiry details'); d.geometry('960x450')
        t=self.table(d,['ID','Batch','Expiry','Remaining','Cost PKR','Status'])
        today=date.today(); soon=(today+timedelta(days=90)).isoformat()
        self.fill(t,[(b['id'],b['batch'],b['expiry'],b['quantity'],fmt(b['cost']),'EXPIRED' if b['expiry']<today.isoformat() else 'EXPIRING <=90 DAYS' if b['expiry']<=soon else 'Available') for b in self.store.rows('SELECT * FROM batches WHERE product_id=? ORDER BY expiry',(pid,))])
    def export_template(self):
        path=filedialog.asksaveasfilename(defaultextension='.xlsx',initialfile='opening-inventory.xlsx')
        if path: excel.template(path); messagebox.showinfo('Template saved','Enter one row per medicine batch. Format SKU and barcode cells as Text.')
    def import_excel(self):
        path=filedialog.askopenfilename(filetypes=[('Excel workbook','*.xlsx')])
        if not path: return
        rows,digest=excel.preview(path)
        d=tk.Toplevel(self); d.title('Review opening stock — no changes yet'); d.geometry('1100x600')
        t=self.table(d,['SKU','Medicine','Batch','Expiry','Qty','Price PKR','Cost PKR'])
        self.fill(t,[(r['sku'],r['name'],r['batch'],r['expiry'],r['quantity'],fmt(r['price']),fmt(r['cost'])) for r in rows])
        def apply():
            if messagebox.askyesno('Apply import',f'Create {len(rows)} opening-stock batches? Existing SKUs are rejected.',parent=d):
                excel.apply(self.store,rows,digest); d.destroy(); self.refresh_all()
        self.button(d,'Confirm import',apply)
    def party_ui(self,kind):
        f=self.tabs[kind+'s']; bar=ttk.Frame(f); bar.pack(fill='x'); self.button(bar,'Add '+kind,lambda:self.party_form(kind)); self.button(bar,'Refresh',lambda:self.refresh_parties(kind))
        if self.store.user['role']=='Admin': self.button(bar,'Record balance payment',lambda:self.party_payment(kind)); self.button(bar,'Statement',lambda:self.party_statement(kind))
        tree=self.table(f,['ID','Name','Phone','Address','Balance PKR']); setattr(self,kind+'_tree',tree); self.refresh_parties(kind)
    def refresh_parties(self,kind): self.fill(getattr(self,kind+'_tree'),[(p['id'],p['name'],p['phone'],p['address'],fmt(self.store.balance(p['id']))) for p in self.store.rows('SELECT * FROM parties WHERE kind=? ORDER BY name',(kind,))])
    def party_form(self,kind):
        def save(v): self.store.add_party(kind,**v); self.refresh_parties(kind)
        self.form('Add '+kind,[('name','Name',''),('phone','Phone',''),('address','Address','')],save)
    def party_payment(self,kind):
        pid=int(self.selected(getattr(self,kind+'_tree'))[0])
        def save(v): self.store.payment(pid,**v); self.refresh_all()
        self.form('Customer receipt' if kind=='Customer' else 'Supplier payment',[('amount','Payment PKR','0.00'),('note','Reference / note','')],save)
    def party_statement(self,kind):
        row=self.selected(getattr(self,kind+'_tree')); pid=int(row[0]); lines=[row[1],row[2],row[3],'All-time ledger:']
        if kind=='Customer':
            bills=self.store.rows("SELECT id,created,total,paid FROM sales WHERE customer_id=? AND status='Posted' ORDER BY id",(pid,))
        else: bills=self.store.rows('SELECT id,created,total,paid FROM purchases WHERE supplier_id=? ORDER BY id',(pid,))
        for b in bills: lines.append(f"Bill #{b['id']} {b['created']} | Total {fmt(b['total'])} | Paid {fmt(b['paid'])} | Due {fmt(b['total']-b['paid'])}")
        for p in self.store.rows('SELECT * FROM payments WHERE party_id=? ORDER BY id',(pid,)): lines.append(f"Payment {p['created']} | PKR {fmt(p['amount'])} | {p['note']}")
        lines.append('Outstanding PKR '+fmt(self.store.balance(pid))); self.print_dialog(kind+' statement',lines,'A4')
    def sales_ui(self):
        f=self.tabs['Sales']; bar=ttk.Frame(f); bar.pack(fill='x'); self.button(bar,'Refresh',self.refresh_sales); self.button(bar,'Reprint receipt',lambda:self.print_dialog(*reports.receipt(self.store,int(self.selected(self.sales_tree)[0])),self.store.get_setting('thermal','80mm')))
        if self.store.user['role']=='Admin': self.button(bar,'Void selected sale',self.void_sale)
        self.sales_tree=self.table(f,['ID','Date','Customer','Total PKR','Paid PKR','Status']); self.refresh_sales()
    def refresh_sales(self):
        where='' if self.store.user['role']=='Admin' else ' WHERE s.user_id=?'; args=() if not where else (self.store.user['id'],)
        self.fill(self.sales_tree,[(s['id'],s['created'],s['customer'],fmt(s['total']),fmt(s['paid']),s['status']) for s in self.store.rows("SELECT s.*,coalesce(p.name,'Walk-in') customer FROM sales s LEFT JOIN parties p ON p.id=s.customer_id"+where+' ORDER BY s.id DESC LIMIT 2000',args)])
    def void_sale(self):
        ident=int(self.selected(self.sales_tree)[0])
        if messagebox.askyesno('Void sale','Restore stock and reverse this entire sale? Handle any cash refund at the counter.'):
            self.store.void_sale(ident); self.refresh_all()
    def purchases_ui(self):
        f=self.tabs['Purchases']; bar=ttk.Frame(f); bar.pack(fill='x')
        self.button(bar,'Add batch to vendor bill',self.purchase_line_form); self.button(bar,'Remove batch',self.purchase_line_remove); self.button(bar,'Save vendor bill',self.purchase_checkout)
        self.purchase_cart_tree=self.table(f,['Line','Product ID','Batch','Expiry','Quantity','Cost PKR'])
        bar2=ttk.Frame(f); bar2.pack(fill='x'); self.button(bar2,'Refresh saved bills',self.refresh_purchases); self.button(bar2,'Print vendor bill',lambda:self.print_dialog(*reports.vendor_bill(self.store,int(self.selected(self.purchase_tree)[0])),'A4'))
        self.purchase_tree=self.table(f,['ID','Date','Supplier','Vendor reference','Total PKR','Paid PKR']); self.refresh_purchases()
    def purchase_line_form(self):
        def save(v):
            line=dict(product_id=self.pickid(v['product']),batch=v['batch'],expiry=v['expiry'],quantity=integer(v['quantity'],1),cost=v['cost']); money(line['cost'])
            self.purchase_lines.append(line); self.refresh_purchase_cart()
        self.form('Receive medicine batch',[('product','Medicine','',self.product_options()),('batch','Batch number',''),('expiry','Expiry YYYY-MM-DD (last valid day)',''),('quantity','Quantity in sale units',1),('cost','Unit cost PKR','0.00')],save)
    def refresh_purchase_cart(self): self.fill(self.purchase_cart_tree,[(i+1,x['product_id'],x['batch'],x['expiry'],x['quantity'],x['cost']) for i,x in enumerate(self.purchase_lines)])
    def purchase_line_remove(self): del self.purchase_lines[int(self.selected(self.purchase_cart_tree)[0])-1]; self.refresh_purchase_cart()
    def purchase_checkout(self):
        if not self.purchase_lines: raise ValueError('Add medicine batches first')
        total=sum(x['quantity']*money(x['cost']) for x in self.purchase_lines)
        def save(v):
            ident=self.store.purchase(self.pickid(v['supplier']),v['reference'],self.purchase_lines,v['paid']); self.purchase_lines=[]; self.refresh_purchase_cart(); self.refresh_all(); self.print_dialog(*reports.vendor_bill(self.store,ident),'A4')
        self.form('Save vendor bill — total PKR '+fmt(total),[('supplier','Supplier','',self.parties_options('Supplier')),('reference','Vendor invoice / reference',''),('paid','Amount paid PKR',f'{total/100:.2f}')],save)
    def refresh_purchases(self): self.fill(self.purchase_tree,[(p['id'],p['created'],p['name'],p['reference'],fmt(p['total']),fmt(p['paid'])) for p in self.store.rows('SELECT x.*,p.name FROM purchases x JOIN parties p ON p.id=x.supplier_id ORDER BY x.id DESC LIMIT 2000')])
    def expenses_ui(self):
        f=self.tabs['Expenses']; bar=ttk.Frame(f); bar.pack(fill='x'); self.button(bar,'Add expense',self.expense_form); self.button(bar,'Refresh',self.refresh_expenses)
        self.expense_tree=self.table(f,['ID','Date','Category','Note','Amount PKR']); self.refresh_expenses()
    def expense_form(self):
        def save(v): self.store.expense(**v); self.refresh_expenses()
        self.form('Expense',[('category','Category',''),('note','Description / reference',''),('amount','Amount PKR','0.00')],save)
    def refresh_expenses(self): self.fill(self.expense_tree,[(e['id'],e['created'],e['category'],e['note'],fmt(e['amount'])) for e in self.store.rows('SELECT * FROM expenses ORDER BY id DESC LIMIT 2000')])
    def reports_ui(self):
        f=self.tabs['Reports']; bar=ttk.Frame(f); bar.pack(fill='x'); self.start=tk.StringVar(value=date.today().replace(day=1).isoformat()); self.end=tk.StringVar(value=date.today().isoformat())
        for text,var in [('From YYYY-MM-DD',self.start),('To YYYY-MM-DD',self.end)]: ttk.Label(bar,text=text).pack(side='left',padx=6); ttk.Entry(bar,textvariable=var,width=14).pack(side='left')
        self.button(bar,'View / print report',lambda:self.print_dialog(*reports.report(self.store,self.start.get(),self.end.get()),'A4'))
        ttk.Label(f,text='Report includes sales, cost of goods, profit, expenses, recorded cash movement,\ncurrent inventory and customer/supplier balances. All amounts are in PKR.',padding=24).pack(anchor='w')
    def admin_ui(self):
        f=self.tabs['Administration']; bar=ttk.Frame(f); bar.pack(fill='x')
        self.button(bar,'New user',self.user_form); self.button(bar,'Change my password',self.password_form); self.button(bar,'Business / printing settings',self.settings_form)
        bar2=ttk.Frame(f); bar2.pack(fill='x'); self.button(bar2,'Create backup',self.backup); self.button(bar2,'Restore backup',self.restore); self.button(bar2,'Refresh audit',self.refresh_audit)
        ttk.Label(f,text='Data folder: '+str(self.store.path.parent)+'\nLAN clients are not enabled in this release. Keep this database on a local disk.',padding=8).pack(anchor='w')
        self.audit_tree=self.table(f,['ID','Date','User ID','Action','Detail']); self.refresh_audit()
    def user_form(self):
        def save(v): self.store.add_user(**v); self.refresh_audit()
        self.form('New account',[('username','Username',''),('password','Password (10+ characters)',''),('role','Role','Cashier',['Cashier','Admin'])],save)
    def password_form(self): self.form('Change password',[('old','Current password',''),('new','New password (10+ characters)','')],lambda v:self.store.change_password(**v))
    def settings_form(self):
        keys=[('name','Pharmacy name','Pharmacy'),('address','Business address',''),('phone','Phone',''),('footer','Receipt footer','Thank you'),('thermal','Thermal roll','80mm'),('thermal_printer','Thermal printer',''),('a4_printer','A4 printer','')]
        choices=printing.printers()
        fields=[]
        for key,label,default in keys:
            field=(key,label,self.store.get_setting(key,default))
            if key=='thermal': field+=(['58mm','80mm'],)
            if key.endswith('_printer'): field+=(['']+choices,)
            fields.append(field)
        self.form('Business and printer settings',fields,lambda v:self.store.settings(v))
    def backup(self):
        path=filedialog.asksaveasfilename(defaultextension='.sqlite3',initialfile='pharmacy-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite3')
        if path: self.store.backup(path); messagebox.showinfo('Backup complete','Keep this backup on a separate drive. It includes all records and accounts.')
    def restore(self):
        path=filedialog.askopenfilename(filetypes=[('Pharmacy backup','*.sqlite3')])
        if path and messagebox.askyesno('Replace current database','Restore ALL records and logins from this backup? An automatic safety backup will be saved first. Sign in using the restored account afterwards.'):
            self.store.restore(path); self.login_screen()
    def refresh_audit(self): self.fill(self.audit_tree,[(a['id'],a['created'],a['user_id'],a['action'],a['detail']) for a in self.store.rows('SELECT * FROM audit ORDER BY id DESC LIMIT 1000')])
    def refresh_all(self):
        self.refresh_stock(); self.counter_search(); self.refresh_sales(); self.refresh_parties('Customer')
        if self.store.user['role']=='Admin': self.refresh_parties('Supplier'); self.refresh_purchases(); self.refresh_expenses(); self.refresh_audit()
    def print_dialog(self,title,lines,paper):
        d=tk.Toplevel(self); d.title(title); d.geometry('850x650'); d.transient(self)
        text=tk.Text(d,wrap='word',font=('Consolas',11)); text.pack(fill='both',expand=True,padx=12,pady=12); text.insert('1.0','\n'.join(lines)); text.configure(state='disabled')
        bar=ttk.Frame(d); bar.pack(fill='x'); paper_var=tk.StringVar(value=paper)
        ttk.Combobox(bar,textvariable=paper_var,values=['A4','58mm','80mm'],state='readonly',width=8).pack(side='left',padx=8)
        options=printing.printers(); default=self.store.get_setting('a4_printer' if paper=='A4' else 'thermal_printer')
        printer=tk.StringVar(value=default if default in options else (options[0] if options else ''))
        ttk.Combobox(bar,textvariable=printer,values=options,state='readonly',width=35).pack(side='left')
        def native():
            if not printer.get(): raise ValueError('Select an installed Windows printer')
            printing.print_native(printer.get(),title,lines,paper_var.get())
        def export():
            path=filedialog.asksaveasfilename(defaultextension='.pdf',initialfile=title.lower().replace(' ','-')+'.pdf',parent=d)
            if path: printing.pdf(path,title,lines,paper_var.get()); messagebox.showinfo('PDF saved',path,parent=d)
        self.button(bar,'Print',native); self.button(bar,'Save PDF',export)

def main():
    # Acquire process lock before opening or initializing the database.
    folder=data_directory(); folder.mkdir(parents=True,exist_ok=True)
    lock=open(folder/'workstation.lock','a+b')
    try:
        if os.name=='nt':
            import msvcrt
            lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        root=tk.Tk(); root.withdraw(); messagebox.showerror('Already running','Pharmacy Desktop is already open for this Windows user.'); root.destroy(); return
    try:
        store=Store(); App(store).mainloop()
    finally: lock.close()
