/* Tabs: shows one page at a time and keeps the address bar in step. */
  (() => {
    const names = ['home', 'enrollment', 'forecast', 'coupled-model', 'south-carolina'];
    let current = names.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'home';
    const show = () => {
      document.querySelectorAll('.fx-page').forEach((p) => { p.hidden = p.id !== current; });
      document.querySelectorAll('.fx-tab').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === current)));
    };
    const go = (name) => {
      current = name;
      show();
      dash.setLink(current);
      window.dispatchEvent(new Event('resize'));
      document.querySelectorAll('.fx-head').forEach((h) => h.scrollIntoView({ block: 'start' }));
    };
    document.querySelectorAll('.fx-tab').forEach((b) => b.addEventListener('click', () => go(b.dataset.tab)));
    document.querySelectorAll('.fx-go').forEach((b) => b.addEventListener('click', () => go(b.dataset.goto)));
    dash.onData(show);
  })();
