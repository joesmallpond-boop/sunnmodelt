"""Builds 'T-100 Amp.amxd' (Max for Live audio effect) with an amp-style front panel."""
import json, math, random, struct, sys
from gen_dsp import generate, CAB_NAMES

W, H = 1060, 169
DBG_X = 930
random.seed(7)

# ------------------------------------------------------------------ background drawing (lcd)
cmds = ["clear"]
def rect(l, t, r, b, c): cmds.append(f"paintrect {l} {t} {r} {b} {c[0]} {c[1]} {c[2]}")
def oval(l, t, r, b, c): cmds.append(f"paintoval {l} {t} {r} {b} {c[0]} {c[1]} {c[2]}")
def foval(l, t, r, b, c): cmds.append(f"frameoval {l} {t} {r} {b} {c[0]} {c[1]} {c[2]}")
def line(x1, y1, x2, y2, c): cmds.append(f"linesegment {x1} {y1} {x2} {y2} {c[0]} {c[1]} {c[2]}")
def text(x, y, s, c, size=9, face="normal", font="Arial"):
    cmds.append(f"frgb {c[0]} {c[1]} {c[2]}")
    cmds.append(f"font {font} {size}")
    cmds.append(f"textface {face}")
    cmds.append(f"moveto {x} {y}")
    cmds.append(f"write {s}")
def ctext(cx, y, s, c, size=9, face="normal"):
    text(int(cx - len(s) * size * 0.27), y, s, c, size, face)

AMP_R = 748
# tolex
rect(0, 0, AMP_R, H, (22, 22, 23))
for _ in range(1400):
    x, y = random.randint(0, AMP_R - 2), random.randint(0, H - 2)
    v = random.choice((14, 30, 34, 38))
    rect(x, y, x + 1, y + 1, (v, v, v))
# metal corners
for (l, t) in ((0, 0), (AMP_R - 12, 0), (0, H - 12), (AMP_R - 12, H - 12)):
    rect(l, t, l + 12, t + 12, (150, 150, 152))
    rect(l + 2, t + 2, l + 10, t + 10, (190, 190, 192))

# grille with tubes visible behind it
GL, GT, GR, GB = 12, 9, AMP_R - 12, 94
rect(GL - 2, GT - 2, GR + 2, GB + 2, (10, 10, 10))
rect(GL, GT, GR, GB, (64, 64, 66))  # perforated metal
power_tubes = [(300 + i * 46, 22, 92, 17) for i in range(4)]       # cx, top, bottom, halfwidth
pre_tubes = [(520 + i * 22, 46, 92, 7) for i in range(5)]
transformers = [(612 + 0, 30, 700, 92)]
def scene(x, y):
    for cx, top, bot, hw in power_tubes + pre_tubes:
        if abs(x - cx) <= hw and top <= y <= bot:
            # rounded top
            if y < top + hw and (x - cx) ** 2 + (y - (top + hw)) ** 2 > hw * hw:
                continue
            h = (y - top) / (bot - top)
            if h < 0.16:
                return (150, 150, 158)                 # silver getter flash
            if h > 0.9:
                return (28, 28, 30)                    # base
            d = abs(x - cx) / hw
            glow = max(0.0, 1 - ((h - 0.55) / 0.28) ** 2) * max(0.0, 1 - d * 1.4)
            base = (62, 60, 60)
            return tuple(int(base[k] + glow * ((255, 140, 40)[k] - base[k])) for k in range(3))
    for l, t, r, b in transformers:
        if l <= x <= r and t <= y <= b:
            return (20, 20, 22)
    return (9, 9, 10)
dx, dy, rr = 6, 5.2, 2
row = 0
y = GT + 3.0
while y < GB - 2:
    x = GL + 3.0 + (dx / 2 if row % 2 else 0)
    while x < GR - 2:
        c = scene(x, y)
        oval(int(x - rr), int(y - rr), int(x + rr), int(y + rr), c)
        x += dx
    y += dy
    row += 1
