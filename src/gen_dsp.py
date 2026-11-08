"""Generates the gen~ (GenExpr) DSP for the T-100 amp device.

Circuit values come from the Fender/Sunn Model T service schematics (sheets 1 & 2).
"""
import math
import sympy as sp
from tonestack import derive, s, t, m, l

TN = 2048          # tube table size
KG1 = 800.0        # 12AX7 Koren kg1 (tuned towards the schematic's cathode test points)

# ---------------------------------------------------------------- tube stages
# name, B+, plate R, cathode R, source R (grid conduction), unbypassed?, table range (V), AC load R
STAGES = [
    ("v1a", 266.0, 100e3, 1500.0, 68e3, 0, 8.0, 76e3),     # V1A input stage (both channels)
    ("v1b", 266.0, 100e3, 1500.0, 120e3, 0, 80.0, 78e3),   # V1B ch2 first gain stage
    ("v2a", 284.0, 100e3, 820.0, 260e3, 0, 120.0, 100e3),  # V2A ch1 gain stage (into V2B CF)
    ("v3a", 284.0, 470e3, 18e3, 60e3, 1, 120.0, 200e3),    # V3A ch2 cold clipper, 470k || R28/C15 network
    ("v3b", 284.0, 100e3, 820.0, 60e3, 0, 120.0, 100e3),   # V3B ch2 gain stage (into V4A CF)
]

# cathode-bypass shelves: (rk, ck) -> H(s)=(s+wz)/(s+wp)
def shelf(rk, ck, rp=62e3, rl=100e3, mu=100.0):
    wz = 1.0 / (rk * ck)
    ratio = (rp + rl) / (rp + rl + (mu + 1) * rk)
    return wz, wz / ratio

SHELVES = {
    "v1b": shelf(1500.0, 0.68e-6),  # R22 / C11
    "v2a": shelf(820.0, 0.68e-6),   # R11 / C7
    "v3b": shelf(820.0, 1.0e-6),    # R32 / C17
}

# ---------------------------------------------------------------- tone stacks
# R1 treble pot, R2 bass pot, R3 mid pot, R4 slope, C1 treble, C2 bass, C3 mid, Rs source, RL load
STACKS = {
    "ts1": dict(R1=250e3, R2=1e6, R3=25e3, R4=68e3, C1=470e-12, C2=22e-9, C3=22e-9, Rs=650.0, RL=1e6),
    "ts2": dict(R1=250e3, R2=250e3, R3=25e3, R4=33e3, C1=470e-12, C2=22e-9, C3=22e-9, Rs=650.0, RL=470e3),
}

# bilinear expansion matrix: coefficient of z^-k in (1-z^-1)^n (1+z^-1)^(3-n)
def bilin_matrix(order=3):
    import numpy as np
    M = []
    for n in range(order + 1):
        p = np.poly1d([1.0])
        for _ in range(n):
            p = p * np.poly1d([-1.0, 1.0])   # (1 - z)
        for _ in range(order - n):
            p = p * np.poly1d([1.0, 1.0])    # (1 + z)
        c = list(p.coeffs[::-1])             # ascending powers of z
        c += [0.0] * (order + 1 - len(c))
        M.append(c)
    return M

def stack_coeff_code(name, tv, mv, lv):
    d = STACKS[name]
    num, den = derive(d["R1"], d["R2"], d["R3"], d["R4"], d["C1"], d["C2"], d["C3"], d["Rs"], d["RL"])
    nc = num.all_coeffs()[::-1]  # ascending in s
    dc = den.all_coeffs()[::-1]
    nc += [0] * (4 - len(nc))
    dc += [0] * (4 - len(dc))
    # scale to keep numbers tame
    scale = float(sp.Abs(dc[0].subs({t: 0.5, m: 0.5, l: 0.5})))
    sub = {t: sp.Symbol(tv), m: sp.Symbol(mv), l: sp.Symbol(lv)}
    lines = []
    for i, c in enumerate(nc):
        e = sp.horner(sp.expand(c / scale)).subs(sub) if c != 0 else 0
        lines.append(f"{name}_sb{i} = {sp.ccode(e)};")
    for i, c in enumerate(dc):
        e = sp.horner(sp.expand(c / scale)).subs(sub) if c != 0 else 0
        lines.append(f"{name}_sa{i} = {sp.ccode(e)};")
    M = bilin_matrix()
    lines.append("bc1 = 2 * fs2; bc2 = bc1 * bc1; bc3 = bc2 * bc1;")
    cp = ["1", "bc1", "bc2", "bc3"]
    for k in range(4):
        tb = " + ".join(f"({M[n][k]:g}) * {name}_sb{n} * {cp[n]}" for n in range(4))
        ta = " + ".join(f"({M[n][k]:g}) * {name}_sa{n} * {cp[n]}" for n in range(4))
        lines.append(f"{name}_B{k} = {tb};")
        lines.append(f"{name}_A{k} = {ta};")
    for k in range(4):
        lines.append(f"h_{name}_b{k} = {name}_B{k} / {name}_A0;")
    for k in range(1, 4):
        lines.append(f"h_{name}_a{k} = {name}_A{k} / {name}_A0;")
    return "\n".join(lines)

