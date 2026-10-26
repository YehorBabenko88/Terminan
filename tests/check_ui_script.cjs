// Parse the shipped browser script before accepting UI changes.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('terminan/index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(script, 'terminal must contain its UI script');
assert.doesNotThrow(() => new vm.Script(script[1]), 'shipped terminal JavaScript must parse');
