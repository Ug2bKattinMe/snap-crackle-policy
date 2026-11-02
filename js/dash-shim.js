/*
 * dash-shim.js — a small stand-in for the dashboard runtime the page was first built on.
 * It loads the data files listed in DATASETS, then gives js/charts.js the same `dash` API:
 *   dash.data(id)        -> { status, data, columns }
 *   dash.calc(id, {inputs, fn}) -> a value worked out from other datasets, read with dash.data(id)
 *   dash.draw(name, fn)  -> runs fn(el) on every [data-draw="name"] once data is ready, and again on resize
 *   dash.colors          -> eight series colors from css/theme.css
 * Requires d3 v7 (loaded in index.html).
 */
(function () {
  const DATASETS = {
    national: { url: 'data/forecast_national.csv', type: 'csv' },
    timeline: { url: 'data/forecast_timeline.csv', type: 'csv' },
    states: { url: 'data/forecast_states.csv', type: 'csv' },
    assumptions: { url: 'data/forecast_assumptions.csv', type: 'csv' },
    shapes: { url: 'data/us_state_shapes.json', type: 'json' },
    coupled: { url: 'data/coupled_national.csv', type: 'csv' },
    coupled_timeline: { url: 'data/coupled_timeline.csv', type: 'csv' },
    coupled_states: { url: 'data/coupled_states.csv', type: 'csv' },
    coupled_inputs: { url: 'data/coupled_assumptions.csv', type: 'csv' },
  };
  const calcs = {};

  const store = {};
  Object.keys(DATASETS).forEach((id) => { store[id] = { status: 'loading', data: [], columns: [] }; });
  const drawers = [];

  const runAll = () => {
    drawers.forEach(({ name, fn }) => {
      document.querySelectorAll(`[data-draw="${name}"]`).forEach((el) => {
        try { fn(el); } catch (err) { console.error(`draw "${name}" failed`, err); }
      });
    });
  };

  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

  window.dash = {
    data(id) {
      if (calcs[id]) {
        const ins = calcs[id].inputs.map((i) => window.dash.data(i));
        const bad = ins.find((x) => x.status !== 'ok');
        if (bad) return { status: bad.status, data: [], columns: [] };
        try { return { status: 'ok', data: calcs[id].fn(...ins.map((x) => x.data)), columns: [] }; }
        catch (err) { console.error(`calc "${id}" failed`, err); return { status: 'error', data: [], columns: [] }; }
      }
      return store[id] || { status: 'missing', data: [], columns: [] };
    },
    calc(id, spec) {
      calcs[id] = spec;
    },
    draw(name, fn) {
      drawers.push({ name, fn });
    },
    get colors() {
      return [1, 2, 3, 4, 5, 6, 7, 8].map((i) => css(`--chart-${i}`) || '#2f6fde');
    },
  };

  const load = Object.entries(DATASETS).map(async ([id, src]) => {
    try {
      const data = src.type === 'csv' ? await d3.csv(src.url) : await d3.json(src.url);
      store[id] = { status: 'ok', data, columns: data.columns || [] };
    } catch (err) {
      console.error(`could not load ${src.url}`, err);
      store[id] = { status: 'error', data: [], columns: [], message: String(err) };
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    runAll(); // placeholders while loading
    Promise.all(load).then(runAll);
    let t;
    window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(runAll, 150); });
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', runAll);
  });
})();