# badge plate (no maker logo - original name)
rect(24, 16, 104, 38, (12, 12, 12))
rect(25, 17, 103, 37, (30, 30, 30))
text(36, 32, "T-100", (235, 235, 235), 14, "bold")

# silver faceplate
PL, PT, PR, PB = 12, 99, AMP_R - 12, 158
for yy in range(PT, PB):
    f = (yy - PT) / (PB - PT)
    v = int(222 - 48 * f)
    line(PL, yy, PR, yy, (v, v, v + 2))
line(PL, PT, PR, PT, (245, 245, 245))
line(PL, PB, PR, PB, (90, 90, 90))
LABEL = (25, 25, 25)
KY = 128
KNOBS = {}  # name -> cx

def knob(cx, label):
    ctext(cx, 110, label, LABEL, 9)
    # scale ticks 1..10 (300 degree sweep like a Live dial)
    for k in range(10):
        a = math.radians(-150 + k * 300 / 9) - math.pi / 2
        x1, y1 = cx + 13 * math.cos(a), KY + 13 * math.sin(a)
        x2, y2 = cx + 16 * math.cos(a), KY + 16 * math.sin(a)
        line(int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2)), (60, 60, 60))
    oval(cx - 11, KY - 11, cx + 11, KY + 11, (8, 8, 8))
    foval(cx - 11, KY - 11, cx + 11, KY + 11, (70, 70, 70))
    oval(cx - 6, KY - 6, cx + 6, KY + 6, (150, 150, 155))
    oval(cx - 5, KY - 5, cx + 4, KY + 4, (205, 205, 210))

# input jack
ctext(34, 110, "in", LABEL, 9)
oval(34 - 9, KY - 9, 34 + 9, KY + 9, (120, 120, 125))
oval(34 - 7, KY - 7, 34 + 7, KY + 7, (200, 200, 205))
oval(34 - 4, KY - 4, 34 + 4, KY + 4, (10, 10, 10))

CH1 = [("ch1_vol", 78, "volume"), ("ch1_treble", 117, "treble"), ("ch1_bass", 156, "bass"), ("ch1_mid", 195, "middle")]
CH2 = [("ch2_gain", 244, "gain"), ("ch2_treble", 283, "treble"), ("ch2_bass", 322, "bass"),
       ("ch2_mid", 361, "middle"), ("ch2_vol", 400, "volume")]
PRES = [("presence", 488, "presence")]
for n, cx, lab in CH1 + CH2 + PRES:
    knob(cx, lab)
    KNOBS[n] = cx
ctext(136, 154, "channel 1", LABEL, 8)
ctext(322, 154, "channel 2", LABEL, 8)
ctext(432, 154, "ch select", LABEL, 7)
line(452, PT + 6, 452, PB - 6, (120, 120, 120))
text(518, 136, "model", (20, 20, 20), 14)
text(564, 136, "T-100", (20, 20, 20), 18, "bold")
ctext(668, 154, "standby", LABEL, 7)
# standby switch housing
rect(657, 112, 679, 146, (40, 40, 40))
rect(659, 114, 677, 144, (15, 15, 15))
# jewel bezel
oval(700, KY - 10, 720, KY + 10, (150, 150, 155))
oval(702, KY - 8, 718, KY + 8, (60, 10, 10))

# ---- cabinet rack strip
RX = AMP_R + 4
rect(AMP_R, 0, W, H, (16, 16, 17))
rect(RX, 2, DBG_X - 2, H - 2, (44, 44, 46))
rect(DBG_X + 2, 2, W - 2, H - 2, (60, 30, 30))
text(DBG_X + 10, 18, "DEBUG", (240, 200, 200), 10, "bold")
text(DBG_X + 10, 66, "nan count", (220, 220, 220), 8)
text(DBG_X + 10, 106, "check (~0.48)", (220, 220, 220), 8)
for (yy) in (8, H - 12):  # rack screws
    for xx in (RX + 6, DBG_X - 12):
        oval(xx, yy, xx + 6, yy + 6, (110, 110, 112))
        line(xx + 1, yy + 3, xx + 5, yy + 3, (40, 40, 40))
