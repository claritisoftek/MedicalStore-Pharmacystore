const $ = (s, r = document) => r.querySelector(s),
  root = $("#root"),
  modal = $("#modal");
const e = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const amount = (n) =>
  (Number(n) / 100).toLocaleString("en-PK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
const money = (n) => "PKR " + amount(n),
  icon = (n) => `<img src="/assets/icons/${n}.png" alt="">`;
let state,
  csrf = "",
  page = "Counter",
  cart = [],
  purchaseLines = [],
  requestKey = null,
  pendingSale = null,
  importFile = null,
  reportData = null;
function notice(message) {
  $("#notices").textContent = message;
  setTimeout(() => {
    $("#notices").textContent = "";
  }, 6000);
}
async function api(path, data) {
  const res = await fetch("/api" + path, {
    method: data === undefined ? "GET" : "POST",
    headers:
      data === undefined
        ? {}
        : { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  let body;
  try {
    body = await res.json();
  } catch {
    throw Error(
      "The server response was interrupted. Retry the same checkout.",
    );
  }
  if (!res.ok) {
    if (res.status === 401) {
      csrf = "";
      await loginScreen();
    }
    throw Object.assign(Error(body.error || "Request failed"), {
      status: res.status,
    });
  }
  return body;
}
function table(headers, data, empty = "No records yet.") {
  return `<div class="table-wrap"><table><thead><tr>${headers.map((h) => `<th>${e(h)}</th>`).join("")}</tr></thead><tbody>${data.length ? data.map((row) => `<tr>${row.map((v) => `<td>${v}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${headers.length}" class="empty">${e(empty)}</td></tr>`}</tbody></table></div>`;
}
function field(name, label, value = "", type = "text", extra = "") {
  return `<label>${e(label)}<input name="${e(name)}" type="${type}" value="${e(value)}" ${extra}></label>`;
}
function select(name, label, options, value = "") {
  return `<label>${e(label)}<select name="${name}">${options.map(([v, l]) => `<option value="${e(v)}" ${String(v) === String(value) ? "selected" : ""}>${e(l)}</option>`).join("")}</select></label>`;
}
const productOptions = () =>
  state.products.map((p) => [p.id, `${p.name} · ${p.sku}`]);
const partyOptions = (kind) =>
  state.parties.filter((p) => p.kind === kind).map((p) => [p.id, p.name]);
function dialog(title, content, submit, label = "Save") {
  modal.innerHTML = `<div class="modal-heading"><h2>${e(title)}</h2><button type="button" id="close-dialog" aria-label="Close">×</button></div><form id="dialog-form"><div class="form-grid">${content}</div><p class="error hidden" id="dialog-error" role="alert"></p><div class="actions"><button type="button" id="cancel-dialog">Cancel</button><button class="primary" type="submit">${e(label)}</button></div></form>`;
  $("#close-dialog").onclick = $("#cancel-dialog").onclick = () =>
    modal.close();
  $("#dialog-form").onsubmit = async (event) => {
    event.preventDefault();
    const button = $("button[type=submit]", event.target);
    button.disabled = true;
    try {
      await submit(Object.fromEntries(new FormData(event.target)));
      modal.close();
      if (state && csrf) await refresh();
      notice("Saved successfully");
    } catch (err) {
      $("#dialog-error").textContent = err.message;
      $("#dialog-error").classList.remove("hidden");
    } finally {
      button.disabled = false;
    }
  };
  modal.showModal();
}
async function loginScreen() {
  const status = await api("/status");
  state = null;
  const setup = !status.configured;
  root.innerHTML = `<section class="login"><img src="/assets/pharmacy-icon.png" alt="Medicine capsule"><h1>${setup ? "Welcome to your dispensary" : "Welcome back"}</h1><p class="muted">${setup ? "Create the first Admin using the private setup token from your hosting settings. Your business database starts empty." : "Sign in to manage your counter and pharmacy."}</p><form id="login-form">${setup ? field("token", "Private setup token", "", "password", 'required autocomplete="off"') : ""}${field("username", "Username", "", "text", 'required autocomplete="username" maxlength="100"')}${field("password", "Password", "", "password", `required autocomplete="${setup ? "new-password" : "current-password"}" ${setup ? 'minlength="10"' : ""} maxlength="200"`)}<p id="login-error" class="error hidden" role="alert"></p><button type="submit" class="primary">${setup ? "Create Admin account" : "Sign in"}</button></form><p class="muted"><small>Pharmacy Web · English · PKR</small></p></section>`;
  $("#login-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const b = $("button", ev.target);
    b.disabled = true;
    try {
      const values = Object.fromEntries(new FormData(ev.target));
      if (setup) {
        await api("/setup", values);
        notice("Admin created. Sign in to continue.");
        await loginScreen();
      } else {
        const data = await api("/login", values);
        csrf = data.csrf;
        page = "Counter";
        await refresh();
      }
    } catch (err) {
      const target = $("#login-error");
      if (target) {
        target.textContent = err.message;
        target.classList.remove("hidden");
      }
    } finally {
      b.disabled = false;
    }
  };
}
async function refresh() {
  state = await api("/state");
  render();
}
function render() {
  const admin = state.user.role === "Admin",
    p = state.profile;
  const pages = admin
    ? [
        "Counter",
        "Stock",
        "Purchases",
        "Sales",
        "Customers",
        "Suppliers",
        "Expenses",
        "Reports",
        "Administration",
      ]
    : ["Counter", "Sales", "Customers"];
  if (!pages.includes(page)) page = "Counter";
  root.innerHTML = `<header><div class="app-identity"><img src="/assets/pharmacy-icon.png" alt="Medicine capsule"><span>Dispensary</span></div><div class="company"><img src="${e(p.logo || "/assets/company-default.png")}" alt="Company logo"><div><strong>${e(p.name || "Your Pharmacy")}</strong><small>${e(p.tagline || "Your health, our care")}</small></div></div><div class="account">${e(state.user.username)} · ${e(state.user.role)}<br><button data-action="password">Password</button><button data-action="logout">Sign out</button></div></header><nav aria-label="Main navigation">${pages.map((n) => `<button data-page="${n}" class="${page === n ? "active" : ""}" ${page === n ? 'aria-current="page"' : ""}>${n}</button>`).join("")}</nav><section class="workspace"><div class="intro"><div><h1>${e(page === "Counter" ? "A little care. A better day." : page)}</h1><p class="muted">${e({ Counter: "Everything you need for a smooth day at the counter.", Stock: "Manage medicines, batches and expiry dates.", Purchases: "Receive stock and keep vendor bills together.", Sales: "Review and reprint your latest 200 sales.", Customers: "Keep customer accounts and receivables in view.", Suppliers: "Manage vendors and outstanding payables.", Expenses: "Record operating costs with a clear audit trail.", Reports: "Understand your sales, costs and recorded cash movement.", Administration: "Manage your company, team and business data." }[page])}</p></div><div class="tag">${e(state.today)} · PKR</div></div><div id="page-content"></div></section><footer class="foot">Pharmacy Web · Shared online database · <button data-action="refresh">Refresh records</button></footer>`;
  renderPage();
}
function renderPage() {
  const node = $("#page-content");
  if (page === "Counter") {
    node.innerHTML = `<div class="counter"><section><h2>Find a medicine</h2><form id="search-form" class="search"><label class="muted" for="search">Search name, SKU or scan a barcode and press Enter</label><input id="search" placeholder="Search or scan a medicine…" autocomplete="off"></form><div id="medicines"></div></section><aside class="cart"><h2>Current sale <small id="cart-count"></small></h2>${select("customer", "Customer", [["", "Walk-in customer"], ...partyOptions("Customer")])}<div class="cart-lines" id="cart-lines"></div><div class="payment"><div class="pair"><span>Subtotal</span><strong id="subtotal"></strong></div><div class="two">${field("discount", "Discount (PKR)", "0", "number", 'min="0" step="0.01"')}${field("tender", "Cash received (PKR)", "0", "number", 'min="0" step="0.01"')}</div><div class="pair total"><span>Total</span><span id="total"></span></div><div class="pair"><span>Change / balance</span><strong id="change"></strong></div><p class="error hidden" id="checkout-error" role="alert"></p><button class="primary" data-action="checkout">${icon("credit-card-white")} Complete sale · F5</button><button data-action="clear-cart">Clear cart</button></div></aside></div>`;
    $("#search").oninput = medicineTable;
    $("#search-form").onsubmit = (ev) => {
      ev.preventDefault();
      const q = $("#search").value.trim().toLowerCase(),
        found = state.products.find(
          (p) => p.barcode?.toLowerCase() === q || p.sku.toLowerCase() === q,
        );
      if (found) addCart(found.id);
      else medicineTable();
    };
    for (const name of ["discount", "tender"])
      $(`[name=${name}]`).oninput = totals;
    medicineTable();
    cartView();
    return;
  }
  if (page === "Stock") {
    node.innerHTML = `<div class="toolbar"><button class="primary" data-action="medicine">Add medicine</button><button data-action="import">Import Excel</button><a class="button" href="/api/import/template">Download Excel template</a></div>${table(
      [
        "Medicine / SKU",
        "Barcode",
        "Category",
        "Sellable / all units",
        "Price",
        "Action",
      ],
      state.products.map((p) => [
        `${e(p.name)}<small>${e(p.sku)}</small>`,
        e(p.barcode),
        e(p.category),
        `${p.sellable} / ${p.stock}${p.sellable <= p.reorder ? '<small class="stock-alert">Low stock</small>' : ""}`,
        money(p.price),
        `<button data-action="medicine" data-id="${p.id}">Edit</button>`,
      ]),
    )}<h2>Batch inventory</h2>${table(
      ["Medicine", "Batch", "Expiry", "Remaining", "Original", "Unit cost"],
      state.batches.map((b) => [
        e(b.name),
        e(b.batch),
        `${e(b.expiry)}${b.expiry < state.today ? '<small class="stock-alert">Expired — blocked from sale</small>' : ""}`,
        b.quantity,
        b.original_quantity,
        money(b.cost),
      ]),
    )}`;
  }
  if (page === "Purchases") {
    node.innerHTML = `<div class="toolbar"><button class="primary" data-action="purchase">New vendor bill</button><button data-action="party" data-kind="Supplier">Add supplier</button></div>${table(
      [
        "Bill",
        "Date",
        "Supplier",
        "Vendor reference",
        "Total",
        "Paid",
        "Balance",
        "",
      ],
      state.purchases.map((p) => [
        p.id,
        e(p.created),
        e(p.supplier),
        e(p.reference),
        money(p.total),
        money(p.paid),
        money(p.total - p.paid),
        `<a class="button" target="_blank" rel="noopener" href="/print/purchase/${p.id}">Print A4</a>`,
      ]),
    )}`;
  }
  if (page === "Sales") {
    node.innerHTML = table(
      ["Receipt", "Date", "Customer", "Total", "Paid", "Status", "Actions"],
      state.sales.map((s) => [
        s.id,
        e(s.created),
        e(s.customer || "Walk-in"),
        money(s.total),
        money(s.paid),
        e(s.status),
        `<a class="button" target="_blank" rel="noopener" href="/print/sale/${s.id}?size=80">Print</a> ${state.user.role === "Admin" && s.status === "Posted" && s.created.slice(0, 10) === state.today ? `<button class="danger" data-action="void" data-id="${s.id}">Cancel sale</button>` : ""}`,
      ]),
    );
  }
  if (page === "Customers" || page === "Suppliers") {
    const kind = page === "Customers" ? "Customer" : "Supplier";
    node.innerHTML = `<button class="primary" data-action="party" data-kind="${kind}">Add ${kind.toLowerCase()}</button>${table(
      ["Name", "Phone", "Address", "Outstanding", ""],
      state.parties
        .filter((p) => p.kind === kind)
        .map((p) => [
          e(p.name),
          e(p.phone),
          e(p.address),
          money(p.balance),
          state.user.role === "Admin"
            ? `<button data-action="payment" data-id="${p.id}">Record payment</button> <a class="button" href="/print/statement/${p.id}" target="_blank" rel="noopener">Statement</a>`
            : "",
        ]),
    )}`;
  }
  if (page === "Expenses")
    node.innerHTML = `<button class="primary" data-action="expense">Record expense</button>${table(
      ["Date", "Category", "Note", "Amount"],
      state.expenses.map((v) => [
        e(v.created),
        e(v.category),
        e(v.note),
        money(v.amount),
      ]),
    )}`;
  if (page === "Reports") {
    node.innerHTML = `<form id="report-form" class="toolbar">${field("from", "From", state.today.slice(0, 8) + "01", "date", "required")}${field("to", "To", state.today, "date", "required")}<button class="primary" type="submit">Generate report</button></form><div id="report-result" class="muted">Choose a date range to view the financial report.</div>`;
    $("#report-form").onsubmit = async (ev) => {
      ev.preventDefault();
      try {
        const v = Object.fromEntries(new FormData(ev.target));
        reportData = await api(`/report?from=${v.from}&to=${v.to}`);
        $("#report-result").innerHTML = `<div class="stats">${[
          ["Sales revenue", "revenue"],
          ["Cost of goods", "cogs"],
          ["Expenses", "expenses"],
          ["Operating result", "profit"],
          ["Recorded cash movement", "cash"],
        ]
          .map(
            ([l, k]) =>
              `<div class="stat">${e(l)}<strong>${money(reportData[k])}</strong></div>`,
          )
          .join(
            "",
          )}</div><p class="muted">Cash movement = sale payments + customer collections − vendor payments − purchase payments − expenses. Opening cash is excluded.</p><a class="button" target="_blank" rel="noopener" href="/print/report/0?from=${v.from}&to=${v.to}">Print A4 / Save PDF</a>`;
      } catch (err) {
        notice(err.message);
      }
    };
  }
  if (page === "Administration")
    node.innerHTML = `<div class="toolbar"><button class="primary" data-action="profile">Company profile & logo</button><button data-action="user">Add team member</button><a class="button" href="/api/backup">Download database backup</a><button data-action="restore">Restore backup</button></div><p class="muted">Backups contain private business data and password hashes. Keep downloads in a secure location.</p><h2>Team</h2>${table(
      ["Username", "Role", "Active"],
      state.users.map((u) => [
        e(u.username),
        e(u.role),
        u.active ? "Yes" : "No",
      ]),
    )}<h2>Safety backups before restore</h2>${table(
      ["Date", ""],
      state.safetyBackups.map((b) => [
        e(b.created),
        `<a href="/api/backup/safety/${b.id}" class="button">Download</a>`,
      ]),
    )}<h2>Recent activity</h2>${table(
      ["Date", "User ID", "Action", "Detail"],
      state.audit.map((a) => [
        e(a.created),
        e(a.user_id),
        e(a.action),
        e(a.detail),
      ]),
    )}`;
}
function medicineTable() {
  const q = $("#search").value.trim().toLowerCase();
  const list = state.products.filter((p) =>
    [p.name, p.sku, p.barcode || ""].some((s) => s.toLowerCase().includes(q)),
  );
  $("#medicines").innerHTML = table(
    ["Medicine", "Available", "Price", ""],
    list.map((p) => [
      `${icon("pill")} <strong>${e(p.name)}</strong><small>${e(p.sku)} · ${e(p.category || "Medicine")}</small>`,
      `${p.sellable}<small class="${p.sellable <= p.reorder ? "stock-alert" : ""}">${p.sellable <= p.reorder ? "Low stock" : "In stock"}</small>`,
      money(p.price),
      `<button class="primary" data-action="add" data-id="${p.id}" ${p.sellable < 1 ? "disabled" : ""}>+ Add</button>`,
    ]),
    "No medicines found. Admin can add medicines and receive stock.",
  );
}
function editable() {
  if (pendingSale)
    throw Error(
      "Checkout result is pending. Retry Complete sale before editing this cart.",
    );
  requestKey = null;
}
function addCart(id) {
  try {
    editable();
    const p = state.products.find((p) => p.id === id),
      line = cart.find((l) => l.product_id === id),
      q = (line?.quantity || 0) + 1;
    if (q > p.sellable) throw Error("No more sellable stock available");
    if (line) line.quantity = q;
    else cart.push({ product_id: id, quantity: 1 });
    cartView();
  } catch (err) {
    notice(err.message);
  }
}
function cartView() {
  if (!$("#cart-lines")) return;
  $("#cart-count").textContent = `(${cart.length})`;
  $("#cart-lines").innerHTML = cart.length
    ? cart
        .map((l) => {
          const p = state.products.find((p) => p.id === l.product_id);
          return `<div class="cart-line"><div><strong>${e(p?.name || "Unavailable medicine")}</strong><small>${money(p?.price || 0)} per unit</small></div><strong>${money((p?.price || 0) * l.quantity)}</strong><div class="quantity"><button data-action="quantity" data-id="${l.product_id}" data-step="-1" aria-label="Decrease quantity">−</button><input aria-label="Quantity for ${e(p?.name)}" data-quantity="${l.product_id}" type="number" min="1" step="1" value="${l.quantity}"><button data-action="quantity" data-id="${l.product_id}" data-step="1" aria-label="Increase quantity">+</button><button class="remove" data-action="remove" data-id="${l.product_id}">Remove</button></div></div>`;
        })
        .join("")
    : '<div class="empty"><img src="/assets/icons/pill.png" alt=""><p>Your cart is ready.<br>Add a medicine to begin.</p></div>';
  for (const input of document.querySelectorAll("[data-quantity]"))
    input.onchange = () => {
      try {
        editable();
        const q = Number(input.value),
          id = Number(input.dataset.quantity),
          p = state.products.find((p) => p.id === id);
        if (!Number.isInteger(q) || q < 1 || q > p.sellable)
          throw Error("Enter a whole quantity within available stock");
        cart.find((l) => l.product_id === id).quantity = q;
        cartView();
      } catch (err) {
        notice(err.message);
        cartView();
      }
    };
  totals();
}
function totals() {
  const subtotal = cart.reduce(
      (n, l) =>
        n +
        (state.products.find((p) => p.id === l.product_id)?.price || 0) *
          l.quantity,
      0,
    ),
    discount = Math.round(Number($("[name=discount]")?.value || 0) * 100),
    tender = Math.round(Number($("[name=tender]")?.value || 0) * 100),
    total = subtotal - discount;
  $("#subtotal").textContent = money(subtotal);
  $("#total").textContent = money(total);
  $("#change").textContent =
    tender >= total
      ? money(tender - total) + " change"
      : money(total - tender) + " due";
  return { subtotal, total };
}
async function fileBase64(file) {
  if (!file || file.size > 5 * 1024 * 1024)
    throw Error("Select a file up to 5 MB");
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(Error("Could not read file"));
    r.readAsDataURL(file);
  });
}
async function checkout(button) {
  if (!cart.length && !pendingSale) throw Error("Add a medicine first");
  if (!pendingSale) {
    requestKey = requestKey || crypto.randomUUID();
    pendingSale = {
      request_key: requestKey,
      lines: cart.map((l) => ({ ...l })),
      customer_id: $("[name=customer]").value || null,
      discount: $("[name=discount]").value,
      tender: $("[name=tender]").value,
    };
  }
  button.disabled = true;
  try {
    const result = await api("/sales", pendingSale);
    cart = [];
    pendingSale = null;
    requestKey = null;
    await refresh();
    notice("Sale completed. Open Sales to print the receipt.");
    page = "Sales";
    render();
    const link = document.querySelector(
      `a[href="/print/sale/${result.id}?size=80"]`,
    );
    link?.focus();
  } catch (err) {
    const target = $("#checkout-error");
    if (target) {
      target.textContent =
        err.message +
        " Retry this checkout with the same request key if its result is uncertain.";
      target.classList.remove("hidden");
    }
    if (err.status >= 400 && err.status < 500 && err.status !== 401) {
      pendingSale = null;
      requestKey = null;
    }
    throw err;
  } finally {
    button.disabled = false;
  }
}
const actions = {
  refresh: () => refresh(),
  add: (b) => addCart(Number(b.dataset.id)),
  quantity: (b) => {
    editable();
    const l = cart.find((l) => l.product_id === Number(b.dataset.id)),
      p = state.products.find((p) => p.id === l.product_id),
      q = l.quantity + Number(b.dataset.step);
    if (q < 1 || q > p.sellable)
      throw Error("Quantity is outside available stock");
    l.quantity = q;
    cartView();
  },
  remove: (b) => {
    editable();
    cart = cart.filter((l) => l.product_id !== Number(b.dataset.id));
    cartView();
  },
  "clear-cart": () => {
    editable();
    cart = [];
    cartView();
  },
  checkout,
  logout: async () => {
    if (pendingSale)
      throw Error("Retry the pending checkout before signing out");
    await api("/logout", {});
    cart = [];
    await loginScreen();
  },
  password: () =>
    dialog(
      "Change your password",
      field(
        "old",
        "Current password",
        "",
        "password",
        'required autocomplete="current-password"',
      ) +
        field(
          "password",
          "New password",
          "",
          "password",
          'required minlength="10" maxlength="200" autocomplete="new-password"',
        ),
      async (v) => {
        await api("/password", v);
        modal.close();
        csrf = "";
        await loginScreen();
      },
    ),
  medicine: (b) => {
    const p = state.products.find((p) => p.id === Number(b.dataset.id)) || {};
    dialog(
      p.id ? "Edit medicine" : "Add medicine",
      field("sku", "SKU", p.sku || "", "text", 'required maxlength="100"') +
        field(
          "name",
          "Medicine name",
          p.name || "",
          "text",
          'required maxlength="250"',
        ) +
        field(
          "barcode",
          "Barcode",
          p.barcode || "",
          "text",
          'maxlength="100"',
        ) +
        field(
          "category",
          "Category",
          p.category || "Medicine",
          "text",
          'maxlength="100"',
        ) +
        field(
          "price",
          "Sale price per unit (PKR)",
          p.id ? (p.price / 100).toFixed(2) : "0",
          "number",
          'required min="0" step="0.01"',
        ) +
        field(
          "reorder",
          "Reorder level",
          p.reorder ?? 5,
          "number",
          'required min="0" step="1"',
        ),
      (v) => api("/products", { ...v, id: p.id }),
    );
  },
  party: (b) => {
    const kind = b.dataset.kind;
    dialog(
      "Add " + kind.toLowerCase(),
      field("name", "Name", "", "text", 'required maxlength="250"') +
        field("phone", "Phone", "", "tel", 'maxlength="100"') +
        '<label class="full">Address<textarea name="address" maxlength="1000"></textarea></label>',
      (v) => api("/parties", { ...v, kind }),
    );
  },
  payment: (b) => {
    const p = state.parties.find((p) => p.id === Number(b.dataset.id));
    dialog(
      `${p.kind === "Customer" ? "Receive from" : "Pay"} ${p.name}`,
      `<p class="full">Outstanding: <strong>${money(p.balance)}</strong></p>` +
        field(
          "amount",
          "Payment (PKR)",
          "",
          "number",
          `required min="0.01" max="${p.balance / 100}" step="0.01"`,
        ) +
        field("note", "Reference / note", "", "text", 'maxlength="1000"'),
      (v) => api("/payments", { ...v, party_id: p.id }),
    );
  },
  expense: () =>
    dialog(
      "Record expense",
      field("category", "Category", "", "text", 'required maxlength="100"') +
        field(
          "amount",
          "Amount (PKR)",
          "",
          "number",
          'required min="0.01" step="0.01"',
        ) +
        field("note", "Note", "", "text", 'maxlength="1000"'),
      (v) => api("/expenses", v),
    ),
  user: () =>
    dialog(
      "Add team member",
      field(
        "username",
        "Username",
        "",
        "text",
        'required maxlength="100" autocomplete="off"',
      ) +
        select("role", "Role", [
          ["Cashier", "Cashier"],
          ["Admin", "Admin"],
        ]) +
        field(
          "password",
          "Password",
          "",
          "password",
          'required minlength="10" maxlength="200" autocomplete="new-password"',
        ),
      (v) => api("/users", v),
    ),
  void: async (b) => {
    if (
      confirm(
        "Cancel this entire sale and return its units to stock? This action is recorded in the audit trail.",
      )
    ) {
      await api(`/sales/${b.dataset.id}/void`, {});
      await refresh();
      notice("Sale cancelled");
    }
  },
  profile: () => {
    const p = state.profile;
    dialog(
      "Company profile",
      `<div class="full"><img id="logo-preview" class="logo-preview" src="${e(p.logo || "/assets/company-default.png")}" alt="Company logo preview"></div><label>Replace logo (PNG / JPEG, max 5 MB)<input type="file" id="logo-file" accept="image/png,image/jpeg"></label><label><span>Remove custom logo</span><input type="checkbox" name="remove" value="yes"></label>` +
        ["name", "tagline", "address", "phone", "email", "footer"]
          .map((k) =>
            field(
              k,
              {
                name: "Company name",
                tagline: "Tagline",
                address: "Address",
                phone: "Phone",
                email: "Email",
                footer: "Receipt footer",
              }[k],
              p[k] || "",
              "text",
              'maxlength="1000"',
            ),
          )
          .join(""),
      async (v) => {
        const file = $("#logo-file").files[0];
        delete v.remove;
        if ($("[name=remove]").checked) v.logo = "";
        else if (file) v.logo = await fileBase64(file);
        await api("/profile", v);
      },
      "Save company profile",
    );
    $("#logo-file").onchange = async (ev) => {
      try {
        $("#logo-preview").src = await fileBase64(ev.target.files[0]);
      } catch (err) {
        notice(err.message);
      }
    };
  },
  purchase: () => {
    purchaseLines = [];
    dialog(
      "New vendor bill",
      select("supplier_id", "Supplier", partyOptions("Supplier")) +
        field(
          "reference",
          "Vendor bill reference",
          "",
          "text",
          'required maxlength="250"',
        ) +
        `<section class="full"><div class="two">${select("product_id", "Medicine", productOptions())}${field("quantity", "Quantity", "1", "number", 'min="1" step="1"')}${field("cost", "Unit cost (PKR)", "0", "number", 'min="0" step="0.01"')}${field("batch", "Batch", "", "text", 'maxlength="100"')}${field("expiry", "Expiry", "", "date", "")}</div><button type="button" id="add-purchase">Add batch to bill</button><div id="purchase-lines"></div></section>` +
        field(
          "paid",
          "Paid (PKR)",
          "0",
          "number",
          'required min="0" step="0.01"',
        ),
      (v) =>
        api("/purchases", {
          supplier_id: v.supplier_id,
          reference: v.reference,
          paid: v.paid,
          lines: purchaseLines,
        }),
      "Save vendor bill",
    );
    $("#add-purchase").onclick = () => {
      const v = Object.fromEntries(new FormData($("#dialog-form")));
      if (!v.product_id || !v.batch || !v.expiry || Number(v.quantity) < 1) {
        notice("Medicine, batch, expiry and whole quantity are required");
        return;
      }
      purchaseLines.push({
        product_id: v.product_id,
        quantity: v.quantity,
        cost: v.cost,
        batch: v.batch,
        expiry: v.expiry,
      });
      purchaseView();
    };
  },
  import: () => {
    importFile = null;
    dialog(
      "Import opening inventory",
      `<p class="full">Download the template from Stock, enter opening inventory and batches, then upload it here. Preview is required before import. Existing medicines must exactly match their catalogue fields.</p><label class="full">Workbook (.xlsx, max 5 MB)<input id="import-file" type="file" accept=".xlsx" required></label><div class="full"><button type="button" id="preview-import">Validate & preview</button><div id="import-preview"></div></div>`,
      async () => {
        if (!importFile) throw Error("Validate and preview the workbook first");
        const result = await api("/import/apply", { file: importFile });
        notice(`Imported ${result.rows} rows`);
      },
      "Apply opening stock",
    );
    $("#preview-import").onclick = async () => {
      try {
        const file = (await fileBase64($("#import-file").files[0])).split(
            ",",
          )[1],
          data = await api("/import/preview", { file });
        importFile = file;
        $("#import-preview").innerHTML =
          `<p>${data.rows} validated rows · first 50 shown</p>` +
          table(
            ["SKU", "Medicine", "Batch", "Expiry", "Quantity"],
            data.preview.map((x) => [
              e(x.sku),
              e(x.name),
              e(x.batch),
              e(x.expiry),
              e(x.quantity),
            ]),
          );
      } catch (err) {
        importFile = null;
        $("#dialog-error").textContent = err.message;
        $("#dialog-error").classList.remove("hidden");
      }
    };
    $("#import-file").onchange = () => {
      importFile = null;
      $("#import-preview").innerHTML = "";
    };
  },
  restore: () => {
    dialog(
      "Restore a web database backup",
      `<p class="full error">This replaces current business records and accounts with the selected web backup. A safety backup is stored first. All users will be signed out. Windows SQLite backups use a different format.</p><label class="full">Web backup (.json)<input id="restore-file" type="file" accept=".json" required></label>` +
        field(
          "password",
          "Your current Admin password",
          "",
          "password",
          'required autocomplete="current-password"',
        ) +
        '<label class="full"><span>I understand this replaces the current database</span><input type="checkbox" required></label>',
      async (v) => {
        const file = $("#restore-file").files[0];
        if (!file || file.size > 12 * 1024 * 1024)
          throw Error("Select a web JSON backup up to 12 MB");
        await api("/restore", {
          backup: JSON.parse(await file.text()),
          password: v.password,
        });
        cart = [];
        csrf = "";
        modal.close();
        await loginScreen();
      },
      "Restore and sign out",
    );
  },
};
function purchaseView() {
  $("#purchase-lines").innerHTML = table(
    ["Medicine", "Batch / expiry", "Qty", "Cost", ""],
    purchaseLines.map((l, i) => [
      e(state.products.find((p) => p.id === Number(l.product_id))?.name),
      `${e(l.batch)} / ${e(l.expiry)}`,
      e(l.quantity),
      e(l.cost),
      `<button type="button" data-purchase-remove="${i}">Remove</button>`,
    ]),
  );
  for (const b of document.querySelectorAll("[data-purchase-remove]"))
    b.onclick = () => {
      purchaseLines.splice(Number(b.dataset.purchaseRemove), 1);
      purchaseView();
    };
}
document.addEventListener("click", async (ev) => {
  const b = ev.target.closest("[data-page],[data-action]");
  if (!b) return;
  try {
    if (b.dataset.page) {
      if (pendingSale)
        throw Error("Retry the pending checkout before navigating");
      page = b.dataset.page;
      render();
    } else await actions[b.dataset.action]?.(b);
  } catch (err) {
    notice(err.message);
  }
});
document.addEventListener("keydown", (ev) => {
  if (page !== "Counter" || modal.open || !state) return;
  if (ev.key === "F2") {
    ev.preventDefault();
    $("#search")?.focus();
  }
  if (ev.key === "F5") {
    ev.preventDefault();
    $("[data-action=checkout]")?.click();
  }
});
(async () => {
  try {
    const me = await api("/me");
    csrf = me.csrf;
    await refresh();
  } catch {
    if (!$("#login-form")) await loginScreen();
  }
})();
