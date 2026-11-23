#!/usr/bin/env python3
"""Write apps/cluster_themes/hud/layouts/livecockpit.json, the Live Cockpit theme (edit this, not the JSON).

    python3 tools/gen_livecockpit.py

After the Live Cockpit Professional's standard view (G20 / G30 / G05 ...): the speed scale on the left, the rev scale
on the right, the digital speed under the line on the left, the gear over the line on the right, fuel in the lower left
corner. Added for this theme: the hybrid battery in the lower right corner (where BMW's PHEVs show it), and two bracket
gauges in the panels like BMW's sport displays: oil on the left, gearbox oil on the right. The Waze map opens in the
middle as an oval (mapLive). The scale outline, its arc lengths and the number positions come from mview.json (the
same Live Cockpit geometry); the line starts at the bottom left of BMW's check-control tray instead of stepping down.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUTS = os.path.join(HERE, '..', 'apps', 'cluster_themes', 'hud', 'layouts')
W = 1920
mv = json.load(open(os.path.join(LAYOUTS, 'mview.json')))
base = mv['widgets'][0]

# the scale's line: mview's (points where straight pieces and arcs meet, "arcs" [cx, cy, r, sweep] per piece) from its
# corner at the bottom (750, 636) on, started a little further in, with the arc lengths of 0 and the top mark moved by
# what was cut off the front
path, arcs = base['path'], base['arcs']
cut = next(i for i, p in enumerate(path) if abs(p[0] - 750) < 0.5 and abs(p[1] - 636) < 0.5)


def piece(i):
    g = arcs[i]
    return abs(g[2] * g[3]) if g[2] else math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])


START_X = 735
new_path = [[START_X, 636]] + path[cut + 1:]
new_arcs = [[0, 0, 0, 0]] + arcs[cut + 1:]
old_to = sum(piece(i) for i in range(cut + 1))               # up to point cut + 1
new_to = math.hypot(path[cut + 1][0] - START_X, path[cut + 1][1] - 636)
shift = old_to - new_to
scale = [round(base['scale'][0] - shift, 1), round(base['scale'][1] - shift, 1)]

BAR = [22, 18, 165, 290]          # inner bracket gauges: offset inside the chevron edge, width, top y, bottom y
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
    'line': [252, 700, 336, START_X],        # over the speed; the bottom line runs on to x
    'lineR': [252, 690, 410],                # under the gear (left frame, mirrored)
    'tray': [770, 1150, 594, 34],            # BMW's check-control frame
    'bar': BAR, 'bar2': BAR2,
    'panel': PANEL,
    'hole': [700, 78, 520, 506], 'holeWhen': 'mapUp', 'holeInset': 0, 'holeOval': 70,
}]

# the scale numbers, as in M view
keep = lambda w: w['id'].startswith(('spd_us', 'spd_km', 'rpm')) and w['id'] != 'rpm_unit'
widgets += [w for w in mv['widgets'] if w.get('type') == 'text' and keep(w)]

T = lambda id, x, y, w, h, text, font, color='fg', align='left', **k: dict(id=id, type='text', z=5, x=x, y=y, w=w, h=h, text=text, font=font, color=color, align=align, **k)
FONTS = os.path.join(HERE, '..', 'apps', 'cluster_themes', 'hud', 'fonts')


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
    # speed and gear drawn by the GPU from a glyph atlas (atext): a new value is one uniform message like the needles,
    # no pixel upload, so they keep up with the needles (CPU text lagged on the car). Cells: the font's widest advance
    # + 2 (s_speed 82 x 68, s_gear 87 x 65 with just their characters), right edge / centre where the text widgets had them
    dict(id='speed', type='atext', z=5, x=626 - 3 * 82, y=350, w=3 * 82, h=68, cells=3, text='{{speed}}', font='s_speed', chars='0123456789-', color='fg', align='right', rate=50),
    T('speed_unit', 634, 352, 100, 29, '{{u:speedLc}}', 's_unit', 'dim'),
    # the gear over the right line, the drive mode under it
    dict(id='gear', type='atext', z=5, x=1350 - 44, y=332, w=87, h=65, cells=1, text='{{gearnum}}', font='s_gear', chars='PRND0123456789-', color='fg', align='center', rate=50, hotWhen='now'),
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
