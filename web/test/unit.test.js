import { test } from "node:test";
import assert from "node:assert/strict";
import {
  money,
  integer,
  date,
  passwordHash,
  verify,
  day,
  Service,
} from "../service.js";
import { documentHtml } from "../printing.js";
import ExcelJS from "exceljs";
test("Exact paisa conversion rejects rounding, negative and overflow", () => {
  assert.equal(money("12.50"), 1250);
  assert.equal(money("0.01"), 1);
  for (const v of ["1.001", "-1", "Infinity", "1e3", "NaN", "1000000001"])
    assert.throws(() => money(v));
});
test("Quantities and dates validate strictly", () => {
  assert.equal(integer("12", 1), 12);
  for (const v of ["1.2", "-1", "1e3"]) assert.throws(() => integer(v));
  assert.throws(() => date("2026-02-30"));
  assert.equal(date("2028-02-29"), "2028-02-29");
  assert.match(day(), /^\d{4}-\d\d-\d\d$/);
});
test("Password hashes use salted PBKDF2 and reject incorrect password", () => {
  const h = passwordHash("correct-password");
  assert(verify("correct-password", h));
  assert(!verify("incorrect-password", h));
  assert.notEqual(h, passwordHash("correct-password"));
  assert.throws(() => passwordHash("short"));
});
test("Print output escapes company and medicine content", () => {
  const html = documentHtml(
    "sale",
    {
      id: 1,
      created: "2026-10-21",
      lines: [
        {
          name: "<script>alert(1)</script>",
          batch: "b",
          expiry: "2028-01-01",
          quantity: 1,
          price: 100,
        },
      ],
      total: 100,
      subtotal: 100,
      discount: 0,
      paid: 100,
    },
    { name: "<img src=x onerror=alert(1)>", logo: "javascript:alert(1)" },
    "80",
  );
  assert(!html.includes("<script>alert"));
  assert(!html.includes('src="javascript:'));
  assert(html.includes("&lt;script&gt;"));
  assert(html.includes("PKR 1.00"));
});
test("Excel validation rejects formulas and expired inventory", async () => {
  const service = new Service(null),
    book = new ExcelJS.Workbook(),
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
    "A",
    "Medicine",
    "",
    "Medicine",
    12.5,
    5,
    "B",
    "2099-12-31",
    10,
    8,
    "Test brand",
    "no",
    "",
  ]);
  let buffer = Buffer.from(await book.xlsx.writeBuffer());
  assert.equal((await service.importRows(buffer)).length, 1);
  sheet.getRow(2).getCell(5).value = { formula: "1+1", result: 2 };
  buffer = Buffer.from(await book.xlsx.writeBuffer());
  await assert.rejects(() => service.importRows(buffer), /Formulas/);
});

test("Logo uploads cannot disguise SVG as PNG", async () => {
  const service = new Service(null);
  const svg = Buffer.from(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"></svg>',
  );
  await assert.rejects(
    () =>
      service.profile(
        { id: 1 },
        { logo: "data:image/png;base64," + svg.toString("base64") },
      ),
    /Only actual PNG/,
  );
});

test("Excel import accepts prefixed SpreadsheetML and reports unreadable files", async () => {
  const { default: JSZip } = await import("jszip");
  const { normalizeSpreadsheetXml } = await import("../workbook.js");
  const service = new Service(null),
    book = new ExcelJS.Workbook();
  const sheet = book.addWorksheet("Opening");
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
    "PREFIX",
    "Medicine & <care>",
    "",
    "Medicine",
    12.5,
    5,
    "B",
    "2099-12-31",
    10,
    8,
    "Test brand",
    "no",
    "",
  ]);
  const zip = await JSZip.loadAsync(await book.xlsx.writeBuffer());
  const original = await zip.file("xl/workbook.xml").async("string");
  zip.file(
    "xl/workbook.xml",
    original
      .replace(
        /xmlns="http:\/\/schemas.openxmlformats.org\/spreadsheetml\/2006\/main"/,
        'xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main"',
      )
      .replace(
        /<(\/?)(workbook|fileVersion|workbookPr|workbookProtection|bookViews|workbookView|sheets|sheet|definedNames|definedName|calcPr)(?=[\s/>])/g,
        "<$1x:$2",
      ),
  );
  const list = await service.importRows(
    await zip.generateAsync({ type: "nodebuffer" }),
  );
  assert.equal(list.length, 1);
  assert.equal(list[0].name, "Medicine & <care>");
  assert.equal(list[0].quantity, "10");
  await assert.rejects(
    service.importRows(Buffer.from("invalid file")),
    /Cannot read this Excel workbook/,
  );
  assert.throws(
    () => normalizeSpreadsheetXml("<!DOCTYPE root><root/>"),
    /Document types/,
  );
});
