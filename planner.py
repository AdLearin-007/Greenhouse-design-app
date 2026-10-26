"""
Greenhouse System Planner - core logic (pure Python, no third-party packages).

Builds a 3D model of a greenhouse as plain data (triangle meshes, lines and
points grouped by component), plus the engineering numbers for the layout.
app.py turns this data into an interactive website with Streamlit + Plotly.

Coordinate system (meters):
    x = across the span (width), centered on 0
    y = along the length, door at +L/2, equipment zone at -L/2
    z = up, floor at 0
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Options shown in the UI
# --------------------------------------------------------------------------
STYLES = {
    "gable": "Gable",
    "hoop": "Quonset (hoop)",
    "gothic": "Gothic arch",
    "venlo": "Venlo (multi-ridge)",
    "lean": "Lean-to",
}
SYSTEMS = {
    "trad": "Traditional (soil beds)",
    "hydro": "Hydroponic",
    "aqua": "Aquaponic",
}
HYDRO_METHODS = {
    "nft": "NFT channels",
    "dwc": "Deep water rafts",
    "tower": "Vertical towers",
}
GLAZING = {
    # name, color, opacity in the model, light transmission %, notes
    "glass": ("Tempered glass", "#CFE6EC", 0.16, 90,
              "Highest clarity and longest life (25+ years), but heavy, costly "
              "and the poorest insulator (single pane)."),
    "poly": ("Twin-wall polycarbonate", "#EDF2F1", 0.40, 80,
             "Two walls with an air gap insulate about twice as well as glass "
             "and diffuse light deeper into the canopy. 10-15 year life."),
    "film": ("Poly film", "#F3F5EF", 0.28, 87,
             "Cheapest cover. 6-mil UV-treated film lasts about 4 years; a "
             "double layer with an inflation fan insulates better."),
}

# key: (display name, description, color)
INFO = {
    "foundation": ("Foundation & floor", "Concrete perimeter curb anchors the frame. Gravel floor drains spills; concrete walks keep aisles and the equipment pad clean.", "#B8B4AC"),
    "frame": ("Structural frame", "Galvanized steel ribs about every 1.5 m with purlins down the full length. Rib spacing sets the snow and wind load rating.", "#9AA3A8"),
    "door": ("Entry door", "1.2 m opening sized for a garden cart. The aisle in front stays clear for loading.", "#3A4448"),
    "glazing": ("Glazing", "", "#CFE6EC"),
    "backwall": ("Insulated back wall", "Solid masonry wall faces north (Northern Hemisphere). It stores daytime heat as thermal mass and releases it at night.", "#8C5A44"),
    "shade": ("Shade cloth (40%)", "Cuts summer heat load and excess light. Pull it over the roof when midday light is more than the crop can use.", "#2B3A2F"),
    "fans": ("Exhaust fans", "Sized for about one full air change per minute in summer. They pull fresh air in through the louvers at the door end.", "#23282A"),
    "louvers": ("Intake louvers", "Motorized shutters open when the fans run so air sweeps the full length of the house.", "#7D878B"),
    "lights": ("LED grow lights", "Top up daylight to reach the daily light integral. Leafy greens target about 12-17 mol/m2/day; fruiting crops 20-30.", "#E45BD0"),
    "beds": ("Raised soil beds", "1.2 m wide so you can reach the middle from the aisle, 45 cm deep. Crops rotate bed to bed each season.", "#9A6B43"),
    "soil": ("Bed soil", "Compost-rich mix about 40 cm deep.", "#3E2B1E"),
    "trellis": ("Trellis line", "Overhead wire for vining tomatoes and cucumbers to climb, keeping fruit off the soil.", "#6B5B4B"),
    "drip": ("Drip lines", "Two lines per bed with emitters about 30 cm apart put water at the roots and cut evaporation and leaf disease.", "#1E1E1E"),
    "tank": ("Water storage tank", "Rainwater or municipal fill. A screen filter and timer sit between it and the drip header.", "#3D5A3A"),
    "bench": ("Potting bench", "Work surface for transplanting, seeding and mixing soil.", "#9A6B43"),
    "compost": ("Compost bins", "Turns crop waste back into bed amendments. Two bins: one filling, one curing.", "#7A5534"),
    "reservoir": ("Nutrient reservoir", "Holds the nutrient solution. Check EC (strength) and pH daily; leafy greens like pH 5.8-6.2.", "#D9DDD8"),
    "controller": ("Dosing controller", "Reads EC and pH probes and injects nutrient A/B and pH adjuster automatically.", "#4C5C66"),
    "nursery": ("Seedling nursery rack", "Germinate in plugs for 2-3 weeks before transplanting into the system.", "#8FA6A0"),
    "nft": ("NFT channels", "A thin film of solution runs down each channel at about 1% slope. Roots sit in the film and stay exposed to air.", "#F2F2EE"),
    "gutter": ("Return gutter", "Catches solution leaving every channel or trough and sends it back toward the tank.", "#E6E6E0"),
    "plumbing": ("Supply & return plumbing", "Supply header (pressurized, from the pump) and gravity return lines that close the loop.", "#2B6FA0"),
    "dwc": ("Deep water culture troughs", "Foam rafts float on 25-30 cm of aerated solution. The water mass buffers temperature swings.", "#2A3236"),
    "rafts": ("Foam rafts", "Floating boards with net-pot holes about 20 cm apart.", "#EDEDE6"),
    "water": ("Water surface", "Open water in tanks and troughs.", "#2E7FA8"),
    "air": ("Air pump", "Feeds air stones in every trough to keep dissolved oxygen above 5 mg/L so roots do not rot.", "#23282A"),
    "towers": ("Vertical grow towers", "Solution drips in at the top and trickles down past each plant. Several times more plants per square meter of floor.", "#F2F2EE"),
    "pump": ("Pump", "Moves water around the loop. Size it to cycle the tank volume about once an hour.", "#23282A"),
    "fishtank": ("Fish tank", "Tilapia or another warm-water fish. A beginner system stocks around 20 kg of fish per m3 of water.", "#27505E"),
    "fish": ("Fish", "Each orange dot is a fish swimming in the tank.", "#E07A2E"),
    "clarifier": ("Clarifier (swirl filter)", "Slows the water so solid fish waste settles out in the cone before it can clog the beds.", "#D9DDD8"),
    "biofilter": ("Biofilter", "Nitrifying bacteria on high-surface media turn toxic ammonia into nitrite, then nitrate that plants can use.", "#3C6E6A"),
    "sump": ("Sump tank", "Lowest point in the loop. Everything drains here, so the fish tank level never drops.", "#2A3236"),
    "mediabed": ("Media grow bed", "Expanded clay filled bed that also filters solids. A bell siphon floods and drains it on a cycle.", "#8A7F6E"),
    "raft": ("Raft beds", "Deep water culture beds where plants float on foam rafts and take nitrate straight from the fish water.", "#2A3236"),
    "plants": ("Crops", "Plant sites at typical spacing for this system. The plant-site count comes from these.", "#6DB34E"),
    "flow": ("Water flow", "Arrows show which way water moves through the loop.", "#3BC4FF"),
}

WATER_LOOPS = {
    "trad": [("Storage tank", "Rainwater or municipal fill"),
             ("Filter & timer", "Screen filter stops emitter clogs; timer sets run length"),
             ("Supply header", "Runs across the back of every bed"),
             ("Drip lines", "Two per bed, emitters every 30 cm"),
             ("Root zone", "Plants take up water; extra drains through the soil")],
    "nft": [("Nutrient reservoir", "Mixed to EC 1.2-2.0, pH 5.8-6.2"),
            ("Pump", "Pushes solution up to the supply header"),
            ("Channel inlets", "Feeds the high end of every channel"),
            ("NFT channels", "Thin film runs down at about 1% slope"),
            ("Return gutter", "Collects outflow across the door end"),
            ("Return line", "Gravity flow back to the reservoir")],
    "dwc": [("Nutrient reservoir", "Mixed to EC 1.2-2.0, pH 5.8-6.2"),
            ("Pump", "Tops up and circulates the troughs"),
            ("Troughs", "Rafts float; air stones keep oxygen up"),
            ("Standpipe drain", "Sets the water depth at the far end"),
            ("Return line", "Gravity flow back to the reservoir")],
    "tower": [("Nutrient reservoir", "Mixed to EC 1.2-2.0, pH 5.8-6.2"),
              ("Pump", "Lifts solution to the overhead feed line"),
              ("Tower tops", "Drip emitters at the top of each tower"),
              ("Down the tower", "Solution trickles past every plant"),
              ("Base gutter", "Catches drainage under each row"),
              ("Return line", "Gravity flow back to the reservoir")],
    "aqua": [("Fish tank", "Fish waste releases ammonia into the water"),
             ("Clarifier", "Solid waste settles out in the cone"),
             ("Biofilter", "Bacteria convert ammonia to nitrite, then nitrate"),
             ("Grow beds", "Plants take up nitrate and clean the water"),
             ("Sump", "All beds drain to the lowest tank"),
             ("Return pump", "Lifts clean water back to the fish tank")],
}

FAN_CAPACITY_M3_PER_MIN = 283   # one 36" exhaust fan, about 10,000 cfm
FEED_G_PER_M2_DAY = 60          # aquaponics feed rate ratio, leafy greens
STOCKING_KG_PER_M3 = 20         # beginner fish stocking density
FEED_PCT_BODY_WEIGHT = 0.015    # fish eat ~1.5% of body weight per day
SHADE_FACTOR = 0.60             # 40% shade cloth passes 60% of light


@dataclass
class Settings:
    style: str = "gothic"
    system: str = "aqua"
    hydro: str = "nft"
    width: float = 9.0
    length: float = 18.0
    glazing: str = "poly"
    lights: bool = True
    fans: bool = True
    shade: bool = False
    flow: bool = True
    hide_glazing: bool = False

    @property
    def method(self) -> str:
        """The specific growing method: trad, nft, dwc, tower or aqua."""
        return self.hydro if self.system == "hydro" else self.system


# --------------------------------------------------------------------------
# Cross-section profiles: list of (x, z) points from left base to right base
# --------------------------------------------------------------------------
def profile(style: str, w: float) -> list[tuple[float, float]]:
    h = w / 2
    if style == "gable":
        eave = 2.4
        ridge = eave + min(w * 0.28, 3)
        return [(-h, 0), (-h, eave), (0, ridge), (h, eave), (h, 0)]
    if style == "hoop":
        H = max(2.5, min(h, 3.8))
        return [(math.cos(math.pi - i * math.pi / 18) * h,
                 math.sin(math.pi - i * math.pi / 18) * H) for i in range(19)]
    if style == "gothic":
        # Two circular arcs that meet in a point, on 1.5 m side walls
        wall, R = 1.5, w * 0.62
        xc = -h + R
        a_end = math.acos(-xc / R)
        k = min(1.0, (1.2 + w * 0.36) / (R * math.sin(a_end)))
        left = [(-h, 0.0)]
        for i in range(10):
            a = math.pi - (math.pi - a_end) * i / 9
            left.append((xc + R * math.cos(a), wall + R * math.sin(a) * k))
        left[-1] = (0.0, left[-1][1])
        right = [(-x, z) for x, z in reversed(left[:-1])]
        return left + right
    if style == "venlo":
        n = max(1, round(w / 3.2))
        bay = w / n
        eave, rise = 3.0, min(1.0, bay * 0.3)
        pts = [(-h, 0), (-h, eave)]
        for i in range(n):
            x0 = -h + i * bay
            pts += [(x0 + bay / 2, eave + rise), (x0 + bay, eave)]
        pts.append((h, 0))
        return pts
    # lean-to: tall solid back wall on the left, glazed slope to the right
    return [(-h, 0), (-h, 3.4), (h, 2.1), (h, 0)]


def roof_at(P, x: float) -> float:
    """Height of the roof surface above point x on the floor."""
    best = 0.0
    for (x1, z1), (x2, z2) in zip(P, P[1:]):
        if abs(x2 - x1) < 1e-4:
            continue
        if min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6:
            best = max(best, z1 + (x - x1) / (x2 - x1) * (z2 - z1))
    return best


def polygon_area(P) -> float:
    a = 0.0
    for i in range(len(P)):
        x1, z1 = P[i]
        x2, z2 = P[(i + 1) % len(P)]
        a += x1 * z2 - x2 * z1
    return abs(a) / 2


def fit_row(widths, gap, span):
    """Place items side by side, centered, shrinking them if they don't fit."""
    total = sum(widths) + gap * (len(widths) - 1)
    s = min(1.0, span / total)
    x = -total * s / 2
    centers = []
    for wd in widths:
        centers.append(x + wd * s / 2)
        x += (wd + gap) * s
    return s, centers


