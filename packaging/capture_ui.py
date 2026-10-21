"""Native screenshots and interaction checks, only in disposable test databases."""
import tempfile,sys,json,time
from pathlib import Path
from datetime import date,timedelta
from PIL import ImageGrab
from tkinter import font as tkfont
from pharmacy.core import Store
from pharmacy.app import App
from pharmacy import branding

def capture(app,path):
    app.update(); app.lift(); app.update_idletasks(); time.sleep(.15); app.update()
    x,y=app.winfo_rootx(),app.winfo_rooty()
    image=ImageGrab.grab(bbox=(x,y,x+app.winfo_width(),y+app.winfo_height())); image.save(path)
    path=Path(path); info_path=path.parent/'render-info.json'; info=json.loads(info_path.read_text()) if info_path.exists() else {}
    family=getattr(app,'font_family',getattr(app.master,'font_family','Segoe UI'))
    info[path.name]={'client':[app.winfo_width(),app.winfo_height()],'image_pixels':list(image.size),'tk_scaling':float(app.tk.call('tk','scaling')),'font':tkfont.Font(root=app,font=(family,11)).actual(),'screen':[app.winfo_screenwidth(),app.winfo_screenheight()]}
    info_path.write_text(json.dumps(info,indent=2))

def prepare_display():
    if sys.platform!='win32': return
    import win32api,win32con,pywintypes
    current=win32api.EnumDisplaySettings(None,win32con.ENUM_CURRENT_SETTINGS)
    if current.PelsWidth>=1600 and current.PelsHeight>=1080: return
    modes=[]
    for index in range(500):
        try: mode=win32api.EnumDisplaySettings(None,index)
        except pywintypes.error: break
        if mode.PelsWidth>=1600 and mode.PelsHeight>=1080: modes.append(mode)
    if modes:
        mode=min(modes,key=lambda m:m.PelsWidth*m.PelsHeight)
        win32api.ChangeDisplaySettings(mode,0)

def run(folder):
    prepare_display()
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        s=Store(Path(temp)/'visual.sqlite3')
        app=None
        try:
            s.setup('Admin','visual-password'); s.login('Admin','visual-password')
            app=App(s); app.geometry('1440x1024+0+0'); app.update(); s.login('Admin','visual-password'); app.main(); app.update()
            vendor=s.add_party('Supplier','Sample supplier')
            products=[('PAN-500','Paracetamol 500mg tablet','12.50',1240),('CET-10','Cetirizine 10mg strip','120.00',320),('AMX-500','Amoxicillin 500mg capsule','75.00',88),('OMP-20','Omeprazole 20mg capsule','35.00',450),('MET-500','Metformin 500mg tablet','18.00',620),('AML-5','Amlodipine 5mg tablet','22.00',210)]
            ids=[]
            for sku,name,price,qty in products:
                pid=s.save_product(sku,name,sku,'Medicine',price,'100'); ids.append(pid)
                s.purchase(vendor,sku,[dict(product_id=pid,batch='DEMO',expiry=(date.today()+timedelta(days=365)).isoformat(),quantity=qty,cost='1')],'0')
            app.cart=[dict(product_id=ids[0],quantity=10),dict(product_id=ids[1],quantity=2)]; app.refresh_cart(); app.refresh_all(); app.tender_var.set('365.00'); app.update()
            capture(app,folder/'counter-1440.png')
            app.update(); assert app.add_buttons, 'Medicine Add controls must be visible'
            app.add_buttons[0].invoke(); assert len(app.cart)==3; app.cart_remove_id(ids[-1])
            # Exercise scan, quantity, change calculation, persisted checkout and clearing.
            app.search.set('PAN-500'); app.scan(); assert app.cart[0]['quantity']==11
            app.cart_adjust(ids[0],-1); app.tender_var.set('500.00'); assert app.change_var.get()=='135.00'
            app.search.set(''); app.tender_var.set('365.00')
            original_print=app.print_dialog; recorded=[]; app.print_dialog=lambda *args:recorded.append(args)
            app.checkout(); assert s.scalar('SELECT count(*) FROM sales')==1; assert not app.cart; assert recorded
            app.print_dialog=original_print
            app.cart=[dict(product_id=ids[0],quantity=10),dict(product_id=ids[1],quantity=2)]; app.refresh_cart(); app.tender_var.set('365.00')
            app.geometry('1080x680+0+0'); app.update()
            app.cart_lines.winfo_children()[0].event_generate('<MouseWheel>',delta=-120); app.update(); assert app.cart_canvas.yview()[0]>0, 'Cart scroll must work over child controls'
            app.cart_canvas.yview_moveto(0); app.update(); capture(app,folder/'counter-1080.png')
            assert app.cart_canvas.winfo_height()>=80, 'Cart needs a visible editable line at minimum viewport'
            assert app.complete_button.winfo_rooty()+app.complete_button.winfo_height() <= app.winfo_rooty()+app.winfo_height()
            app.geometry('1440x1024+0+0'); app.update()
            dialog=app.company_profile(); dialog.geometry('700x800+300+60'); app.update(); capture(dialog,folder/'company-profile.png')
            from tkinter import filedialog,ttk
            def buttons(widget):
                found=[]
                for child in widget.winfo_children():
                    if isinstance(child,ttk.Button): found.append(child)
                    found+=buttons(child)
                return found
            before=list(map(dict,app.cart)); original_picker=filedialog.askopenfilename
            try:
                from pharmacy.theme import asset
                filedialog.askopenfilename=lambda **kwargs:str(asset('company-default.png'))
                next(b for b in buttons(dialog) if b.cget('text')=='Replace logo').invoke()
                next(b for b in buttons(dialog) if b.cget('text')=='Save company profile').invoke()
                assert branding.logo_bytes(s); assert app.cart==before
            finally: filedialog.askopenfilename=original_picker
            capture(app,folder/'branded-header.png')
            for page in ('Stock','Purchases','Reports','Administration'):
                app.show_page(page); app.update(); capture(app,folder/(page.lower()+'.png'))
            s.add_user('cashier','cashier-password','Cashier'); s.login('cashier','cashier-password'); app.main(); app.update(); assert len(app.tabs)==4
            capture(app,folder/'cashier-empty.png'); app.login_screen(); app.update(); capture(app,folder/'sign-in.png')
        finally:
            if app is not None:
                try: app.destroy()
                except Exception: pass
            s.close()
    (folder/'interaction-checks.json').write_text(json.dumps({'ok':True,'checks':['Visible Add button','Logo picker and profile save preserve cart','Barcode scan','Cart wheel scrolling','Cart quantity change','Cash change calculation','Complete sale creates one invoice','Cart clears after commit','Minimum viewport payment controls visible','Company profile dialog','Cashier navigation','Sign-in screen']},indent=2))
if __name__=='__main__': run(sys.argv[1] if len(sys.argv)>1 else 'build/screenshots')
