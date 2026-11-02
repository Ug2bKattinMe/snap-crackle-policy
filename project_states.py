"""Project US state GeoJSON to SVG path strings using a d3.geoAlbersUsa-equivalent composite
(lower 48 Albers equal-area conic, Alaska and Hawaii as insets). Output frame is 960x500."""
import json, math, sys

src, abbr_csv, out = sys.argv[1], sys.argv[2], sys.argv[3]
R = math.radians

def conic(parallels, rotate, center, k, translate):
    p0, p1 = R(parallels[0]), R(parallels[1])
    sy0 = math.sin(p0)
    n = (sy0 + math.sin(p1)) / 2
    c = 1 + sy0 * (2 * n - sy0)
    r0 = math.sqrt(c) / n
    def raw(lon, lat):  # degrees, already rotated
        x, y = R(lon), R(lat)
        r = math.sqrt(c - 2 * n * math.sin(y)) / n
        x *= n
        return r * math.sin(x), r0 - r * math.cos(x)
    cx, cy = raw(*center)
    tx, ty = translate
    dx, dy = tx - k * cx, ty + k * cy
    def proj(lon, lat):
        lon = lon + rotate
        if lon > 180: lon -= 360
        if lon < -180: lon += 360
        x, y = raw(lon, lat)
        return dx + k * x, dy - k * y
    return proj

k, tx, ty = 1070, 480, 250
lower48 = conic((29.5, 45.5), 96, (-0.6, 38.7), k, (tx, ty))
alaska = conic((55, 65), 154, (-2, 58.5), 0.35 * k, (tx - 0.307 * k, ty + 0.201 * k))
hawaii = conic((8, 18), 157, (-3, 19.9), k, (tx - 0.205 * k, ty + 0.212 * k))

abbr = {}
for line in open(abbr_csv).read().splitlines()[1:]:
    parts = line.split(',')
    abbr[parts[0]] = parts[1]

g = json.load(open(src))
rows = []
for f in g['features']:
    name = f['properties']['name']
    if name not in abbr:
        continue  # Puerto Rico: no population/enrollment row in this comparison
    proj = alaska if name == 'Alaska' else hawaii if name == 'Hawaii' else lower48
    geom = f['geometry']
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    d = []
    for poly in polys:
        for ring in poly:
            pts = [proj(lon, lat) for lon, lat in ring]
            d.append('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in pts) + 'Z')
    rows.append({'abbr': abbr[name], 'state': name, 'path': ''.join(d)})

rows.sort(key=lambda r: r['state'])
json.dump(rows, open(out, 'w'), separators=(',', ':'))
xs = [float(v) for r in rows for v in r['path'].replace('M', ' ').replace('L', ' ').replace('Z', ' ').replace(',', ' ').split()]
print(len(rows), 'states; bytes', len(json.dumps(rows)), 'x range', min(xs[0::2]), max(xs[0::2]), 'y range', min(xs[1::2]), max(xs[1::2]))