def rows_for(span, bed_w, aisle):
    n = max(1, int((span + aisle) // (bed_w + aisle)))
    total = n * bed_w + (n - 1) * aisle
    return [-total / 2 + bed_w / 2 + i * (bed_w + aisle) for i in range(n)]


# --------------------------------------------------------------------------
# Model: geometry grouped by component key
# --------------------------------------------------------------------------
@dataclass
class Mesh:
    x: list = field(default_factory=list)
    y: list = field(default_factory=list)
    z: list = field(default_factory=list)
    i: list = field(default_factory=list)
    j: list = field(default_factory=list)
    k: list = field(default_factory=list)


@dataclass
class Model:
    meshes: dict = field(default_factory=dict)   # key -> Mesh
    lines: dict = field(default_factory=dict)    # key -> ([x],[y],[z], width)
    points: dict = field(default_factory=dict)   # key -> ([x],[y],[z],[color],[size])
    flow_paths: list = field(default_factory=list)  # list of [(x,y,z), ...]
    stats: dict = field(default_factory=dict)
    glazing_color: str = "#EDF2F1"
    glazing_opacity: float = 0.4

    # ---- primitives ----
    def tris(self, key, verts, faces):
        m = self.meshes.setdefault(key, Mesh())
        n = len(m.x)
        for vx, vy, vz in verts:
            m.x.append(vx); m.y.append(vy); m.z.append(vz)
        for a, b, c in faces:
            m.i.append(a + n); m.j.append(b + n); m.k.append(c + n)

    def box(self, key, cx, cy, z0, w, d, h):
        """Box centered on (cx, cy), sitting on z0. w along x, d along y, h up."""
        x0, x1, y0, y1, z1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, z0 + h
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1),
             (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)]
        self.tris(key, v, f)

    def cylinder(self, key, cx, cy, z0, r, h, seg=24, r_top=None, caps=True):
        rt = r if r_top is None else r_top
        v, f = [], []
        for s in range(seg):
            a = 2 * math.pi * s / seg
            v.append((cx + r * math.cos(a), cy + r * math.sin(a), z0))
            v.append((cx + rt * math.cos(a), cy + rt * math.sin(a), z0 + h))
        for s in range(seg):
            b0, t0 = 2 * s, 2 * s + 1
            b1, t1 = 2 * ((s + 1) % seg), 2 * ((s + 1) % seg) + 1
            f += [(b0, b1, t1), (b0, t1, t0)]
        if caps:
            cb, ct = len(v), len(v) + 1
            v += [(cx, cy, z0), (cx, cy, z0 + h)]
            for s in range(seg):
                b0, b1 = 2 * s, 2 * ((s + 1) % seg)
                f += [(cb, b1, b0), (ct, b0 + 1, b1 + 1)]
        self.tris(key, v, f)

    def quad(self, key, a, b, c, d):
        self.tris(key, [a, b, c, d], [(0, 1, 2), (0, 2, 3)])

    def line(self, key, *pts, width=3):
        xs, ys, zs, _ = self.lines.setdefault(key, ([], [], [], width))
        for p in pts:
            xs.append(p[0]); ys.append(p[1]); zs.append(p[2])
        xs.append(None); ys.append(None); zs.append(None)

    def point(self, key, x, y, z, color, size):
        xs, ys, zs, cs, ss = self.points.setdefault(key, ([], [], [], [], []))
        xs.append(x); ys.append(y); zs.append(z); cs.append(color); ss.append(size)

    def pipe(self, pts, skip=()):
        """A plumbing run. Segments listed in skip are water moving through a
        bed or channel, so no pipe is drawn there, but water still flows."""
        for n, (a, b) in enumerate(zip(pts, pts[1:])):
            if n not in skip:
                self.line("plumbing", a, b, width=5)
        self.flow_paths.append(pts)


