/* Review4 C3 raw-text codec. Shape validity never establishes authority.
 * Deliberately no host-object writer: browser APIs cannot detect all Proxies.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object') module.exports = api;
  else root.TerminanC3 = api;
})(globalThis, function () {
  'use strict';
  const tokens = new WeakMap();
  const MAX_BYTES = 2097152;
  const PROFILE_SHA256 = '335cda8e5d451fd9ab90586b6f6a4d6fbaf5f52eabb5a11762d9100ed92fefdf';
  const BOUNDS_SHA256 = 'be9a0eb518ab14683cbb8e002e18f05e03d948b8c5d1537d635736bde8789203';
  function fail(code) { throw new Error(code); }
  function parse(raw, maxBytes = MAX_BYTES) {
    if (!Number.isSafeInteger(maxBytes) || maxBytes < 1 || maxBytes > MAX_BYTES) fail('BYTE_LIMIT');
    if (typeof raw !== 'string' || !raw.length || raw.length > maxBytes) fail('RAW_CAP');
    let offset = 0, nodes = 0;
    function count() { if (++nodes > 32768) fail('NODE_CAP'); }
    function string(limit, minimum = 0) {
      if (raw[offset++] !== '"') fail('STRING_REQUIRED');
      let result = '';
      while (offset < raw.length) {
        let ch = raw[offset++];
        if (ch === '"') {
          if (result.length < minimum) fail('KEY_CAP');
          return result;
        }
        if (ch === '\\') {
          ch = raw[offset++];
          if (ch !== '"' && ch !== '\\') fail('ESCAPE_ALIAS');
        } else if (ch.charCodeAt(0) < 32 || ch.charCodeAt(0) > 126) fail('ASCII_REQUIRED');
        result += ch;
        if (result.length > limit) fail('STRING_CAP');
      }
      fail('UNTERMINATED_STRING');
    }
    function read(parentDepth) {
      count();
      const ch = raw[offset];
      if (ch === '"') return string(16384);
      for (const [literal, value] of [['null', null], ['true', true], ['false', false]]) {
        if (raw.startsWith(literal, offset)) { offset += literal.length; return value; }
      }
      if (ch !== '[' && ch !== '{') fail('VALUE_REQUIRED_NO_NUMBERS');
      const depth = parentDepth + 1;
      if (depth > 12) fail('DEPTH_CAP');
      offset++;
      if (ch === '[') {
        const values = [];
        if (raw[offset] === ']') { offset++; return Object.freeze(values); }
        while (true) {
          if (values.length >= 1000) fail('ARRAY_CAP');
          values.push(read(depth));
          if (raw[offset] === ']') { offset++; return Object.freeze(values); }
          if (raw[offset++] !== ',') fail('ARRAY_SEPARATOR');
        }
      }
      const values = Object.create(null);
      let previous = null, members = 0;
      if (raw[offset] === '}') { offset++; return Object.freeze(values); }
      while (true) {
        if (++members > 64) fail('MEMBER_CAP');
        count();
        const key = string(128, 1);
        if (previous !== null && key <= previous) fail('KEY_ORDER_OR_DUPLICATE');
        previous = key;
        if (raw[offset++] !== ':') fail('OBJECT_SEPARATOR');
        values[key] = read(depth);
        if (raw[offset] === '}') { offset++; return Object.freeze(values); }
        if (raw[offset++] !== ',') fail('OBJECT_SEPARATOR');
      }
    }
    const value = read(0);
    if (offset !== raw.length) fail('TRAILING_DATA');
    const token = Object.freeze(Object.create(null));
    tokens.set(token, { raw, value });
    return token;
  }
  function lookup(token) {
    const entry = tokens.get(token);
    if (!entry) fail('C3_TOKEN_REQUIRED');
    return entry;
  }
  return Object.freeze({ parse, text: token => lookup(token).raw,
    value: token => lookup(token).value, PROFILE_SHA256, BOUNDS_SHA256 });
});
