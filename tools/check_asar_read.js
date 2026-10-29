// Read a path through Electron's ASAR-aware fs layer and report what happened.
// Usage: ELECTRON_RUN_AS_NODE=1 WorkBuddy.exe check_asar_read.js <path>
const fs = require('fs');
const crypto = require('crypto');
const target = process.argv[2];
try {
  const buf = fs.readFileSync(target);
  const sha = crypto.createHash('sha256').update(buf).digest('hex');
  const head = buf.toString('utf8').slice(0, 120).replace(/\n/g, '\\n');
  console.log(JSON.stringify({ ok: true, bytes: buf.length, sha256: sha, head }, null, 0));
} catch (e) {
  console.log(JSON.stringify({ ok: false, name: e.name, code: e.code, message: String(e.message) }, null, 0));
}
