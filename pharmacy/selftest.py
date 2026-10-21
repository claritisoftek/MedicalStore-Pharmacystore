"""Frozen Windows smoke check, using a disposable database and no print jobs."""
import json,tempfile,traceback
from pathlib import Path
from datetime import date,timedelta

def run(output):
    result={'ok':False,'checks':[]}
    try:
        from .core import Store
        from .app import App
        from . import printing,excel,reports
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); s=Store(root/'smoke.sqlite3')
            s.setup('smoke','smoke-password'); s.login('smoke','smoke-password')
            app=App(s); app.withdraw(); s.login('smoke','smoke-password'); app.main(); app.update_idletasks()
            assert len(app.tabs)==9
            result['checks'].append('Admin desktop tabs initialize')
            p=s.save_product('T','Smoke medicine','0001','','10','2'); v=s.add_party('Supplier','Smoke vendor')
            s.purchase(v,'SMOKE',[dict(product_id=p,batch='B',expiry=(date.today()+timedelta(days=30)).isoformat(),quantity=10,cost='4')],'40')
            app.add_cart_product(p); app.refresh_all()
            sale=s.sell([dict(product_id=p,quantity=1)],paid='10')
            title,lines=reports.receipt(s,sale)
            for paper in ('58mm','80mm','A4'): printing.pdf(root/(paper+'.pdf'),title,lines,paper)
            excel.template(root/'template.xlsx'); printing.printers()
            result['checks'].append('Bundled Excel, PDF and Windows printer modules load')
            s.add_user('cashier','cashier-password','Cashier'); s.login('cashier','cashier-password'); app.main(); app.update_idletasks()
            assert len(app.tabs)==4
            result['checks'].append('Cashier desktop tabs initialize')
            app.shutdown()
        result['ok']=True
    except Exception: result['error']=traceback.format_exc()
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return 0 if result['ok'] else 1
