import mysql from "mysql2/promise";
export function createPool(env = process.env) {
  if (!env.DB_NAME || !env.DB_USER)
    throw new Error(
      "Configure DB_HOST, DB_USER, DB_PASSWORD and DB_NAME in Hostinger Environment variables.",
    );
  return mysql.createPool({
    host: env.DB_HOST || "127.0.0.1",
    port: Number(env.DB_PORT || 3306),
    user: env.DB_USER,
    password: env.DB_PASSWORD || "",
    database: env.DB_NAME,
    connectionLimit: 5,
    charset: "utf8mb4",
    supportBigNumbers: true,
    bigNumberStrings: false,
    dateStrings: true,
  });
}
export async function rows(db, sql, args = []) {
  return (await db.execute(sql, args))[0];
}
export async function tx(pool, fn) {
  const c = await pool.getConnection();
  try {
    await c.beginTransaction();
    const result = await fn(c);
    await c.commit();
    return result;
  } catch (e) {
    await c.rollback();
    throw e;
  } finally {
    c.release();
  }
}
export async function initialize(pool) {
  const definitions = {
    web_meta: "id INT PRIMARY KEY, version INT NOT NULL",
    web_lock: "id INT PRIMARY KEY",
    users:
      "id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL, password VARCHAR(250) NOT NULL, role ENUM('Admin','Cashier') NOT NULL, active TINYINT NOT NULL DEFAULT 1",
    settings: "`key` VARCHAR(100) PRIMARY KEY, value LONGTEXT NOT NULL",
    products:
      "id INT AUTO_INCREMENT PRIMARY KEY, sku VARCHAR(100) UNIQUE NOT NULL, name VARCHAR(250) NOT NULL, barcode VARCHAR(100) UNIQUE, category VARCHAR(100) NOT NULL DEFAULT '', price BIGINT NOT NULL CHECK(price>=0), reorder INT NOT NULL DEFAULT 5 CHECK(reorder>=0), active TINYINT NOT NULL DEFAULT 1",
    parties:
      "id INT AUTO_INCREMENT PRIMARY KEY, kind ENUM('Customer','Supplier') NOT NULL, name VARCHAR(250) NOT NULL, phone VARCHAR(100) NOT NULL DEFAULT '', address TEXT NOT NULL",
    purchases:
      "id INT AUTO_INCREMENT PRIMARY KEY, created VARCHAR(30) NOT NULL, supplier_id INT NOT NULL, reference VARCHAR(250) NOT NULL, total BIGINT NOT NULL CHECK(total>=0), paid BIGINT NOT NULL CHECK(paid>=0), CHECK(paid<=total), FOREIGN KEY(supplier_id) REFERENCES parties(id)",
    batches:
      "id INT AUTO_INCREMENT PRIMARY KEY, product_id INT NOT NULL, purchase_id INT, batch VARCHAR(100) NOT NULL, expiry VARCHAR(10) NOT NULL, quantity INT NOT NULL CHECK(quantity>=0), cost BIGINT NOT NULL CHECK(cost>=0), original_quantity INT NOT NULL CHECK(original_quantity>0), FOREIGN KEY(product_id) REFERENCES products(id), FOREIGN KEY(purchase_id) REFERENCES purchases(id), INDEX batch_product(product_id,expiry)",
    sales:
      "id INT AUTO_INCREMENT PRIMARY KEY, created VARCHAR(30) NOT NULL, user_id INT NOT NULL, customer_id INT, subtotal BIGINT NOT NULL CHECK(subtotal>=0), discount BIGINT NOT NULL CHECK(discount>=0), total BIGINT NOT NULL CHECK(total>=0), paid BIGINT NOT NULL CHECK(paid>=0), CHECK(paid<=total), status ENUM('Posted','Void') NOT NULL DEFAULT 'Posted', FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(customer_id) REFERENCES parties(id), INDEX sale_created(created)",
    sale_lines:
      "id INT AUTO_INCREMENT PRIMARY KEY, sale_id INT NOT NULL, batch_id INT NOT NULL, quantity INT NOT NULL CHECK(quantity>0), price BIGINT NOT NULL CHECK(price>=0), cost BIGINT NOT NULL CHECK(cost>=0), FOREIGN KEY(sale_id) REFERENCES sales(id), FOREIGN KEY(batch_id) REFERENCES batches(id)",
    payments:
      "id INT AUTO_INCREMENT PRIMARY KEY, created VARCHAR(30) NOT NULL, party_id INT NOT NULL, amount BIGINT NOT NULL CHECK(amount>0), note TEXT NOT NULL, FOREIGN KEY(party_id) REFERENCES parties(id)",
    expenses:
      "id INT AUTO_INCREMENT PRIMARY KEY, created VARCHAR(30) NOT NULL, category VARCHAR(100) NOT NULL, note TEXT NOT NULL, amount BIGINT NOT NULL CHECK(amount>0)",
    audit:
      "id INT AUTO_INCREMENT PRIMARY KEY, created VARCHAR(30) NOT NULL, user_id INT, action VARCHAR(100) NOT NULL, detail TEXT NOT NULL",
    imports:
      "id INT AUTO_INCREMENT PRIMARY KEY, digest VARCHAR(64) UNIQUE NOT NULL, created VARCHAR(30) NOT NULL, `rows` INT NOT NULL",
    web_sessions:
      "token VARCHAR(64) PRIMARY KEY, user_id INT NOT NULL, csrf VARCHAR(64) NOT NULL, expires BIGINT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id)",
    web_requests:
      "request_key VARCHAR(100) PRIMARY KEY, sale_id INT NOT NULL, user_id INT NOT NULL, FOREIGN KEY(sale_id) REFERENCES sales(id)",
    web_backups:
      "id INT AUTO_INCREMENT PRIMARY KEY, created VARCHAR(30) NOT NULL, content LONGTEXT NOT NULL",
  };
  for (const [name, definition] of Object.entries(definitions))
    await pool.query(
      `CREATE TABLE IF NOT EXISTS \`${name}\` (${definition}) ENGINE=InnoDB`,
    );
  await pool.query("INSERT IGNORE INTO web_meta VALUES(1,1)");
  await pool.query("INSERT IGNORE INTO web_lock VALUES(1)");
  if (
    (await rows(pool, "SELECT version FROM web_meta WHERE id=1"))[0].version !==
    1
  )
    throw new Error("Unsupported web database version");
}
