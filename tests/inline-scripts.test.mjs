import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import test from 'node:test'
import {Script} from 'node:vm'

for (const page of ['index.html', 'monitor.html']) {
  test(`${page} inline JavaScript parses`, () => {
    const html = readFileSync(new URL(`../terminan/${page}`, import.meta.url), 'utf8')
    const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)]
      .map(([, source]) => source)
      .filter(source => source.trim())
    assert.ok(scripts.length > 0, `No inline scripts found in ${page}`)
    for (const source of scripts) new Script(source, {filename: page})
  })
}
