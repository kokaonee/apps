#!/usr/bin/env python3
"""Write apps/cluster_themes/hud/layouts/livecockpit.json, the Live Cockpit theme (edit this, not the JSON).

    python3 tools/gen_livecockpit.py

After BMW's Live Cockpit Professional M Performance view (angular outline, after M8 / Z4 M40i photos): the speed
scale on the left, the rev scale on the right, the digital speed and the gear each over a line, fuel in the lower left
corner. Added for this theme: the hybrid battery in the lower right corner (where BMW's PHEVs show it), and two bracket
gauges in the panels like BMW's sport displays: oil on the left, gearbox oil on the right. The Waze map opens in the
middle as an oval (mapLive). The scale outline is drawn here (CORNERS), the numbers set along it; the corner dials
come from mview.json.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUTS = os.path.join(HERE, '..', 'apps', 'cluster_themes', 'hud', 'layouts')
FONTS = os.path.join(HERE, '..', 'apps', 'cluster_themes', 'hud', 'fonts')
W = 1920
mv = json.load(open(os.path.join(LAYOUTS, 'mview.json')))
base = mv['widgets'][0]

# the scale's line, angular like BMW's M Performance view (M8 / Z4 M40i photos, Nov 23 2026): straight pieces with small
# rounded corners instead of M view's wide arcs. Corners: (x, y, corner radius), from the end by the middle (a short
# raised piece, then a step down, as BMW's bottom line by the check-control area) round to the top end. Written as
# points where straight pieces and arcs meet plus "arcs" [cx, cy, r, sweep] per piece, as the shader takes it.
CORNERS = [(842, 619, 0), (776, 619, 8), (752, 636, 8), (330, 636, 22), (130, 470, 22), (104, 385, 16),
           (118, 292, 22), (300, 112, 22), (742, 26, 0)]
START_X = CORNERS[0][0]


def fillet(corners):
    pts, arcs = [list(corners[0][:2])], []
    for i in range(1, len(corners) - 1):
        (ax, ay, _), (bx, by, r), (cx, cy, _) = corners[i - 1], corners[i], corners[i + 1]
        u = ((ax - bx), (ay - by)); v = ((cx - bx), (cy - by))
        lu, lv = math.hypot(*u), math.hypot(*v)
        u = (u[0] / lu, u[1] / lu); v = (v[0] / lv, v[1] / lv)
        ang = math.acos(max(-1, min(1, u[0] * v[0] + u[1] * v[1])))          # the inner angle at the corner
        if r <= 0 or ang > math.pi - 1e-3:
            pts.append([bx, by]); arcs.append([0, 0, 0, 0]); continue
        t = r / math.tan(ang / 2)                                           # corner to the tangent points
        p1 = (bx + u[0] * t, by + u[1] * t); p2 = (bx + v[0] * t, by + v[1] * t)
        bis = (u[0] + v[0], u[1] + v[1]); lb = math.hypot(*bis); bis = (bis[0] / lb, bis[1] / lb)
        d = r / math.sin(ang / 2)
        c = (bx + bis[0] * d, by + bis[1] * d)
        a1 = math.atan2(p1[1] - c[1], p1[0] - c[0]); a2 = math.atan2(p2[1] - c[1], p2[0] - c[0])
        sw = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi                  # the short way round
        pts.append([round(p1[0], 2), round(p1[1], 2)]); arcs.append([0, 0, 0, 0])         # the straight piece to it
        pts.append([round(p2[0], 2), round(p2[1], 2)]); arcs.append([round(c[0], 3), round(c[1], 3), r, round(sw, 6)])
    pts.append(list(corners[-1][:2])); arcs.append([0, 0, 0, 0])
    return pts, arcs


new_path, new_arcs = fillet(CORNERS)
assert len(new_path) <= 16, 'the shader takes 16 points'


def pieces():
    """(length, point at h 0..1, unit tangent at h) of each piece."""
    out = []
    for i, g in enumerate(new_arcs):
        a, b = new_path[i], new_path[i + 1]
        if g[2]:
            c, r, sw = (g[0], g[1]), g[2], g[3]
            a0 = math.atan2(a[1] - c[1], a[0] - c[0])
            pt = lambda h, c=c, r=r, sw=sw, a0=a0: (c[0] + r * math.cos(a0 + sw * h), c[1] + r * math.sin(a0 + sw * h))
            tg = lambda h, sw=sw, a0=a0: (-math.sin(a0 + sw * h) * math.copysign(1, sw), math.cos(a0 + sw * h) * math.copysign(1, sw))
            out.append((abs(r * sw), pt, tg))
        else:
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            out.append((L, lambda h, a=a, b=b: (a[0] + (b[0] - a[0]) * h, a[1] + (b[1] - a[1]) * h),
                        lambda h, a=a, b=b, L=L: ((b[0] - a[0]) / L, (b[1] - a[1]) / L)))
    return out


PIECES = pieces()
TOTAL = sum(p[0] for p in PIECES)


def at(s):
    """The point and the inward normal (into the scale) at arc length s."""
    for L, pt, tg in PIECES:
        if s <= L or L == PIECES[-1][0] and pt is PIECES[-1][1]:
            h = max(0, min(1, s / L)); t = tg(h)
            return pt(h), (-t[1], t[0])      # the shader's sd > 0 side: d.y * t.x - d.x * t.y > 0
        s -= L
    return PIECES[-1][1](1), (0, 1)


def s_at_x(x, y):
    """Arc length of the line's point nearest (x, y)."""
    best, bs, s0 = 1e9, 0, 0
    for L, pt, _ in PIECES:
        for k in range(201):
            q = pt(k / 200); dd = math.hypot(q[0] - x, q[1] - y)
            if dd < best: best, bs = dd, s0 + L * k / 200
        s0 += L
    return bs


