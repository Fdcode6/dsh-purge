import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import https from 'node:https';
const home = fs.mkdtempSync(path.join(os.tmpdir(), 'dsh-update-lock-test-'));
process.env.DSH_HOME = home;
const deny = () => { throw new Error('Unexpected network access'); };
http.request = https.request = http.get = https.get = deny;
globalThis.fetch = deny;
const updater = await import('../lib/update.js');
const checks = [
  ['check', () => updater.checkUpdate(), true],
  ['auto', () => updater.autoUpdateIfNeeded(), true],
  ['direct apply', () => updater.applyUpdate(), false],
  ['channel', () => updater.switchChannel('beta'), false],
  ['version', () => updater.switchVersion('v1.9'), false],
  ...['apply','auto','switch','rollback','channel','check'].map(op => [op, () => updater.handleUpdateOp({op,ref:'master',force:true}), false]),
];
for (const [name, call, ok] of checks) {
  const result = await call();
  assert.equal(result.ok, ok, name);
  assert.equal(result.updatesLocked, true, name);
  assert.equal(result.hasUpdate, false, name);
  assert.equal(result.applied, false, name);
  assert.equal(result.restartAfter, false, name);
  assert.match(result.error, /已锁定/);
}
assert.deepEqual(fs.readdirSync(home), []);
console.log('PASS: all update entry points locked; no network or DSH_HOME writes');