# ---------------------------------------------------------------- cabinets
# section: (type, freq, Q, gain dB) type 1=HP 2=LP 3=peak 0=off
import json as _json
_fit = _json.load(open(__file__.replace("gen_dsp.py", "cabs.json")))
CAB_NAMES = ["Direct (no speaker)", "4x12 Greenback", "4x12 V30", "1x15 Bass", "2x12 V30", "2x10", "1x12 Open", "1x8"]
# section lists fitted (fitcab.py) to close-mic response targets for each cab type
CABS = [(CAB_NAMES[0], [])] + [(n, [tuple(sec) for sec in _fit[n]]) for n in CAB_NAMES[1:]]
NSEC = 8
CAB_MAKEUP = None  # filled in by calibrate_cabs()

def rbj(tp, f, q, g, fs):
    A = 10 ** (g / 40.0)
    w = 2 * math.pi * f / fs
    cw, sw = math.cos(w), math.sin(w)
    al = sw / (2 * q)
    if tp == 1:
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]; a = [1 + al, -2 * cw, 1 - al]
    elif tp == 2:
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]; a = [1 + al, -2 * cw, 1 - al]
    elif tp == 3:
        b = [1 + al * A, -2 * cw, 1 - al * A]; a = [1 + al / A, -2 * cw, 1 - al / A]
    else:
        return [1, 0, 0], [1, 0, 0]
    return [x / a[0] for x in b], [x / a[0] for x in a]

def calibrate_cabs(fs=48000.0):
    """Equal-loudness makeup: match each cab's RMS on a guitar-like spectrum to Direct."""
    import numpy as np
    from scipy.signal import lfilter
    rng = np.random.default_rng(1)
    n = 1 << 17
    w = rng.standard_normal(n)
    X = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1 / fs)
    shape = np.where(f > 20, 1 / np.sqrt(np.maximum(f, 20)), 0)  # pink
    shape *= (f < 9000)
    sig = np.fft.irfft(X * shape)
    ref = np.sqrt(np.mean(sig ** 2))
    out = []
    for name, secs in CABS:
        y = sig.copy()
        for sec in secs:
            b, a = rbj(*sec, fs)
            y = lfilter(b, a, y)
        r = np.sqrt(np.mean(y ** 2))
        out.append(ref / r)
    return out

# ---------------------------------------------------------------- code
def table_init_code(name, B, RL, RK, RS, unb, vmax, RAC):
    a = RS / (RS + 1500.0)
    vk = "ti * %r" % RK if unb else f"h_{name}_vk0"
    return f"""
// ---- {name}: B+={B}V Rp={RL:g} Rk={RK:g}{' (unbypassed)' if unb else ' (bypassed)'}
// quiescent (dynamic cathode) solve
lo = 0; hi = {B!r} / ({RL!r} + {RK!r});
for (j = 0; j < 48; j = j + 1) {{
    ti = 0.5 * (lo + hi);
    vpk = {B!r} - ti * {RL!r} - ti * {RK!r};
    vgk = 0 - ti * {RK!r};
    kz = 600 * (0.01 + vgk / sqrt(300 + vpk * vpk));
    ksp = kz;
    if (kz < 30) {{ ksp = log(1 + exp(kz)); }}
    ke1 = vpk / 600 * ksp;
    kip = 0;
    if (ke1 > 0 && vpk > 0) {{ kip = pow(ke1, 1.4) / {KG1!r}; }}
    if (ti - kip > 0) {{ hi = ti; }} else {{ lo = ti; }}
}}
h_{name}_vk0 = ti * {RK!r};
iq = ti; vp0 = {B!r} - ti * {RL!r};
// AC load line through the quiescent point
for (i = 0; i < {TN}; i = i + 1) {{
    vin = (i / {TN - 1}.0 * 2 - 1) * {vmax!r};
    lo = 0; hi = iq + vp0 / {RAC!r};
    for (j = 0; j < 44; j = j + 1) {{
        ti = 0.5 * (lo + hi);
        vkk = {vk};
        gx = 5 * (vin - vkk);
        gsp = gx / 5;
        if (gx < 30) {{ gsp = log(1 + exp(gx)) / 5; }}
        vg = vin - {a!r} * gsp;
        vpk = vp0 - (ti - iq) * {RAC!r} - vkk;
        vgk = vg - vkk;
        kz = 600 * (0.01 + vgk / sqrt(300 + vpk * vpk));
        ksp = kz;
        if (kz < 30) {{ ksp = log(1 + exp(kz)); }}
        ke1 = vpk / 600 * ksp;
        kip = 0;
        if (ke1 > 0 && vpk > 0) {{ kip = pow(ke1, 1.4) / {KG1!r}; }}
        if (ti - kip > 0) {{ hi = ti; }} else {{ lo = ti; }}
    }}
    poke(tb_{name}, vp0 - (ti - iq) * {RAC!r}, i);
}}
h_{name}_q = peek(tb_{name}, {TN // 2});
"""