text(RX + 22, 20, "SPEAKER CAB", (220, 220, 220), 10, "bold")
text(RX + 14, 64, "output power", (170, 170, 170), 8)
lcd_msg = ", ".join(cmds)

# ------------------------------------------------------------------ patch
boxes, lines = [], []
_id = [0]
def nid():
    _id[0] += 1
    return f"obj-{_id[0]}"
def box(**kw):
    b = {"id": nid()}
    b.update(kw)
    boxes.append({"box": b})
    return b["id"]
def wire(a, ao, b, bi):
    lines.append({"patchline": {"source": [a, ao], "destination": [b, bi]}})

# gen~
code = generate()
gen_patcher = {
    "fileversion": 1,
    "appversion": {"major": 8, "minor": 5, "revision": 5, "architecture": "x64", "modernui": 1},
    "classnamespace": "dsp.gen",
    "rect": [100, 100, 900, 700],
    "bglocked": 0, "openinpresentation": 0, "default_fontsize": 12.0, "default_fontface": 0,
    "default_fontname": "Arial", "gridonopen": 1, "gridsize": [15, 15], "gridsnaponopen": 1,
    "objectsnaponopen": 1, "statusbarvisible": 2, "toolbarvisible": 1, "boxanimatetime": 200,
    "enablehscroll": 1, "enablevscroll": 1, "devicewidth": 0.0, "description": "", "digest": "",
    "tags": "", "style": "", "subpatcher_template": "",
    "boxes": [
        {"box": {"id": "obj-1", "maxclass": "newobj", "text": "in 1", "numinlets": 0, "numoutlets": 1,
                 "outlettype": [""], "patching_rect": [20, 20, 30, 22]}},
        {"box": {"id": "obj-2", "maxclass": "newobj", "text": "in 2", "numinlets": 0, "numoutlets": 1,
                 "outlettype": [""], "patching_rect": [300, 20, 30, 22]}},
        {"box": {"id": "obj-3", "maxclass": "codebox", "code": code, "fontface": 0,
                 "fontname": "<Monospaced>", "fontsize": 12.0, "numinlets": 2, "numoutlets": 4,
                 "outlettype": ["", "", "", ""], "patching_rect": [20, 60, 760, 560]}},
        {"box": {"id": "obj-6", "maxclass": "newobj", "text": "out 3", "numinlets": 1, "numoutlets": 0,
                 "patching_rect": [300, 640, 37, 22]}},
        {"box": {"id": "obj-7", "maxclass": "newobj", "text": "out 4", "numinlets": 1, "numoutlets": 0,
                 "patching_rect": [500, 640, 37, 22]}},
        {"box": {"id": "obj-4", "maxclass": "newobj", "text": "out 1", "numinlets": 1, "numoutlets": 0,
                 "patching_rect": [20, 640, 37, 22]}},
        {"box": {"id": "obj-5", "maxclass": "newobj", "text": "out 2", "numinlets": 1, "numoutlets": 0,
                 "patching_rect": [740, 640, 37, 22]}},
    ],
    "lines": [
        {"patchline": {"source": ["obj-1", 0], "destination": ["obj-3", 0]}},
        {"patchline": {"source": ["obj-2", 0], "destination": ["obj-3", 1]}},
        {"patchline": {"source": ["obj-3", 0], "destination": ["obj-4", 0]}},
        {"patchline": {"source": ["obj-3", 1], "destination": ["obj-5", 0]}},
        {"patchline": {"source": ["obj-3", 2], "destination": ["obj-6", 0]}},
        {"patchline": {"source": ["obj-3", 3], "destination": ["obj-7", 0]}},
    ],
}

lcd = box(maxclass="lcd", numinlets=1, numoutlets=4, outlettype=["list", "list", "int", ""],
          patching_rect=[700, 400, W, H], presentation=1, presentation_rect=[0, 0, W, H],
          background=1, ignoreclick=1, border=0, local=1, bgcolor=[0.086, 0.086, 0.09, 1.0])
