/* Charts, tables and figures for the forecast dashboard. Uses d3 v7 and js/dash-shim.js. */
window.fcCompact = (v, isMoney) => {
    const n = Number(v);
    const f = Intl.NumberFormat('en', {notation: 'compact', maximumFractionDigits: Math.abs(n) >= 1e9 ? 1 : (Math.abs(n) >= 1e6 ? 2 : 0)});
    return (isMoney ? '$' : '') + f.format(n);
  };
  window.fcInt = d3.format(',');
  window.fcRow = (rows, id, months) => rows.find((r) => r.metric_id === id && Number(r.months) === months);
  window.fcResolve = (host, expr) => {
    const probe = document.createElement('span');
    probe.style.color = expr;
    probe.style.display = 'none';
    host.appendChild(probe);
    const c = getComputedStyle(probe).color;
    probe.remove();
    return c;
  };
  window.fcFail = (el) => {
    const f = document.createElement('div');
    f.className = 'fc-fail';
    f.textContent = 'Failed to load';
    el.appendChild(f);
  };
  window.fcTip = (el) => {
    const tip = d3.select(el).append('div').attr('class', 'fc-tip').style('display', 'none');
    tip.place = (event) => {
      tip.style('display', 'block');
      const box = el.getBoundingClientRect();
      const node = tip.node();
      let x = event.clientX - box.left + 12;
      let y = event.clientY - box.top + 12;
      x = Math.min(x, box.width - node.offsetWidth - 4);
      if (y + node.offsetHeight > box.height) y = event.clientY - box.top - node.offsetHeight - 12;
      tip.style('left', `${Math.max(4, x)}px`).style('top', `${Math.max(4, y)}px`);
    };
    return tip;
  };

  dash.draw('nat', (el) => {
    const d = dash.data('national');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const [k, v] = el.dataset.where.split('&').map((p) => p.split('=')[1]);
    const r = fcRow(d.data, k, Number(v));
    if (!r) { el.textContent = '—'; return; }
    el.textContent = fcCompact(r[el.dataset.field], r.unit === 'dollars');
  });

  dash.draw('natrange', (el) => {
    const d = dash.data('national');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const [k, v] = el.dataset.where.split('&').map((p) => p.split('=')[1]);
    const r = fcRow(d.data, k, Number(v));
    if (!r) { el.textContent = '—'; return; }
    const m = r.unit === 'dollars';
    el.textContent = `95% interval ${fcCompact(r.low, m)} – ${fcCompact(r.high, m)}`;
  });

  dash.draw('assume', (el) => {
    const d = dash.data('assumptions');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const r = d.data.find((x) => x.id === el.dataset.where.split('=')[1]);
    el.textContent = r ? Number(r[el.dataset.field]).toFixed(1) : '—';
  });

  dash.draw('timeline', (el) => {
    const d = dash.data('timeline');
    el.replaceChildren();
    if (d.status === 'error') { fcFail(el); return; }
    if (d.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');
    const rows = d.data.map((r) => ({...r, t: new Date(r.date + 'T00:00:00Z'), lo: +r.combined_low, mid: +r.combined_median, hi: +r.combined_high, m: +r.month}))
      .map((r, i) => ({...r, i}));
    const W = Math.max(320, el.clientWidth || 640), H = 300;
    const left = 52, right = 92, y0 = 14, bottom = 30;
    const x = d3.scaleUtc(d3.extent(rows, (r) => r.t), [left, W - right]);
    const y = d3.scaleLinear([0, d3.max(rows, (r) => r.hi) * 1.08], [H - bottom, y0]).nice();
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('role', 'img')
      .attr('aria-label', 'People affected month by month in 2027 with 95% interval');
    const accent = fcResolve(el, dash.colors[0]);
    const grid = svg.append('g');
    y.ticks(5).forEach((v) => {
      grid.append('line').attr('x1', left).attr('x2', W - right).attr('y1', y(v)).attr('y2', y(v)).attr('stroke', 'var(--cds-chart-grid)');
      grid.append('text').attr('x', left - 8).attr('y', y(v) + 4).attr('text-anchor', 'end').attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(fcCompact(v));
    });
    const ticks = rows.filter((r) => r.i > 0 && r.m % 3 === 0);
    ticks.forEach((r) => svg.append('text').attr('x', x(r.t)).attr('y', H - 10).attr('text-anchor', 'middle').attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(d3.utcFormat('%b %-d')(r.t)));
    svg.append('path').datum(rows).attr('fill', accent).attr('fill-opacity', 0.16)
      .attr('d', d3.area().x((r) => x(r.t)).y0((r) => y(r.lo)).y1((r) => y(r.hi)));
    svg.append('path').datum(rows).attr('fill', 'none').attr('stroke', accent).attr('stroke-width', 2).attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round')
      .attr('d', d3.line().x((r) => x(r.t)).y((r) => y(r.mid)));
    const marks = rows.filter((r) => r.i === 6 || r.i === 12);
    marks.forEach((r) => {
      svg.append('line').attr('x1', x(r.t)).attr('x2', x(r.t)).attr('y1', y0).attr('y2', H - bottom).attr('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '4 3');
      svg.append('circle').attr('cx', x(r.t)).attr('cy', y(r.mid)).attr('r', 4).attr('fill', accent);
      svg.append('text').attr('x', x(r.t) + 6).attr('y', y(r.mid) - 8).attr('font-size', 12).attr('fill', 'var(--color-fg)').text(fcCompact(r.mid));
      svg.append('text').attr('x', x(r.t) + 6).attr('y', y(r.mid) + 16).attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(r.i === 6 ? '6 months' : '12 months');
    });
    const tip = fcTip(el);
    const dot = svg.append('circle').attr('r', 4).attr('fill', accent).style('display', 'none');
    svg.append('rect').attr('x', left).attr('y', y0).attr('width', W - right - left).attr('height', H - bottom - y0).attr('fill', 'transparent')
      .on('pointermove', (event) => {
        const [px] = d3.pointer(event);
        const t = x.invert(px);
        const r = rows.reduce((a, b) => (Math.abs(b.t - t) < Math.abs(a.t - t) ? b : a));
        dot.style('display', null).attr('cx', x(r.t)).attr('cy', y(r.mid));
        tip.selectAll('*').remove();
        tip.append('div').attr('class', 't1').text(d3.utcFormat('%b %-d, %Y')(r.t));
        tip.append('div').text(`${fcInt(Math.round(r.mid / 1000) * 1000)} people`);
        tip.append('div').text(`95% interval ${fcCompact(r.lo)} – ${fcCompact(r.hi)}`);
        tip.place(event);
      })
      .on('pointerleave', () => { tip.style('display', 'none'); dot.style('display', 'none'); });
  });

  dash.draw('components', (el) => {
    const d = dash.data('timeline');
    el.replaceChildren();
    if (d.status === 'error') { fcFail(el); return; }
    if (d.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');
    const r6 = d.data[6], r12 = d.data[12];
    const groups = [
      {key: 'snap', name: 'Off SNAP because of the law'},
      {key: 'medicaid', name: 'Off Medicaid (work rules, renewals)'},
      {key: 'marketplace', name: 'Lost Marketplace coverage or subsidy'},
      {key: 'jobs', name: 'Lost a job'},
      {key: 'immigrants', name: 'Immigrants losing Medicaid or Medicare'},
    ];
    const W = Math.max(320, el.clientWidth || 640);
    const labelW = Math.min(230, W * 0.42), right = 64, rowH = 46, y0 = 28;
    const H = y0 + groups.length * rowH + 8;
    const max = d3.max(groups, (g) => Math.max(+r6[g.key], +r12[g.key]));
    const x = d3.scaleLinear([0, max], [labelW, W - right]);
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('role', 'img').attr('aria-label', 'People in each group at 6 and 12 months');
    const c6 = fcResolve(el, dash.colors[0]);
    const legend = svg.append('g');
    [[c6, 0.45, '6 months'], [c6, 1, '12 months']].forEach(([c, o, t], i) => {
      legend.append('rect').attr('x', labelW + i * 96).attr('y', 4).attr('width', 10).attr('height', 10).attr('rx', 2).attr('fill', c).attr('fill-opacity', o);
      legend.append('text').attr('x', labelW + i * 96 + 15).attr('y', 13).attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(t);
    });
    const tip = fcTip(el);
    groups.forEach((g, i) => {
      const yy = y0 + i * rowH;
      svg.append('text').attr('x', labelW - 8).attr('y', yy + 18).attr('text-anchor', 'end').attr('font-size', 12).attr('fill', 'var(--color-fg)').text(g.name);
      [[r6, 0.45, 0], [r12, 1, 18]].forEach(([r, o, dy]) => {
        const v = +r[g.key];
        svg.append('rect').attr('x', labelW).attr('y', yy + dy).attr('height', 15).attr('rx', 2).attr('width', Math.max(1, x(v) - labelW)).attr('fill', c6).attr('fill-opacity', o)
          .on('pointermove', (event) => {
            tip.selectAll('*').remove();
            tip.append('div').attr('class', 't1').text(`${g.name}, ${dy ? '12' : '6'} months`);
            tip.append('div').text(`${fcInt(Math.round(v / 1000) * 1000)} people (median)`);
            tip.place(event);
          })
          .on('pointerleave', () => tip.style('display', 'none'));
        svg.append('text').attr('x', x(v) + 5).attr('y', yy + dy + 12).attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(fcCompact(v));
      });
    });
  });

  dash.draw('dollars', (el) => {
    const d = dash.data('national');
    el.replaceChildren();
    if (d.status === 'error') { fcFail(el); return; }
    if (d.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');
    const ids = [
      ['fed_cut', 'Federal spending reduction'],
      ['gdp_loss', 'Lost economic output (GDP)'],
      ['household_cost', 'Added household costs'],
      ['lost_snap', '  Lost SNAP benefits'],
      ['medicare_cost', '  Higher Medicare premiums and drug costs'],
      ['new_oop', '  New medical bills, newly uninsured'],
      ['hosp_er_cost', 'Hospital and ER care for the newly uninsured'],
      ['uncomp_care', '  Unpaid: uncompensated hospital care'],
      ['tax_loss', 'State and local tax revenue lost'],
    ];
    const W = Math.max(320, el.clientWidth || 900);
    const labelW = Math.min(280, W * 0.4), right = 70, rowH = 44, y0 = 30;
    const H = y0 + ids.length * rowH + 22;
    const rows = ids.map(([id, name]) => ({id, name, r6: fcRow(d.data, id, 6), r12: fcRow(d.data, id, 12)})).filter((g) => g.r6 && g.r12);
    const max = d3.max(rows, (g) => +g.r12.high);
    const x = d3.scaleLinear([0, max], [labelW, W - right]).nice();
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('role', 'img').attr('aria-label', 'Financial and economic impact at 6 and 12 months');
    const c = fcResolve(el, dash.colors[1]);
    x.ticks(5).forEach((v) => {
      svg.append('line').attr('x1', x(v)).attr('x2', x(v)).attr('y1', y0 - 6).attr('y2', H - 22).attr('stroke', 'var(--cds-chart-grid)');
      svg.append('text').attr('x', x(v)).attr('y', H - 6).attr('text-anchor', 'middle').attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(fcCompact(v, true));
    });
    [[0.45, '6 months (Jan–Jun 2027)'], [1, '12 months (Jan–Dec 2027)']].forEach(([o, t], i) => {
      svg.append('rect').attr('x', labelW + i * 170).attr('y', 4).attr('width', 10).attr('height', 10).attr('rx', 2).attr('fill', c).attr('fill-opacity', o);
      svg.append('text').attr('x', labelW + i * 170 + 15).attr('y', 13).attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(t);
    });
    const tip = fcTip(el);
    rows.forEach((g, i) => {
      const yy = y0 + i * rowH;
      const sub = g.name.startsWith('  ');
      svg.append('text').attr('x', labelW - 8).attr('y', yy + 18).attr('text-anchor', 'end').attr('font-size', sub ? 11 : 12)
        .attr('fill', sub ? 'var(--color-fg-muted)' : 'var(--color-fg)').text(g.name.trim());
      [[g.r6, 0.45, 0, '6 months'], [g.r12, 1, 18, '12 months']].forEach(([r, o, dy, lab]) => {
        const mid = +r.median, lo = +r.low, hi = +r.high;
        svg.append('rect').attr('x', labelW).attr('y', yy + dy).attr('height', 14).attr('rx', 2).attr('width', Math.max(1, x(mid) - labelW)).attr('fill', c).attr('fill-opacity', o)
          .on('pointermove', (event) => {
            tip.selectAll('*').remove();
            tip.append('div').attr('class', 't1').text(`${g.name.trim()}, ${lab}`);
            tip.append('div').text(`${fcCompact(mid, true)} (median)`);
            tip.append('div').text(`95% interval ${fcCompact(lo, true)} – ${fcCompact(hi, true)}`);
            tip.place(event);
          })
          .on('pointerleave', () => tip.style('display', 'none'));
        svg.append('line').attr('x1', x(lo)).attr('x2', x(hi)).attr('y1', yy + dy + 7).attr('y2', yy + dy + 7).attr('stroke', 'var(--color-fg)').attr('stroke-opacity', 0.55).attr('stroke-width', 1.2);
        svg.append('text').attr('x', x(hi) + 5).attr('y', yy + dy + 11).attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(fcCompact(mid, true));
      });
    });
  });

  dash.draw('jobs', (el) => {
    const d = dash.data('national');
    el.replaceChildren();
    if (d.status === 'error') { fcFail(el); return; }
    if (d.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');
    const ids = [['jobs_cut', 'Jobs lost from the cuts'], ['jobs_econ', 'Change in unemployed, economy-wide'], ['job_losers', 'Job losers counted in the forecast']];
    const rows = [];
    ids.forEach(([id, name]) => [6, 12].forEach((m) => { const r = fcRow(d.data, id, m); if (r) rows.push({id, name, m, lo: +r.low, mid: +r.median, hi: +r.high}); }));
    const W = Math.max(320, el.clientWidth || 640);
    const labelW = Math.min(210, W * 0.42), right = 24, rowH = 30, y0 = 10;
    const H = y0 + rows.length * rowH + 28;
    const x = d3.scaleLinear([Math.min(0, d3.min(rows, (r) => r.lo)), d3.max(rows, (r) => r.hi)], [labelW, W - right]).nice();
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('role', 'img').attr('aria-label', 'Job loss measures at 6 and 12 months with 95% intervals');
    x.ticks(5).forEach((v) => {
      svg.append('line').attr('x1', x(v)).attr('x2', x(v)).attr('y1', y0).attr('y2', H - 24).attr('stroke', v === 0 ? 'var(--cds-chart-axis)' : 'var(--cds-chart-grid)');
      svg.append('text').attr('x', x(v)).attr('y', H - 8).attr('text-anchor', 'middle').attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(fcCompact(v));
    });
    const c = fcResolve(el, dash.colors[2]);
    const tip = fcTip(el);
    rows.forEach((r, i) => {
      const yy = y0 + i * rowH + 12;
      svg.append('text').attr('x', labelW - 8).attr('y', yy + 4).attr('text-anchor', 'end').attr('font-size', 11).attr('fill', 'var(--color-fg)').text(`${r.name}, ${r.m} mo`);
      svg.append('line').attr('x1', x(r.lo)).attr('x2', x(r.hi)).attr('y1', yy).attr('y2', yy).attr('stroke', c).attr('stroke-width', 2).attr('stroke-linecap', 'round');
      svg.append('circle').attr('cx', x(r.mid)).attr('cy', yy).attr('r', 5).attr('fill', c)
        .on('pointermove', (event) => {
          tip.selectAll('*').remove();
          tip.append('div').attr('class', 't1').text(`${r.name}, ${r.m} months`);
          tip.append('div').text(`${fcInt(Math.round(r.mid / 1000) * 1000)} (median)`);
          tip.append('div').text(`95% interval ${fcCompact(r.lo)} – ${fcCompact(r.hi)}`);
          tip.place(event);
        })
        .on('pointerleave', () => tip.style('display', 'none'));
    });
  });

  dash.draw('map', (el) => {
    const s = dash.data('states');
    const g = dash.data('shapes');
    el.replaceChildren();
    if (s.status === 'error' || g.status === 'error') { el.classList.remove('dash-skeleton'); fcFail(el); return; }
    if (s.status !== 'ok' || g.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');
    const by = new Map(s.data.map((r) => [r.abbr, r]));
    const vals = s.data.map((r) => +r.per10k_12m);
    const lo = d3.min(vals), hi = d3.max(vals);
    const mix = d3.interpolateRgb(fcResolve(el, 'var(--color-panel)'), fcResolve(el, dash.colors[3] || dash.colors[0]));
    const t = d3.scaleLinear([lo, hi], [0.12, 1]).clamp(true);
    const color = (v) => mix(t(v));
    const svg = d3.select(el).append('svg').attr('viewBox', '0 0 960 500').attr('width', '100%').attr('role', 'img').attr('aria-label', 'Map of people affected per 10,000 residents by state, end of 2027');
    const tip = fcTip(el);
    svg.append('g').selectAll('path').data(g.data.filter((d) => by.has(d.abbr))).join('path')
      .attr('d', (d) => d.path).attr('fill', (d) => color(+by.get(d.abbr).per10k_12m))
      .on('pointermove', function (event, d) {
        d3.select(this).classed('on', true).raise();
        const r = by.get(d.abbr);
        tip.selectAll('*').remove();
        tip.append('div').attr('class', 't1').text(r.state);
        tip.append('div').text(`${Number(r.per10k_12m).toFixed(0)} per 10,000 residents by Dec 31`);
        tip.append('div').text(`6 months: ${fcInt(+r.people_6m)} (${fcInt(+r.people_6m_low)}–${fcInt(+r.people_6m_high)})`);
        tip.append('div').text(`12 months: ${fcInt(+r.people_12m)} (${fcInt(+r.people_12m_low)}–${fcInt(+r.people_12m_high)})`);
        tip.append('div').text(`GDP loss, 12 months: ${fcCompact(+r.gdp_loss_12m * 1e6, true)}`);
        tip.place(event);
      })
      .on('pointerleave', function () { d3.select(this).classed('on', false); tip.style('display', 'none'); });
    const legend = d3.select(el).append('div').attr('class', 'fc-legend');
    legend.append('span').text(`${lo.toFixed(0)} per 10,000`);
    legend.append('span').attr('class', 'fc-ramp').style('background', `linear-gradient(to right, ${d3.range(0, 1.0001, 0.1).map((k) => color(lo + k * (hi - lo))).join(', ')})`);
    legend.append('span').text(`${hi.toFixed(0)} per 10,000`);
  });

  dash.draw('statetable', (tbody) => {
    const s = dash.data('states');
    tbody.replaceChildren();
    if (s.status !== 'ok') return;
    const money = (v) => d3.format(',.0f')(+v);
    [...s.data].sort((a, b) => d3.ascending(a.state, b.state)).forEach((r) => {
      const tr = document.createElement('tr');
      [
        [r.state, ''], [fcInt(+r.people_6m), ''], [fcInt(+r.people_12m), ''],
        [fcInt(+r.people_12m_low), 'hide-narrow'], [fcInt(+r.people_12m_high), 'hide-narrow'],
        [Number(r.per10k_12m).toFixed(0), ''], [fcInt(+r.jobs_cut_12m), 'hide-narrow'],
        [money(r.fed_cut_12m), 'hide-narrow'], [money(r.gdp_loss_6m), 'hide-narrow'], [money(r.gdp_loss_12m), ''],
        [money(r.medicare_cost_12m), 'hide-narrow'],
        [money(r.hosp_er_12m), ''], [money(r.uncomp_12m), 'hide-narrow'],
      ].forEach(([text, cls]) => { const td = document.createElement('td'); if (cls) td.className = cls; td.textContent = text; tr.appendChild(td); });
      tbody.appendChild(tr);
    });
  });

  dash.draw('assumetable', (tbody) => {
    const s = dash.data('assumptions');
    tbody.replaceChildren();
    if (s.status !== 'ok') return;
    const f = (v) => { const n = Number(v); return Math.abs(n) >= 1000 ? fcInt(n) : String(v); };
    s.data.forEach((r) => {
      const tr = document.createElement('tr');
      [[r.parameter, 'txt'], [f(r.low), ''], [f(r.central), ''], [f(r.high), ''], [r.unit, 'txt'], [r.basis, 'txt']]
        .forEach(([text, cls]) => { const td = document.createElement('td'); if (cls) td.className = cls; td.textContent = text; tr.appendChild(td); });
      tbody.appendChild(tr);
    });
  });
  dash.draw('hosptable', (tbody) => {
    const d = dash.data('national');
    tbody.replaceChildren();
    if (d.status !== 'ok') return;
    const ids = ['newly_uninsured', 'er_visits', 'ip_stays', 'er_cost', 'ip_cost', 'hosp_er_cost', 'uncomp_care'];
    ids.forEach((id) => [6, 12].forEach((m) => {
      const r = fcRow(d.data, id, m);
      if (!r) return;
      const money = r.unit === 'dollars';
      const tr = document.createElement('tr');
      tr.dataset.key = `${encodeURIComponent(r.metric_id)},${encodeURIComponent(r.months)}`;
      [[r.metric, 'txt'], [r.horizon, ''], [fcCompact(r.median, money), ''], [fcCompact(r.low, money), ''], [fcCompact(r.high, money), '']]
        .forEach(([text, cls]) => { const td = document.createElement('td'); if (cls) td.className = cls; td.textContent = text; tr.appendChild(td); });
      tbody.appendChild(tr);
    }));
  });

/* Coupled model section */
  window.fcMoney = (unit) => String(unit || '').startsWith('dollars');
  window.fcCpl = (v, unit) => {
    const n = Number(v);
    if (unit === 'dollars per person') return `$${n.toFixed(2)}`;
    if (fcMoney(unit) && Math.abs(n) >= 1e6 && Math.abs(n) < 1e9) return `$${Math.round(n / 1e6)}M`;
    return fcCompact(n, fcMoney(unit));
  };

  dash.calc('cpl_compare', {
    inputs: ['national', 'coupled'],
    title: 'First model vs coupled model',
    description: 'Pairs each 12-month measure in the first forecast with the same measure in the coupled model.',
    fn: (national, coupled) => {
      const pairs = [
        ['people', 'Combined people affected', 'people', 'people'],
        ['medicaid', 'Off Medicaid because of the new rules', 'mcd_loss', 'mcd_net'],
        ['snap', 'Off SNAP because of the law', 'snap_off', 'snap_total'],
        ['marketplace', 'Lost Marketplace coverage or subsidy', 'mkt', 'mkt'],
        ['jobs', 'Job losers counted', 'job_losers', 'job_losers'],
        ['uninsured', 'Newly uninsured people', 'newly_uninsured', 'newly_uninsured'],
        ['er', 'ER visits by the newly uninsured', 'er_visits', 'er_visits'],
        ['stays', 'Hospital stays by the newly uninsured', 'ip_stays', 'ip_stays'],
        ['hosp', 'Hospital and ER care, newly uninsured', 'hosp_er_cost', 'hosp_er_cost'],
        ['uncomp', 'Unpaid hospital care', 'uncomp_care', 'uncomp_care'],
        ['fed', 'Federal spending reduction', 'fed_cut', 'fed_cut'],
        ['gdp', 'Lost economic output (GDP)', 'gdp_loss', 'gdp_loss'],
        ['household', 'Added household costs', 'household_cost', 'household_cost'],
      ];
      const pick = (rows, id) => rows.find((r) => r.metric_id === id && Number(r.months) === 12);
      return pairs.map(([measure_id, measure, a, b]) => {
        const x = pick(national, a), y = pick(coupled, b);
        if (!y) return null;
        return {measure_id, measure, unit: y.unit, independent: x ? Number(x.median) : null, coupled: Number(y.median),
          coupled_low: Number(y.low), coupled_high: Number(y.high), unlinked_low: Number(y.low_unlinked), unlinked_high: Number(y.high_unlinked)};
      }).filter(Boolean);
    },
  });

  dash.draw('cpl', (el) => {
    const d = dash.data('coupled');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const [k, v] = el.dataset.where.split('&').map((p) => p.split('=')[1]);
    const r = fcRow(d.data, k, Number(v));
    el.textContent = r ? fcCpl(r[el.dataset.field], r.unit) : '—';
  });

  dash.draw('cplrange', (el) => {
    const d = dash.data('coupled');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const [k, v] = el.dataset.where.split('&').map((p) => p.split('=')[1]);
    const r = fcRow(d.data, k, Number(v));
    el.textContent = r ? `95% interval ${fcCpl(r.low, r.unit)} – ${fcCpl(r.high, r.unit)}` : '—';
  });

  dash.draw('cplwidth', (el) => {
    const d = dash.data('coupled');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const r = fcRow(d.data, 'people', 12);
    if (!r) { el.textContent = '—'; return; }
    const w = (r.high - r.low) / (r.high_unlinked - r.low_unlinked) - 1;
    el.textContent = `${Math.round(w * 100)}%`;
  });

  dash.draw('cplshare', (el) => {
    const d = dash.data('coupled_timeline');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const jun = d.data.find((r) => Number(r.month) === 6), dec = d.data.find((r) => Number(r.month) === 12);
    el.textContent = jun && dec ? `${Math.round(jun.mcd_net / dec.mcd_net * 100)}%` : '—';
  });

  dash.draw('cpltimeline', (el) => {
    const d = dash.data('coupled_timeline');
    el.replaceChildren();
    if (d.status === 'error') { fcFail(el); return; }
    if (d.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');
    const rows = d.data.map((r) => ({t: new Date(r.date + 'T00:00:00Z'), m: +r.month, net: +r.mcd_net, lo: +r.mcd_net_low, hi: +r.mcd_net_high, ever: +r.mcd_ever, ov: +r.overlap}));
    const W = Math.max(320, el.clientWidth || 560), H = 290;
    const left = 52, right = 18, y0 = 34, bottom = 30;
    const x = d3.scaleUtc(d3.extent(rows, (r) => r.t), [left, W - right]);
    const y = d3.scaleLinear([0, d3.max(rows, (r) => Math.max(r.hi, r.ever)) * 1.05], [H - bottom, y0]).nice();
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('role', 'img')
      .attr('aria-label', 'Medicaid losses month by month in 2027, coupled model');
    const cNet = fcResolve(el, dash.colors[0]), cEver = fcResolve(el, dash.colors[1]), cOv = fcResolve(el, dash.colors[2]);
    y.ticks(5).forEach((v) => {
      svg.append('line').attr('x1', left).attr('x2', W - right).attr('y1', y(v)).attr('y2', y(v)).attr('stroke', 'var(--cds-chart-grid)');
      svg.append('text').attr('x', left - 8).attr('y', y(v) + 4).attr('text-anchor', 'end').attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(fcCompact(v));
    });
    rows.filter((r) => r.m % 3 === 0).forEach((r) => svg.append('text').attr('x', x(r.t)).attr('y', H - 10).attr('text-anchor', 'middle').attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(d3.utcFormat('%b %-d')(r.t)));
    svg.append('path').datum(rows).attr('fill', cNet).attr('fill-opacity', 0.16).attr('d', d3.area().x((r) => x(r.t)).y0((r) => y(r.lo)).y1((r) => y(r.hi)));
    const line = (key, c, dash_) => svg.append('path').datum(rows).attr('fill', 'none').attr('stroke', c).attr('stroke-width', 2).attr('stroke-dasharray', dash_ || null)
      .attr('stroke-linecap', 'round').attr('d', d3.line().x((r) => x(r.t)).y((r) => y(r[key])));
    line('ever', cEver, '5 4'); line('net', cNet); line('ov', cOv);
    [[cNet, 'Off Medicaid at month end'], [cEver, 'Ever lost'], [cOv, 'Also cut from SNAP']].forEach(([c, t], i) => {
      const lx = left + i * Math.min(170, (W - left) / 3);
      svg.append('rect').attr('x', lx).attr('y', 6).attr('width', 10).attr('height', 10).attr('rx', 2).attr('fill', c);
      svg.append('text').attr('x', lx + 15).attr('y', 15).attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(t);
    });
    const tip = fcTip(el);
    const dot = svg.append('circle').attr('r', 4).attr('fill', cNet).style('display', 'none');
    svg.append('rect').attr('x', left).attr('y', y0).attr('width', W - right - left).attr('height', H - bottom - y0).attr('fill', 'transparent')
      .on('pointermove', (event) => {
        const [px] = d3.pointer(event);
        const t = x.invert(px);
        const r = rows.reduce((a, b) => (Math.abs(b.t - t) < Math.abs(a.t - t) ? b : a));
        dot.style('display', null).attr('cx', x(r.t)).attr('cy', y(r.net));
        tip.selectAll('*').remove();
        tip.append('div').attr('class', 't1').text(d3.utcFormat('%b %-d, %Y')(r.t));
        tip.append('div').text(`Off Medicaid: ${fcCompact(r.net)} (${fcCompact(r.lo)} – ${fcCompact(r.hi)})`);
        tip.append('div').text(`Ever lost: ${fcCompact(r.ever)}`);
        tip.append('div').text(`Also cut from SNAP: ${fcCompact(r.ov)}`);
        tip.place(event);
      })
      .on('pointerleave', () => { tip.style('display', 'none'); dot.style('display', 'none'); });
  });

  dash.draw('cplcompare', (tbody) => {
    const d = dash.data('cpl_compare');
    tbody.replaceChildren();
    if (d.status !== 'ok') return;
    d.data.forEach((r) => {
      const tr = document.createElement('tr');
      const f = (v) => (v == null ? '—' : fcCpl(v, r.unit));
      [[r.measure, 'txt'], [f(r.independent), ''], [f(r.coupled), ''], [f(r.coupled_low), 'hide-narrow'], [f(r.coupled_high), 'hide-narrow'],
        [f(r.unlinked_low), 'hide-narrow'], [f(r.unlinked_high), 'hide-narrow']]
        .forEach(([text, cls]) => { const td = document.createElement('td'); if (cls) td.className = cls; td.textContent = text; tr.appendChild(td); });
      tbody.appendChild(tr);
    });
  });

  dash.draw('cplinputs', (tbody) => {
    const s = dash.data('coupled_inputs');
    tbody.replaceChildren();
    if (s.status !== 'ok') return;
    s.data.forEach((r) => {
      const tr = document.createElement('tr');
      [[r.parameter, 'txt'], [r.low, ''], [r.central, ''], [r.high, ''], [r.unit, 'txt'], [r.basis, 'txt']]
        .forEach(([text, cls]) => { const td = document.createElement('td'); if (cls) td.className = cls; td.textContent = text; tr.appendChild(td); });
      tbody.appendChild(tr);
    });
  });

  dash.draw('cplstates', (tbody) => {
    const s = dash.data('coupled_states');
    tbody.replaceChildren();
    if (s.status !== 'ok') return;
    const money = (v) => d3.format(',.1f')(+v);
    [...s.data].sort((a, b) => d3.ascending(a.state, b.state)).forEach((r) => {
      const tr = document.createElement('tr');
      [[r.state, ''], [fcInt(+r.people_12m), ''], [fcInt(+r.people_12m_low), 'hide-narrow'], [fcInt(+r.people_12m_high), 'hide-narrow'],
        [Number(r.per10k_12m).toFixed(0), ''], [money(r.hosp_er_12m), ''], [money(r.uncomp_12m), 'hide-narrow']]
        .forEach(([text, cls]) => { const td = document.createElement('td'); if (cls) td.className = cls; td.textContent = text; tr.appendChild(td); });
      tbody.appendChild(tr);
    });
  });
