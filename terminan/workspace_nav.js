/* Shared navigation for routes served by the primary Terminan process.
   No network requests, persistence or cross-origin navigation. */
(function () {
  'use strict';
  const pages = [
    ['/', 'Терминал'],
    ['/monitor', 'Мониторинг'],
    ['/math', 'Научная лаборатория'],
    ['/history-overlay', 'Исследования / история']
  ];
  const path = window.location.pathname;
  if (!pages.some(([route]) => route === path)) return;
  if (document.getElementById('terminan-workspace-nav')) return;
  const style = document.createElement('style');
  style.textContent = [
    '#terminan-workspace-nav{display:flex;flex-wrap:wrap;gap:7px;align-items:center;',
    'padding:10px 18px;background:#101b29;border-bottom:1px solid #31485e;',
    'font:13px Segoe UI,system-ui,sans-serif;color:#dce8f4}',
    '#terminan-workspace-nav a,#terminan-workspace-nav span{padding:8px 12px;',
    'border:1px solid #38516a;border-radius:6px;color:#dce8f4;text-decoration:none}',
    '#terminan-workspace-nav a[aria-current="page"]{background:#28506a;',
    'border-color:#80c6ed;font-weight:700}',
    '#terminan-workspace-nav a:focus-visible{outline:2px solid #a4d8ff;outline-offset:2px}',
    '#terminan-workspace-nav span{opacity:.65;border-style:dashed}',
    'body:has(#terminan-workspace-nav) main{max-height:calc(100vh - 118px)}'
  ].join('');
  document.head.appendChild(style);
  const nav = document.createElement('nav');
  nav.id = 'terminan-workspace-nav';
  nav.setAttribute('aria-label', 'Разделы Terminan');
  for (const [route, label] of pages) {
    const link = document.createElement('a');
    link.href = route;
    link.textContent = label;
    if (route === path) link.setAttribute('aria-current', 'page');
    nav.appendChild(link);
  }
  const pending = document.createElement('span');
  pending.textContent = 'Сохранённые данные / кэш — отдельный сервер';
  pending.title = 'Исторический workspace пока запускается отдельно и не доступен на этом порту';
  nav.appendChild(pending);
  const header = document.querySelector('header');
  if (header) header.insertAdjacentElement('afterend', nav);
  else document.body.prepend(nav);
}());
