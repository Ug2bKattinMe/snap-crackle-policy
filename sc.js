/* South Carolina page: county map, charts and tables. Uses d3 v7, js/dash-shim.js and helpers from js/charts.js. */
  window.scRow = (rows, id, months) => rows.find((r) => r.metric_id === id && (months == null || Number(r.months) === months));
  window.scFmt = (v, unit) => {
    const n = Number(v);
    if (unit === 'dollars') return Math.abs(n) >= 1e9 ? `$${(n / 1e9).toFixed(1)}B` : `$${Math.round(n / 1e6)}M`;
    return Math.abs(n) >= 1e6 ? fcCompact(n) : fcInt(Math.round(n / 100) * 100);
  };
  window.scMetric = 'snap_change_pct';
  document.querySelectorAll('.sc-metric').forEach((sel) => sel.addEventListener('change', () => {
    window.scMetric = sel.value;
    dash.draw('sccountymap');
  }));

  dash.draw('scnum', (el) => {
    const d = dash.data('sc_forecast');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const [k, v] = el.dataset.where.split('&').map((p) => p.split('=')[1]);
    const r = scRow(d.data, k, Number(v));
    el.textContent = r ? scFmt(r[el.dataset.field], r.unit) : '—';
  });

  dash.draw('scrange', (el) => {
    const d = dash.data('sc_forecast');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const [k, v] = el.dataset.where.split('&').map((p) => p.split('=')[1]);
    const r = scRow(d.data, k, Number(v));
    el.textContent = r ? `95% interval ${scFmt(r.low, r.unit)} – ${scFmt(r.high, r.unit)}` : '—';
  });

  dash.draw('scctx', (el) => {
    const d = dash.data('sc_context');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const r = scRow(d.data, el.dataset.where.split('=')[1]);
    if (!r) { el.textContent = '—'; return; }
    const n = Number(r.value);
    el.textContent = Number.isInteger(n) && Math.abs(n) >= 1000 ? fcInt(n) : String(n);
  });

  dash.draw('scctxabs', (el) => {
    const d = dash.data('sc_context');
    if (d.status !== 'ok') { el.textContent = '—'; return; }
    const r = scRow(d.data, el.dataset.where.split('=')[1]);
    el.textContent = r ? String(Math.abs(Number(r.value))) : '—';
  });

  dash.draw('scgroups', (el) => {
    const d = dash.data('sc_forecast');
    el.replaceChildren();
    if (d.status === 'error') { fcFail(el); return; }
    if (d.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');
    const groups = [['snap_off', 'Off SNAP because of the law', 'snap'], ['mkt', 'Lost Marketplace coverage or subsidy', 'mkt'],
      ['imm', 'Immigrants losing Medicaid or Medicare', 'imm'], ['job_losers', 'Lost a job tied to the cuts', 'jobs']];
    const rows = groups.map(([id, name, c]) => ({id, name, c, r: scRow(d.data, id, 12)})).filter((g) => g.r);
    const W = Math.max(300, el.clientWidth || 560);
    const narrow = fcNarrow(W, 680);
    const lab = narrow ? 18 : 0, labelW = narrow ? 14 : Math.min(240, W * 0.42), right = 70, rowH = 40 + lab, y0 = 8;
    const H = y0 + rows.length * rowH + 26;
    const x = d3.scaleLinear([0, d3.max(rows, (g) => +g.r.high)], [labelW, W - right]).nice();
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('role', 'img')
      .attr('aria-label', 'South Carolinians affected in 2027 by group, with 95% intervals');
    x.ticks(narrow ? 3 : 5).forEach((v) => {
      svg.append('line').attr('x1', x(v)).attr('x2', x(v)).attr('y1', y0).attr('y2', H - 22).attr('stroke', 'var(--cds-chart-grid)');
      svg.append('text').attr('x', x(v)).attr('y', H - 6).attr('text-anchor', 'middle').attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(fcCompact(v));
    });
    const tip = fcTip(el);
    rows.forEach((g, i) => {
      const yy = y0 + i * rowH;
      const c = fcC(el, g.c);
      const t = svg.append('text').attr('font-size', 12).attr('fill', 'var(--color-fg)').text(g.name);
      if (narrow) t.attr('x', 0).attr('y', yy + 12); else t.attr('x', labelW - 8).attr('y', yy + 19).attr('text-anchor', 'end');
      const mid = +g.r.median, lo = +g.r.low, hi = +g.r.high, by = yy + lab + 6;
      svg.append('rect').attr('x', labelW).attr('y', by).attr('height', 18).attr('rx', 2).attr('width', Math.max(1, x(mid) - labelW)).attr('fill', c)
        .on('pointermove', (event) => {
          tip.selectAll('*').remove();
          tip.append('div').attr('class', 't1').text(g.name);
          tip.append('div').text(`${fcInt(Math.round(mid / 100) * 100)} (median)`);
          tip.append('div').text(`95% interval ${fcInt(Math.round(lo / 100) * 100)} – ${fcInt(Math.round(hi / 100) * 100)}`);
          tip.place(event);
        })
        .on('pointerleave', () => tip.style('display', 'none'));
      svg.append('line').attr('x1', x(lo)).attr('x2', x(hi)).attr('y1', by + 9).attr('y2', by + 9).attr('stroke', 'var(--color-fg)').attr('stroke-opacity', 0.55).attr('stroke-width', 1.2);
      svg.append('text').attr('x', x(hi) + 5).attr('y', by + 13).attr('font-size', 11).attr('fill', 'var(--color-fg-muted)').text(fcCompact(mid));
    });
  });

  dash.draw('sccountymap', (el) => {
    const s = dash.data('sc_counties');
    const g = dash.data('sc_shapes');
    el.replaceChildren();
    if (s.status === 'error' || g.status === 'error') { el.classList.remove('dash-skeleton'); fcFail(el); return; }
    if (s.status !== 'ok' || g.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');
    const m = window.scMetric;
    const by = new Map(s.data.map((r) => [r.county, r]));
    const val = (r) => (m === 'snap_change_pct' ? -Number(r[m]) : Number(r[m]));  // a bigger drop reads darker
    const vals = s.data.map(val);
    const lo = d3.min(vals), hi = d3.max(vals);
    const rgb = (fcResolve(el, 'var(--color-panel)').match(/[\d.]+/g) || [255, 255, 255]).map(Number);
    const dark = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) < 128;
    const stops = dark ? ['#3b0f70', '#8c2981', '#de4968', '#fe9f6d', '#fcfdbf'] : ['#fff3b0', '#fdc35f', '#fb8b3c', '#e3322b', '#8f0b2e'];
    const ramp = (k) => {
      const p = Math.max(0, Math.min(1, k)) * (stops.length - 1), i = Math.min(stops.length - 2, Math.floor(p));
      return d3.interpolateRgb(stops[i], stops[i + 1])(p - i);
    };
    const t = d3.scaleLinear([lo, hi], [0, 1]).clamp(true);
    const svg = d3.select(el).append('svg').attr('viewBox', '0 0 800 640').attr('width', '100%').attr('role', 'img')
      .attr('aria-label', 'Map of South Carolina counties');
    const tip = fcTip(el);
    svg.append('g').selectAll('path').data(g.data.filter((d) => by.has(d.county))).join('path')
      .attr('d', (d) => d.path).attr('fill', (d) => ramp(t(val(by.get(d.county)))))
      .on('pointermove', function (event, d) {
        d3.select(this).classed('on', true).raise();
        const r = by.get(d.county);
        tip.selectAll('*').remove();
        tip.append('div').attr('class', 't1').text(`${r.county} County`);
        tip.append('div').text(`SNAP: ${fcInt(+r.persons_jul2025)} → ${fcInt(+r.persons_jul2026)} (${Number(r.snap_change_pct).toFixed(1)}%)`);
        tip.append('div').text(`${Number(r.snap_per_1000).toFixed(0)} SNAP recipients per 1,000 residents`);
        tip.append('div').text(`Forecast affected, 2027: ${fcInt(+r.people_12m)} (${fcInt(+r.people_12m_low)}–${fcInt(+r.people_12m_high)})`);
        tip.place(event);
      })
      .on('pointerleave', function () { d3.select(this).classed('on', false); tip.style('display', 'none'); });
    const fmt = (v) => (m === 'snap_change_pct' ? `${(-v).toFixed(1)}%` : `${v.toFixed(0)} per 1,000`);
    const legend = d3.select(el).append('div').attr('class', 'fc-legend');
    legend.append('span').text(fmt(lo));
    legend.append('span').attr('class', 'fc-ramp').style('background', `linear-gradient(to right, ${d3.range(0, 1.0001, 0.1).map(ramp).join(', ')})`);
    legend.append('span').text(fmt(hi));
  });

  dash.draw('scmoney', (tbody) => {
    const d = dash.data('sc_forecast');
    tbody.replaceChildren();
    if (d.status !== 'ok') return;
    ['fed_cut', 'gdp_loss', 'tax_loss', 'household_cost', 'lost_snap', 'medicare_cost', 'hosp_er_cost', 'uncomp_care',
      'snap_extra_cost', 'state_admin', 'state_benefit', 'state_total', 'state_benefit_fy28'].forEach((id) => {
      const r = scRow(d.data, id, 12);
      if (!r) return;
      const tr = document.createElement('tr');
      tr.dataset.key = `${encodeURIComponent(r.metric_id)},${encodeURIComponent(r.months)}`;
      [[r.metric, 'txt'], [scFmt(r.median, r.unit), ''], [scFmt(r.low, r.unit), ''], [scFmt(r.high, r.unit), '']]
        .forEach(([text, cls]) => { const td = document.createElement('td'); if (cls) td.className = cls; td.textContent = text; tr.appendChild(td); });
      tbody.appendChild(tr);
    });
  });

  dash.draw('sccountytable', (tbody) => {
    const s = dash.data('sc_counties');
    tbody.replaceChildren();
    if (s.status !== 'ok') return;
    [...s.data].sort((a, b) => d3.ascending(a.county, b.county)).forEach((r) => {
      const tr = document.createElement('tr');
      [[r.county, ''], [fcInt(+r.persons_jul2025), 'hide-narrow'], [fcInt(+r.persons_jul2026), ''], [Number(r.snap_change_pct).toFixed(1), ''],
        [Number(r.snap_per_1000).toFixed(0), 'hide-narrow'], [fcInt(+r.people_12m), ''], [fcInt(+r.people_12m_low), 'hide-narrow'],
        [fcInt(+r.people_12m_high), 'hide-narrow'], [Number(r.people_per_1000).toFixed(1), '']]
        .forEach(([text, cls]) => { const td = document.createElement('td'); if (cls) td.className = cls; td.textContent = text; tr.appendChild(td); });
      tbody.appendChild(tr);
    });
  });
