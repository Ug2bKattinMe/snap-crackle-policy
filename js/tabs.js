/* Tabs: shows one page at a time and keeps the address bar in step. */
  (() => {
    const names = ['enrollment', 'forecast', 'coupled-model'];
    let current = names.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'enrollment';
    const show = () => {
      document.querySelectorAll('.fx-page').forEach((p) => { p.hidden = p.id !== current; });
      document.querySelectorAll('.fx-tab').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === current)));
    };
    document.querySelectorAll('.fx-tab').forEach((b) => b.addEventListener('click', () => {
      current = b.dataset.tab;
      show();
      dash.setLink(current);
      window.dispatchEvent(new Event('resize'));
    }));
    dash.onData(show);
  })();
