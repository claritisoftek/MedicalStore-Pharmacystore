"""Warm Dispensary design tokens and native ttk styles."""
from pathlib import Path
import sys
from tkinter import ttk
from PIL import Image,ImageTk

BG='#FBFAF6'; NAV='#F0F0E7'; WHITE='#FFFFFF'; INK='#172D23'; GREEN='#24573E'; MUTED='#69756D'; LINE='#DDE1D7'; SAGE='#E4EBDE'; AMBER='#A24D36'

def asset(name): return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))/'assets'/name

def configure(root):
    from tkinter import font as tkfont
    available={name.lower():name for name in tkfont.families(root)}
    family=next((available[name.lower()] for name in ('Segoe UI','DejaVu Sans','Nimbus Sans L','Helvetica') if name.lower() in available),'Helvetica')
    root.font_family=family; root.configure(background=BG)
    root.option_add('*Font',(family,10)); root.option_add('*Background',BG); root.option_add('*Foreground',INK)
    style=ttk.Style(root); style.theme_use('clam')
    style.configure('.',background=BG,foreground=INK,font=(family,10),borderwidth=0)
    style.configure('TFrame',background=BG); style.configure('White.TFrame',background=WHITE)
    style.configure('TLabel',background=BG,foreground=INK)
    style.configure('Muted.TLabel',foreground=MUTED)
    style.configure('TButton',padding=(13,9),background=NAV,foreground=INK,bordercolor=LINE,lightcolor=NAV,darkcolor=NAV,relief='flat',font=(family,10))
    style.map('TButton',background=[('active',SAGE),('pressed',SAGE)],bordercolor=[('focus',GREEN)])
    style.configure('Primary.TButton',background=GREEN,foreground=WHITE,font=(family,11,'bold'),padding=(18,13),bordercolor=GREEN,lightcolor=GREEN,darkcolor=GREEN)
    style.map('Primary.TButton',background=[('active','#1A4430'),('pressed','#163A29'),('disabled','#879A8B')],foreground=[('disabled','#E5EAE5')])
    style.configure('Compact.Primary.TButton',padding=(16,8))
    style.configure('Compact.TButton',padding=(10,4))
    style.configure('TEntry',padding=(9,8),fieldbackground=WHITE,foreground=INK,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE)
    style.configure('Amount.TEntry',padding=(8,3))
    style.map('TEntry',bordercolor=[('focus',GREEN)],lightcolor=[('focus',GREEN)],darkcolor=[('focus',GREEN)])
    style.configure('TCombobox',padding=(8,8),fieldbackground=WHITE,background=NAV,foreground=INK,arrowcolor=GREEN,bordercolor=LINE)
    style.map('TCombobox',fieldbackground=[('readonly',WHITE)],foreground=[('readonly',INK)])
    style.configure('Treeview',background=BG,fieldbackground=BG,foreground=INK,rowheight=42,borderwidth=0,font=(family,10))
    style.configure('Treeview.Heading',background=NAV,foreground=INK,padding=(10,13),font=(family,10,'bold'),relief='flat')
    style.map('Treeview',background=[('selected',SAGE)],foreground=[('selected',INK)])
    style.layout('Treeview',[('Treeview.treearea',{'sticky':'nswe'})])
    style.configure('Counter.Treeview',rowheight=76,font=(family,11),background=BG,fieldbackground=BG)
    style.configure('Counter.Treeview.Heading',padding=(8,15),font=(family,10,'bold'))
    style.configure('Vertical.TScrollbar',background=NAV,troughcolor=BG,borderwidth=0,arrowsize=12)
    style.configure('Horizontal.TScrollbar',background=NAV,troughcolor=BG,borderwidth=0,arrowsize=12)
    style.configure('TSeparator',background=LINE)
    return style

def photo(root,name,size=(24,24),raw=None):
    from io import BytesIO
    image=Image.open(BytesIO(raw) if raw else asset(name)).convert('RGBA')
    image.thumbnail(size,Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image,master=root)