# --------------------------------------------------------------------------
# Build the whole greenhouse
# --------------------------------------------------------------------------
def build(s: Settings, seed: int = 7) -> Model:
    rnd = random.Random(seed)
    m = Model()
    w, L = s.width, s.length
    h = w / 2
    P = profile(s.style, w)
    roof = lambda x: roof_at(P, x)  # noqa: E731
    method = s.method

    # Usable half-width: where the roof is high enough to work under
    need = 2.4 if method == "tower" else 1.75
    uh, x = 0.0, 0.0
    while x <= h:
        if roof(x) >= need and roof(-x) >= need:
            uh = x
        else:
            break
        x += 0.05
    uh = max(0.9, min(uh, h - 0.3))

    r_tank = min(1.25, max(0.7, uh * 0.3)) if method == "aqua" else 0
    eq_depth = (max(2.8, 2 * r_tank + 0.9) if method == "aqua"
                else 2.2 if method == "trad" else 2.5)
    yA, yB = -L / 2 + eq_depth, L / 2 - 1.1          # growing zone
    run = yB - yA
    yC = (yA + yB) / 2
    yE = -L / 2 + eq_depth / 2                       # equipment zone center
    bed_w, aisle = {"trad": (1.2, .8), "nft": (1.2, .8), "dwc": (1.2, .7),
                    "tower": (.7, .9), "aqua": (1.2, .8)}[method]
    xs = rows_for(2 * uh, bed_w, aisle)
    xr = min(uh, h - 0.35)                           # return line along the wall
    st = {"rows": len(xs), "grow_area": len(xs) * bed_w * run, "water_l": 0.0}

    def leaf():
        if rnd.random() < 0.1:
            return "#9E3F4A"  # red-leaf lettuce
        return rnd.choice(["#8BC34A", "#7CB342", "#9CCC65", "#A5D46A", "#6FAE45"])

    # ---------------- foundation ----------------
    m.box("foundation", 0, 0, 0, w + .2, L + .2, .04)
    m.box("foundation", -h, 0, 0, .2, L + .2, .28)
    m.box("foundation", h, 0, 0, .2, L + .2, .28)
    m.box("foundation", 0, -L / 2, 0, w + .2, .2, .28)
    m.box("foundation", 0, L / 2, 0, w + .2, .2, .28)
    m.box("foundation", 0, (yB + L / 2) / 2, .04, w - .2, L / 2 - yB, .02)
    m.box("foundation", 0, yE, .04, 2 * uh + .3, eq_depth - .1, .02)
    for a, b in zip(xs, xs[1:]):
        m.box("foundation", (a + b) / 2, yC, .04, b - a - bed_w - .1, run, .02)

    # ---------------- frame ----------------
    n_ribs = max(2, round(L / 1.5))
    for r in range(n_ribs + 1):
        y = -L / 2 + r * L / n_ribs
        m.line("frame", *[(px, y, pz) for px, pz in P], width=4)
    for px, pz in P:
        if pz > 0.01:
            m.line("frame", (px, -L / 2, pz), (px, L / 2, pz), width=3)
    n_studs = max(2, round(w / 1.6))
    for y in (-L / 2, L / 2):
        for j in range(1, n_studs):
            sx = -h + j * w / n_studs
            if y > 0 and abs(sx) < 0.8:
                continue  # leave the doorway open
            m.line("frame", (sx, y, 0), (sx, y, roof(sx)), width=3)
    m.line("door", (-.6, L / 2, 0), (-.6, L / 2, 2.15), (.6, L / 2, 2.15), (.6, L / 2, 0), width=7)
    m.box("door", .32, L / 2 + .05, 0, .62, .03, 2.05)

    # ---------------- glazing ----------------
    g_name, g_color, g_opacity, g_trans, _ = GLAZING[s.glazing]
    m.glazing_color, m.glazing_opacity = g_color, g_opacity
    glaze_area = 0.0
    for n, ((x1, z1), (x2, z2)) in enumerate(zip(P, P[1:])):
        if s.style == "lean" and n == 0:
            continue  # solid back wall instead of glass
        m.quad("glazing", (x1, -L / 2, z1), (x2, -L / 2, z2), (x2, L / 2, z2), (x1, L / 2, z1))
        glaze_area += math.hypot(x2 - x1, z2 - z1) * L
    for y in (-L / 2, L / 2):  # end walls, filled as vertical strips
        for (x1, z1), (x2, z2) in zip(P, P[1:]):
            if abs(x2 - x1) > 1e-4:
                m.quad("glazing", (x1, y, 0), (x2, y, 0), (x2, y, z2), (x1, y, z1))
    area = polygon_area(P)
    glaze_area += 2 * area
    if s.style == "lean":
        m.box("backwall", -h - .15, 0, 0, .3, L + .2, P[1][1])
    if s.shade:
        for (x1, z1), (x2, z2) in zip(P, P[1:]):
            if abs(x2 - x1) > 0.05:
                m.quad("shade", (x1, -L / 2, z1 + .08), (x2, -L / 2, z2 + .08),
                       (x2, L / 2, z2 + .08), (x1, L / 2, z1 + .08))

    # ---------------- ventilation ----------------
    volume = area * L
    fans_needed = max(1, math.ceil(volume / FAN_CAPACITY_M3_PER_MIN))
    fans_placed = 0
    if s.fans:
        span, x = 0.0, 0.0
        while x < h:
            if roof(x) >= 2.25 and roof(-x) >= 2.25:
                span = x
            else:
                break
            x += 0.05
        fit = max(1, int((2 * min(span, h - .2) + .3) // 1.3))
        fans_placed = min(fans_needed, fit)
        for fx in fit_row([1.0] * fans_placed, .3, 2 * span)[1]:
            m.box("fans", fx, -L / 2 - .17, .75, 1, .3, 1)
            for a in range(4):  # blades
                ang = a * math.pi / 2 + math.pi / 4
                m.line("fans", (fx, -L / 2 - .34, 1.25),
                       (fx + .42 * math.cos(ang), -L / 2 - .34, 1.25 + .42 * math.sin(ang)), width=6)
        lx = max(1.3, uh * .55)
        if roof(lx) > 2:
            for sx in (-lx, lx):
                m.box("louvers", sx, L / 2 + .06, .8, .9, .08, .9)

    # ---------------- grow lights ----------------
    def light_z(x):
        return min(2.6, roof(x - bed_w / 2) - .3, roof(x + bed_w / 2) - .3)

    if s.lights:
        for x in xs:
            for o in (-bed_w * .25, bed_w * .25):
                m.box("lights", x + o, yC, light_z(x), .08, run - .2, .03)

    # ---------------- growing systems ----------------
    if method == "trad":
        sc, (tx, bx, cx) = fit_row([1.2, 2.0, 1.9], .4, 2 * uh - .2)
        m.cylinder("tank", tx, yE, 0, .55 * sc, 1.5)
        st["water_l"] = math.pi * (.55 * sc) ** 2 * 1.4 * 1000
        m.box("bench", bx, yE, .88, 2 * sc, .7, .05)
        for a in (-1, 1):
            for b in (-1, 1):
                m.box("bench", bx + a * (sc - .06), yE + b * .3, 0, .05, .05, .88)
        for o in (-.48, .48):
            m.box("compost", cx + o * sc, yE, 0, .9 * sc, .9, .85)
        bed_h = 0.45
        crops = ["lettuce", "tomato", "pepper"]
        for n, x in enumerate(xs):
            m.box("beds", x, yC, 0, bed_w, run, bed_h)
            m.box("soil", x, yC, bed_h, bed_w - .1, run - .1, .01)
            crop = crops[n % 3]
            if crop == "lettuce":
                y = yA + .2
                while y < yB - .1:
                    for c in range(4):
                        m.point("plants", x - .45 + c * .3, y, bed_h + .07, leaf(), 5)
                    y += .3
            else:
                tall = crop == "tomato"
                sp = .5 if tall else .42
                y = yA + .25
                while y < yB - .1:
                    for o in (-.28, .28):
                        m.point("plants", x + o, y, bed_h + (.55 if tall else .25),
                                "#3A7F3A" if tall else "#4C9440", 9 if tall else 7)
                        for _ in range(4 if tall else 2):
                            m.point("plants", x + o + rnd.uniform(-.12, .12), y + rnd.uniform(-.12, .12),
                                    bed_h + (rnd.uniform(.3, 1.0) if tall else rnd.uniform(.15, .35)),
                                    "#D8342A" if tall else "#F08A1C", 3)
                    y += sp
                if tall:
                    for o in (-.28, .28):
                        m.line("trellis", (x + o, yA + .1, bed_h), (x + o, yA + .1, 2.0),
                               (x + o, yB - .1, 2.0), (x + o, yB - .1, bed_h), width=3)
            for o in (-.25, .25):
                m.line("drip", (x + o * bed_w, yA + .05, bed_h + .03), (x + o * bed_w, yB - .05, bed_h + .03), width=2)
            xd = x - .25 * bed_w
            m.pipe([(tx, yE, .12), (tx, yA - .3, .12), (xd, yA - .3, .12), (xd, yA - .3, bed_h + .03),
                    (xd, yA + .05, bed_h + .03), (xd, yB - .05, bed_h + .03)], skip=(4,))
        st["soil_m3"] = st["grow_area"] * .4

    if method in ("nft", "dwc", "tower"):
        sc, (rx, cx, nx) = fit_row([1.4, .7, 1.7], .4, 2 * uh - .2)
        m.box("reservoir", rx, yE, 0, 1.3 * sc, .9, .8)
        m.box("water", rx, yE, .72, 1.3 * sc - .06, .84, .01)
        m.box("pump", rx + .5 * sc, yE + .3, .8, .25, .2, .2)
        st["water_l"] = 1.3 * sc * .9 * .65 * 1000
        m.box("controller", cx, yE, .62, .55 * sc, .3, .75)
        for z in (.3, .8, 1.3):
            m.box("nursery", nx, yE, z, 1.6 * sc, .55, .04)
            for t in range(4):
                m.box("nursery", nx - .6 * sc + t * .4 * sc, yE, z + .04, .35 * sc, .5, .05)
        x_min, x_max = min(xs) - bed_w / 2, max(xs) + bed_w / 2

        if method == "nft":
            z_front, z_back = .9, .9 + run * .01     # 1% slope toward the door
            z_hdr = z_back + .2
            m.box("gutter", (x_min + x_max) / 2, yB + .15, z_front - .18, x_max - x_min + .2, .18, .12)
            for x in xs:
                y = yA
                step = max(1.5, run / math.ceil(run / 2))
                while y <= yB + .01:
                    zz = z_front + (yB - y) * .01 - .06
                    m.line("nft", (x - .55, y, 0), (x - .55, y, zz), (x + .55, y, zz), (x + .55, y, 0), width=3)
                    y += step
                for c in range(6):
                    cxp = x - .5 + c * .2
                    # channel as a sloped box: two quads (top and side) are enough to read
                    m.tris("nft", [(cxp - .05, yA, z_back), (cxp + .05, yA, z_back),
                                   (cxp + .05, yB, z_front), (cxp - .05, yB, z_front),
                                   (cxp - .05, yA, z_back - .06), (cxp + .05, yA, z_back - .06),
                                   (cxp + .05, yB, z_front - .06), (cxp - .05, yB, z_front - .06)],
                           [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 7), (0, 7, 3),
                            (1, 2, 6), (1, 6, 5)])
                    y = yA + .1
                    while y < yB:
                        m.point("plants", cxp, y, z_front + (yB - y) * .01 + .07, leaf(), 4)
                        y += .2
                st["water_l"] += 6 * run * .3
                m.pipe([(rx, yE, .85), (rx, yE, z_hdr), (rx, yA - .2, z_hdr), (x - .3, yA - .2, z_hdr),
                        (x - .3, yA + .02, z_back + .04), (x - .3, yB, z_front + .04), (x - .3, yB + .15, z_front - .1),
                        (xr, yB + .15, z_front - .1), (xr, yB + .15, .08), (xr, yE + .6, .08),
                        (rx, yE + .6, .08), (rx, yE + .45, .5)], skip=(5, 6))

        if method == "dwc":
            m.box("gutter", (x_min + x_max) / 2, yB + .2, .02, x_max - x_min + .2, .2, .08)
            m.box("air", rx - .45 * sc, yE + .3, .8, .3, .22, .18)
            for x in xs:
                m.box("dwc", x, yC, 0, bed_w, run, .34)
                m.box("water", x, yC, .3, bed_w - .08, run - .08, .01)
                n_raft = max(1, round(run / 1.2))
                rl = run / n_raft
                for r in range(n_raft):
                    m.box("rafts", x, yA + rl * (r + .5), .31, bed_w - .12, rl - .03, .04)
                y = yA + .12
                while y < yB - .05:
                    for c in range(5):
                        m.point("plants", x - .4 + c * .2, y, .4, leaf(), 4)
                    y += .2
                m.line("air", (rx - .45 * sc, yE + .3, .9), (x + .5, yA + .05, .36), width=1)
                st["water_l"] += (bed_w - .08) * run * .27 * 1000
                m.pipe([(rx, yE, .85), (rx, yE, .55), (rx, yA - .25, .55), (x, yA - .25, .55),
                        (x, yA + .08, .3), (x, yB - .08, .3), (x, yB + .2, .06), (xr, yB + .2, .06),
                        (xr, yE + .6, .06), (rx, yE + .6, .06), (rx, yE + .45, .5)], skip=(4, 5))

        if method == "tower":
            m.box("gutter", (x_min + x_max) / 2, yB + .2, .02, x_max - x_min + .2, .2, .08)
            for x in xs:
                top = light_z(x) if s.lights else roof(x) - .3
                th = min(1.7, top - .45)
                m.box("towers", x, yC, 0, .55, run, .15)
                y, k = yA + .3, 0
                while y < yB - .1:
                    tx2 = x + (.15 if k % 2 else -.15)
                    m.cylinder("towers", tx2, y, .15, .08, th, seg=10, caps=False)
                    zz = .35
                    while zz < .15 + th - .1:
                        for a in range(4):
                            ang = a * math.pi / 2 + zz * 2.3
                            m.point("plants", tx2 + math.cos(ang) * .12, y + math.sin(ang) * .12, zz, leaf(), 3)
                        zz += .22
                    y += .55
                    k += 1
                z_feed = .15 + th + .12
                m.line("plumbing", (x, yA + .2, z_feed), (x, yB - .1, z_feed), width=5)
                st["water_l"] += .5 * run * .04 * 1000
                m.pipe([(rx, yE, .85), (rx, yE, z_feed), (rx, yA - .2, z_feed), (x, yA - .2, z_feed),
                        (x, yB - .1, z_feed), (x, yB - .1, .12), (x, yB + .2, .06), (xr, yB + .2, .06),
                        (xr, yE + .6, .06), (rx, yE + .6, .06), (rx, yE + .45, .5)], skip=(4, 5))

    if method == "aqua":
        sc, (fx, cx, bx, sx) = fit_row([2 * r_tank + .1, 1, .9, 1.2], .35, 2 * uh - .1)
        r = r_tank * sc
        m.cylinder("fishtank", fx, yE, 0, r, 1.2, seg=36, caps=False)
        m.cylinder("fishtank", fx, yE, 0, r, .04, seg=36)
        m.cylinder("water", fx, yE, 1.06, r - .02, .02, seg=36)
        tank_l = math.pi * r * r * 1.05 * 1000
        st["tank_l"] = tank_l
        st["water_l"] = tank_l
        n_fish = max(6, min(40, round(tank_l * STOCKING_KG_PER_M3 / 1000 / .5)))
        for _ in range(n_fish):
            rr, a = rnd.uniform(.2, r - .2), rnd.uniform(0, 2 * math.pi)
            m.point("fish", fx + rr * math.cos(a), yE + rr * math.sin(a), rnd.uniform(.4, 1.0), "#E07A2E", 4)
        cr = .42 * sc
        m.cylinder("clarifier", cx, yE, .65, cr, .85)
        m.cylinder("clarifier", cx, yE, .2, .06, .45, r_top=cr)
        for t in range(3):
            a = t * 2.094
            m.line("clarifier", (cx + math.cos(a) * cr, yE + math.sin(a) * cr, 0),
                   (cx + math.cos(a) * cr, yE + math.sin(a) * cr, .65), width=3)
        br = .38 * sc
        m.cylinder("biofilter", bx, yE, 0, br, 1.0)
        m.box("sump", sx, yE, 0, 1.1 * sc, .9, .6)
        m.box("water", sx, yE, .52, 1.1 * sc - .06, .84, .01)
        m.box("pump", sx + .3 * sc, yE, .6, .22, .2, .2)
        st["water_l"] += (math.pi * cr * cr * 1.1 + math.pi * br * br * .9 + 1.1 * sc * .9 * .5) * 1000
        bed_area = 0.0
        head = [(fx, yE, 1.0), (cx, yE, 1.0), (cx, yE, .85), (bx, yE, .85)]
        tail = [(xr, yE + .75, .06), (sx, yE + .75, .06), (sx, yE + .2, .55),
                (sx, yE, 1.35), (fx, yE, 1.35), (fx, yE, 1.05)]
        for n, x in enumerate(xs):
            if len(xs) >= 2 and n == 0:     # first row: media bed
                y = yA + .1
                step = max(1.5, run / math.ceil(run / 2))
                while y < yB:
                    for o in (-.55, .55):
                        m.line("mediabed", (x + o, y, 0), (x + o, y, .55), width=3)
                    y += step
                m.box("mediabed", x, yC, .55, bed_w, run, .32)
                y = yA + .2
                while y < yB - .1:
                    for o in (-.3, .3):
                        basil = rnd.random() < .5
                        m.point("plants", x + o, y, 1.0 + (.05 if basil else .2),
                                "#3E8E41" if basil else "#3A7F3A", 6 if basil else 9)
                        if not basil:
                            for _ in range(3):
                                m.point("plants", x + o + rnd.uniform(-.1, .1), y + rnd.uniform(-.1, .1),
                                        rnd.uniform(.95, 1.3), "#D8342A", 3)
                    y += .35
                st["water_l"] += bed_w * run * .3 * .35 * 1000
                z_in, z_bed = .95, .88
            else:                            # raft beds
                m.box("raft", x, yC, 0, bed_w, run, .36)
                m.box("water", x, yC, .31, bed_w - .08, run - .08, .01)
                n_raft = max(1, round(run / 1.2))
                rl = run / n_raft
                for t in range(n_raft):
                    m.box("rafts", x, yA + rl * (t + .5), .32, bed_w - .12, rl - .03, .04)
                y = yA + .12
                while y < yB - .05:
                    for c in range(5):
                        m.point("plants", x - .4 + c * .2, y, .41, leaf(), 4)
                    y += .2
                st["water_l"] += (bed_w - .08) * run * .28 * 1000
                z_in, z_bed = .6, .31
            bed_area += bed_w * run
            m.pipe(head + [(bx, yE + .45, z_in), (bx, yA - .25, z_in), (x, yA - .25, z_in),
                           (x, yA + .05, z_bed), (x, yB - .1, z_bed), (x, yB + .2, .06),
                           (xr, yB + .2, .06)] + tail, skip=(7,))
        st["feed_g_day"] = bed_area * FEED_G_PER_M2_DAY
        st["fish_capacity_kg"] = tank_l / 1000 * STOCKING_KG_PER_M3
        st["fish_needed_kg"] = st["feed_g_day"] / FEED_PCT_BODY_WEIGHT / 1000

    st["plant_sites"] = sum(1 for c, sz in zip(*m.points.get("plants", ([], [], [], [], []))[3:])
                            if c not in ("#D8342A", "#F08A1C"))
    st.update(width=w, length=L, footprint=w * L, volume=volume, cross_section=area,
              glazing_area=glaze_area, fans_needed=fans_needed, fans_placed=fans_placed,
              light_pct=round(g_trans * (SHADE_FACTOR if s.shade else 1)), glazing_name=g_name)
    m.stats = st
    return m


def balance_note(st: dict, method: str) -> str:
    """A plain-language read on the layout numbers."""
    if method != "aqua":
        return ("Exhaust is sized at one air change per minute; one 36-inch fan "
                f"moves about {FAN_CAPACITY_M3_PER_MIN} m3/min.")
    need, cap = st["fish_needed_kg"], st["fish_capacity_kg"]
    if need > cap * 1.1:
        verdict = "The beds need more fish than the tank can hold: widen the house or add a second tank."
    elif need < cap * 0.6:
        verdict = "The tank can carry more fish than the beds need: add grow beds or stock lighter."
    else:
        verdict = "Tank and beds are roughly in balance."
    return (f"Feed rate uses {FEED_G_PER_M2_DAY} g/day per m2 of grow bed. That feeds about "
            f"{need:,.0f} kg of fish eating {FEED_PCT_BODY_WEIGHT:.1%} of body weight daily; "
            f"the tank holds {cap:,.0f} kg at {STOCKING_KG_PER_M3} kg/m3. {verdict}")