# 0 on the bottom line at x 480 (30 then still on it, as BMW's), the top mark (330 km/h, 200 mph, 8000 rpm) 30 px before the end (clear of the line's fade)
scale = [round(s_at_x(480, 636), 1), round(TOTAL - 30, 1)]

BAR = [22, 18, 188, 290]          # inner bracket gauges: offset inside the chevron edge, width, top y, bottom y
BAR2 = [110, 18]                  # outer ones: offset, width (same top and bottom)
PANEL = [[790, 30], [530, 398], [650, 640], 34]


def chevron_x(y):
    (tx, ty), (mx, my) = PANEL[0], PANEL[1]
    return tx + (mx - tx) * (y - ty) / (my - ty)


def mirror(w):
    w = dict(w)
    w['x'] = W - w['x'] - w['w']
    if w.get('align') == 'left': w['align'] = 'right'
    elif w.get('align') == 'right': w['align'] = 'left'
    return w


widgets = [{
    'id': 'lcp', 'type': 'lcp', 'class': 'content', 'z': 1, 'x': 0, 'y': 0, 'w': W, 'h': 660,
    'path': new_path, 'arcs': new_arcs, 'scale': scale,
    'dial': base['dial'], 'dialAng': base['dialAng'],
    # the lines under the speed and under the gear at one height (M Performance view: both figures stand on them)
    'line': [252, 700, 410, START_X],        # under the speed; no bottom line beyond the scale's own
    'lineR': [252, 690, 410],                # under the gear (left frame, mirrored)
    'bar': BAR, 'bar2': BAR2,
    'panel': PANEL,
    # the map window: the whole middle between the panels' chevron edges, faded at the edges (BMW's own map view)
    'hole': [500, 40, 920, 590], 'holeWhen': 'mapUp', 'holeInset': 0, 'holeChevron': 45,
}]

# the scale numbers along the line, at their marks, set inwards past the long mark (30 px) by their own half size in
# the direction of the line's normal (wide numbers sit further in on the steep sides)
def numbers(prefix, labels, toggle=None, right=False):
    out = []
    n = len(labels) - 1
    m = json.load(open(os.path.join(FONTS, 's_scale.json'))); m = m.get('metrics', m)
    for k, t in enumerate(labels):
        (x, y), (nx, ny) = at(scale[0] + k * (scale[1] - scale[0]) / n)
        hw = sum(m['glyphs'][c]['advance'] for c in t) / 2; hh = 12
        off = 36 + hw * abs(nx) + hh * abs(ny)
        cx, cy = x + nx * off, y + ny * off
        if right: cx = W - cx
        w = dict(id='%s%d' % (prefix, k), type='text', z=5, x=int(round(cx - 55)), y=int(round(cy - 13.5)), w=110, h=27,
                 text=t, font='s_scale', color='fg', align='center')
        if toggle: w['toggle'] = toggle
        out.append(w)
    return out


