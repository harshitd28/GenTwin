(function () {
  var PAGES = [
    { id: 'demo', label: 'Demo', href: 'demo.html' },
    { id: 'operator', label: 'Operator', href: 'operator.html' },
    { id: 'analytics', label: 'Analytics', href: 'analytics.html' },
    { id: 'docs', label: 'Docs', href: 'docs.html' },
    { id: 'simulator', label: 'Simulator', href: 'simulator.html' },
    { id: 'deploy', label: 'Deploy', href: 'deploy.html' },
    { id: 'paper', label: 'Paper', href: 'paper.html' }
  ];

  var LOGO =
    '<svg width="22" height="22" viewBox="0 0 28 28" fill="none" aria-hidden="true">' +
    '<path d="M14 3L24 8.5V19.5L14 25L4 19.5V8.5L14 3Z" stroke="#1EE8A4" stroke-width="1.5"/>' +
    '<path d="M14 8L20 11.5V18.5L14 22L8 18.5V11.5L14 8Z" stroke="#1EE8A4" stroke-width="1" fill="rgba(30,232,164,0.08)"/></svg>';

  function currentPage() {
    var fromBody = document.body && document.body.getAttribute('data-suite-page');
    if (fromBody) return fromBody;
    var file = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
    if (file === '' || file === 'index.html' || file === 'gentwin_enterprise_landing.html') return 'index';
    return file.replace(/\.html$/, '');
  }

  function pageTitle(page, custom) {
    if (custom) return custom;
    var map = {
      index: 'TwinGuard Dynamics',
      demo: 'Interactive Demo',
      operator: 'Operator SCADA',
      analytics: 'Analytics',
      docs: 'Documentation',
      simulator: 'Simulator',
      deploy: 'Deploy',
      paper: 'Research Paper'
    };
    return map[page] || 'GenTwin';
  }

  var page = currentPage();
  var title = pageTitle(page, document.body.getAttribute('data-suite-title'));
  var isLanding = page === 'index';
  var brandHref = isLanding ? '#hero' : 'index.html';

  var links = PAGES.map(function (p) {
    var active = p.id === page;
    return (
      '<a href="' +
      p.href +
      '"' +
      (active ? ' class="active" aria-current="page"' : '') +
      '>' +
      p.label +
      '</a>'
    );
  }).join('');

  /* Landing uses its own section navbar — no product suite bar */
  if (isLanding) return;

  var navClass = 'suite-nav';
  var html =
    '<header class="' +
    navClass +
    '" role="navigation" aria-label="Product suite">' +
    '<a class="suite-nav-brand" href="' +
    brandHref +
    '">' +
    LOGO +
    '<span>GenTwin</span>' +
    '<span class="suite-nav-brand-sub">· ' +
    title +
    '</span></a>' +
    '<nav class="suite-nav-links">' +
    links +
    '</nav>' +
    '</header>';

  var mount = document.getElementById('suite-nav-mount');
  if (mount) {
    mount.outerHTML = html;
  } else {
    document.body.insertAdjacentHTML('afterbegin', html);
  }
})();
