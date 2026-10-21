"""Tk desktop UI. All writes pass through Store authorization/transaction methods."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import date, datetime, timedelta
import os, traceback
from .core import Store, fmt, money, integer, data_directory
from . import excel, printing, reports, branding, theme
from PIL import Image, ImageTk
from io import BytesIO

class App(tk.Tk):
    def __init__(self,store):
        super().__init__(); self.store=store; self.title('Pharmacy Desktop — 0.2.0'); self.geometry(f'{min(1440,max(1080,self.winfo_screenwidth()-40))}x{min(940,max(680,self.winfo_screenheight()-100))}+20+10'); self.minsize(1080,680)
        self.style=theme.configure(self); self.images={}; self.checkout_busy=False
        self.app_icon=self.image('pharmacy-icon.png',(64,64)); self.iconphoto(True,self.app_icon)
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
    def image(self,name,size=(22,22),raw=None):
        key=(name,size,hash(raw) if raw else None)
        if key not in self.images: self.images[key]=theme.photo(self,name,size,raw)
        return self.images[key]
    def button(self,parent,label,callback,primary=False,icon=None):
        kwargs={'image':self.image('icons/'+icon+'.png'),'compound':'left'} if icon else {}
        b=ttk.Button(parent,text=label,command=self.safe(callback),style='Primary.TButton' if primary else 'TButton',**kwargs)
        b.pack(side='left',padx=4,pady=6); return b
    def heading(self,parent,title,description=''):
        frame=ttk.Frame(parent,padding=(12,12,12,10)); frame.pack(fill='x')
        ttk.Label(frame,text=title,font=(self.font_family,23,'bold'),foreground=theme.GREEN).pack(anchor='w')
        if description: ttk.Label(frame,text=description,style='Muted.TLabel').pack(anchor='w',pady=(6,0))
    def login_screen(self):
        self.clear(); self.store.user=None
        for key in ('<F2>','<F3>','<F5>'): self.unbind(key)
        first=self.store.scalar('SELECT count(*) FROM users')==0
        frame=ttk.Frame(self,padding=36); frame.place(relx=.5,rely=.47,anchor='center')
        ttk.Label(frame,image=self.app_icon).pack(pady=(0,14))
        ttk.Label(frame,text='Pharmacy Desktop',font=(self.font_family,27,'bold'),foreground=theme.GREEN).pack(pady=8)
        ttk.Label(frame,text=self.store.get_setting('name','Dispense with care'),style='Muted.TLabel').pack(pady=(0,18))
        ttk.Label(frame,text='Create your administrator account' if first else 'Welcome back. Sign in to your workstation.',font=(self.font_family,11)).pack(pady=10)
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
        login=ttk.Button(frame,text='Create account' if first else 'Sign in',command=self.safe(submit),style='Primary.TButton'); login.pack(pady=15)
        self.bind('<Return>',lambda e: login.invoke())
    def form(self,title,fields,callback):
        """fields: (key,label,default[, choices]). Choice labels start with database ID."""
        d=tk.Toplevel(self); d.title(title); d.transient(self); d.grab_set(); d.geometry('620x'+str(min(820,120+len(fields)*70)))
        content=ttk.Frame(d,padding=22); content.pack(fill='both',expand=True); values={}
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
        self.header=ttk.Frame(self,padding=(24,8)); self.header.pack(fill='x')
        app_brand=ttk.Frame(self.header); app_brand.pack(side='left')
        ttk.Label(app_brand,image=self.image('pharmacy-icon.png',(50,50))).pack(side='left',padx=(0,12))
        name=ttk.Frame(app_brand); name.pack(side='left')
        ttk.Label(name,text='Pharmacy Desktop',font=(self.font_family,17,'bold')).pack(anchor='w')
        ttk.Label(name,text='Dispense with care',style='Muted.TLabel').pack(anchor='w',pady=(4,0))
        actions=ttk.Frame(self.header); actions.pack(side='right')
        self.button(actions,self.store.user['username'],self.account_menu,icon='user')
        if self.store.user['role']=='Admin': self.button(actions,'Company profile',self.company_profile,icon='building-store')
        self.company_header=ttk.Frame(self.header); self.company_header.pack(side='left',expand=True,fill='x',padx=30)
        self.refresh_header()
        self.nav=tk.Frame(self,background=theme.NAV,height=48); self.nav.pack(fill='x'); self.nav.pack_propagate(False)
        self.body=ttk.Frame(self,padding=(16,8))
        self.tabs={}; self.nav_buttons={}
        names=['Counter','Stock','Customers','Sales']
        if self.store.user['role']=='Admin': names+=['Purchases','Suppliers','Expenses','Reports','Administration']
        self.body.rowconfigure(0,weight=1); self.body.columnconfigure(0,weight=1)
        for name in names:
            f=ttk.Frame(self.body); f.grid(row=0,column=0,sticky='nsew'); self.tabs[name]=f
            button=tk.Button(self.nav,text=name,command=lambda n=name:self.show_page(n),background=theme.NAV,foreground=theme.INK,activebackground=theme.SAGE,activeforeground=theme.GREEN,relief='flat',borderwidth=0,highlightthickness=0,font=(self.font_family,10),cursor='hand2',takefocus=True)
            button.pack(side='left',fill='both',expand=True); self.nav_buttons[name]=button
        self.counter_ui(); self.stock_ui(); self.party_ui('Customer'); self.sales_ui()
        if 'Purchases' in self.tabs:
            self.purchases_ui(); self.party_ui('Supplier'); self.expenses_ui(); self.reports_ui(); self.admin_ui()
        ttk.Separator(self).pack(side='bottom',fill='x')
        self.footer=ttk.Frame(self,padding=(24,7)); self.footer.pack(side='bottom',fill='x')
        ttk.Label(self.footer,image=self.image('icons/database.png',(18,18))).pack(side='left',padx=(0,10))
        self.backup_status=ttk.Label(self.footer,style='Muted.TLabel'); self.backup_status.pack(side='left')
        ttk.Label(self.footer,text='F2  Search     F3  Add medicine     F5  Complete sale',style='Muted.TLabel').pack(side='right')
        self.body.pack(fill='both',expand=True); self.refresh_backup_status(); self.show_page('Counter')
        self.bind('<F2>',self.safe_event(self.focus_search)); self.bind('<F3>',self.safe_event(self.cart_add)); self.bind('<F5>',self.safe_event(self.checkout))
    def short_text(self,text,length):
        return text if len(text)<=length else text[:length-1]+'…'
    def refresh_header(self):
        for child in self.company_header.winfo_children(): child.destroy()
        raw=branding.logo_bytes(self.store)
        logo=self.image('company-default.png',(48,48),raw)
        company=ttk.Frame(self.company_header); company.pack(anchor='center')
        ttk.Label(company,image=logo).pack(side='left',padx=(0,10))
        text=ttk.Frame(company); text.pack(side='left',fill='x',expand=True)
        ttk.Label(text,text=self.short_text(self.store.get_setting('name','Your pharmacy'),40),font=(self.font_family,16,'bold'),foreground=theme.GREEN,wraplength=320).pack(anchor='w')
        ttk.Label(text,text=self.short_text(self.store.get_setting('tagline','Healthier people. Brighter days.'),60),style='Muted.TLabel',wraplength=320).pack(anchor='w',pady=(4,0))
    def refresh_backup_status(self):
        last=self.store.rows("SELECT created FROM audit WHERE action='Backup' ORDER BY id DESC LIMIT 1")
        self.backup_status.configure(text='Local database  |  Last backup: '+(last[0]['created'].replace('T',' ') if last else 'Not yet created'))
    def account_menu(self):
        menu=tk.Menu(self,tearoff=0); menu.add_command(label='Change my password',command=self.safe(self.password_form)); menu.add_separator(); menu.add_command(label='Sign out',command=self.safe(self.login_screen)); menu.tk_popup(self.winfo_pointerx(),self.winfo_pointery())
    def show_page(self,name):
        self.tabs[name].tkraise(); self.current_page=name
        for n,b in self.nav_buttons.items(): b.configure(background=theme.SAGE if n==name else theme.NAV,foreground=theme.GREEN if n==name else theme.INK,font=(self.font_family,10,'bold' if n==name else 'normal'))
    def focus_search(self):
        self.show_page('Counter'); self.search_entry.focus_set(); self.search_entry.selection_range(0,'end')
    def counter_ui(self):
        f=self.tabs['Counter']; f.columnconfigure(0,weight=62); f.columnconfigure(2,weight=38); f.rowconfigure(0,weight=1)
        left=ttk.Frame(f,padding=(12,12,24,8)); left.grid(row=0,column=0,sticky='nsew')
        ttk.Separator(f,orient='vertical').grid(row=0,column=1,sticky='ns',padx=(0,4))
        right=ttk.Frame(f,padding=(20,12,12,8)); right.grid(row=0,column=2,sticky='nsew')
        self.counter_title=ttk.Label(left,text='Ready for the next customer',font=(self.font_family,28,'bold'),foreground=theme.GREEN)
        self.counter_title.pack(anchor='w',pady=(8,10)); left.bind('<Configure>',lambda e:self.counter_title.configure(wraplength=max(250,e.width-38)))
        ttk.Label(left,text='Scan a barcode or search the medicine list',style='Muted.TLabel',font=(self.font_family,11)).pack(anchor='w',pady=(0,22))
        searchbar=ttk.Frame(left); searchbar.pack(fill='x',pady=(0,20))
        ttk.Label(searchbar,image=self.image('icons/search.png')).pack(side='left',padx=(0,8))
        self.search=tk.StringVar(); self.search_entry=ttk.Entry(searchbar,textvariable=self.search,font=(self.font_family,11)); self.search_entry.pack(side='left',fill='x',expand=True)
        self.search_hint=ttk.Label(searchbar,text='Search by name, SKU or barcode',foreground=theme.MUTED,background=theme.WHITE,font=(self.font_family,11))
        self.search_hint.place(in_=self.search_entry,x=10,rely=.5,anchor='w'); self.search_hint.bind('<Button-1>',lambda e:self.search_entry.focus_set())
        self.search_entry.bind('<FocusIn>',lambda e:self.search_hint.place_forget()); self.search_entry.bind('<FocusOut>',lambda e:self.update_search_hint())
        self.search_entry.bind('<Return>',self.safe_event(self.scan)); self.search.trace_add('write',lambda *a:self.counter_search())
        self.button(searchbar,'Clear',lambda:self.search.set(''))
        table_holder=ttk.Frame(left); table_holder.pack(fill='both',expand=True)
        self.lookup=ttk.Treeview(table_holder,columns=('ID','Medicine','SKU','In stock','PKR price','Add'),displaycolumns=('Medicine','SKU','In stock','PKR price','Add'),show='tree headings',selectmode='browse',style='Counter.Treeview')
        self.lookup.column('#0',width=48,minwidth=48,stretch=False); self.lookup.heading('#0',text='')
        for name,width,anchor in [('Medicine',220,'w'),('SKU',105,'w'),('In stock',74,'e'),('PKR price',84,'e'),('Add',50,'center')]:
            self.lookup.heading(name,text=name,anchor=anchor); self.lookup.column(name,width=width,minwidth=width if name!='Medicine' else 160,anchor=anchor,stretch=name=='Medicine')
        self.lookup.pack(side='left',fill='both',expand=True); self.lookup.tag_configure('low',foreground=theme.AMBER)
        self.add_buttons=[]
        def scroll(*args): self.lookup.yview(*args); self.after_idle(self.draw_add_buttons)
        scrollbar=ttk.Scrollbar(table_holder,orient='vertical',command=scroll); scrollbar.pack(side='right',fill='y'); self.lookup.configure(yscrollcommand=scrollbar.set)
        for event in ('<Configure>','<MouseWheel>','<Button-4>','<Button-5>','<KeyRelease>'): self.lookup.bind(event,lambda e:self.after_idle(self.draw_add_buttons),add='+')
        self.lookup.bind('<Double-1>',self.safe_event(self.cart_add)); self.lookup.bind('<ButtonRelease-1>',self.counter_click)
        self.empty_stock=ttk.Label(left,text='',style='Muted.TLabel',padding=(8,10)); self.empty_stock.pack(anchor='w')
        top=ttk.Frame(right); top.pack(fill='x',pady=(7,16)); ttk.Label(top,text='Current sale',font=(self.font_family,20,'bold'),foreground=theme.GREEN).pack(side='left')
        ttk.Label(top,text=date.today().strftime('%d %b %Y'),style='Muted.TLabel').pack(side='right',padx=(8,0))
        customer_row=ttk.Frame(right); customer_row.pack(fill='x',pady=(0,12))
        ttk.Label(customer_row,text='Customer',font=(self.font_family,10,'bold')).pack(side='left',padx=(0,12))
        self.customer_var=tk.StringVar(value='Walk-in customer'); self.customer_combo=ttk.Combobox(customer_row,textvariable=self.customer_var,values=['Walk-in customer']+self.parties_options('Customer'),state='readonly'); self.customer_combo.pack(side='left',fill='x',expand=True)
        ttk.Separator(right).pack(fill='x',pady=(0,10))
        # Reserve the payment controls at the bottom; the line list scrolls independently.
        payment=ttk.Frame(right); payment.pack(side='bottom',fill='x')
        self.subtotal_var=tk.StringVar(value='0.00'); self.discount_var=tk.StringVar(value='0.00'); self.total_var=tk.StringVar(value='0.00'); self.tender_var=tk.StringVar(); self.change_var=tk.StringVar(value='0.00'); self.payment_error=tk.StringVar()
        self.amount_row(payment,'Subtotal (PKR)',self.subtotal_var)
        self.amount_row(payment,'Discount (PKR)',self.discount_var,entry=True)
        self.amount_row(payment,'Amount due (PKR)',self.total_var,bold=True)
        ttk.Separator(payment).pack(fill='x',pady=4)
        self.amount_row(payment,'Payment received (PKR)',self.tender_var,entry=True)
        self.amount_row(payment,'Change (PKR)',self.change_var,bold=True)
        self.payment_error_label=ttk.Label(payment,textvariable=self.payment_error,foreground=theme.AMBER,wraplength=360)
        self.complete_button=ttk.Button(payment,text='Complete sale     F5',image=self.image('icons/credit-card-white.png'),compound='left',style='Primary.TButton',command=self.safe(self.checkout)); self.complete_button.pack(fill='x',pady=(6,4))
        ttk.Button(payment,text='Clear cart',image=self.image('icons/trash.png'),compound='left',command=self.safe(self.cart_clear)).pack(fill='x',pady=(3,0))
        headings=ttk.Frame(right); headings.pack(fill='x',pady=(0,8)); ttk.Label(headings,text='Medicine',font=(self.font_family,10,'bold')).pack(side='left'); ttk.Label(headings,text='Quantity / line total',style='Muted.TLabel').pack(side='right')
        holder=ttk.Frame(right); holder.pack(fill='both',expand=True)
        self.cart_canvas=tk.Canvas(holder,background=theme.BG,highlightthickness=0,width=380,height=160)
        scrollbar=ttk.Scrollbar(holder,orient='vertical',command=self.cart_canvas.yview); self.cart_canvas.configure(yscrollcommand=scrollbar.set)
        self.cart_canvas.pack(side='left',fill='both',expand=True); scrollbar.pack(side='right',fill='y')
        self.cart_lines=ttk.Frame(self.cart_canvas); self.cart_window=self.cart_canvas.create_window((0,0),window=self.cart_lines,anchor='nw')
        self.cart_lines.bind('<Configure>',lambda e:self.cart_canvas.configure(scrollregion=self.cart_canvas.bbox('all')))
        self.cart_canvas.bind('<Configure>',lambda e:self.cart_canvas.itemconfigure(self.cart_window,width=e.width))
        self.cart_canvas.bind('<MouseWheel>',lambda e:self.cart_canvas.yview_scroll(-int(e.delta/120),'units'))
        self.cart_total=0
        for var in (self.discount_var,self.tender_var): var.trace_add('write',lambda *a:self.refresh_payment())
        self.counter_search(); self.refresh_cart()
    def amount_row(self,parent,label,var,entry=False,bold=False):
        row=ttk.Frame(parent); row.pack(fill='x',pady=3)
        ttk.Label(row,text=label,font=(self.font_family,11,'bold' if bold else 'normal')).pack(side='left')
        if entry: ttk.Entry(row,textvariable=var,width=12,justify='right',style='Amount.TEntry').pack(side='right')
        else: ttk.Label(row,textvariable=var,font=(self.font_family,15 if bold else 11,'bold' if bold else 'normal'),foreground=theme.GREEN if bold else theme.INK).pack(side='right')
    def update_search_hint(self):
        if self.search.get() or self.focus_get()==self.search_entry: self.search_hint.place_forget()
        else: self.search_hint.place(in_=self.search_entry,x=10,rely=.5,anchor='w')
    def draw_add_buttons(self):
        if not self.lookup.winfo_exists(): return
        for button in self.add_buttons: button.destroy()
        self.add_buttons=[]
        if not self.lookup.winfo_ismapped(): return
        for iid in self.lookup.get_children():
            box=self.lookup.bbox(iid,'Add')
            if not box: continue
            x,y,w,h=box
            if y<40: continue
            button=tk.Button(self.lookup,image=self.image('icons/plus-white.png',(18,18)),background=theme.GREEN,activebackground='#183F2B',relief='flat',borderwidth=0,cursor='hand2',command=lambda pid=int(iid):self.safe(lambda:self.add_cart_product(pid))())
            button.place(x=x+(w-32)//2,y=y+(h-32)//2,width=32,height=32); self.add_buttons.append(button)
    def counter_click(self,event):
        if self.lookup.identify_column(event.x)=='#5' and self.lookup.identify_row(event.y):
            self.lookup.selection_set(self.lookup.identify_row(event.y)); self.safe(self.cart_add)()
    def safe_event(self,fn): return lambda e:self.safe(fn)()
    def counter_search(self):
        if not hasattr(self,'lookup') or not self.lookup.winfo_exists(): return
        self.lookup.delete(*self.lookup.get_children())
        for p in self.store.inventory(self.search.get()):
            self.lookup.insert('',tk.END,iid=str(p['id']),values=(p['id'],p['name'],p['sku'],p['sellable'],fmt(p['price']),''),image=self.image('icons/pill.png',(23,23)),tags=('low',) if p['sellable']<=p['reorder'] else ())
        self.update_search_hint(); self.after_idle(self.draw_add_buttons)
        if hasattr(self,'empty_stock'): self.empty_stock.configure(text='No medicines found. Admin can add medicines or import opening stock.' if not self.lookup.get_children() else 'Double-click a medicine or select Add. Prices are per sale unit.')
    def scan(self):
        exact=self.store.rows('SELECT id FROM products WHERE active=1 AND (barcode=? OR sku=?)',(self.search.get(),self.search.get()))
        if len(exact)==1: self.add_cart_product(exact[0]['id']); self.search.set('')
        else: self.counter_search()
    def cart_add(self):
        if self.current_page!='Counter': return
        self.add_cart_product(int(self.selected(self.lookup)[0]))
    def add_cart_product(self,pid):
        for item in self.cart:
            if item['product_id']==pid: item['quantity']+=1; break
        else: self.cart.append({'product_id':pid,'quantity':1})
        self.refresh_cart()
    def refresh_cart(self):
        for child in self.cart_lines.winfo_children(): child.destroy()
        self.cart_total=0
        if not self.cart: ttk.Label(self.cart_lines,text='Your cart is empty.\nAdd a medicine to start a sale.',style='Muted.TLabel',padding=(0,18)).pack(anchor='w')
        for item in self.cart:
            pid=item['product_id']; p=self.store.rows('SELECT * FROM products WHERE id=?',(pid,))[0]; amount=p['price']*item['quantity']; self.cart_total+=amount
            row=ttk.Frame(self.cart_lines,padding=(0,10,3,12)); row.pack(fill='x')
            row.columnconfigure(0,weight=1)
            ttk.Label(row,text=p['name'],font=(self.font_family,10,'bold'),wraplength=250).grid(row=0,column=0,sticky='w')
            ttk.Button(row,image=self.image('icons/trash.png',(17,17)),padding=(5,5),command=lambda ident=pid:self.safe(lambda:self.cart_remove_id(ident))()).grid(row=0,column=1,sticky='e')
            controls=ttk.Frame(row); controls.grid(row=1,column=0,sticky='w',pady=(8,0))
            for icon,delta in [('minus',-1),('plus',1)]:
                if delta==1: ttk.Button(controls,text=str(item['quantity']),width=4,padding=(5,5),command=lambda ident=pid:self.quantity_form(ident)).pack(side='left',padx=4)
                ttk.Button(controls,image=self.image('icons/'+icon+'.png',(16,16)),width=2,padding=(5,5),command=lambda ident=pid,d=delta:self.safe(lambda:self.cart_adjust(ident,d))()).pack(side='left')
            ttk.Label(controls,text='  @ '+fmt(p['price']),style='Muted.TLabel',font=(self.font_family,9)).pack(side='left')
            ttk.Label(row,text=fmt(amount),font=(self.font_family,11,'bold')).grid(row=1,column=1,sticky='e',pady=(8,0))
            ttk.Separator(self.cart_lines).pack(fill='x')
        self.subtotal_var.set(fmt(self.cart_total)); self.refresh_payment()
    def cart_adjust(self,pid,delta):
        for item in self.cart:
            if item['product_id']==pid: item['quantity']=max(1,item['quantity']+delta)
        self.refresh_cart()
    def quantity_form(self,pid):
        quantity=next(x['quantity'] for x in self.cart if x['product_id']==pid)
        def save(v):
            q=integer(v['quantity'],1)
            for item in self.cart:
                if item['product_id']==pid: item['quantity']=q
            self.refresh_cart()
        self.form('Change quantity',[('quantity','Whole sale units',quantity)],save)
    def cart_remove_id(self,pid):
        self.cart=[x for x in self.cart if x['product_id']!=pid]; self.refresh_cart()
    def cart_clear(self):
        self.cart=[]; self.discount_var.set('0.00'); self.tender_var.set(''); self.refresh_cart()
    def refresh_payment(self):
        try:
            discount=money(self.discount_var.get() or '0'); tender=money(self.tender_var.get() or '0')
            if discount>self.cart_total: raise ValueError('Discount cannot exceed subtotal')
            total=self.cart_total-discount; self.total_var.set(fmt(total)); self.change_var.set(fmt(max(0,tender-total)))
            self.payment_error.set(''); self.payment_error_label.pack_forget(); self.complete_button.configure(state='normal' if self.cart else 'disabled')
        except ValueError as e:
            self.payment_error.set(str(e)); self.payment_error_label.pack(anchor='w',before=self.complete_button,pady=(0,5)); self.complete_button.configure(state='disabled')
    def checkout(self):
        if self.current_page!='Counter' or self.checkout_busy: return
        if not self.cart: raise ValueError('Cart is empty')
        discount=money(self.discount_var.get() or '0'); tender=money(self.tender_var.get() or '0'); total=self.cart_total-discount
        if total<0: raise ValueError('Discount cannot exceed subtotal')
        customer=None if self.customer_var.get()=='Walk-in customer' else self.pickid(self.customer_var.get())
        if customer is None and tender<total: raise ValueError('Payment is below the total. Select a named customer to record credit.')
        applied=min(tender,total); change=max(0,tender-total)
        self.checkout_busy=True
        try:
            ident=self.store.sell(self.cart,customer,f'{applied/100:.2f}',self.discount_var.get() or '0')
            self.cart_clear(); self.customer_var.set('Walk-in customer'); self.refresh_all()
            title,lines=reports.receipt(self.store,ident)
            self.print_dialog(title,lines,self.store.get_setting('thermal','80mm'))
        finally: self.checkout_busy=False
    def stock_ui(self):
        self.heading(self.tabs['Stock'],'Medicine inventory','Manage medicines, batches and expiry dates.')
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
        self.heading(self.tabs[kind+'s'],kind+'s','Contact details, outstanding balances and payment records.')
        f=self.tabs[kind+'s']; bar=ttk.Frame(f); bar.pack(fill='x'); self.button(bar,'Add '+kind,lambda:self.party_form(kind)); self.button(bar,'Refresh',lambda:self.refresh_parties(kind))
        if self.store.user['role']=='Admin': self.button(bar,'Record balance payment',lambda:self.party_payment(kind)); self.button(bar,'Statement',lambda:self.party_statement(kind))
        tree=self.table(f,['ID','Name','Phone','Address','Balance PKR']); setattr(self,kind+'_tree',tree); self.refresh_parties(kind)
    def refresh_parties(self,kind): self.fill(getattr(self,kind+'_tree'),[(p['id'],p['name'],p['phone'],p['address'],fmt(self.store.balance(p['id']))) for p in self.store.rows('SELECT * FROM parties WHERE kind=? ORDER BY name',(kind,))])
    def party_form(self,kind):
        def save(v):
            self.store.add_party(kind,**v); self.refresh_parties(kind)
            if kind=='Customer': self.customer_combo.configure(values=['Walk-in customer']+self.parties_options('Customer'))
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
        self.heading(self.tabs['Sales'],'Sales history','Find invoices, reprint receipts and review sales.')
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
        self.heading(self.tabs['Purchases'],'Supplier purchases','Receive batches and keep vendor bills together.')
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
        self.heading(self.tabs['Expenses'],'Business expenses','Record paid expenses with clear references.')
        f=self.tabs['Expenses']; bar=ttk.Frame(f); bar.pack(fill='x'); self.button(bar,'Add expense',self.expense_form); self.button(bar,'Refresh',self.refresh_expenses)
        self.expense_tree=self.table(f,['ID','Date','Category','Note','Amount PKR']); self.refresh_expenses()
    def expense_form(self):
        def save(v): self.store.expense(**v); self.refresh_expenses()
        self.form('Expense',[('category','Category',''),('note','Description / reference',''),('amount','Amount PKR','0.00')],save)
    def refresh_expenses(self): self.fill(self.expense_tree,[(e['id'],e['created'],e['category'],e['note'],fmt(e['amount'])) for e in self.store.rows('SELECT * FROM expenses ORDER BY id DESC LIMIT 2000')])
    def reports_ui(self):
        self.heading(self.tabs['Reports'],'Reports and insights','Choose a date range to review your business.')
        f=self.tabs['Reports']; bar=ttk.Frame(f); bar.pack(fill='x'); self.start=tk.StringVar(value=date.today().replace(day=1).isoformat()); self.end=tk.StringVar(value=date.today().isoformat())
        for text,var in [('From YYYY-MM-DD',self.start),('To YYYY-MM-DD',self.end)]: ttk.Label(bar,text=text).pack(side='left',padx=6); ttk.Entry(bar,textvariable=var,width=14).pack(side='left')
        self.button(bar,'View / print report',lambda:self.print_dialog(*reports.report(self.store,self.start.get(),self.end.get()),'A4'))
        ttk.Label(f,text='Report includes sales, cost of goods, profit, expenses, recorded cash movement,\ncurrent inventory and customer/supplier balances. All amounts are in PKR.',padding=24).pack(anchor='w')
    def admin_ui(self):
        self.heading(self.tabs['Administration'],'Administration','Manage accounts, printers, backups and the audit trail.')
        f=self.tabs['Administration']; bar=ttk.Frame(f); bar.pack(fill='x')
        self.button(bar,'New user',self.user_form); self.button(bar,'Change my password',self.password_form); self.button(bar,'Printer settings',self.settings_form); self.button(bar,'Company profile',self.company_profile)
        bar2=ttk.Frame(f); bar2.pack(fill='x'); self.button(bar2,'Create backup',self.backup); self.button(bar2,'Restore backup',self.restore); self.button(bar2,'Refresh audit',self.refresh_audit)
        ttk.Label(f,text='Data folder: '+str(self.store.path.parent)+'\nLAN clients are not enabled in this release. Keep this database on a local disk.',padding=8).pack(anchor='w')
        self.audit_tree=self.table(f,['ID','Date','User ID','Action','Detail']); self.refresh_audit()
    def user_form(self):
        def save(v): self.store.add_user(**v); self.refresh_audit()
        self.form('New account',[('username','Username',''),('password','Password (10+ characters)',''),('role','Role','Cashier',['Cashier','Admin'])],save)
    def password_form(self): self.form('Change password',[('old','Current password',''),('new','New password (10+ characters)','')],lambda v:self.store.change_password(**v))
    def company_profile(self):
        self.store.authorize(True)
        d=tk.Toplevel(self); d.title('Company profile'); d.geometry('700x'+str(min(800,self.winfo_screenheight()-80))); d.transient(self); d.grab_set()
        bar=ttk.Frame(d,padding=(20,8)); bar.pack(side='bottom',fill='x')
        shell=ttk.Frame(d); shell.pack(fill='both',expand=True)
        canvas=tk.Canvas(shell,background=theme.BG,highlightthickness=0)
        scroll=ttk.Scrollbar(shell,orient='vertical',command=canvas.yview); scroll.pack(side='right',fill='y'); canvas.configure(yscrollcommand=scroll.set); canvas.pack(side='left',fill='both',expand=True)
        content=ttk.Frame(canvas,padding=24); window=canvas.create_window((0,0),window=content,anchor='nw')
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width)); content.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        ttk.Label(content,text='Company profile',font=(self.font_family,23,'bold'),foreground=theme.GREEN).pack(anchor='w')
        ttk.Label(content,text='Update your identity anytime. Changes apply to new printouts.',style='Muted.TLabel').pack(anchor='w',pady=(6,18))
        preview=ttk.Frame(content); preview.pack(fill='x',pady=(0,12)); draft={'logo':None}; values={}
        logo_label=ttk.Label(preview); logo_label.pack(side='left',padx=(0,16))
        def refresh_preview(raw=None):
            image=self.image('company-default.png',(90,90),raw); logo_label.configure(image=image); logo_label.image=image
        refresh_preview(branding.logo_bytes(self.store))
        def choose():
            path=filedialog.askopenfilename(parent=d,filetypes=[('Company logo','*.png *.jpg *.jpeg')])
            if path:
                if Path(path).stat().st_size>branding.MAX_FILE: raise ValueError('Logo must be smaller than 5 MB')
                draft['logo']=branding.normalize_logo(Path(path).read_bytes()); refresh_preview(draft['logo'])
        def remove(): draft['logo']=b''; refresh_preview()
        self.button(preview,'Replace logo',choose,icon='photo'); self.button(preview,'Remove',remove)
        ttk.Label(content,text='PNG or JPEG, up to 5 MB. The logo is included in database backups.',style='Muted.TLabel').pack(anchor='w',pady=(0,16))
        for key,label,default in [('name','Company / pharmacy name','Your pharmacy'),('tagline','Tagline','Healthier people. Brighter days.'),('address','Address',''),('phone','Phone',''),('email','Email',''),('footer','Receipt footer','Thank you')]:
            ttk.Label(content,text=label,font=(self.font_family,10,'bold')).pack(anchor='w')
            value=tk.StringVar(value=self.store.get_setting(key,default)); values[key]=value
            ttk.Entry(content,textvariable=value).pack(fill='x',pady=(4,12))
        def save():
            branding.save_profile(self.store,{k:v.get() for k,v in values.items()},draft['logo'])
            self.refresh_header(); self.refresh_audit(); d.destroy()
        self.button(bar,'Save company profile',save,primary=True); self.button(bar,'Cancel',d.destroy)
        return d
    def settings_form(self):
        choices=printing.printers()
        fields=[('thermal','Thermal roll',self.store.get_setting('thermal','80mm'),['58mm','80mm']),('thermal_printer','Thermal printer',self.store.get_setting('thermal_printer'),['']+choices),('a4_printer','A4 printer',self.store.get_setting('a4_printer'),['']+choices)]
        self.form('Printer settings',fields,lambda v:self.store.settings(v))
    def backup(self):
        path=filedialog.asksaveasfilename(defaultextension='.sqlite3',initialfile='pharmacy-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite3')
        if path: self.store.backup(path); self.refresh_backup_status(); messagebox.showinfo('Backup complete','Keep this backup on a separate drive. It includes all records and accounts.')
    def restore(self):
        path=filedialog.askopenfilename(filetypes=[('Pharmacy backup','*.sqlite3')])
        if path and messagebox.askyesno('Replace current database','Restore ALL records and logins from this backup? An automatic safety backup will be saved first. Sign in using the restored account afterwards.'):
            self.store.restore(path); self.login_screen()
    def refresh_audit(self): self.fill(self.audit_tree,[(a['id'],a['created'],a['user_id'],a['action'],a['detail']) for a in self.store.rows('SELECT * FROM audit ORDER BY id DESC LIMIT 1000')])
    def refresh_all(self):
        self.refresh_stock(); self.counter_search(); self.refresh_sales(); self.refresh_parties('Customer')
        self.customer_combo.configure(values=['Walk-in customer']+self.parties_options('Customer'))
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
            printing.print_native(printer.get(),title,lines,paper_var.get(),branding.logo_bytes(self.store))
        def export():
            path=filedialog.asksaveasfilename(defaultextension='.pdf',initialfile=title.lower().replace(' ','-')+'.pdf',parent=d)
            if path: printing.pdf(path,title,lines,paper_var.get(),branding.logo_bytes(self.store)); messagebox.showinfo('PDF saved',path,parent=d)
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
