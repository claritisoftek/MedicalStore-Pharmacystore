import { test } from "node:test";
import assert from "node:assert/strict";
import { createPool, initialize, rows } from "../db.js";
import { createApp } from "../../server.js";
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
          ]);
          sheet.addRow([
            "IMPORTED",
            "Imported medicine",
            "999",
            "Medicine",
            10,
            5,
            "OPENING",
            "2099-12-31",
            20,
            5,
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
        "Invalid restore rolls back; valid restore retains safety backup and signs out",
        async () => {
          const backup = (await request("/api/backup")).body;
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
        },
      );
    } finally {
      await new Promise((r) => server.close(r));
    }
  },
);