widgets += numbers('spd_km', [str(v) for v in range(0, 331, 30)], '!units=us')
widgets += numbers('spd_us', [str(v) for v in range(0, 201, 20)], 'units=us')
widgets += numbers('rpm', [str(v) for v in range(0, 9)], right=True)

T = lambda id, x, y, w, h, text, font, color='fg', align='left', **k: dict(id=id, type='text', z=5, x=x, y=y, w=w, h=h, text=text, font=font, color=color, align=align, **k)


def cell(font, chars):
    """An atext cell for these characters of a font: (width, height), as hud.js _atlas makes it."""
    m = json.load(open(os.path.join(FONTS, font + '.json')))
    m = m.get('metrics', m)
    return int(math.ceil(max(m['glyphs'][c]['advance'] for c in chars + ' ' if c in m['glyphs']))) + 2, m['cellHeight']


def A(id, right, y, cells, text, font, chars, align='right', z=5, **k):
    """GPU atlas text (atext), "cells" wide, its right edge at "right" (left edge for align left)."""
    cw, ch = cell(font, chars)
    w = cells * cw
    x = right - w if align == 'right' else right
    return dict(id=id, type='atext', z=z, x=int(round(x)), y=y, w=w, h=ch, cells=cells, text=text, font=font,
                chars=chars, color='fg', align=align, rate=100, **k)


DIG = '0123456789-.'

widgets += [
    # the speed under the line, the unit beside it (BMW's standard view)
    # speed and gear (checked on every 50 ms tick: rate 1) drawn by the GPU from a glyph atlas (atext): a new value is one uniform message like the needles,
    # no pixel upload, so they keep up with the needles (CPU text lagged on the car). Cells: the font's widest advance
    # + 2 (s_speed 82 x 68, s_gear 87 x 65 with just their characters), right edge / centre where the text widgets had them
    dict(id='speed', type='atext', z=5, x=626 - 3 * 82, y=338, w=3 * 82, h=68, cells=3, text='{{speed}}', font='s_speed', chars='0123456789-', color='fg', align='right', rate=1),
    T('speed_unit', 634, 374, 100, 29, '{{u:speedLc}}', 's_unit', 'dim'),   # beside the figure's foot
    # the gear over the right line, the drive mode under it
    dict(id='gear', type='atext', z=5, x=1350 - 44, y=332, w=87, h=65, cells=1, text='{{gearnum}}', font='s_gear', chars='PRND0123456789-', color='fg', align='center', rate=1, hotWhen='now'),
    T('mode', 1230, 424, 300, 29, '{{mode}}', 's_label', 'dim', 'center'),
    T('rpm_unit', 1220, 586, 220, 29, '1/min x 1000', 's_unit', 'dim', 'center'),
    T('scale_unit', 520, 586, 140, 29, '{{u:speedLc}}', 's_unit', 'dim', 'center'),
    T('badge', 810, 70, 300, 29, '{{badge}}', 's_unit', 'dim', 'center'),
]

# the bracket gauges, left to right: coolant, oil | gearbox (EGS), consumption; the value centred over the top, the name
# under the bottom (the right ones mirrored). The offsets are across the chevron edge, so along x they grow by the slope.
(tx, ty), (mx, my) = PANEL[0], PANEL[1]
ALONG = math.hypot(1, (mx - tx) / (my - ty))


def bar_x(y, off, wd):
    return chevron_x(y) - (off + wd / 2) * ALONG


def gauge(id, off, wd, value, label, unit, cells=3, flip=False):
    # the value by the GPU (atext, right-aligned up to the gauge's top), the unit beside it (still text: it never
    # changes), the name under the bottom; mirrored for the right panel
    vx, lx = bar_x(BAR[2], off, wd), bar_x(BAR[3], off, wd)
    if flip: vx, lx = W - vx, W - lx
    cw = cell('k_lab', DIG)[0]
    split = vx + (4 if unit else cells * cw / 2)
    # (conn 2: the panel readouts get a connection of their own, cluster-render draws 8 layers per connection)
    out = [A(id + '_val', split, BAR[2] - 34, cells, value, 'k_lab', DIG, conn=2),
           T(id + '_lab', round(lx - 60), BAR[3] + 4, 120, 32, label, 'k_lab', 'dim', 'center')]
    if unit: out.append(T(id + '_unit', round(split + 4), BAR[2] - 34, 40, 32, unit, 'k_lab', 'fg', 'left'))
    return out


