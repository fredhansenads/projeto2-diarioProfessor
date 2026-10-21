// Dependency-free behavioral tests. These are simulations, not device/browser certification.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {runInNewContext} = require('node:vm');
const {join} = require('node:path');
const source = file => readFileSync(join(__dirname, '../static/diary', file), 'utf8');

function worker(network = async () => new Response('network')) {
  const listeners = {}, stores = new Map(), requests = [];
  const caches = {
    keys: async () => [...stores.keys()],
    delete: async key => stores.delete(key),
    open: async key => {
      if (!stores.has(key)) stores.set(key, new Map());
      const store = stores.get(key);
      return {put: async (url, response) => store.set(url, await response.text()),
        match: async url => store.has(url) ? new Response(store.get(url)) : undefined};
    }
  };
  const self = {location: {origin: 'https://diario.test'},
    addEventListener: (type, callback) => listeners[type] = callback};
  runInNewContext(source('service-worker.js'), {
    self, caches, URL, Response, fetch: async (...args) => { requests.push(args); return network(...args); }
  });
  return {stores, requests, async event(type, request) {
    let result;
    listeners[type]({request, waitUntil: promise => result = promise, respondWith: promise => result = promise});
    return result;
  }};
}
const request = (method = 'GET', path = '/', mode = 'navigate') =>
  ({method, url: `https://diario.test${path}`, mode});

test('only generic offline content enters CacheStorage even after private pages and downloads', async () => {
  const sw = worker(async req => new Response(typeof req === 'string' ? 'public offline' : 'private student grades'));
  await sw.event('install');
  for (const path of ['/', '/notas/1/', '/relatorios/?format=pdf', '/conta/login/']) {
    const response = await sw.event('fetch', request('GET', path));
    assert.equal(await response.text(), 'private student grades');
  }
  assert.equal(sw.stores.size, 1);
  assert.deepEqual([...sw.stores.values()][0], new Map([['/offline/', 'public offline']]));
  assert.equal(sw.requests[0][1].credentials, 'omit');
});
test('failed POST gets explicit uncertain-result response and is never retried or cached', async () => {
  const sw = worker(async req => {
    if (typeof req === 'string') return new Response('Confira o registro antes de repetir.');
    throw new TypeError('Network failure');
  });
  await sw.event('install');
  const post = request('POST', '/aulas/1/chamada/');
  const response = await sw.event('fetch', post);
  assert.equal(response.status, 503);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  assert.match(await response.text(), /Confira/);
  assert.equal(sw.requests.filter(([req]) => req === post).length, 1);
  assert.deepEqual([...sw.stores.values()][0].keys().toArray(), ['/offline/']);
});
test('successful POST and server validation/auth errors are passed through unchanged', async () => {
  for (const status of [200, 403, 409, 500]) {
    const original = new Response('server result', {status});
    const sw = worker(async () => original);
    assert.equal(await sw.event('fetch', request('POST')), original);
    assert.equal(sw.stores.size, 0);
    assert.equal(sw.requests.length, 1);
  }
});
test('third-party requests and non-navigation assets bypass worker', async () => {
  const sw = worker();
  assert.equal(await sw.event('fetch', {url: 'https://external.test/', mode: 'navigate'}), undefined);
  assert.equal(await sw.event('fetch', request('GET', '/asset.css', 'cors')), undefined);
  assert.equal(sw.requests.length, 0);
});
test('failed installation does not cache an error document', async () => {
  const sw = worker(async () => new Response('server error', {status: 500}));
  await assert.rejects(sw.event('install'));
  assert.equal([...sw.stores.values()][0].size, 0);
});
test('activation deletes only older diary caches and does not claim open pages', async () => {
  const sw = worker();
  await sw.event('install');
  sw.stores.set('diario-public-old', new Map());
  sw.stores.set('another-app', new Map());
  await sw.event('activate');
  assert.deepEqual([...sw.stores.keys()], ['diario-public-v1', 'another-app']);
  // Harness intentionally lacks skipWaiting/clients.claim: invoking either fails the test.
});
test('missing fallback cache still returns safe connection message', async () => {
  const sw = worker(async () => { throw new Error('offline'); });
  const response = await sw.event('fetch', request());
  assert.equal(response.status, 503);
  assert.match(await response.text(), /Sem conexão/);
});

