from .core import fmt

def receipt(store,ident):
    s=store.rows('''SELECT s.*,coalesce(p.name,'Walk-in') customer,u.username cashier FROM sales s LEFT JOIN parties p ON p.id=s.customer_id JOIN users u ON u.id=s.user_id WHERE s.id=?''',(ident,))
    if not s: raise ValueError('Sale not found')
    s=s[0]; lines=[store.get_setting('name','Pharmacy'),store.get_setting('address'),store.get_setting('phone'),store.get_setting('email'),f"Receipt #{ident} | {s['status']}",s['created'],f"Customer: {s['customer']}",f"Cashier: {s['cashier']}",'-'*30]
    for l in store.rows('''SELECT p.name,b.batch,b.expiry,l.* FROM sale_lines l JOIN batches b ON b.id=l.batch_id JOIN products p ON p.id=b.product_id WHERE l.sale_id=?''',(ident,)):
        lines += [l['name'],f"Batch {l['batch']} Exp {l['expiry']}",f"{l['quantity']} x {fmt(l['price'])} = PKR {fmt(l['quantity']*l['price'])}"]
    lines += ['-'*30,f"Subtotal PKR {fmt(s['subtotal'])}",f"Discount PKR {fmt(s['discount'])}",f"TOTAL PKR {fmt(s['total'])}",f"Paid PKR {fmt(s['paid'])}",f"Due PKR {fmt(s['total']-s['paid'])}",store.get_setting('footer','Thank you')]
    return 'Customer receipt',lines

def vendor_bill(store,ident):
    p=store.rows('''SELECT x.*,p.name,p.phone,p.address FROM purchases x JOIN parties p ON p.id=x.supplier_id WHERE x.id=?''',(ident,))
    if not p: raise ValueError('Purchase not found')
    p=p[0]; lines=[store.get_setting('name','Pharmacy'),store.get_setting('address'),store.get_setting('phone'),store.get_setting('email'),f"Purchase #{ident} | Vendor ref: {p['reference']}",p['created'],p['name'],p['phone'],p['address'],'']
    for b in store.rows('SELECT b.*,p.name FROM batches b JOIN products p ON p.id=b.product_id WHERE b.purchase_id=?',(ident,)):
        lines += [f"{b['name']} | Batch {b['batch']} | Exp {b['expiry']}",f"{b['original_quantity']} x PKR {fmt(b['cost'])} = PKR {fmt(b['original_quantity']*b['cost'])}"]
    lines += [f"Total PKR {fmt(p['total'])}",f"Paid at purchase PKR {fmt(p['paid'])}",f"Due at purchase PKR {fmt(p['total']-p['paid'])}"]
    return 'Vendor purchase bill',lines

def report(store,start,end):
    store.authorize(True)
    from .core import valid_date
    start=valid_date(start); end=valid_date(end)
    if start>end: raise ValueError('Start date must be before end date')
    args=(start,end)
    s=store.rows("SELECT coalesce(sum(total),0) revenue,coalesce(sum(discount),0) discounts,coalesce(sum(paid),0) collected,count(*) invoices FROM sales WHERE status='Posted' AND substr(created,1,10) BETWEEN ? AND ?",args)[0]
    c=store.scalar("SELECT coalesce(sum(l.quantity*l.cost),0) FROM sale_lines l JOIN sales s ON s.id=l.sale_id WHERE s.status='Posted' AND substr(s.created,1,10) BETWEEN ? AND ?",args)
    e=store.scalar('SELECT coalesce(sum(amount),0) FROM expenses WHERE substr(created,1,10) BETWEEN ? AND ?',args)
    purchases=store.scalar('SELECT coalesce(sum(total),0) FROM purchases WHERE substr(created,1,10) BETWEEN ? AND ?',args)
    incoming=store.scalar("SELECT coalesce(sum(x.amount),0) FROM payments x JOIN parties p ON p.id=x.party_id WHERE p.kind='Customer' AND substr(x.created,1,10) BETWEEN ? AND ?",args)
    outgoing=store.scalar("SELECT coalesce(sum(x.amount),0) FROM payments x JOIN parties p ON p.id=x.party_id WHERE p.kind='Supplier' AND substr(x.created,1,10) BETWEEN ? AND ?",args)
    purchase_cash=store.scalar('SELECT coalesce(sum(paid),0) FROM purchases WHERE substr(created,1,10) BETWEEN ? AND ?',args)
    lines=[store.get_setting('name','Pharmacy'),f'{start} to {end}',f"Posted invoices: {s['invoices']}"]
    for label,v in [('Net sales',s['revenue']),('Discounts',s['discounts']),('Cost of goods sold',c),('Gross profit',s['revenue']-c),('Expenses',e),('Operating result (before taxes/other adjustments)',s['revenue']-c-e),('Purchases',purchases),('Cash collected at sale',s['collected']),('Customer balance payments',incoming),('Cash paid at purchase',purchase_cash),('Supplier balance payments',outgoing),('Net recorded cash movement',s['collected']+incoming-purchase_cash-outgoing-e)]: lines.append(f'{label}: PKR {fmt(v)}')
    lines+=['','CURRENT INVENTORY (at report generation, not historical):']
    for p in store.inventory(): lines.append(f"{p['sku']} | {p['name']} | Total {p['stock']} | Sellable {p['sellable']} | Reorder {p['reorder']}")
    lines+=['','CURRENT PARTY BALANCES:']
    for p in store.rows('SELECT * FROM parties ORDER BY kind,name'): lines.append(f"{p['kind']} | {p['name']} | PKR {fmt(store.balance(p['id']))}")
    lines+=['','EXPENSES IN PERIOD:']
    for x in store.rows('SELECT * FROM expenses WHERE substr(created,1,10) BETWEEN ? AND ? ORDER BY id',args): lines.append(f"{x['created']} | {x['category']} | {x['note']} | PKR {fmt(x['amount'])}")
    return 'Pharmacy management report',lines
