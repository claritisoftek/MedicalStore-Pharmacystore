import JSZip from "jszip";
import { SaxesParser } from "saxes";

const spreadsheet = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
const escape = (value) =>
  String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

// ExcelJS expects unprefixed SpreadsheetML element names. Resolve namespaces
// with an XML parser, rather than replacing prefixes in cell text or attributes.
export function normalizeSpreadsheetXml(xml) {
  const parser = new SaxesParser({ xmlns: true });
  const output = [];
  parser.on("doctype", () => {
    throw Error("Document types are not supported");
  });
  parser.on("error", (error) => {
    throw error;
  });
  parser.on("opentag", (node) => {
    const name = node.uri === spreadsheet ? node.local : node.name;
    output.push("<" + name);
    for (const attr of Object.values(node.attributes)) {
      if (node.uri === spreadsheet && attr.name === "xmlns") continue;
      output.push(" " + attr.name + '="' + escape(attr.value) + '"');
    }
    if (node.uri === spreadsheet) output.push(' xmlns="' + spreadsheet + '"');
    output.push(">");
  });
  parser.on("closetag", (node) =>
    output.push(
      "</" + (node.uri === spreadsheet ? node.local : node.name) + ">",
    ),
  );
  parser.on("text", (value) => output.push(escape(value)));
  parser.on("cdata", (value) => output.push(escape(value)));
  parser.write(xml).close();
  return output.join("");
}

export async function compatibleWorkbook(buffer) {
  const zip = await JSZip.loadAsync(buffer);
  let total = 0;
  for (const entry of Object.values(zip.files)) {
    if (entry.dir) continue;
    total += entry._data?.uncompressedSize || 0;
    if (total > 50 * 1024 * 1024)
      throw Error("Expanded workbook exceeds 50 MB");
  }
  for (const entry of Object.values(zip.files)) {
    if (!entry.dir && /^xl\/.*\.xml$/.test(entry.name)) {
      zip.file(
        entry.name,
        normalizeSpreadsheetXml(await entry.async("string")),
      );
    }
  }
  return zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}