def lookup(name, x, vmax):
    return f"""lx = clamp(({x}) / {vmax!r} * 0.5 + 0.5, 0, 1) * {TN - 1}.0;
li = floor(lx); li = min(li, {TN - 2}.0); lf = lx - li;
la = peek(tb_{name}, li); lb = peek(tb_{name}, li + 1);
{x} = la + (lb - la) * lf - h_{name}_q;"""

def onepole_lp(var, st, coef):
    return f"{st} = {st} + {coef} * ({var} - {st}); {var} = {st};"

def onepole_hp(var, xst, yst, coef):
    return f"hpt = {coef} * ({yst} + {var} - {xst}); {xst} = {var}; {yst} = hpt; {var} = hpt;"

def first_order(var, b0, b1, a1, xs, ys):
    return f"fot = {b0} * {var} + {b1} * {xs} - {a1} * {ys}; {xs} = {var}; {ys} = fot; {var} = fot;"

def stack_run(name, var):
    return (f"tsy = h_{name}_b0 * {var} + h_{name}_z1;\n"
            f"h_{name}_z1 = h_{name}_b1 * {var} - h_{name}_a1 * tsy + h_{name}_z2;\n"
            f"h_{name}_z2 = h_{name}_b2 * {var} - h_{name}_a2 * tsy + h_{name}_z3;\n"
            f"h_{name}_z3 = h_{name}_b3 * {var} - h_{name}_a3 * tsy;\n"
            f"{var} = tsy;")

PARAMS = [
    # name, default, min, max
    ("p_input", 0, -24, 24),
    ("ch1_vol", 4, 1, 10), ("ch1_treble", 5.5, 1, 10), ("ch1_bass", 5.5, 1, 10), ("ch1_mid", 5.5, 1, 10),
    ("ch2_gain", 5.5, 1, 10), ("ch2_treble", 5.5, 1, 10), ("ch2_bass", 5.5, 1, 10), ("ch2_mid", 5.5, 1, 10),
    ("ch2_vol", 4, 1, 10),
    ("chsel", 1, 0, 1), ("presence", 3, 1, 10), ("standby", 0, 0, 1),
    ("power", 1, 0, 1), ("cab", 1, 0, 7), ("p_output", -6, -36, 12),
]
SMOOTHED = ["p_input", "ch1_vol", "ch1_treble", "ch1_bass", "ch1_mid", "ch2_gain", "ch2_treble",
            "ch2_bass", "ch2_mid", "ch2_vol", "chsel", "presence", "standby", "power", "p_output"]

