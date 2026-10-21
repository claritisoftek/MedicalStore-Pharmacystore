import unittest, tempfile, sqlite3
from pathlib import Path
from datetime import date,timedelta
from openpyxl import Workbook
from pharmacy.core import Store, money
from pharmacy import excel,reports,printing

class Workflows(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.s=Store(self.root/'test.sqlite3'); self.s.setup('owner','strong-password'); self.s.login('owner','strong-password')
        self.p=self.s.save_product('M001','Test medicine','001234','Tablets','12.50','5')
        self.vendor=self.s.add_party('Supplier','Vendor'); self.customer=self.s.add_party('Customer','Customer')
        self.expiry=(date.today()+timedelta(days=365)).isoformat()
    def tearDown(self): self.s.close(); self.temp.cleanup()
    def receive(self,q=10,cost='5.00',paid='0',batch='B1',expiry=None):
        return self.s.purchase(self.vendor,'INV-01',[dict(product_id=self.p,batch=batch,expiry=expiry or self.expiry,quantity=q,cost=cost)],paid)
    def test_empty_database_no_samples(self):
        with StoreContext(self.root/'empty.sqlite3') as s:
            for table in ['users','products','batches','sales','parties','purchases','expenses']: self.assertEqual(s.scalar('SELECT count(*) FROM '+table),0)
    def test_money_exact(self):
        self.assertEqual(money('1.01'),101)
        for bad in ['NaN','Infinity','-1','2.001']:
            with self.assertRaises(ValueError): money(bad)
    def test_full_purchase_sale_balances_and_profit(self):
        self.receive(paid='10')
        sale=self.s.sell([dict(product_id=self.p,quantity=3)],self.customer,'20','2.50')
        self.assertEqual(self.s.inventory()[0]['stock'],7)
        self.assertEqual(self.s.balance(self.customer),1500)
        self.assertEqual(self.s.balance(self.vendor),4000)
        self.s.payment(self.customer,'15','received'); self.s.payment(self.vendor,'10','paid')
        self.assertEqual(self.s.balance(self.customer),0); self.assertEqual(self.s.balance(self.vendor),3000)
        self.s.expense('Rent','daily','3')
        title,lines=reports.report(self.s,date.today().isoformat(),date.today().isoformat())
        self.assertIn('Gross profit: PKR 20.00',lines)
        self.assertIn('Operating result (before taxes/other adjustments): PKR 17.00',lines)
        self.assertIn('Net recorded cash movement: PKR 12.00',lines)
        self.assertIn('TOTAL PKR 35.00',reports.receipt(self.s,sale)[1])
    def test_sale_rollback_when_later_line_fails(self):
        self.receive(); p2=self.s.save_product('M2','No stock','','','1','0')
        with self.assertRaises(ValueError): self.s.sell([dict(product_id=self.p,quantity=2),dict(product_id=p2,quantity=1)],paid='26')
        self.assertEqual(self.s.inventory('M001')[0]['stock'],10); self.assertEqual(self.s.scalar('SELECT count(*) FROM sales'),0)
    def test_earliest_expiry_and_duplicate_cart_lines(self):
        late=self.receive(q=4,batch='LATE'); early_date=(date.today()+timedelta(days=20)).isoformat(); self.receive(q=3,batch='EARLY',expiry=early_date)
        ident=self.s.sell([dict(product_id=self.p,quantity=2),dict(product_id=self.p,quantity=3)],paid='62.50')
        self.assertEqual(self.s.rows('SELECT quantity FROM batches WHERE batch=?',('EARLY',))[0]['quantity'],0)
        self.assertEqual(self.s.rows('SELECT quantity FROM batches WHERE batch=?',('LATE',))[0]['quantity'],2)
        self.assertEqual(self.s.scalar('SELECT count(*) FROM sale_lines WHERE sale_id=?',(ident,)),2)
    def test_expired_stock_blocked(self):
        self.receive(); self.s.db.execute("UPDATE batches SET expiry='2000-01-01'")
        with self.assertRaises(ValueError): self.s.sell([dict(product_id=self.p,quantity=1)],paid='12.50')
        self.assertEqual(self.s.inventory()[0]['sellable'],0)
    def test_expired_purchase_and_invalid_discount_blocked(self):
        with self.assertRaises(ValueError): self.receive(expiry='2000-01-01')
        self.receive()
        with self.assertRaises(ValueError): self.s.sell([dict(product_id=self.p,quantity=1)],paid='0',discount='20')
        self.assertEqual(self.s.inventory()[0]['stock'],10)
    def test_walk_in_cannot_have_credit_or_overpay(self):
        self.receive()
        for amount in ['10','15']:
            with self.assertRaises(ValueError): self.s.sell([dict(product_id=self.p,quantity=1)],paid=amount)
    def test_supplier_overpayment_rejected(self):
        self.receive()
        with self.assertRaises(ValueError): self.s.payment(self.vendor,'51','bad')
        self.assertEqual(self.s.balance(self.vendor),5000)
    def test_void_reverses_stock_and_credit_once(self):
        self.receive(); ident=self.s.sell([dict(product_id=self.p,quantity=2)],self.customer,'0')
        self.s.void_sale(ident)
        self.assertEqual(self.s.inventory()[0]['stock'],10); self.assertEqual(self.s.balance(self.customer),0)
        with self.assertRaises(ValueError): self.s.void_sale(ident)
    def test_void_after_balance_receipt_blocked(self):
        self.receive(); ident=self.s.sell([dict(product_id=self.p,quantity=2)],self.customer,'0'); self.s.payment(self.customer,'1','partial')
        with self.assertRaises(ValueError): self.s.void_sale(ident)
    def test_historical_void_blocked(self):
        self.receive(); ident=self.s.sell([dict(product_id=self.p,quantity=1)],paid='12.50')
        self.s.db.execute("UPDATE sales SET created='2000-01-01T12:00:00' WHERE id=?",(ident,))
        with self.assertRaises(ValueError): self.s.void_sale(ident)
        self.assertEqual(self.s.inventory()[0]['stock'],9)
    def test_cashier_permissions(self):
        self.s.add_user('cashier','cashier-password','Cashier'); self.receive(); self.s.login('cashier','cashier-password')
        self.s.sell([dict(product_id=self.p,quantity=1)],paid='12.50')
        for op in [lambda:self.s.save_product('x','x','','','0','0'),lambda:self.s.backup(self.root/'no.sqlite3'),lambda:reports.report(self.s,'2020-01-01','2030-01-01'),lambda:self.s.expense('x','x','1'),lambda:self.receive(),lambda:self.s.settings({'name':'x'})]:
            with self.assertRaises(PermissionError): op()
    def test_password_change_and_failed_login_clears_session(self):
        self.s.change_password('strong-password','new-password')
        with self.assertRaises(ValueError): self.s.login('owner','strong-password')
        self.assertIsNone(self.s.user); self.s.login('owner','new-password')
    def test_backup_restore_safety_and_reauthentication(self):
        self.receive(); target=self.root/'backup.sqlite3'; self.s.backup(target)
        self.s.sell([dict(product_id=self.p,quantity=1)],paid='12.50'); self.s.restore(target)
        self.assertIsNone(self.s.user); self.s.login('owner','strong-password'); self.assertEqual(self.s.inventory()[0]['stock'],10)
        self.assertEqual(len(list(self.root.glob('before-restore-*.sqlite3'))),1)
        with self.assertRaises(ValueError): self.s.backup(target)
    def test_invalid_restore_leaves_current_database(self):
        invalid=self.root/'invalid.sqlite3'; sqlite3.connect(invalid).close()
        with self.assertRaises(sqlite3.DatabaseError): self.s.restore(invalid)
        self.assertEqual(self.s.inventory()[0]['sku'],'M001')
    def make_book(self,rows):
        path=self.root/'import.xlsx'; w=Workbook(); w.active.append(excel.HEADERS)
        for row in rows: w.active.append(row)
        w.save(path); return path
    def test_excel_valid_preview_apply_and_duplicate(self):
        path=self.make_book([['M002','Imported','000111','Tablets','10.25',5,'A',self.expiry,8,'4.50'],['M002','Imported','000111','Tablets','10.25',5,'B',self.expiry,7,'5.00']])
        clean,digest=excel.preview(path); self.assertEqual(self.s.scalar('SELECT count(*) FROM batches'),0)
        excel.apply(self.s,clean,digest); self.assertEqual(self.s.inventory('M002')[0]['stock'],15)
        with self.assertRaises(ValueError): excel.apply(self.s,clean,digest)
    def test_excel_errors_no_partial_import(self):
        path=self.make_book([['M002','Imported','000111','','10.25',5,'A',self.expiry,8,'4.50'],['M003','Invalid','000222','','10.25',5,'B',self.expiry,-1,'4.50']])
        with self.assertRaises(ValueError): excel.preview(path)
        self.assertEqual(self.s.scalar('SELECT count(*) FROM batches'),0)
    def test_excel_conflicting_barcode_transaction_rollback(self):
        path=self.make_book([['M002','Imported','000111','','10',5,'A',self.expiry,8,'4'],['M003','Conflict','001234','','10',5,'B',self.expiry,8,'4']])
        clean,digest=excel.preview(path)
        with self.assertRaises(sqlite3.IntegrityError): excel.apply(self.s,clean,digest)
        self.assertEqual(self.s.scalar('SELECT count(*) FROM products'),1); self.assertEqual(self.s.scalar('SELECT count(*) FROM batches'),0)
    def test_excel_formulas_rejected(self):
        path=self.make_book([['M002','=1+2','000111','','10',5,'A',self.expiry,8,'4']])
        with self.assertRaises(ValueError): excel.preview(path)
    def test_pdf_all_sizes(self):
        self.receive(); ident=self.s.sell([dict(product_id=self.p,quantity=1)],paid='12.50')
        title,lines=reports.receipt(self.s,ident)
        for paper in ['A4','58mm','80mm']:
            path=self.root/(paper+'.pdf'); printing.pdf(path,title,lines,paper); self.assertTrue(path.read_bytes().startswith(b'%PDF'))
    def test_purchase_atomic_failure_and_reference_required(self):
        with self.assertRaises(ValueError): self.s.purchase(self.vendor,'',[dict(product_id=self.p,batch='x',expiry=self.expiry,quantity=1,cost='1')],'0')
        self.assertEqual(self.s.scalar('SELECT count(*) FROM purchases'),0)

class StoreContext:
    def __init__(self,path): self.store=Store(path)
    def __enter__(self): return self.store
    def __exit__(self,*args): self.store.close()
if __name__=='__main__': unittest.main()