class Element {
  constructor() { this.handlers = {}; this.attributes = {}; this.children = []; this.hidden = true; this.textContent = ''; this.classList = {contains: () => false}; }
  addEventListener(type, fn) { (this.handlers[type] ??= []).push(fn); }
  async emit(type, fields = {}) {
    const event = {prevented: false, preventDefault() { this.prevented = true; }, ...fields};
    for (const fn of this.handlers[type] ?? []) await fn(event);
    return event;
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  removeAttribute(key) { delete this.attributes[key]; }
  append(child) { this.children.push(child); }
  scrollIntoView() {}
}
function page({online = true, secure = true, standalone = false} = {}) {
  const window = new Element(), form = new Element(), logout = new Element(), ids = {}, registrations = [];
  logout.classList.contains = name => name === 'logout-form';
  ['connection-status', 'install-app', 'installed-status', 'install-unavailable'].forEach(id => ids[id] = new Element());
  const navigator = {onLine: online, serviceWorker: {register: async (...args) => registrations.push(args)}};
  window.isSecureContext = secure;
  window.matchMedia = () => ({matches: standalone});
  window.setTimeout = fn => { window.delayed = fn; return 1; };
  const document = {getElementById: id => ids[id], createElement: () => new Element(),
    querySelectorAll: selector => selector.startsWith('form') ? [form, logout] : []};
  runInNewContext(source('pwa.js'), {window, navigator, document, clearTimeout() {}});
  return {window, form, logout, ids, navigator, registrations, status: form.children[0]};
}
test('offline submission stays on form, never says saved, then permits one online send', async () => {
  const p = page({online: false});
  assert.equal(p.ids['connection-status'].hidden, false);
  assert.equal((await p.form.emit('submit')).prevented, true);
  assert.match(p.status.textContent, /nada foi enviado/);
  p.navigator.onLine = true;
  await p.window.emit('online');
  assert.equal(p.ids['connection-status'].hidden, true);
  assert.equal((await p.form.emit('submit')).prevented, false);
  assert.match(p.status.textContent, /aguarde a confirmação/);
  assert.equal((await p.form.emit('submit')).prevented, true);
  p.window.delayed();
  assert.match(p.status.textContent, /ainda não confirmou/);
});
test('dirty forms warn on leaving; intentional submit proceeds; restored form warns before reuse', async () => {
  const p = page();
  assert.equal((await p.window.emit('beforeunload')).prevented, false);
  await p.form.emit('change');
  assert.equal((await p.window.emit('beforeunload')).prevented, true);
  await p.form.emit('submit');
  assert.equal((await p.window.emit('beforeunload')).prevented, false);
  await p.window.emit('pageshow', {persisted: true});
  assert.match(p.status.textContent, /pode já ter sido salvo/);
  assert.equal((await p.form.emit('submit')).prevented, false);
});
test('install UI appears only with a browser offer; dismissed prompt is used once', async () => {
  const p = page();
  assert.equal(p.ids['install-app'].hidden, true);
  let prompts = 0;
  await p.window.emit('beforeinstallprompt', {prompt: async () => prompts++, userChoice: Promise.resolve({outcome: 'dismissed'})});
  assert.equal(p.ids['install-app'].hidden, false);
  await p.ids['install-app'].emit('click');
  await p.ids['install-app'].emit('click');
  assert.equal(prompts, 1);
  assert.equal(p.ids['install-app'].hidden, true);
  await p.window.emit('appinstalled');
  assert.equal(p.ids['installed-status'].hidden, false);
});
test('logout respects dirty form warning and stays usable after the user cancels leaving', async () => {
  const p = page();
  await p.form.emit('input');
  assert.equal((await p.logout.emit('submit')).prevented, false);
  assert.equal((await p.window.emit('beforeunload')).prevented, true);
  assert.equal((await p.logout.emit('submit')).prevented, false);
  assert.equal((await p.window.emit('beforeunload')).prevented, true);
});
test('HTTP context skips worker and shows HTTPS guidance; installed app hides promotion', async () => {
  const p = page({secure: false});
  assert.equal(p.registrations.length, 0);
  assert.equal(p.ids['install-unavailable'].hidden, false);
  const installed = page({standalone: true});
  assert.equal(installed.ids['installed-status'].hidden, false);
  await installed.window.emit('beforeinstallprompt');
  assert.equal(installed.ids['install-app'].hidden, true);
});
