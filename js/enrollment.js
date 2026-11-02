/* Enrollment and SNAP overlap page: maps, tables and figures. Uses d3 v7 and js/dash-shim.js. */
  dash.calc('shares', {
    inputs: ['population', 'medicare', 'medicaid', 'duals', 'ma', 'kids'],
    title: 'Coverage groups by state',
    description: 'Splits enrollees into Medicare only (Medicare minus all duals), dual enrollees, and Medicaid/CHIP only (Medicaid/CHIP minus full-benefit duals), plus Medicare Advantage, each as a percent of state population rounded to one decimal; joined on state abbreviation.',
    fn: (population, medicare, medicaid, duals, ma, kids) => {
      const mcr = new Map(medicare.map((r) => [r.abbr, Number(r.medicare_enrollees)]));
      const mcd = new Map(medicaid.map((r) => [r.abbr, Number(r.medicaid_chip_enrollees)]));
      const dual = new Map(duals.map((r) => [r.abbr, r]));
      const adv = new Map(ma.map((r) => [r.abbr, Number(r.ma_enrollees)]));
      const age = new Map(kids.map((r) => [r.abbr, r]));
      const pct = (n, pop) => Math.round((n / pop) * 1000) / 10;
      return population.map((p) => {
        const pop = Number(p.population);
        const d = dual.get(p.abbr);
        const totalDuals = Number(d.total_duals);
        const fullDuals = Number(d.full_benefit_duals);
        const medicareOnly = mcr.get(p.abbr) - totalDuals;
        const medicaidOnly = mcd.get(p.abbr) - fullDuals;
        const maN = adv.get(p.abbr);
        return {
          state: p.state, abbr: p.abbr, population: pop,
          medicare_only: medicareOnly, medicare_only_pct: pct(medicareOnly, pop),
          total_duals: totalDuals, dual_pct: pct(totalDuals, pop),
          medicaid_only: medicaidOnly, medicaid_only_pct: pct(medicaidOnly, pop),
          ma_enrollees: maN, ma_pct: pct(maN, pop),
          total_covered: medicareOnly + totalDuals + medicaidOnly,
          total_pct: pct(medicareOnly + totalDuals + medicaidOnly, pop),
          medicaid_children: Number(age.get(p.abbr).child_enrollees),
          medicaid_adults: Number(age.get(p.abbr).adult_enrollees),
          child_share_pct: pct(Number(age.get(p.abbr).child_enrollees), mcd.get(p.abbr)),
        };
      });
    },
  });

  dash.calc('hm_national', {
    inputs: ['shares'],
    title: 'National shares and extremes',
    description: 'Each group summed over the 50 states and DC and divided by total population, plus the highest and lowest states for dual enrollment and Medicare Advantage.',
    fn: (shares) => {
      const sum = (k) => shares.reduce((s, r) => s + r[k], 0);
      const pop = sum('population');
      const pct = (n) => Math.round((n / pop) * 1000) / 10;
      const mo = sum('medicare_only');
      const du = sum('total_duals');
      const md = sum('medicaid_only');
      const byDual = [...shares].sort((a, b) => a.dual_pct - b.dual_pct);
      const byMa = [...shares].sort((a, b) => a.ma_pct - b.ma_pct);
      const last = shares.length - 1;
      return [{
        any_pct: pct(mo + du + md),
        medicare_only_pct: pct(mo), dual_pct: pct(du), medicaid_only_pct: pct(md), ma_pct: pct(sum('ma_enrollees')),
        dual_high_state: byDual[last].state, dual_high_pct: byDual[last].dual_pct,
        dual_low_state: byDual[0].state, dual_low_pct: byDual[0].dual_pct,
        ma_high_state: byMa[last].state, ma_high_pct: byMa[last].ma_pct,
        ma_low_state: byMa[0].state, ma_low_pct: byMa[0].ma_pct,
      }];
    },
  });

  window.hmFmtPct = (v) => `${Number(v).toFixed(1)}%`;
  window.hmFmtInt = d3.format(',');

  dash.draw('hmnat', (el) => {
    const d = dash.data('hm_national');
    if (d.status !== 'ok' || !d.data.length) { el.textContent = '—'; return; }
    const v = d.data[0][el.dataset.field];
    el.textContent = typeof v === 'number' ? hmFmtPct(v) : String(v);
  });

  // Resolve a CSS color expression (a token or a series color) to rgb() so d3 can blend it.
  window.hmResolve = (host, expr) => {
    const probe = document.createElement('span');
    probe.style.color = expr;
    probe.style.display = 'none';
    host.appendChild(probe);
    const c = getComputedStyle(probe).color;
    probe.remove();
    return c;
  };

  dash.draw('hmmap', (el) => {
    const s = dash.data('shares');
    const g = dash.data('shapes');
    el.replaceChildren();
    if (s.status === 'error' || g.status === 'error') {
      el.classList.remove('dash-skeleton');
      const f = document.createElement('div');
      f.className = 'hm-fail';
      f.textContent = 'Failed to load';
      el.appendChild(f);
      return;
    }
    if (s.status !== 'ok' || g.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');

    const metric = el.dataset.metric;
    const countField = el.dataset.count;
    const label = el.dataset.label;
    const byAbbr = new Map(s.data.map((r) => [r.abbr, r]));
    const values = s.data.map((r) => r[metric]);
    const lo = d3.min(values);
    const hi = d3.max(values);
    const series = hmResolve(el, dash.colors[Number(el.dataset.color)] || dash.colors[0]);
    const base = hmResolve(el, 'var(--color-panel)');
    const mix = d3.interpolateRgb(base, series);
    const t = d3.scaleLinear([lo, hi], [0.12, 1]).clamp(true);
    const color = (v) => mix(t(v));

    const svg = d3.select(el).append('svg')
      .attr('viewBox', '0 0 960 500')
      .attr('width', '100%')
      .attr('role', 'img')
      .attr('aria-label', `Map of the share of each state's residents ${label}`);

    const tip = d3.select(el).append('div').attr('class', 'hm-tip').style('display', 'none');
    const showTip = (event, row) => {
      tip.selectAll('*').remove();
      tip.append('div').attr('class', 't1').text(row.state);
      tip.append('div').text(`${hmFmtPct(row[metric])} ${label}`);
      tip.append('div').text(`${hmFmtInt(row[countField])} of ${hmFmtInt(row.population)} residents`);
      tip.style('display', 'block');
      const box = el.getBoundingClientRect();
      const node = tip.node();
      let x = event.clientX - box.left + 12;
      let y = event.clientY - box.top + 12;
      x = Math.min(x, box.width - node.offsetWidth - 4);
      if (y + node.offsetHeight > box.height) y = event.clientY - box.top - node.offsetHeight - 12;
      tip.style('left', `${Math.max(4, x)}px`).style('top', `${Math.max(4, y)}px`);
    };

    svg.append('g').selectAll('path')
      .data(g.data.filter((d) => byAbbr.has(d.abbr)))
      .join('path')
      .attr('d', (d) => d.path)
      .attr('fill', (d) => color(byAbbr.get(d.abbr)[metric]))
      .on('pointermove', function (event, d) {
        d3.select(this).classed('on', true).raise();
        showTip(event, byAbbr.get(d.abbr));
      })
      .on('pointerleave', function () {
        d3.select(this).classed('on', false);
        tip.style('display', 'none');
      });

    const legend = d3.select(el).append('div').attr('class', 'hm-legend');
    legend.append('span').text(hmFmtPct(lo));
    const stops = d3.range(0, 1.0001, 0.1).map((k) => color(lo + k * (hi - lo)));
    legend.append('span').attr('class', 'hm-ramp').style('background', `linear-gradient(to right, ${stops.join(', ')})`);
    legend.append('span').text(hmFmtPct(hi));
  });

  dash.draw('hmtable', (tbody) => {
    const s = dash.data('shares');
    tbody.replaceChildren();
    if (s.status !== 'ok') return;
    const rows = [...s.data].sort((a, b) => d3.ascending(a.state, b.state));
    for (const r of rows) {
      const tr = document.createElement('tr');
      const cells = [
        [r.state, ''],
        [hmFmtInt(r.population), 'hide-narrow'],
        [hmFmtInt(r.medicare_only), 'hide-narrow'],
        [hmFmtPct(r.medicare_only_pct), ''],
        [hmFmtInt(r.total_duals), 'hide-narrow'],
        [hmFmtPct(r.dual_pct), ''],
        [hmFmtInt(r.medicaid_only), 'hide-narrow'],
        [hmFmtPct(r.medicaid_only_pct), ''],
        [hmFmtInt(r.medicaid_children), 'hide-narrow'],
        [hmFmtInt(r.medicaid_adults), 'hide-narrow'],
        [hmFmtPct(r.child_share_pct), ''],
        [hmFmtInt(r.ma_enrollees), 'hide-narrow'],
        [hmFmtPct(r.ma_pct), ''],
        [hmFmtInt(r.total_covered), 'hide-narrow'],
        [hmFmtPct(r.total_pct), 'hm-total'],
      ];
      for (const [text, cls] of cells) {
        const td = document.createElement('td');
        if (cls) td.className = cls;
        td.textContent = text;
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
  });

  dash.calc('snapx', {
    inputs: ['snap'],
    title: 'SNAP overlap per 10,000 residents',
    description: 'Converts each state\'s modeled count of people losing SNAP who also face 2027 Medicare or Medicaid changes into a rate per 10,000 residents, for the median and the 2.5th and 97.5th percentiles (95% interval).',
    fn: (snap) => snap.map((r) => {
      const pop = Number(r.population);
      const per = (v) => Math.round((Number(v) / pop) * 100000) / 10;
      return {
        state: r.state, abbr: r.abbr, population: pop,
        older_adults: Number(r.older_adults), parents: Number(r.parents), children: Number(r.children), duals: Number(r.duals),
        total_low: Number(r.total_low), total_mid: Number(r.total_mid), total_high: Number(r.total_high),
        range_label: `${Number(r.total_low).toLocaleString('en-US')} – ${Number(r.total_high).toLocaleString('en-US')}`,
        per10k_low: per(r.total_low), per10k_mid: per(r.total_mid), per10k_high: per(r.total_high),
        snap_all: Number(r.snap_fy2025),
        snap_pct_pop: Math.round((Number(r.snap_fy2025) / pop) * 1000) / 10,
        overlap_pct_snap: Math.round((Number(r.total_mid) / Number(r.snap_fy2025)) * 1000) / 10,
      };
    }),
  });

  dash.calc('snaptot', {
    inputs: ['snapx'],
    title: 'All SNAP recipients, national',
    description: 'Sums FY2025 average monthly SNAP recipients over the 50 states and DC, as a share of their population, and the modeled overlap median as a share of those recipients.',
    fn: (snapx) => {
      const snap = snapx.reduce((s, r) => s + r.snap_all, 0);
      const pop = snapx.reduce((s, r) => s + r.population, 0);
      const overlap = snapx.reduce((s, r) => s + r.total_mid, 0);
      return [{ snap_all: snap, snap_pct_pop: Math.round((snap / pop) * 1000) / 10, overlap_pct_snap: Math.round((overlap / snap) * 1000) / 10 }];
    },
  });

  dash.draw('snaptot', (el) => {
    const d = dash.data('snaptot');
    if (d.status !== 'ok' || !d.data.length) { el.textContent = '—'; return; }
    const v = d.data[0][el.dataset.field];
    el.textContent = el.dataset.field === 'snap_all'
      ? Intl.NumberFormat('en', {notation: 'compact', maximumFractionDigits: 1}).format(v)
      : `${Number(v).toFixed(1)}%`;
  });

  dash.draw('snapallmap', (el) => {
    const s = dash.data('snapx');
    const g = dash.data('shapes');
    el.replaceChildren();
    if (s.status === 'error' || g.status === 'error') {
      el.classList.remove('dash-skeleton');
      const f = document.createElement('div');
      f.className = 'hm-fail';
      f.textContent = 'Failed to load';
      el.appendChild(f);
      return;
    }
    if (s.status !== 'ok' || g.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');
    const byAbbr = new Map(s.data.map((r) => [r.abbr, r]));
    const values = s.data.map((r) => r.snap_pct_pop);
    const lo = d3.min(values);
    const hi = d3.max(values);
    const mix = d3.interpolateRgb(hmResolve(el, 'var(--color-panel)'), hmResolve(el, dash.colors[5] || dash.colors[0]));
    const t = d3.scaleLinear([lo, hi], [0.12, 1]).clamp(true);
    const color = (v) => mix(t(v));
    const svg = d3.select(el).append('svg')
      .attr('viewBox', '0 0 960 500').attr('width', '100%').attr('role', 'img')
      .attr('aria-label', 'Map of SNAP recipients as a share of state population, FY2025');
    const tip = d3.select(el).append('div').attr('class', 'hm-tip').style('display', 'none');
    const showTip = (event, row) => {
      tip.selectAll('*').remove();
      tip.append('div').attr('class', 't1').text(row.state);
      tip.append('div').text(`${hmFmtPct(row.snap_pct_pop)} of residents on SNAP`);
      tip.append('div').text(`${hmFmtInt(row.snap_all)} recipients in an average month`);
      tip.append('div').text(`Overlap group: ${hmFmtInt(row.total_mid)} (${Number(row.overlap_pct_snap).toFixed(1)}% of recipients)`);
      tip.style('display', 'block');
      const box = el.getBoundingClientRect();
      const node = tip.node();
      let x = event.clientX - box.left + 12;
      let y = event.clientY - box.top + 12;
      x = Math.min(x, box.width - node.offsetWidth - 4);
      if (y + node.offsetHeight > box.height) y = event.clientY - box.top - node.offsetHeight - 12;
      tip.style('left', `${Math.max(4, x)}px`).style('top', `${Math.max(4, y)}px`);
    };
    svg.append('g').selectAll('path')
      .data(g.data.filter((d) => byAbbr.has(d.abbr)))
      .join('path')
      .attr('d', (d) => d.path)
      .attr('fill', (d) => color(byAbbr.get(d.abbr).snap_pct_pop))
      .on('pointermove', function (event, d) { d3.select(this).classed('on', true).raise(); showTip(event, byAbbr.get(d.abbr)); })
      .on('pointerleave', function () { d3.select(this).classed('on', false); tip.style('display', 'none'); });
    const legend = d3.select(el).append('div').attr('class', 'hm-legend');
    legend.append('span').text(hmFmtPct(lo));
    const stops = d3.range(0, 1.0001, 0.1).map((k) => color(lo + k * (hi - lo)));
    legend.append('span').attr('class', 'hm-ramp').style('background', `linear-gradient(to right, ${stops.join(', ')})`);
    legend.append('span').text(hmFmtPct(hi));
  });

  dash.draw('snapnat', (el) => {
    const d = dash.data('snapnat');
    if (d.status !== 'ok' || !d.data.length) { el.textContent = '—'; return; }
    const v = Number(d.data[0][el.dataset.field]);
    el.textContent = Intl.NumberFormat('en', {notation: 'compact', maximumFractionDigits: 0}).format(Math.round(v / 1000) * 1000);
  });

  dash.draw('snapmap', (el) => {
    const s = dash.data('snapx');
    const g = dash.data('shapes');
    el.replaceChildren();
    if (s.status === 'error' || g.status === 'error') {
      el.classList.remove('dash-skeleton');
      const f = document.createElement('div');
      f.className = 'hm-fail';
      f.textContent = 'Failed to load';
      el.appendChild(f);
      return;
    }
    if (s.status !== 'ok' || g.status !== 'ok') { el.classList.add('dash-skeleton'); return; }
    el.classList.remove('dash-skeleton');
    const byAbbr = new Map(s.data.map((r) => [r.abbr, r]));
    const values = s.data.map((r) => r.per10k_mid);
    const lo = d3.min(values);
    const hi = d3.max(values);
    const series = hmResolve(el, dash.colors[4] || dash.colors[0]);
    const base = hmResolve(el, 'var(--color-panel)');
    const mix = d3.interpolateRgb(base, series);
    const t = d3.scaleLinear([lo, hi], [0.12, 1]).clamp(true);
    const color = (v) => mix(t(v));
    const fmt1 = (v) => Number(v).toFixed(1);
    const svg = d3.select(el).append('svg')
      .attr('viewBox', '0 0 960 500').attr('width', '100%').attr('role', 'img')
      .attr('aria-label', 'Map of people per 10,000 residents likely to lose SNAP who also face 2027 Medicare or Medicaid changes');
    const tip = d3.select(el).append('div').attr('class', 'hm-tip').style('display', 'none');
    const showTip = (event, row) => {
      tip.selectAll('*').remove();
      tip.append('div').attr('class', 't1').text(row.state);
      tip.append('div').text(`${fmt1(row.per10k_mid)} per 10,000 residents (95% interval ${fmt1(row.per10k_low)}–${fmt1(row.per10k_high)})`);
      tip.append('div').text(`About ${hmFmtInt(row.total_mid)} people (95% interval ${hmFmtInt(row.total_low)}–${hmFmtInt(row.total_high)})`);
      tip.append('div').text(`Adults 55–64 ${hmFmtInt(row.older_adults)} · parents ${hmFmtInt(row.parents)} · children ${hmFmtInt(row.children)} · duals ${hmFmtInt(row.duals)}`);
      tip.style('display', 'block');
      const box = el.getBoundingClientRect();
      const node = tip.node();
      let x = event.clientX - box.left + 12;
      let y = event.clientY - box.top + 12;
      x = Math.min(x, box.width - node.offsetWidth - 4);
      if (y + node.offsetHeight > box.height) y = event.clientY - box.top - node.offsetHeight - 12;
      tip.style('left', `${Math.max(4, x)}px`).style('top', `${Math.max(4, y)}px`);
    };
    svg.append('g').selectAll('path')
      .data(g.data.filter((d) => byAbbr.has(d.abbr)))
      .join('path')
      .attr('d', (d) => d.path)
      .attr('fill', (d) => color(byAbbr.get(d.abbr).per10k_mid))
      .on('pointermove', function (event, d) { d3.select(this).classed('on', true).raise(); showTip(event, byAbbr.get(d.abbr)); })
      .on('pointerleave', function () { d3.select(this).classed('on', false); tip.style('display', 'none'); });
    const legend = d3.select(el).append('div').attr('class', 'hm-legend');
    legend.append('span').text(`${fmt1(lo)} per 10,000`);
    const stops = d3.range(0, 1.0001, 0.1).map((k) => color(lo + k * (hi - lo)));
    legend.append('span').attr('class', 'hm-ramp').style('background', `linear-gradient(to right, ${stops.join(', ')})`);
    legend.append('span').text(`${fmt1(hi)} per 10,000`);
  });

  dash.draw('snaptable', (tbody) => {
    const s = dash.data('snapx');
    tbody.replaceChildren();
    if (s.status !== 'ok') return;
    const rows = [...s.data].sort((a, b) => d3.ascending(a.state, b.state));
    for (const r of rows) {
      const tr = document.createElement('tr');
      const cells = [
        [r.state, ''],
        [hmFmtInt(r.snap_all), 'hide-narrow'],
        [hmFmtPct(r.snap_pct_pop), ''],
        [hmFmtInt(r.older_adults), 'hide-narrow'],
        [hmFmtInt(r.parents), 'hide-narrow'],
        [hmFmtInt(r.children), 'hide-narrow'],
        [hmFmtInt(r.duals), 'hide-narrow'],
        [hmFmtInt(r.total_mid), 'hm-total'],
        [r.range_label, ''],
        [Number(r.per10k_mid).toFixed(1), ''],
        [hmFmtPct(r.overlap_pct_snap), ''],
      ];
      for (const [text, cls] of cells) {
        const td = document.createElement('td');
        if (cls) td.className = cls;
        td.textContent = text;
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
  });
