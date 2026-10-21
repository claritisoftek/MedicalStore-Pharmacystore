export const escape = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const money = (n) =>
  "PKR " +
  (Number(n) / 100).toLocaleString("en-PK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
export function documentHtml(kind, d, p, size) {
  const e = escape;
  const title =
    kind === "sale"
      ? "Customer receipt"
      : kind === "purchase"
        ? "Vendor bill"
        : kind === "report"
          ? "Financial report"
          : "Account statement";
  let content;
  if (kind === "report") {
    content = `<p>${e(d.from)} to ${e(d.to)}</p><table>${[
      ["Sales revenue", "revenue"],
      ["Cost of goods", "cogs"],
      ["Expenses", "expenses"],
      ["Operating result", "profit"],
      ["Recorded cash movement", "cash"],
    ]
      .map(
        ([label, key]) =>
          `<tr><th>${e(label)}</th><td>${money(d[key])}</td></tr>`,
      )
      .join(
        "",
      )}</table><p>Cash movement excludes opening cash. Report uses posted sales only.</p>`;
  } else if (kind === "statement") {
    content = `<h2>${e(d.party.name)}</h2><p>${e(d.party.kind)} · ${e(d.party.phone)}</p><table><thead><tr><th>Bill/date</th><th>Status</th><th>Total</th><th>Paid</th></tr></thead><tbody>${d.bills.map((b) => `<tr><td>#${b.id} · ${e(b.created)}</td><td>${e(b.status || "Posted")}</td><td>${money(b.total)}</td><td>${money(b.paid)}</td></tr>`).join("")}</tbody></table><h3>Subsequent payments</h3>${d.payments.map((x) => `<p>${e(x.created)} — ${money(x.amount)} — ${e(x.note)}</p>`).join("") || "<p>None</p>"}<h2>Outstanding ${money(d.balance)}</h2>`;
  } else {
    content = `<p>#${d.id} · ${e(d.created)}<br>${e(d.party || "Walk-in customer")} ${d.status === "Void" ? "<strong>VOID</strong>" : ""}${kind === "purchase" ? "<br>Vendor reference: " + e(d.reference) : ""}</p><table><thead><tr><th>Medicine / batch</th><th>Qty</th><th>Rate</th><th>Total</th></tr></thead><tbody>${d.lines
      .map((l) => {
        const q = kind === "purchase" ? l.original_quantity : l.quantity,
          r = kind === "purchase" ? l.cost : l.price;
        return `<tr><td>${e(l.name)}<small>${e(l.batch)} · ${e(l.expiry)}</small></td><td>${q}</td><td>${money(r)}</td><td>${money(q * r)}</td></tr>`;
      })
      .join(
        "",
      )}</tbody></table>${kind === "sale" ? `<p>Subtotal ${money(d.subtotal)}<br>Discount ${money(d.discount)}</p>` : ""}<h2>Total ${money(d.total)}</h2><p>Applied payment ${money(d.paid)}<br>Balance ${money(d.total - d.paid)}</p>`;
  }
  const logo =
    typeof p.logo === "string" &&
    /^data:image\/png;base64,[a-zA-Z0-9+/=]+$/.test(p.logo)
      ? p.logo
      : "/assets/company-default.png";
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title><link rel="stylesheet" href="/print.css"><style>@page{size:${size === "A4" ? "A4" : size + "mm auto"};margin:${size === "A4" ? "15mm" : "3mm"}}article{max-width:${size === "A4" ? "180mm" : Number(size) - 6 + "mm"}}</style></head><body><div class="tools"><button id="print">Print / Save PDF</button><label>Paper <select id="paper"><option>A4</option><option ${size === "80" ? "selected" : ""}>80</option><option ${size === "58" ? "selected" : ""}>58</option></select></label><span>Choose the matching paper size in your printer settings.</span></div><article><header><img src="${logo}" alt="Company logo"><h1>${e(p.name || "Pharmacy")}</h1><p>${e(p.tagline || "Your health, our care")}<br>${e(p.address)}<br>${e(p.phone)} ${e(p.email)}</p></header><h2>${title}</h2>${content}<footer>${e(p.footer || "Thank you for visiting. Keep this receipt for your records.")}</footer></article><script src="/print.js"></script></body></html>`;
}