plugin = box(maxclass="newobj", text="plugin~", numinlets=2, numoutlets=2, outlettype=["signal", "signal"],
             patching_rect=[30, 420, 60, 22])
gen = box(maxclass="newobj", text="gen~", numinlets=2, numoutlets=4, outlettype=["signal", "signal", "signal", "signal"],
          patching_rect=[30, 520, 300, 22], patcher=gen_patcher)
plugout = box(maxclass="newobj", text="plugout~", numinlets=2, numoutlets=0, patching_rect=[30, 600, 60, 22])
wire(plugin, 0, gen, 0); wire(plugin, 1, gen, 1)
wire(gen, 0, plugout, 0); wire(gen, 1, plugout, 1)

thisdev = box(maxclass="newobj", text="live.thisdevice", numinlets=1, numoutlets=3,
              outlettype=["bang", "int", "int"], patching_rect=[400, 20, 85, 22])
trig = box(maxclass="newobj", text="t b b", numinlets=1, numoutlets=2, outlettype=["bang", "bang"],
           patching_rect=[400, 50, 40, 22])
drawmsg = box(maxclass="message", text=lcd_msg, numinlets=2, numoutlets=1, outlettype=[""],
              patching_rect=[700, 360, 200, 22])
sinit = box(maxclass="newobj", text="s ---t100init", numinlets=1, numoutlets=0, patching_rect=[400, 80, 80, 22])
wire(thisdev, 0, trig, 0)
wire(trig, 1, drawmsg, 0)
wire(drawmsg, 0, lcd, 0)
wire(trig, 0, sinit, 0)

SILVER_TXT = [0.1, 0.1, 0.1, 1.0]
px = [30]
def to_gen(ctrl, pname, outlet=0):
    x = px[0]; px[0] += 110
    r = box(maxclass="newobj", text="r ---t100init", numinlets=0, numoutlets=1, outlettype=[""],
            patching_rect=[x, 140, 80, 22])
    p = box(maxclass="newobj", text=f"prepend {pname}", numinlets=1, numoutlets=1, outlettype=[""],
            patching_rect=[x, 300, 100, 22])
    wire(r, 0, ctrl, 0)
    wire(ctrl, outlet, p, 0)
    wire(p, 0, gen, 0)
    return ctrl

def dial(pname, longname, shortname, rect, mn, mx, init, unit=1, show=False, varname=None):
    x = px[0]
    vo = {"parameter_initial": [init], "parameter_initial_enable": 1, "parameter_longname": longname,
          "parameter_mmax": float(mx), "parameter_mmin": float(mn), "parameter_shortname": shortname,
          "parameter_type": 0, "parameter_unitstyle": unit}
    kw = dict(maxclass="live.dial", numinlets=1, numoutlets=2, outlettype=["", "float"], parameter_enable=1,
              patching_rect=[x, 200, 44, 48], presentation=1, presentation_rect=rect,
              varname=varname or pname, saved_attribute_attributes={"valueof": vo})
    if not show:
        kw.update(showname=0, shownumber=0, triangle=0,
                  dialcolor=[0, 0, 0, 0], activedialcolor=[0, 0, 0, 0],
                  needlecolor=[0.97, 0.97, 0.97, 1.0], activeneedlecolor=[0.97, 0.97, 0.97, 1.0],
                  panelcolor=[0, 0, 0, 0], focusbordercolor=[0.9, 0.5, 0.1, 1.0])
    d = box(**kw)
    return to_gen(d, pname)

for n, cx, lab in CH1 + CH2 + PRES:
    ch = "Ch1 " if n.startswith("ch1") else ("Ch2 " if n.startswith("ch2") else "")
    long = (ch + lab.capitalize()).replace("Middle", "Middle")
    init = {"ch1_vol": 4.0, "ch2_vol": 4.0, "presence": 3.0}.get(n, 5.5)
    dial(n, long, long[:10], [cx - 14, KY - 14, 28, 28], 1, 10, init)

