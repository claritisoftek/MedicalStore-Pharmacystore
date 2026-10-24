import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';

// Exercise the actual entry: LiteSpeed requires it; npm start executes it.
test('entry starts under direct Node and LiteSpeed-style require', { skip: !process.env.RUN_DB_TESTS }, async () => {
  for (const args of [['server.js'], ['--input-type=commonjs', '-e', "require('./server.js')"]]) {
    const child = spawn(process.execPath, args, {
      env: { ...process.env, PORT: '3198', NODE_ENV: 'test' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let output = '';
    child.stdout.on('data', data => { output += data; });
    child.stderr.on('data', data => { output += data; });
    try {
      const deadline = Date.now() + 15000;
      while (!output.includes('Pharmacy Web is ready')) {
        assert.equal(child.exitCode, null, output);
        assert.ok(Date.now() < deadline, output || 'Startup timed out');
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      const response = await fetch('http://127.0.0.1:3198/health');
      assert.equal(response.status, 200, output);
    } finally {
      if (child.exitCode === null) { const closed = once(child, 'exit'); child.kill(); await closed; }
    }
  }
});
