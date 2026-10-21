"""Local PDF output and Windows GDI printer integration, no browser/cloud required."""
import os, textwrap
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

def pdf(path,title,lines,paper='A4'):
    width= A4[0] if paper=='A4' else (58 if paper=='58mm' else 80)*72/25.4
    # Thermal PDF extends to fit content; physical print uses printer's driver settings.
    size=A4 if paper=='A4' else (width,max(240,len(lines)*24+100))
    styles=getSampleStyleSheet(); body=styles['BodyText']; body.fontSize=8 if paper!='A4' else 10
    doc=SimpleDocTemplate(str(path),pagesize=size,rightMargin=10,leftMargin=10,topMargin=15,bottomMargin=15)
    story=[Paragraph(escape(title),styles['Heading2']),Spacer(1,8)]
    for line in lines: story.append(Paragraph(escape(str(line)) or ' ',body))
    doc.build(story)

def printers():
    if os.name!='nt': return []
    import win32print
    return [p[2] for p in win32print.EnumPrinters(6)]

def print_native(printer,title,lines,paper='A4'):
    if os.name!='nt': raise ValueError('Native printing is available in the Windows build. Export PDF here.')
    import win32ui, win32con
    dc=win32ui.CreateDC(); dc.CreatePrinterDC(printer)
    started=False
    try:
        w=dc.GetDeviceCaps(win32con.HORZRES); h=dc.GetDeviceCaps(win32con.VERTRES)
        dpi=dc.GetDeviceCaps(win32con.LOGPIXELSY); margin=max(10,int(dpi*.15))
        font=win32ui.CreateFont({'name':'Consolas','height':-int(dpi*(9 if paper=='A4' else 8)/72)})
        dc.SelectObject(font)
        charw=max(1,dc.GetTextExtent('M')[0]); lineh=int(dpi*13/72)
        columns=max(12,(w-margin*2)//charw)
        dc.StartDoc(title); started=True; dc.StartPage(); y=margin
        for line in [title,'']+list(lines):
            for part in textwrap.wrap(str(line),width=columns,replace_whitespace=False) or ['']:
                if y+lineh>h-margin: dc.EndPage(); dc.StartPage(); dc.SelectObject(font); y=margin
                dc.TextOut(margin,y,part); y+=lineh
        dc.EndPage(); dc.EndDoc(); started=False
    except Exception:
        if started: dc.AbortDoc()
        raise
    finally: dc.DeleteDC()