def generate():
    global CAB_MAKEUP
    CAB_MAKEUP = [float(v) for v in calibrate_cabs()]
    hist = set()
    L = []
    L.append("// T-100 : Sunn Model T (1997 Fender reissue) circuit model")
    L.append("// generated by gen_dsp.py - edit the generator, not this file")
    for n, d, lo, hi in PARAMS:
        L.append(f"Param {n}({d}, min={lo}, max={hi});")
    for st in STAGES:
        L.append(f"Data tb_{st[0]}({TN});")
    H = []
    def hv(*names):
        for n in names:
            if n not in hist:
                hist.add(n); H.append(n)
    hv("h_init", "h_sr", "h_xprev", "h_fb", "h_env", "h_cabsel", "h_cabfade")
    for n in SMOOTHED:
        hv("sm_" + n)
    for st in STAGES:
        hv(f"h_{st[0]}_q", f"h_{st[0]}_vk0")
    for nm in STACKS:
        hv(*[f"h_{nm}_b{k}" for k in range(4)], *[f"h_{nm}_a{k}" for k in range(1, 4)],
           f"h_{nm}_z1", f"h_{nm}_z2", f"h_{nm}_z3", f"h_{nm}_ut", f"h_{nm}_um", f"h_{nm}_ul")
    # filter states
    hv("h_lp_in", "h_v1a_hpx", "h_v1a_hpy",
       "h_c1_vx", "h_c1_vy", "h_c1_vb0", "h_c1_vb1", "h_c1_va1", "h_c1_div", "h_c1_mill", "h_c1_lp", "h_c1_used",
       "h_v2a_sx", "h_v2a_sy",
       "h_c2_gdiv", "h_c2_mill", "h_c2_lp", "h_c2_used", "h_v1b_sx", "h_v1b_sy",
       "h_v1b_hpx", "h_v1b_hpy", "h_n1x", "h_n1y", "h_v3a_hpx", "h_v3a_hpy", "h_n2x", "h_n2y",
       "h_v3b_sx", "h_v3b_sy", "h_c16", "h_c2_volr",
       "h_fx_hpx", "h_fx_hpy", "h_pi_hpx", "h_pi_hpy", "h_pg_hpx", "h_pg_hpy",
       "h_ot_hpx", "h_ot_hpy", "h_ot_lp", "h_pres_x", "h_pres_y",
       "h_d1x1", "h_d1x2", "h_d1y1", "h_d1y2", "h_d2x1", "h_d2x2", "h_d2y1", "h_d2y2",
       "h_dc_b0", "h_dc_b1", "h_dc_b2", "h_dc_a1", "h_dc_a2", "h_dc2_b0", "h_dc2_b1", "h_dc2_b2", "h_dc2_a1", "h_dc2_a2",
       "h_k_in", "h_k_v1b_sh", "h_k_c2a", "h_k_c2b", "h_k_c2c", "h_k_v2a_sh", "h_k_v3b_sh",
       "h_k_hp7", "h_k_hp10", "h_k_hp5", "h_k_hp15", "h_k_hp34", "h_k_hp30", "h_k_lpot", "h_k_c16", "h_k_pres",
       "h_k_att", "h_k_rel", "h_k_n_b0", "h_k_n_b1", "h_k_n_a1",
       "h_k_v1b_b0", "h_k_v1b_b1", "h_k_v1b_a1", "h_k_v2a_b0", "h_k_v2a_b1", "h_k_v2a_a1",
       "h_k_v3b_b0", "h_k_v3b_b1", "h_k_v3b_a1")
    for i in range(NSEC):
        hv(*[f"h_cb{i}_{c}" for c in ("b0", "b1", "b2", "a1", "a2", "x1", "x2", "y1", "y2")])
    hv("h_cabgain")
    for n in H:
        L.append(f"History {n}(0);")

    # ---------------- body
    B = []
    B.append("iq = 0; vp0 = 0; x = 0; y = 0; i = 0; j = 0; lo = 0; hi = 0; ti = 0; vin = 0; vkk = 0; vg = 0; vpk = 0; vgk = 0;")
    B.append("kz = 0; ksp = 0; ke1 = 0; kip = 0; gx = 0; gsp = 0; lx = 0; li = 0; lf = 0; la = 0; lb = 0;")
    B.append("hpt = 0; fot = 0; tsy = 0; bc1 = 0; bc2 = 0; bc3 = 0; fs2 = samplerate * 2; os = 0; xin = 0;")
    B.append("a = 0; b = 0; pre = 0; pin = 0; vpi = 0; u = 0; pz = 0; psp = 0; pp = 0; sA = 0; sB = 0; pm = 0;")
    B.append("vs = 0; fbr = 0; yo = 0; dy = 0; vbias = 0; vfull = 0; sagamt = 0; sagf = 0; r1 = 0; r2 = 0; rth = 0;")
    B.append("pt = 0; pm1 = 0; pl = 0; tap = 0; wc = 0; cw = 0; sw = 0; al = 0; ga = 0; a0 = 0; ysec = 0; cb = 0; cg = 0;")
    for nm in STACKS:
        B.append(" ".join(f"{nm}_sb{k} = 0; {nm}_sa{k} = 0; {nm}_B{k} = 0; {nm}_A{k} = 0;" for k in range(4)))
    # init / samplerate dependent
    B.append("if (h_init == 0) {")
    for st in STAGES:
        B.append(table_init_code(*st))
    for n in SMOOTHED:
        B.append(f"sm_{n} = {n};")
    B.append("h_cabsel = -1;")
    B.append("h_init = 1;")
    B.append("}")
    B.append("if (h_sr != samplerate) {")
    B.append("h_sr = samplerate;")
    def rc(fc):
        return f"(1 - exp(-2 * pi * {fc!r} / fs2))"
    def hpk(fc):
        return f"(1 / (1 + 2 * pi * {fc!r} / fs2))"
    B.append(f"h_k_in = {rc(1/(2*math.pi*68e3*110e-12))};")
    B.append(f"h_k_hp7 = {hpk(7.0)}; h_k_hp10 = {hpk(10.5)}; h_k_hp5 = {hpk(5.0)}; h_k_hp15 = {hpk(15.0)};")
    B.append(f"h_k_hp34 = {hpk(34.0)}; h_k_hp30 = {hpk(30.0)}; h_k_lpot = {rc(14000.0)};")
    B.append(f"h_k_c16 = {rc(1/(2*math.pi*38e3*680e-12))}; h_k_pres = {hpk(2200.0)};")
    B.append("h_k_att = 1 - exp(-1 / (0.02 * fs2)); h_k_rel = 1 - exp(-1 / (0.25 * fs2));")
    B.append("bc1 = 2 * fs2;")
    for nm, (wz, wp) in SHELVES.items():
        B.append(f"h_k_{nm}_b0 = (bc1 + {wz!r}) / (bc1 + {wp!r}); h_k_{nm}_b1 = ({wz!r} - bc1) / (bc1 + {wp!r}); h_k_{nm}_a1 = ({wp!r} - bc1) / (bc1 + {wp!r});")
    # R23/C13 + R24 network: H=(Rb + s Rb Rt C)/((Rb+Rt) + s Rb Rt C)
    Rt, Rb, C = 470e3, 220e3, 750e-12
    n0, n1, d0, d1 = Rb, Rb * Rt * C, Rb + Rt, Rb * Rt * C
    B.append(f"h_k_n_b0 = ({n0!r} + {n1!r} * bc1) / ({d0!r} + {d1!r} * bc1); h_k_n_b1 = ({n0!r} - {n1!r} * bc1) / ({d0!r} + {d1!r} * bc1); h_k_n_a1 = ({d0!r} - {d1!r} * bc1) / ({d0!r} + {d1!r} * bc1);")
    # decimation LPF (4th order butterworth)
    for nm, q in (("dc", 0.5412), ("dc2", 1.3066)):
        B.append(f"wc = 2 * pi * min(20000, 0.45 * samplerate) / fs2; cw = cos(wc); sw = sin(wc); al = sw / (2 * {q});")
        B.append(f"a0 = 1 + al; h_{nm}_b0 = (1 - cw) / 2 / a0; h_{nm}_b1 = (1 - cw) / a0; h_{nm}_b2 = (1 - cw) / 2 / a0; h_{nm}_a1 = -2 * cw / a0; h_{nm}_a2 = (1 - al) / a0;")
    B.append("h_c1_used = -1; h_c2_used = -1; h_ts1_ut = -1; h_ts2_ut = -1; h_cabsel = -1;")
    B.append("}")

    # smoothing
    for n in SMOOTHED:
        B.append(f"sm_{n} = sm_{n} + 0.002 * ({n} - sm_{n});")

    # ---- control-rate coefficient updates
    def aud(p, a):
        return f"((pow({a!r}, {p}) - 1) / {a - 1!r})"
    A30, A15, A10 = 5.444, 32.11, 81.0
    # ch1 volume network (R6 1M 10A, bright cap C4 .0022u, R7/R8 470k) - matches TP2->TP4 level at vol 3
    B.append("if (abs(sm_ch1_vol - h_c1_used) > 0.0005) {")
    B.append("h_c1_used = sm_ch1_vol;")
    B.append(f"tap = clamp({aud('(sm_ch1_vol - 1) / 9', A10)}, 0.0005, 0.9995);")
    B.append("r1 = (1 - tap) * 1000000; r2 = tap * 1000000; r2 = r2 * 940000 / (r2 + 940000);")
    B.append("rth = r1 * r2 / (r1 + r2);")
    B.append("bc1 = 2 * fs2;")
    B.append("h_c1_vb0 = (r2 + r2 * r1 * 2.2e-9 * bc1) / ((r1 + r2) + r2 * r1 * 2.2e-9 * bc1);")
    B.append("h_c1_vb1 = (r2 - r2 * r1 * 2.2e-9 * bc1) / ((r1 + r2) + r2 * r1 * 2.2e-9 * bc1);")
    B.append("h_c1_va1 = ((r1 + r2) - r2 * r1 * 2.2e-9 * bc1) / ((r1 + r2) + r2 * r1 * 2.2e-9 * bc1);")
    B.append("h_c1_div = 470000 / (940000 + rth);")
    B.append("h_c1_mill = 1 - exp(-2 * pi / (2 * pi * ((rth + 470000) * 470000 / (rth + 940000) + 10000) * 1.1e-10) / fs2);")
    B.append("}")
    # ch2 gain (R17 220k + R18 250k 15A) and volume (R39 220k + R40 250k 30A)
    B.append("if (abs(sm_ch2_gain - h_c2_used) > 0.0005) {")
    B.append("h_c2_used = sm_ch2_gain;")
    B.append(f"tap = clamp({aud('(sm_ch2_gain - 1) / 9', A15)}, 0.0005, 0.9995);")
    B.append("r2 = tap * 250000; r1 = 470000 - r2;")
    B.append("h_c2_gdiv = r2 / 470000; rth = r1 * r2 / 470000;")
    B.append("h_c2_mill = 1 - exp(-2 * pi / (2 * pi * (rth + 10000) * 1.1e-10) / fs2);")
    B.append("}")
    B.append(f"h_c2_volr = {aud('(sm_ch2_vol - 1) / 9', A30)} * 250000 / 470000;")
    # tone stacks
    for nm, pots in (("ts1", ("ch1_treble", "ch1_mid", "ch1_bass", A30, A10)),
                     ("ts2", ("ch2_treble", "ch2_mid", "ch2_bass", A30, A15))):
        pt_, pm_, pl_, at, ab = pots
        B.append(f"if (abs(sm_{pt_} - h_{nm}_ut) + abs(sm_{pm_} - h_{nm}_um) + abs(sm_{pl_} - h_{nm}_ul) > 0.001) {{")
        B.append(f"h_{nm}_ut = sm_{pt_}; h_{nm}_um = sm_{pm_}; h_{nm}_ul = sm_{pl_};")
        B.append(f"pt = clamp({aud(f'(sm_{pt_} - 1) / 9', at)}, 0.002, 0.998);")
        B.append(f"pm1 = clamp((sm_{pm_} - 1) / 9, 0.002, 0.998);")
        B.append(f"pl = clamp({aud(f'(sm_{pl_} - 1) / 9', ab)}, 0.002, 0.998);")
        B.append(stack_coeff_code(nm, "pt", "pm1", "pl"))
        B.append("}")

    # cabinet coefficients (base rate)
    B.append("cb = floor(clamp(cab, 0, 7) + 0.5);")
    B.append("if (cb != h_cabsel) {")
    B.append("h_cabsel = cb; h_cabfade = 0;")
    for ci, (cname, secs) in enumerate(CABS):
        B.append(f"{'if' if ci == 0 else 'else if'} (cb == {ci}) {{")
        B.append(f"h_cabgain = {CAB_MAKEUP[ci]!r};")
        for si in range(NSEC):
            if si < len(secs):
                tp, f, q, g = secs[si]
                B.append(f"wc = 2 * pi * min({float(f)!r}, 0.45 * samplerate) / samplerate; cw = cos(wc); sw = sin(wc); al = sw / (2 * {q!r}); ga = pow(10, {g!r} / 40);")
                if tp == 1:
                    B.append(f"a0 = 1 + al; h_cb{si}_b0 = (1 + cw) / 2 / a0; h_cb{si}_b1 = -(1 + cw) / a0; h_cb{si}_b2 = (1 + cw) / 2 / a0;")
                    B.append(f"h_cb{si}_a1 = -2 * cw / a0; h_cb{si}_a2 = (1 - al) / a0;")
                elif tp == 2:
                    B.append(f"a0 = 1 + al; h_cb{si}_b0 = (1 - cw) / 2 / a0; h_cb{si}_b1 = (1 - cw) / a0; h_cb{si}_b2 = (1 - cw) / 2 / a0;")
                    B.append(f"h_cb{si}_a1 = -2 * cw / a0; h_cb{si}_a2 = (1 - al) / a0;")
                else:
                    B.append(f"a0 = 1 + al / ga; h_cb{si}_b0 = (1 + al * ga) / a0; h_cb{si}_b1 = -2 * cw / a0; h_cb{si}_b2 = (1 - al * ga) / a0;")
                    B.append(f"h_cb{si}_a1 = -2 * cw / a0; h_cb{si}_a2 = (1 - al / ga) / a0;")
            else:
                B.append(f"h_cb{si}_b0 = 1; h_cb{si}_b1 = 0; h_cb{si}_b2 = 0; h_cb{si}_a1 = 0; h_cb{si}_a2 = 0;")
        B.append("}")
    for si in range(NSEC):
        B.append(f"h_cb{si}_x1 = 0; h_cb{si}_x2 = 0; h_cb{si}_y1 = 0; h_cb{si}_y2 = 0;")
    B.append("}")

    # ---- audio
    B.append("x = (in1 + in2) * 0.5 * 2 * dbtoa(sm_p_input);")
    B.append("vbias = 24.1 + (60.3 - 24.1) * sm_power;      // bias supply: club -24.1V / arena -60.3V")
    B.append("vfull = 21.6 + (44.7 - 21.6) * sm_power;      // peak speaker volts at full power (15.3 / 31.6 Vrms)")
    B.append("sagamt = 0.10 - 0.04 * sm_power;")
    B.append("yo = 0;")
    B.append("for (os = 0; os < 2; os = os + 1) {")
    B.append("xin = x;")
    B.append("if (os == 0) { xin = 0.5 * (h_xprev + x); }")
    B.append("// V1A: 68k grid stopper + Miller C")
    B.append(onepole_lp("xin", "h_lp_in", "h_k_in"))
    B.append(lookup("v1a", "xin", 8.0))
    B.append(onepole_hp("xin", "h_v1a_hpx", "h_v1a_hpy", "h_k_hp7"))
    B.append("// ---------- channel 1: bright/volume net -> V2A -> V2B cathode follower -> tone stack")
    B.append("a = xin;")
    B.append(first_order("a", "h_c1_vb0", "h_c1_vb1", "h_c1_va1", "h_c1_vx", "h_c1_vy"))
    B.append("a = a * h_c1_div;")
    B.append(onepole_lp("a", "h_c1_lp", "h_c1_mill"))
    B.append(first_order("a", "h_k_v2a_b0", "h_k_v2a_b1", "h_k_v2a_a1", "h_v2a_sx", "h_v2a_sy"))
    B.append(lookup("v2a", "a", 120.0))
    B.append("a = a * 0.98;")
    B.append(stack_run("ts1", "a"))
    B.append("// ---------- channel 2: gain -> V1B -> R23/C13 -> V3A (cold) -> R28/C15 -> V3B -> V4A CF -> stack -> volume")
    B.append("b = xin * h_c2_gdiv;")
    B.append(onepole_lp("b", "h_c2_lp", "h_c2_mill"))
    B.append(first_order("b", "h_k_v1b_b0", "h_k_v1b_b1", "h_k_v1b_a1", "h_v1b_sx", "h_v1b_sy"))
    B.append(lookup("v1b", "b", 80.0))
    B.append(onepole_hp("b", "h_v1b_hpx", "h_v1b_hpy", "h_k_hp10"))
    B.append(first_order("b", "h_k_n_b0", "h_k_n_b1", "h_k_n_a1", "h_n1x", "h_n1y"))
    B.append(lookup("v3a", "b", 120.0))
    B.append(onepole_hp("b", "h_v3a_hpx", "h_v3a_hpy", "h_k_hp5"))
    B.append(first_order("b", "h_k_n_b0", "h_k_n_b1", "h_k_n_a1", "h_n2x", "h_n2y"))
    B.append(first_order("b", "h_k_v3b_b0", "h_k_v3b_b1", "h_k_v3b_a1", "h_v3b_sx", "h_v3b_sy"))
    B.append(lookup("v3b", "b", 120.0))
    B.append(onepole_lp("b", "h_c16", "h_k_c16"))
    B.append("b = b * 0.98;")
    B.append(stack_run("ts2", "b"))
    B.append("b = b * h_c2_volr;")
    B.append("// ---------- channel relays, fx loop buffers (unity)")
    B.append("pre = a + (b - a) * sm_chsel;")
    B.append(onepole_hp("pre", "h_fx_hpx", "h_fx_hpy", "h_k_hp15"))
    B.append("// ---------- power amp: V6 long-tail PI, 4x6L6GC push-pull, NFB with presence")
    B.append(onepole_hp("pre", "h_pi_hpx", "h_pi_hpy", "h_k_hp7"))
    B.append("pin = pre - h_fb;")
    B.append("vpi = 70 * tanh(27 * pin / 70);")
    B.append(onepole_hp("vpi", "h_pg_hpx", "h_pg_hpy", "h_k_hp34"))
    B.append("u = vpi / vbias;")
    B.append("sagf = 1 - sagamt * min(sqrt(h_env), 1);")
    B.append("pm = 2.6 * sagf;")
    B.append("pz = 1 + u; psp = pz; if (8 * pz < 30) { psp = log(1 + exp(8 * pz)) / 8; }")
    B.append("pp = pow(psp, 1.5); sA = pm * tanh(pp / pm);")
    B.append("pz = 1 - u; psp = pz; if (8 * pz < 30) { psp = log(1 + exp(8 * pz)) / 8; }")
    B.append("pp = pow(psp, 1.5); sB = pm * tanh(pp / pm);")
    B.append("dy = (sA - sB) / 3;")
    B.append(onepole_hp("dy", "h_ot_hpx", "h_ot_hpy", "h_k_hp30"))
    B.append(onepole_lp("dy", "h_ot_lp", "h_k_lpot"))
    B.append("vs = dy * vfull;")
    B.append("fbr = vs * 0.1;")
    B.append(onepole_hp("fbr", "h_pres_x", "h_pres_y", "h_k_pres"))
    B.append("h_fb = vs * 0.1 - ((sm_presence - 1) / 9) * h_pres_y;")
    B.append("if (dy * dy > h_env) { h_env = h_env + h_k_att * (dy * dy - h_env); } else { h_env = h_env + h_k_rel * (dy * dy - h_env); }")
    B.append("y = vs / 44.7;")
    B.append("// decimation filter")
    B.append("ysec = h_dc_b0 * y + h_dc_b1 * h_d1x1 + h_dc_b2 * h_d1x2 - h_dc_a1 * h_d1y1 - h_dc_a2 * h_d1y2;")
    B.append("h_d1x2 = h_d1x1; h_d1x1 = y; h_d1y2 = h_d1y1; h_d1y1 = ysec; y = ysec;")
    B.append("ysec = h_dc2_b0 * y + h_dc2_b1 * h_d2x1 + h_dc2_b2 * h_d2x2 - h_dc2_a1 * h_d2y1 - h_dc2_a2 * h_d2y2;")
    B.append("h_d2x2 = h_d2x1; h_d2x1 = y; h_d2y2 = h_d2y1; h_d2y1 = ysec; yo = ysec;")
    B.append("}")
    B.append("h_xprev = x;")
    B.append("// ---------- cabinet")
    B.append("y = yo;")
    for si in range(NSEC):
        B.append(f"ysec = h_cb{si}_b0 * y + h_cb{si}_b1 * h_cb{si}_x1 + h_cb{si}_b2 * h_cb{si}_x2 - h_cb{si}_a1 * h_cb{si}_y1 - h_cb{si}_a2 * h_cb{si}_y2;")
        B.append(f"h_cb{si}_x2 = h_cb{si}_x1; h_cb{si}_x1 = y; h_cb{si}_y2 = h_cb{si}_y1; h_cb{si}_y1 = ysec; y = ysec;")
    B.append("h_cabfade = min(h_cabfade + 0.0005, 1);")
    B.append("cg = h_cabgain * h_cabfade * (1 - sm_standby) * dbtoa(sm_p_output);")
    B.append("y = y * cg;")
    B.append("out1 = y;")
    B.append("out2 = y;")
    return "\n".join(L) + "\n\n" + "\n".join(B) + "\n"

if __name__ == "__main__":
    code = generate()
    open("t100.genexpr", "w").write(code)
    print(len(code), "chars;", "cab makeup:", [round(x, 3) for x in CAB_MAKEUP])