widgets += gauge('cool', BAR2[0], BAR2[1], '{{coolant}}', 'Coolant', '{{u:temp}}') + gauge('oil', BAR[0], BAR[1], '{{oil}}', 'Oil', '{{u:temp}}')
widgets += gauge('gear', BAR[0], BAR[1], '{{gearT}}', 'EGS', '{{u:temp}}', flip=True) + gauge('cons', BAR2[0], BAR2[1], '{{cons}}', 'Mileage', None, cells=4, flip=True)
# the drive's average consumption, centred in height beside the consumption gauge (right of it)
mid = (BAR[2] + BAR[3]) / 2
ax = W - bar_x(BAR[3], BAR2[0], BAR2[1]) + BAR2[1] * ALONG / 2 + 20    # clear of the gauge's lower end, which leans out
widgets += [T('cons_avg_sym', round(ax), round(mid) - 30, 24, 32, 'Ø', 'k_lab', align='left'),
            A('cons_avg', round(ax) + 26, round(mid) - 30, 4, '{{consAvg}}', 'k_lab', DIG, align='left', conn=2),
            T('cons_avg_u', round(ax), round(mid) + 4, 150, 29, '{{u:cons}}', 's_unit', 'dim', 'left')]

# the corner dials: fuel (as M view) and the hybrid battery in the oil dial's place
for w in mv['widgets']:
    if w['id'] in ('fuel0', 'fuel1', 'fuel2', 'fuel_icon'):
        widgets.append(w)
oil = {w['id']: w for w in mv['widgets']}
for i, t in enumerate(('100', '50', '0')):
    w = dict(oil['oil%d' % i]); w['id'] = 'soc%d' % i; w['text'] = t
    widgets.append(w)
widgets.append(dict(oil['oil_icon'], id='soc_icon', icon='battery', x=1872, y=604, w=36, h=30))
widgets += [A('soc_val', 1882, 408, 3, '{{hvSoc}}', 'k_lab', DIG, conn=2), T('soc_unit', 1886, 408, 24, 32, '%', 'k_lab', align='left')]

# the bottom strip: range and clock on the left, outside temperature on the right; BMW's gear letter left uncovered
S = lambda id, x, y, w, h, text, font, color, align, row: dict(T(id, x, y, w, h, text, font, color, align), z=3, stripRow=row)
for w in mv['widgets']:
    if w['id'] in ('strip_cover_l', 'strip_cover_r', 'strip_out_u'):
        widgets.append(w)
# the clock, range and outside temperature by the GPU too (their units stay text)
widgets += [
    A('strip_out', 1756, 678, 4, '{{ambient}}', 's_val', '+-0123456789.', z=3, stripRow='r'),
    A('strip_range', 266, 678, 4, '{{range}}', 's_val', DIG, z=3, stripRow='l'),
    S('strip_range_u', 272, 676, 36, 29, '{{u:distLc}}', 's_unit', 'dim', 'left', 'l'),
    A('strip_time', 504, 678, 5, '{{time}}', 's_val', '0123456789:-', z=3, stripRow='l'),
    S('strip_ampm', 510, 676, 35, 29, '{{ampmLc}}', 's_unit', 'dim', 'left', 'l'),
]

layout = {
    'schemaVersion': 2,
    'name': 'Live Cockpit',
    'theme': 'mdash',
    'mapLive': True,
    '_about': "After the Live Cockpit Professional's standard view, generated by tools/gen_livecockpit.py (edit that and "
              "regenerate). One lcp effect layer draws the black backdrop, both scales (the right one mirrored: speed "
              "0..200 mph / 0..330 km/h, revs 0..8000), the dark panels, the orange-red needles with BMW's red glow and a "
              "warm trail, the red rev band, the fuel dial (left) and the hybrid battery dial (right), the coolant and oil (left) and "
              "gearbox oil and fuel consumption (right) bracket gauges with the drive's average consumption, the lines and BMW's check-control tray; the numbers are text widgets. "
              "The oval map window opens while the Waze map shows, without a rebuild (mapLive). BMW's gear letter in the "
              "bottom strip stays uncovered. Widget reference: shared/hud.js header.",
    'widgets': widgets,
}
out = os.path.join(LAYOUTS, 'livecockpit.json')
with open(out, 'w') as f:
    json.dump(layout, f, indent=2, ensure_ascii=False)
    f.write('\n')
print('wrote', out, len(widgets), 'widgets, scale', scale)
