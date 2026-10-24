// Compatible with direct Node execution and Hostinger LiteSpeed require().
// Keep this entry free of static ESM imports and top-level await.
import("./web-server.js")
  .then(({ start }) => start())
  .catch((error) => {
    console.error("Pharmacy Web startup:", error.code || error.message);
    process.exitCode = 1;
  });
