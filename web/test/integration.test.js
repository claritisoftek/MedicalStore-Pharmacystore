import { test } from "node:test";
import assert from "node:assert/strict";
import { createPool, initialize, rows } from "../db.js";
import { createApp } from "../../web-server.js";
import { Service, day, tables } from "../service.js";
import ExcelJS from "exceljs";
import { randomUUID } from "node:crypto";
const enabled = process.env.RUN_DB_TESTS === "1";
test(
  "MySQL end-to-end security, FEFO, rollback, checkout retry, reports, imports and restore",
  { skip: !enabled },
  async (t) => {
    assert.match(
      process.env.DB_NAME || "",
      /_test$/,
      "Use a dedicated database ending _test",
    );
    const pool = createPool();
    t.after(async () => pool.end());
    await initialize(pool);
    await rows(pool, "DELETE FROM web_requests");
    await rows(pool, "DELETE FROM web_sessions");
    for (const table of [...tables].reverse())
      await rows(pool, `DELETE FROM \`${table}\``);
    await rows(pool, "DELETE FROM web_backups");
    await t.test(
      "Version 1 migration preserves records and is repeatable",
      async () => {
        await pool.query(
          "ALTER TABLE products DROP COLUMN brand, DROP COLUMN prescription, DROP COLUMN variant",
        );
        await pool.query("ALTER TABLE parties DROP COLUMN active");
        await pool.query(
          "ALTER TABLE users MODIFY role ENUM('Admin','Cashier') NOT NULL",
        );
        await rows(pool, "UPDATE web_meta SET version=1");
        await rows(
          pool,
          "INSERT INTO products(sku,name,price,reorder) VALUES('LEGACY','Legacy medicine',100,5)",
        );
        await rows(
          pool,
          "INSERT INTO parties(kind,name,address) VALUES('Customer','Legacy customer','')",
        );
        await initialize(pool);
        await initialize(pool);
        const [legacy] = await rows(
          pool,
          "SELECT * FROM products WHERE sku='LEGACY'",
        );
        assert.equal(legacy.name, "Legacy medicine");
        assert.equal(legacy.price, 100);
        assert.equal(legacy.brand, "");
        assert.equal(legacy.prescription, null);
        assert.equal(
          (
            await rows(
              pool,
              "SELECT active FROM parties WHERE name='Legacy customer'",
            )
          )[0].active,
          1,
        );
        await rows(pool, "DELETE FROM web_backups");
        await rows(pool, "DELETE FROM products");
        await rows(pool, "DELETE FROM parties");
      },
    );
    const app = await createApp(pool, {
        APP_URL: "http://localhost:3000",
        SETUP_TOKEN: "test-token-which-is-longer-than-32-characters",
      }),
      server = app.listen(0, "127.0.0.1");
    await new Promise((r) => server.once("listening", r));
    const base = "http://127.0.0.1:" + server.address().port;
    let cookie = "",
      csrf = "";
    async function request(path, data, options = {}) {
      const res = await fetch(base + path, {
        method: data === undefined ? "GET" : "POST",
        headers: {
          ...(data === undefined
            ? {}
            : {
                "Content-Type": "application/json",
                Origin: "http://localhost:3000",
              }),
          Cookie: cookie,
          "X-CSRF-Token": csrf,
          ...options.headers,
        },
        body: data === undefined ? undefined : JSON.stringify(data),
      });
      const body = res.headers.get("content-type")?.includes("application/json")
        ? await res.json()
        : await res.text();
      return { res, body };
    }
    try {
      await t.test(
        "Setup token, login cookie and CSRF protection",
        async () => {
          assert.equal((await request("/api/state")).res.status, 401);
          assert.equal(
            (
              await request("/api/setup", {
                token: "bad",
                username: "Admin",
                password: "test-password",
              })
            ).res.status,
            400,
          );
          assert.equal(
            (
              await request("/api/setup", {
                token: "test-token-which-is-longer-than-32-characters",
                username: "Admin",
                password: "test-password",
              })
            ).res.status,
            200,
          );
          const login = await request("/api/login", {
            username: "Admin",
            password: "test-password",
          });
          assert.equal(login.res.status, 200);
          assert.match(login.res.headers.get("set-cookie"), /HttpOnly/);
          cookie = login.res.headers.get("set-cookie").split(";")[0];
          csrf = login.body.csrf;
          assert.equal(
            (
              await request(
                "/api/products",
                {},
                { headers: { "X-CSRF-Token": "" } },
              )
            ).res.status,
            403,
          );
          assert.equal(
            (
              await request(
                "/api/products",
                {},
                { headers: { Origin: "https://evil.example" } },
              )
            ).res.status,
            403,
          );
        },
      );
      let pid, supplier, customer;
      await t.test(
        "Empty database then medicine, parties and vendor bill",
        async () => {
          assert.equal((await request("/api/state")).body.products.length, 0);
          pid = (
            await request("/api/products", {
              brand: "Test manufacturer",
              prescription: "no",
              variant: "Tablet",
              sku: "TEST",
              name: "Test medicine",
              barcode: "123",
              category: "Medicine",
              price: "12.50",
              reorder: 5,
            })
          ).body.id;
          supplier = (
            await request("/api/parties", { kind: "Supplier", name: "Vendor" })
          ).body.id;
          customer = (
            await request("/api/parties", {
              kind: "Customer",
              name: "Customer",
            })
          ).body.id;
          assert(pid && supplier && customer);
          const bill = await request("/api/purchases", {
            supplier_id: supplier,
            reference: "Bill-1",
            paid: "0",
            lines: [
              {
                product_id: pid,
                batch: "LATER",
                expiry: "2099-12-31",
                quantity: 10,
                cost: "6",
              },
              {
                product_id: pid,
                batch: "EARLIER",
                expiry: "2098-12-31",
                quantity: 4,
                cost: "5",
              },
            ],
          });
          assert.equal(bill.res.status, 200);
        },
      );
      let sale;
      await t.test(
        "Sale allocates FEFO, returns change and retries only once",
        async () => {
          const data = {
            request_key: randomUUID(),
            lines: [{ product_id: pid, quantity: 5 }],
            customer_id: customer,
            discount: "2.50",
            tender: "100",
          };
          const a = await request("/api/sales", data);
          assert.equal(a.res.status, 200, JSON.stringify(a.body));
          sale = a.body.id;
          assert.equal((await request("/api/sales", data)).body.id, sale);
          const [stored] = await rows(pool, "SELECT * FROM sales WHERE id=?", [
            sale,
          ]);
          assert.equal(stored.total, 6000);
          assert.equal(stored.paid, 6000);
          const batches = await rows(
            pool,
            "SELECT batch,quantity FROM batches ORDER BY expiry",
          );
          assert.equal(batches[0].quantity, 0);
          assert.equal(batches[1].quantity, 9);
          assert.equal((await rows(pool, "SELECT id FROM sales")).length, 1);
        },
      );
      await t.test(
        "Insufficient stock rolls back; concurrent requests cannot oversell",
        async () => {
          assert.equal(
            (
              await request("/api/sales", {
                request_key: randomUUID(),
                lines: [{ product_id: pid, quantity: 1 }],
                expected_subtotal: 1,
                discount: "0",
                tender: "100",
              })
            ).res.status,
            400,
          );
          const before = (
            await rows(pool, "SELECT SUM(quantity) n FROM batches")
          )[0].n;
          assert.equal(
            (
              await request("/api/sales", {
                request_key: randomUUID(),
                lines: [{ product_id: pid, quantity: 999 }],
                discount: "0",
                tender: "999999",
              })
            ).res.status,
            400,
          );
          assert.equal(
            (await rows(pool, "SELECT SUM(quantity) n FROM batches"))[0].n,
            before,
          );
          const results = await Promise.all(
            [1, 2].map(() =>
              request("/api/sales", {
                request_key: randomUUID(),
                lines: [{ product_id: pid, quantity: 6 }],
                discount: "0",
                tender: "100",
              }),
            ),
          );
          assert.deepEqual(results.map((x) => x.res.status).sort(), [200, 400]);
        },
      );
      await t.test("Reports, logo normalization and print routes", async () => {
        const result = await request(
          "/api/report?from=" + day() + "&to=" + day(),
        );
        assert.equal(result.res.status, 200);
        assert(result.body.revenue > 0);
        assert.equal(
          (await request("/print/sale/" + sale + "?size=58")).res.status,
          200,
        );
        assert.equal(
          (await request("/print/report/0?from=" + day() + "&to=" + day())).res
            .status,
          200,
        );
        const sharp = (await import("sharp")).default;
        const logo = await sharp({
          create: { width: 20, height: 20, channels: 4, background: "#24573e" },
        })
          .png()
          .toBuffer();
        assert.equal(
          (
            await request("/api/profile", {
              name: "Test pharmacy",
              logo: "data:image/png;base64," + logo.toString("base64"),
            })
          ).res.status,
          200,
        );
        assert.match(
          (await request("/api/state")).body.profile.logo,
          /^data:image\/png;base64,/,
        );
      });
      await t.test(
        "Customer credit, payment limits, expenses and same-day cancellation",
        async () => {
          const credit = await request("/api/sales", {
            request_key: randomUUID(),
            lines: [{ product_id: pid, quantity: 1 }],
            customer_id: customer,
            discount: "0",
            tender: "0",
          });
          assert.equal(credit.res.status, 200);
          assert.equal(
            (
              await request("/api/payments", {
                party_id: customer,
                amount: "20",
                note: "Too much",
              })
            ).res.status,
            400,
          );
          assert.equal(
            (
              await request("/api/payments", {
                party_id: customer,
                amount: "2.50",
                note: "Collection",
              })
            ).res.status,
            200,
          );
          assert.equal(
            (await request(`/api/sales/${credit.body.id}/void`, {})).res.status,
            400,
          );
          assert.equal(
            (
              await request("/api/expenses", {
                category: "Rent",
                amount: "10",
                note: "Test",
              })
            ).res.status,
            200,
          );
          assert.equal(
            (await request(`/api/sales/${sale}/void`, {})).res.status,
            200,
          );
        },
      );
      await t.test(
        "Atomic Excel import and duplicate-file prevention",
        async () => {
          const book = new ExcelJS.Workbook(),
            sheet = book.addWorksheet("Opening");
          sheet.addRow([
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
            "brand",
            "prescription",
            "variant",
          ]);
          sheet.addRow([
            "IMPORTED",
            "Imported medicine with a long name, strength and pack description to exercise wrapping across narrow catalogue panels and preserve visible price and Add controls",
            "999",
            "Medicine",
            10,
            5,
            "OPENING",
            "2099-12-31",
            20,
            5,
            "Test brand",
            "no",
            "",
          ]);
          const file = Buffer.from(await book.xlsx.writeBuffer()).toString(
            "base64",
          );
          assert.equal(
            (await request("/api/import/preview", { file })).body.rows,
            1,
          );
          assert.equal(
            (await request("/api/import/apply", { file })).res.status,
            200,
          );
          assert.equal(
            (await request("/api/import/apply", { file })).res.status,
            400,
          );
        },
      );
      await t.test(
        "Cashier authorization is enforced by the server",
        async () => {
          await request("/api/users", {
            username: "Cashier",
            password: "cashier-password",
            role: "Cashier",
          });
          const old = [cookie, csrf],
            login = await request("/api/login", {
              username: "Cashier",
              password: "cashier-password",
            });
          cookie = login.res.headers.get("set-cookie").split(";")[0];
          csrf = login.body.csrf;
          for (const path of [
            "/api/products",
            "/api/profile",
            "/api/purchases",
            "/api/restore",
            "/api/users",
          ])
            assert.equal((await request(path, {})).res.status, 403);
          assert.equal((await request("/api/backup")).res.status, 403);
          assert(
            !(await request("/api/state")).body.parties.some(
              (p) => p.kind === "Supplier",
            ),
          );
          [cookie, csrf] = old;
        },
      );
      await t.test(
        "Product metadata and reversible customer corrections are enforced",
        async () => {
          const invalid = {
            sku: "MISSING",
            name: "Missing metadata",
            price: "10",
            reorder: 5,
          };
          assert.equal(
            (await request("/api/products", invalid)).res.status,
            400,
          );
          assert.equal(
            (await request("/api/products", { ...invalid, brand: "Brand" })).res
              .status,
            400,
          );
          const before = await rows(pool, "SELECT COUNT(*) n FROM sales");
          assert.equal(
            (
              await request(`/api/parties/${customer}`, {
                name: "Corrected customer",
                phone: "123",
                address: "Updated",
              })
            ).res.status,
            200,
          );
          assert.equal(
            (await request(`/api/parties/${customer}`, { active: 0 })).res
              .status,
            200,
          );
          assert.equal(
            (
              await request("/api/sales", {
                request_key: randomUUID(),
                customer_id: customer,
                lines: [{ product_id: pid, quantity: 1 }],
                discount: "0",
                tender: "0",
              })
            ).res.status,
            400,
          );
          assert.deepEqual(
            await rows(pool, "SELECT COUNT(*) n FROM sales"),
            before,
          );
          assert.equal(
            (await request(`/api/parties/${customer}`, { active: 1 })).res
              .status,
            200,
          );
          assert.equal(
            (await request("/api/parties/999999", { active: 0 })).res.status,
            400,
          );
          assert.equal(
            (
              await request("/api/payments", {
                party_id: supplier,
                amount: "1",
                note: "Vendor payment test",
              })
            ).res.status,
            200,
          );
        },
      );
      await t.test(
        "Manager and IT roles are isolated and revocation ends sessions",
        async () => {
          const adminSession = [cookie, csrf],
            adminId = (await request("/api/me")).body.user.id;
          for (const role of ["Manager", "IT"])
            assert.equal(
              (
                await request("/api/users", {
                  username: role,
                  password: "role-test-password",
                  role,
                })
              ).res.status,
              200,
            );
          assert.equal(
            (
              await request(`/api/users/${adminId}`, {
                username: "Admin",
                role: "Cashier",
                active: 1,
              })
            ).res.status,
            400,
          );
          const signin = async (name) => {
            const login = await request("/api/login", {
              username: name,
              password: "role-test-password",
            });
            assert.equal(login.res.status, 200);
            cookie = login.res.headers.get("set-cookie").split(";")[0];
            csrf = login.body.csrf;
          };
          await signin("Manager");
          const managerId = (await request("/api/me")).body.user.id,
            managerSession = [cookie, csrf];
          assert.equal(
            (await request("/api/report?from=" + day() + "&to=" + day())).res
              .status,
            200,
          );
          assert.equal((await request("/api/backup")).res.status, 403);
          assert.equal((await request("/api/users", {})).res.status, 403);
          const managerState = (await request("/api/state")).body;
          assert(managerState.batches);
          assert(!managerState.users);
          assert(!managerState.audit);
          await signin("IT");
          const itState = (await request("/api/state")).body;
          assert(itState.users);
          assert(!itState.batches);
          assert.equal(itState.products.length, 0);
          assert.equal(itState.sales.length, 0);
          assert.equal(
            (await request("/api/report?from=" + day() + "&to=" + day())).res
              .status,
            403,
          );
          for (const path of [
            "/api/products",
            "/api/sales",
            "/api/purchases",
            "/api/expenses",
            "/api/restore",
          ])
            assert.equal((await request(path, {})).res.status, 403, path);
          assert.equal(
            (
              await request("/api/users", {
                username: "ForbiddenAdmin",
                role: "Admin",
                password: "role-test-password",
              })
            ).res.status,
            400,
          );
          assert.equal(
            (
              await request(`/api/users/${adminId}`, {
                username: "Admin",
                role: "IT",
                active: 1,
              })
            ).res.status,
            400,
          );
          assert.equal(
            (
              await request(`/api/users/${managerId}`, {
                username: "Manager",
                role: "Manager",
                active: 0,
              })
            ).res.status,
            200,
          );
          [cookie, csrf] = managerSession;
          assert.equal((await request("/api/state")).res.status, 401);
          [cookie, csrf] = adminSession;
          assert.equal(
            (
              await request(`/api/users/${managerId}`, {
                username: "Manager",
                role: "Manager",
                active: 1,
              })
            ).res.status,
            200,
          );
        },
      );
      await t.test(
        "Invalid restore rolls back; valid restore retains safety backup and signs out",
        async () => {
          const backup = (await request("/api/backup")).body;
          const totalsBroken = structuredClone(backup);
          totalsBroken.data.sales[0].total += 1;
          assert.equal(
            (
              await request("/api/restore", {
                backup: totalsBroken,
                password: "test-password",
              })
            ).res.status,
            400,
          );
          const broken = structuredClone(backup);
          broken.data.batches[0].product_id = 999999;
          assert.equal(
            (
              await request("/api/restore", {
                backup: broken,
                password: "test-password",
              })
            ).res.status,
            500,
          );
          assert.equal((await request("/api/state")).res.status, 200);
          assert.equal(
            (
              await request("/api/restore", {
                backup,
                password: "test-password",
              })
            ).res.status,
            200,
          );
          assert.equal((await request("/api/state")).res.status, 401);
          assert.equal(
            (await rows(pool, "SELECT id FROM web_backups")).length,
            1,
          );
          const legacy = structuredClone(backup);
          legacy.version = 1;
          for (const p of legacy.data.products) {
            delete p.brand;
            delete p.prescription;
            delete p.variant;
          }
          for (const p of legacy.data.parties) delete p.active;
          const relogin = await request("/api/login", {
            username: "Admin",
            password: "test-password",
          });
          cookie = relogin.res.headers.get("set-cookie").split(";")[0];
          csrf = relogin.body.csrf;
          assert.equal(
            (
              await request("/api/restore", {
                backup: legacy,
                password: "test-password",
              })
            ).res.status,
            200,
          );
          assert.equal(
            (await rows(pool, "SELECT prescription FROM products LIMIT 1"))[0]
              .prescription,
            null,
          );
        },
      );
    } finally {
      await new Promise((r) => server.close(r));
    }
  },
);
