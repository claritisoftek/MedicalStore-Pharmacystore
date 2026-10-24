import {
  randomBytes,
  pbkdf2Sync,
  timingSafeEqual,
  createHash,
} from "node:crypto";
import { rows, tx } from "./db.js";
import ExcelJS from "exceljs";
import { compatibleWorkbook } from "./workbook.js";
import sharp from "sharp";
export const day = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Karachi",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
export const now = () =>
  `${day()}T${new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Karachi", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(new Date())}`;
export function assert(ok, message) {
  if (!ok) throw Object.assign(new Error(message), { status: 400 });
}
export function text(v, max = 250) {
  assert(typeof v === "string" && v.trim().length <= max, "Invalid text");
  return v.trim();
}
export function integer(v, min = 0) {
  assert(
    /^\d+$/.test(String(v)) &&
      Number.isSafeInteger(Number(v)) &&
      Number(v) >= min &&
      Number(v) <= 100000000,
    "Enter a valid whole quantity",
  );
  return Number(v);
}
export function money(v) {
  assert(
    /^\d+(\.\d{1,2})?$/.test(String(v)),
    "Use a positive amount with up to two decimal places",
  );
  const [a, b = ""] = String(v).split(".");
  const n = Number(a) * 100 + Number(b.padEnd(2, "0"));
  assert(Number.isSafeInteger(n) && n <= 1e11, "Amount out of range");
  return n;
}
export function date(v) {
  assert(
    /^\d{4}-\d\d-\d\d$/.test(String(v)) &&
      !Number.isNaN(Date.parse(v)) &&
      new Date(v).toISOString().slice(0, 10) === v,
    "Invalid date",
  );
  return v;
}
export function passwordHash(value) {
  assert(
    typeof value === "string" && value.length >= 10 && value.length <= 200,
    "Password must contain 10–200 characters",
  );
  const salt = randomBytes(16).toString("hex");
  return (
    salt +
    ":" +
    pbkdf2Sync(value, Buffer.from(salt, "hex"), 600000, 32, "sha256").toString(
      "hex",
    )
  );
}
export function verify(value, encoded) {
  try {
    if (typeof value !== "string" || value.length > 200) return false;
    const [salt, hash] = encoded.split(":");
    const a = pbkdf2Sync(value, Buffer.from(salt, "hex"), 600000, 32, "sha256"),
      b = Buffer.from(hash, "hex");
    return a.length === b.length && timingSafeEqual(a, b);
  } catch {
    return false;
  }
}
export const digest = (s) => createHash("sha256").update(s).digest("hex");
export const tables = [
  "users",
  "settings",
  "products",
  "parties",
  "purchases",
  "batches",
  "sales",
  "sale_lines",
  "payments",
  "expenses",
  "audit",
  "imports",
];
export class Service {
  constructor(pool) {
    this.pool = pool;
  }
  async write(user, fn) {
    return tx(this.pool, async (c) => {
      await rows(c, "SELECT id FROM web_lock WHERE id=1 FOR UPDATE");
      return fn(c);
    });
  }
  async audit(c, user, action, detail = "") {
    await rows(
      c,
      "INSERT INTO audit(created,user_id,action,detail) VALUES(?,?,?,?)",
      [now(), user?.id || null, action, String(detail)],
    );
  }
  async setup(username, password) {
    const name = text(username, 100);
    assert(name, "Username required");
    const hash = passwordHash(password);
    return this.write(null, async (c) => {
      assert(
        !(await rows(c, "SELECT id FROM users LIMIT 1")).length,
        "Already configured",
      );
      await rows(
        c,
        "INSERT INTO users(username,password,role) VALUES(?,?,'Admin')",
        [name, hash],
      );
      await this.audit(c, null, "Initial setup", name);
    });
  }
  async login(username, password) {
    const [user] = await rows(
      this.pool,
      "SELECT * FROM users WHERE username=? AND active=1",
      [text(username, 100)],
    );
    assert(
      user && verify(password, user.password),
      "Incorrect username or password",
    );
    const token = randomBytes(32).toString("hex"),
      csrf = randomBytes(32).toString("hex");
    await rows(this.pool, "DELETE FROM web_sessions WHERE expires<?", [
      Date.now(),
    ]);
    await rows(this.pool, "INSERT INTO web_sessions VALUES(?,?,?,?)", [
      digest(token),
      user.id,
      csrf,
      Date.now() + 8 * 60 * 60 * 1000,
    ]);
    await this.audit(this.pool, user, "Login");
    return {
      token,
      csrf,
      user: { id: user.id, username: user.username, role: user.role },
    };
  }
  async inventory() {
    return rows(
      this.pool,
      `SELECT p.*,COALESCE(SUM(b.quantity),0) stock,COALESCE(SUM(CASE WHEN b.expiry>=? THEN b.quantity ELSE 0 END),0) sellable FROM products p LEFT JOIN batches b ON b.product_id=p.id WHERE p.active=1 GROUP BY p.id ORDER BY p.name`,
      [day()],
    );
  }
  async product(user, v, c = null) {
    const run = async (db) => {
      const a = [
        text(v.sku, 100),
        text(v.name),
        text(v.barcode || "", 100) || null,
        text(v.category || "", 100),
        money(v.price),
        integer(v.reorder ?? 5),
      ];
      assert(a[0] && a[1], "SKU and name required");
      let id = v.id ? integer(v.id, 1) : null;
      if (id) {
        assert(
          (await rows(db, "SELECT id FROM products WHERE id=?", [id])).length,
          "Unknown medicine",
        );
        await rows(
          db,
          "UPDATE products SET sku=?,name=?,barcode=?,category=?,price=?,reorder=? WHERE id=?",
          [...a, id],
        );
      } else
        id = (
          await rows(
            db,
            "INSERT INTO products(sku,name,barcode,category,price,reorder) VALUES(?,?,?,?,?,?)",
            a,
          )
        ).insertId;
      await this.audit(db, user, "Save product", id);
      return id;
    };
    return c ? run(c) : this.write(user, run);
  }
  async party(user, v) {
    assert(["Customer", "Supplier"].includes(v.kind), "Invalid party type");
    assert(
      user.role === "Admin" || v.kind === "Customer",
      "Admin access required",
    );
    const name = text(v.name);
    assert(name, "Name required");
    return this.write(user, async (c) => {
      const r = await rows(
        c,
        "INSERT INTO parties(kind,name,phone,address) VALUES(?,?,?,?)",
        [v.kind, name, text(v.phone || "", 100), text(v.address || "", 1000)],
      );
      await this.audit(c, user, "Create " + v.kind, r.insertId);
      return r.insertId;
    });
  }
  async checkParty(c, id, kind) {
    assert(
      (
        await rows(c, "SELECT id FROM parties WHERE id=? AND kind=?", [
          integer(id, 1),
          kind,
        ])
      ).length,
      kind + " required",
    );
  }
  async purchase(user, v) {
    return this.write(user, async (c) => {
      await this.checkParty(c, v.supplier_id, "Supplier");
      const reference = text(v.reference);
      assert(
        reference &&
          Array.isArray(v.lines) &&
          v.lines.length &&
          v.lines.length <= 500,
        "Reference and 1–500 items required",
      );
      const lines = [];
      let total = 0;
      for (const line of v.lines) {
        const pid = integer(line.product_id, 1),
          quantity = integer(line.quantity, 1),
          cost = money(line.cost),
          expiry = date(line.expiry),
          batch = text(line.batch, 100);
        assert(batch && expiry >= day(), "Batch and unexpired date required");
        assert(
          (
            await rows(c, "SELECT id FROM products WHERE id=? AND active=1", [
              pid,
            ])
          ).length,
          "Unknown medicine",
        );
        total += quantity * cost;
        assert(
          Number.isSafeInteger(total) && total <= 1e13,
          "Bill total too large",
        );
        lines.push([pid, batch, expiry, quantity, cost, quantity]);
      }
      const paid = money(v.paid);
      assert(paid <= total, "Paid exceeds bill");
      const id = (
        await rows(
          c,
          "INSERT INTO purchases(created,supplier_id,reference,total,paid) VALUES(?,?,?,?,?)",
          [now(), v.supplier_id, reference, total, paid],
        )
      ).insertId;
      for (const l of lines)
        await rows(
          c,
          "INSERT INTO batches(purchase_id,product_id,batch,expiry,quantity,cost,original_quantity) VALUES(?,?,?,?,?,?,?)",
          [id, ...l],
        );
      await this.audit(c, user, "Purchase", id);
      return id;
    });
  }
  async sell(user, v) {
    assert(
      typeof v.request_key === "string" &&
        /^[a-zA-Z0-9-]{16,90}$/.test(v.request_key),
      "Checkout request key required",
    );
    return this.write(user, async (c) => {
      const existing = await rows(
        c,
        "SELECT sale_id,user_id FROM web_requests WHERE request_key=?",
        [v.request_key],
      );
      if (existing.length) {
        assert(existing[0].user_id === user.id, "Invalid request key");
        return existing[0].sale_id;
      }
      const customer = v.customer_id ? integer(v.customer_id, 1) : null;
      if (customer) await this.checkParty(c, customer, "Customer");
      assert(
        Array.isArray(v.lines) && v.lines.length && v.lines.length <= 500,
        "Cart must contain 1–500 items",
      );
      const wanted = new Map();
      for (const l of v.lines) {
        const p = integer(l.product_id, 1);
        wanted.set(p, (wanted.get(p) || 0) + integer(l.quantity, 1));
      }
      let subtotal = 0;
      const allocations = [];
      for (const [pid, q] of [...wanted].sort((a, b) => a[0] - b[0])) {
        const [p] = await rows(
          c,
          "SELECT * FROM products WHERE id=? AND active=1",
          [pid],
        );
        assert(p, "Unknown medicine");
        let left = q;
        for (const b of await rows(
          c,
          "SELECT * FROM batches WHERE product_id=? AND expiry>=? AND quantity>0 ORDER BY expiry,id FOR UPDATE",
          [pid, day()],
        )) {
          const take = Math.min(left, b.quantity);
          allocations.push([b.id, take, p.price, b.cost]);
          left -= take;
          if (!left) break;
        }
        assert(!left, "Insufficient unexpired stock: " + p.name);
        subtotal += q * p.price;
      }
      assert(
        Number.isSafeInteger(subtotal) && subtotal <= 1e13,
        "Sale total too large",
      );
      if (v.expected_subtotal !== undefined)
        assert(
          v.expected_subtotal === subtotal,
          "Catalogue prices changed. Refresh records and review this cart before retrying.",
        );
      const discount = money(v.discount),
        tender = money(v.tender);
      assert(discount <= subtotal, "Discount exceeds subtotal");
      const total = subtotal - discount,
        paid = Math.min(tender, total);
      assert(customer || paid === total, "Select a customer for a credit sale");
      const id = (
        await rows(
          c,
          "INSERT INTO sales(created,user_id,customer_id,subtotal,discount,total,paid) VALUES(?,?,?,?,?,?,?)",
          [now(), user.id, customer, subtotal, discount, total, paid],
        )
      ).insertId;
      for (const [batch, q, price, cost] of allocations) {
        await rows(c, "UPDATE batches SET quantity=quantity-? WHERE id=?", [
          q,
          batch,
        ]);
        await rows(
          c,
          "INSERT INTO sale_lines(sale_id,batch_id,quantity,price,cost) VALUES(?,?,?,?,?)",
          [id, batch, q, price, cost],
        );
      }
      await rows(c, "INSERT INTO web_requests VALUES(?,?,?)", [
        v.request_key,
        id,
        user.id,
      ]);
      await this.audit(c, user, "Sale", id);
      return id;
    });
  }
  async balance(c, id) {
    const [p] = await rows(c, "SELECT kind FROM parties WHERE id=?", [id]);
    assert(p, "Unknown party");
    const customer = p.kind === "Customer";
    const [r] = await rows(
      c,
      `SELECT COALESCE(SUM(total-paid),0) owed FROM ${customer ? "sales" : "purchases"} WHERE ${customer ? "customer_id" : "supplier_id"}=? ${customer ? "AND status='Posted'" : ""}`,
      [id],
    );
    const [paid] = await rows(
      c,
      "SELECT COALESCE(SUM(amount),0) paid FROM payments WHERE party_id=?",
      [id],
    );
    return Number(r.owed) - Number(paid.paid);
  }
  async parties() {
    const list = await rows(this.pool, "SELECT * FROM parties ORDER BY name");
    for (const p of list) p.balance = await this.balance(this.pool, p.id);
    return list;
  }
  async payment(user, v) {
    return this.write(user, async (c) => {
      const id = integer(v.party_id, 1),
        amount = money(v.amount);
      assert(
        amount > 0 && amount <= (await this.balance(c, id)),
        "Payment must be positive and no more than the balance",
      );
      await rows(
        c,
        "INSERT INTO payments(created,party_id,amount,note) VALUES(?,?,?,?)",
        [now(), id, amount, text(v.note || "", 1000)],
      );
      await this.audit(c, user, "Payment", id);
    });
  }
  async expense(user, v) {
    const amount = money(v.amount),
      category = text(v.category, 100);
    assert(amount > 0 && category, "Category and positive amount required");
    return this.write(user, async (c) => {
      await rows(
        c,
        "INSERT INTO expenses(created,category,note,amount) VALUES(?,?,?,?)",
        [now(), category, text(v.note || "", 1000), amount],
      );
      await this.audit(c, user, "Expense", category);
    });
  }
  async void(user, id) {
    return this.write(user, async (c) => {
      const [sale] = await rows(c, "SELECT * FROM sales WHERE id=?", [
        integer(id, 1),
      ]);
      assert(
        sale && sale.status === "Posted" && sale.created.slice(0, 10) === day(),
        "Only posted same-day sales can be cancelled",
      );
      if (sale.customer_id)
        assert(
          (await this.balance(c, sale.customer_id)) >= sale.total - sale.paid,
          "Later payments prevent cancellation",
        );
      for (const l of await rows(
        c,
        "SELECT * FROM sale_lines WHERE sale_id=?",
        [id],
      ))
        await rows(c, "UPDATE batches SET quantity=quantity+? WHERE id=?", [
          l.quantity,
          l.batch_id,
        ]);
      await rows(c, "UPDATE sales SET status='Void' WHERE id=?", [id]);
      await this.audit(c, user, "Void sale", id);
    });
  }
  async report(from, to) {
    date(from);
    date(to);
    assert(from <= to, "Invalid date range");
    const range = [from + "T00:00:00", to + "T23:59:59"];
    return tx(this.pool, async (db) => {
      const [s] = await rows(
        db,
        "SELECT COALESCE(SUM(total),0) revenue,COALESCE(SUM(paid),0) sale_cash FROM sales WHERE status='Posted' AND created BETWEEN ? AND ?",
        range,
      );
      const [c] = await rows(
        db,
        "SELECT COALESCE(SUM(l.quantity*l.cost),0) cogs FROM sale_lines l JOIN sales s ON s.id=l.sale_id WHERE s.status='Posted' AND s.created BETWEEN ? AND ?",
        range,
      );
      const [e] = await rows(
        db,
        "SELECT COALESCE(SUM(amount),0) expenses FROM expenses WHERE created BETWEEN ? AND ?",
        range,
      );
      const [p] = await rows(
        db,
        "SELECT COALESCE(SUM(paid),0) purchase_cash FROM purchases WHERE created BETWEEN ? AND ?",
        range,
      );
      const [pay] = await rows(
        db,
        "SELECT COALESCE(SUM(CASE WHEN p.kind='Customer' THEN m.amount ELSE -m.amount END),0) cash FROM payments m JOIN parties p ON p.id=m.party_id WHERE m.created BETWEEN ? AND ?",
        range,
      );
      return {
        from,
        to,
        revenue: Number(s.revenue),
        cogs: Number(c.cogs),
        expenses: Number(e.expenses),
        profit: Number(s.revenue) - Number(c.cogs) - Number(e.expenses),
        cash:
          Number(s.sale_cash) -
          Number(p.purchase_cash) +
          Number(pay.cash) -
          Number(e.expenses),
      };
    });
  }
  async profile(user, v) {
    const allowed = ["name", "tagline", "address", "phone", "email", "footer"];
    let logo;
    if (v.logo !== undefined) {
      assert(typeof v.logo === "string", "Invalid logo");
      if (v.logo === "") logo = "";
      else {
        assert(
          /^data:image\/(png|jpeg);base64,/.test(v.logo) && v.logo.length < 7e6,
          "Use PNG/JPEG smaller than 5 MB",
        );
        const input = Buffer.from(v.logo.split(",")[1], "base64");
        assert(input.length <= 5 * 1024 * 1024, "Logo exceeds 5 MB");
        const metadata = await sharp(input, {
          limitInputPixels: 12000000,
        }).metadata();
        assert(
          ["png", "jpeg"].includes(metadata.format),
          "Only actual PNG or JPEG files are supported",
        );
        const out = await sharp(input, { limitInputPixels: 12000000 })
          .rotate()
          .resize(512, 512, { fit: "inside", withoutEnlargement: true })
          .png()
          .toBuffer();
        logo = "data:image/png;base64," + out.toString("base64");
      }
    }
    return this.write(user, async (c) => {
      for (const key of allowed)
        if (v[key] !== undefined)
          await rows(
            c,
            "INSERT INTO settings(`key`,value) VALUES(?,?) ON DUPLICATE KEY UPDATE value=VALUES(value)",
            [key, text(v[key], 1000)],
          );
      if (logo !== undefined)
        await rows(
          c,
          "INSERT INTO settings(`key`,value) VALUES('logo',?) ON DUPLICATE KEY UPDATE value=VALUES(value)",
          [logo],
        );
      await this.audit(c, user, "Company profile");
    });
  }
  async importRows(buffer) {
    assert(buffer.length <= 5 * 1024 * 1024, "Workbook exceeds 5 MB");
    const w = new ExcelJS.Workbook();
    try {
      await w.xlsx.load(await compatibleWorkbook(buffer));
    } catch {
      assert(
        false,
        "Cannot read this Excel workbook. Save it as an Excel Workbook (.xlsx) and upload it again. Password-protected or damaged files are not supported.",
      );
    }
    const sheet = w.worksheets[0];
    assert(
      w.worksheets.length === 1 && sheet && sheet.rowCount <= 5001,
      "Use one sheet with at most 5,000 rows",
    );
    const headers = [
      "sku",
      "name",
      "barcode",
      "category",
      "price",
      "reorder",
      "batch",
      "expiry",
      "quantity",
      "cost",
    ];
    assert(
      headers.every(
        (x, i) =>
          sheet
            .getRow(1)
            .getCell(i + 1)
            .text.trim()
            .toLowerCase() === x,
      ),
      "Columns must be: " + headers.join(", "),
    );
    const result = [];
    sheet.eachRow((row, n) => {
      if (n === 1) return;
      const item = {};
      headers.forEach((key, i) => {
        const cell = row.getCell(i + 1);
        assert(!cell.formula, "Formulas are not supported");
        item[key] =
          cell.value instanceof Date
            ? cell.value.toISOString().slice(0, 10)
            : cell.text.trim();
      });
      assert(
        item.sku && item.name && item.batch,
        "Missing required cell at row " + n,
      );
      text(item.sku, 100);
      text(item.name);
      text(item.barcode, 100);
      text(item.category, 100);
      text(item.batch, 100);
      money(item.price);
      money(item.cost);
      integer(item.reorder);
      integer(item.quantity, 1);
      assert(date(item.expiry) >= day(), "Expired stock at row " + n);
      result.push(item);
    });
    assert(result.length, "Workbook is empty");
    return result;
  }
  async import(user, buffer) {
    const list = await this.importRows(buffer),
      hash = digest(buffer);
    return this.write(user, async (c) => {
      assert(
        !(await rows(c, "SELECT id FROM imports WHERE digest=?", [hash]))
          .length,
        "This workbook was already imported",
      );
      for (const v of list) {
        const [p] = await rows(c, "SELECT * FROM products WHERE sku=?", [
          v.sku,
        ]);
        let pid = p?.id;
        if (p) {
          assert(
            p.name === v.name &&
              p.price === money(v.price) &&
              (p.barcode || "") === v.barcode &&
              p.category === v.category &&
              p.reorder === integer(v.reorder),
            "Existing medicine differs from workbook: " + v.sku,
          );
        } else pid = await this.product(user, v, c);
        await rows(
          c,
          "INSERT INTO batches(product_id,purchase_id,batch,expiry,quantity,cost,original_quantity) VALUES(?,NULL,?,?,?,?,?)",
          [
            pid,
            v.batch,
            v.expiry,
            integer(v.quantity, 1),
            money(v.cost),
            integer(v.quantity, 1),
          ],
        );
      }
      await rows(
        c,
        "INSERT INTO imports(digest,created,`rows`) VALUES(?,?,?)",
        [hash, now(), list.length],
      );
      await this.audit(c, user, "Excel import", list.length);
      return list.length;
    });
  }
  async snapshot(c) {
    const data = {};
    for (const table of tables)
      data[table] = await rows(c, `SELECT * FROM \`${table}\``);
    return { format: "pharmacy-web", version: 1, created: now(), data };
  }
  async backup(user) {
    return this.write(user, async (c) => {
      const data = await this.snapshot(c);
      await this.audit(c, user, "Backup download");
      return data;
    });
  }
  async restore(user, backup, password) {
    const [u] = await rows(this.pool, "SELECT password FROM users WHERE id=?", [
      user.id,
    ]);
    assert(verify(password, u.password), "Current password required");
    assert(
      backup?.format === "pharmacy-web" && backup.version === 1 && backup.data,
      "Unsupported web backup",
    );
    for (const table of tables)
      assert(
        Array.isArray(backup.data[table]) &&
          backup.data[table].length <= 100000,
        "Invalid backup table: " + table,
      );
    assert(
      backup.data.users.some((u) => u.role === "Admin" && u.active === 1),
      "Backup needs an active Admin",
    );
    for (const u of backup.data.users)
      assert(
        /^[a-f0-9]{32}:[a-f0-9]{64}$/.test(u.password),
        "Invalid account password hash in backup",
      );
    for (const b of backup.data.batches)
      assert(
        Number.isSafeInteger(b.quantity) &&
          b.quantity >= 0 &&
          b.quantity <= b.original_quantity,
        "Invalid batch quantity in backup",
      );
    const saleTotals = new Map(),
      purchaseTotals = new Map();
    for (const l of backup.data.sale_lines)
      saleTotals.set(
        l.sale_id,
        (saleTotals.get(l.sale_id) || 0) + l.quantity * l.price,
      );
    for (const b of backup.data.batches)
      if (b.purchase_id !== null)
        purchaseTotals.set(
          b.purchase_id,
          (purchaseTotals.get(b.purchase_id) || 0) +
            b.original_quantity * b.cost,
        );
    for (const s of backup.data.sales) {
      const subtotal = saleTotals.get(s.id) || 0;
      assert(
        Number.isSafeInteger(subtotal) &&
          subtotal === s.subtotal &&
          s.total === s.subtotal - s.discount &&
          s.paid >= 0 &&
          s.paid <= s.total,
        "Inconsistent sale totals in backup",
      );
    }
    for (const p of backup.data.purchases) {
      const total = purchaseTotals.get(p.id) || 0;
      assert(
        Number.isSafeInteger(total) && total === p.total,
        "Inconsistent vendor bill totals in backup",
      );
    }
    return this.write(user, async (c) => {
      for (const table of tables) {
        const cols = (await rows(c, `SHOW COLUMNS FROM \`${table}\``))
          .map((x) => x.Field)
          .sort();
        for (const row of backup.data[table])
          assert(
            JSON.stringify(Object.keys(row).sort()) === JSON.stringify(cols),
            "Invalid columns in " + table,
          );
      }
      const safety = JSON.stringify(await this.snapshot(c));
      await rows(c, "INSERT INTO web_backups(created,content) VALUES(?,?)", [
        now(),
        safety,
      ]);
      await rows(c, "DELETE FROM web_requests");
      await rows(c, "DELETE FROM web_sessions");
      for (const table of [...tables].reverse())
        await rows(c, `DELETE FROM \`${table}\``);
      for (const table of tables)
        for (const row of backup.data[table]) {
          const cols = Object.keys(row);
          await rows(
            c,
            `INSERT INTO \`${table}\` (${cols.map((k) => "`" + k + "`").join(",")}) VALUES (${cols.map(() => "?").join(",")})`,
            cols.map((k) => row[k]),
          );
        }
      await this.audit(
        c,
        null,
        "Restore completed",
        "All sessions invalidated; safety snapshot stored",
      );
    });
  }
}