def enum_vo(longname, short, items, init):
    return {"valueof": {"parameter_enum": items, "parameter_initial": [init], "parameter_initial_enable": 1,
                        "parameter_longname": longname, "parameter_mmax": len(items) - 1,
                        "parameter_shortname": short, "parameter_type": 2, "parameter_unitstyle": 9}}

# channel select button
chs = box(maxclass="live.text", numinlets=1, numoutlets=2, outlettype=["", ""], parameter_enable=1, mode=1,
          text="1", texton="2", patching_rect=[px[0], 200, 40, 20], presentation=1,
          presentation_rect=[422, KY - 8, 20, 16], varname="chsel",
          bgcolor=[0.15, 0.15, 0.15, 1.0], bgoncolor=[0.15, 0.15, 0.15, 1.0],
          activebgcolor=[0.15, 0.15, 0.15, 1.0], activebgoncolor=[0.95, 0.55, 0.1, 1.0],
          textcolor=[0.95, 0.95, 0.95, 1.0], textoncolor=[0.05, 0.05, 0.05, 1.0],
          bordercolor=[0.3, 0.3, 0.3, 1.0], fontsize=9.0,
          saved_attribute_attributes=enum_vo("Channel", "Channel", ["Ch 1", "Ch 2"], 1))
to_gen(chs, "chsel")

# standby rocker
stb = box(maxclass="live.text", numinlets=1, numoutlets=2, outlettype=["", ""], parameter_enable=1, mode=1,
          text="ON", texton="STBY", patching_rect=[px[0], 200, 40, 20], presentation=1,
          presentation_rect=[660, 115, 16, 28], varname="standby",
          bgcolor=[0.22, 0.22, 0.22, 1.0], bgoncolor=[0.08, 0.08, 0.08, 1.0],
          activebgcolor=[0.22, 0.22, 0.22, 1.0], activebgoncolor=[0.08, 0.08, 0.08, 1.0],
          textcolor=[0.85, 0.85, 0.85, 1.0], textoncolor=[0.6, 0.6, 0.6, 1.0],
          bordercolor=[0.5, 0.5, 0.5, 1.0], fontsize=6.0,
          saved_attribute_attributes=enum_vo("Standby", "Standby", ["Play", "Standby"], 0))
to_gen(stb, "standby")
# jewel lamp follows standby
jewel = box(maxclass="panel", numinlets=1, numoutlets=0, mode=0, rounded=16, border=0,
            bgcolor=[0.95, 0.12, 0.08, 1.0], bgfillcolor_type="color",
            bgfillcolor_color=[0.95, 0.12, 0.08, 1.0], ignoreclick=1,
            patching_rect=[px[0], 330, 20, 20], presentation=1, presentation_rect=[704, KY - 6, 12, 12])
sel = box(maxclass="newobj", text="sel 0 1", numinlets=1, numoutlets=3, outlettype=["bang", "bang", ""],
          patching_rect=[px[0], 250, 50, 22])
m_on = box(maxclass="message", text="bgfillcolor 0.95 0.12 0.08 1.", numinlets=2, numoutlets=1, outlettype=[""],
           patching_rect=[px[0], 280, 160, 22])
m_off = box(maxclass="message", text="bgfillcolor 0.25 0.04 0.03 1.", numinlets=2, numoutlets=1, outlettype=[""],
            patching_rect=[px[0] + 170, 280, 160, 22])
wire(stb, 0, sel, 0); wire(sel, 0, m_on, 0); wire(sel, 1, m_off, 0)
wire(m_on, 0, jewel, 0); wire(m_off, 0, jewel, 0)
px[0] += 340

# cab menu
cabm = box(maxclass="live.menu", numinlets=1, numoutlets=3, outlettype=["", "", "float"], parameter_enable=1,
           patching_rect=[px[0], 200, 120, 15], presentation=1, presentation_rect=[RX + 10, 30, DBG_X - RX - 20, 16],
           varname="cab", saved_attribute_attributes=enum_vo("Cabinet", "Cabinet", CAB_NAMES, 1))
to_gen(cabm, "cab")
# club / arena
pw = box(maxclass="live.tab", numinlets=1, numoutlets=3, outlettype=["", "", "float"], parameter_enable=1,
         num_lines_patching=1, num_lines_presentation=1,
         patching_rect=[px[0], 200, 100, 20], presentation=1, presentation_rect=[RX + 10, 70, DBG_X - RX - 20, 18],
         varname="power", saved_attribute_attributes=enum_vo("Output Power", "Power", ["Club 25W", "Arena 100W"], 1))
to_gen(pw, "power")
# debug tap + readouts
dbg = box(maxclass="live.menu", numinlets=1, numoutlets=3, outlettype=["", "", "float"], parameter_enable=1,
          patching_rect=[px[0], 200, 120, 15], presentation=1, presentation_rect=[DBG_X + 10, 30, W - DBG_X - 20, 16],
          varname="dbg_tap", saved_attribute_attributes=enum_vo("Debug Tap", "Tap",
          ["Full amp", "Dry input", "Test tone", "After V1A", "Preamp out", "Power amp out"], 0))
to_gen(dbg, "dbg_tap")
for k, yy in ((2, 72), (3, 112)):
    sn = box(maxclass="newobj", text="snapshot~ 200", numinlets=2, numoutlets=1, outlettype=["float"],
             patching_rect=[30 + k * 120, 700, 90, 22])
    fl = box(maxclass="flonum", numinlets=1, numoutlets=2, outlettype=["", "bang"], format=6,
             patching_rect=[30 + k * 120, 730, 80, 22], presentation=1,
             presentation_rect=[DBG_X + 10, yy, W - DBG_X - 20, 20], fontsize=11.0, ignoreclick=1)
    wire(gen, k, sn, 0); wire(sn, 0, fl, 0)
# input / output trims (Live style)
dial("p_input", "Input", "Input", [RX + 14, 100, 60, 56], -24, 24, 0.0, unit=4, show=True)
dial("p_output", "Output", "Output", [RX + 94, 100, 60, 56], -36, 12, -6.0, unit=4, show=True)

patcher = {
    "patcher": {
        "fileversion": 1,
        "appversion": {"major": 8, "minor": 5, "revision": 5, "architecture": "x64", "modernui": 1},
        "classnamespace": "box",
        "rect": [60, 80, 1300, 760],
        "openrect": [0.0, 0.0, 0.0, 169.0],
        "bglocked": 0, "openinpresentation": 1, "default_fontsize": 10.0, "default_fontface": 0,
        "default_fontname": "Arial Bold", "gridonopen": 1, "gridsize": [8.0, 8.0], "gridsnaponopen": 1,
        "objectsnaponopen": 1, "statusbarvisible": 2, "toolbarvisible": 1, "lefttoolbarpinned": 0,
        "toptoolbarpinned": 0, "righttoolbarpinned": 0, "bottomtoolbarpinned": 0, "toolbars_unpinned_last_save": 0,
        "tallnewobj": 0, "boxanimatetime": 500, "enablehscroll": 1, "enablevscroll": 1,
        "devicewidth": float(W), "description": "Sunn Model T circuit model with cab sims", "digest": "",
        "tags": "", "style": "", "subpatcher_template": "", "assistshowspatchername": 0,
        "boxes": boxes, "lines": lines,
        "dependency_cache": [], "latency": 0, "is_mpe": 0, "minimum_live_version": "",
        "minimum_max_version": "", "platform_compatibility": 0, "autosave": 0,
    }
}

def write_amxd(path, patch):
    data = json.dumps(patch, indent=1).encode("utf-8") + b"\n\x00"
    head = b"ampf" + struct.pack("<I", 4) + b"aaaa" + b"meta" + struct.pack("<I", 4) + struct.pack("<I", 0) \
        + b"ptch" + struct.pack("<I", len(data))
    open(path, "wb").write(head + data)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "T-100 Amp.amxd"
    write_amxd(out, patcher)
    import os
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "t100.genexpr"), "w").write(code)
    print("wrote", out, "boxes", len(boxes), "lcd cmds", len(cmds), "msg bytes", len(lcd_msg))
