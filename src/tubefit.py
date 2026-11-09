"""Fit each 12AX7 stage's load-line transfer curve (Koren model) with a loop-free formula:
   y = sum c_k T_k(tanh(x / s))   (Chebyshev series, evaluated with an unrolled Clenshaw recurrence)."""
import math, numpy as np
MU, EX, KG1, KP, KVB = 100.0, 1.4, 800.0, 600.0, 300.0
def ip(vpk, vgk):
    if vpk <= 0: return 0.0
    z = KP * (1 / MU + vgk / math.sqrt(KVB + vpk * vpk))
    sp = z if z > 30 else math.log1p(math.exp(z))
    e1 = vpk / KP * sp
    return e1 ** EX / KG1 if e1 > 0 else 0.0
def stage_curve(B, RL, RK, RS, unb, vmax, RAC, n=1201):
    def solve(vin, vk0, iq, vp0, dc):
        a = RS / (RS + 1500.0)
        lo, hi = 0.0, (B / (RL + RK) if dc else iq + vp0 / RAC)
        for _ in range(60):
            m = 0.5 * (lo + hi)
            vk = m * RK if (unb or dc) else vk0
            x = vin - vk
            spx = x if 5 * x > 30 else math.log1p(math.exp(5 * x)) / 5
            vg = vin - a * spx
            vp = (B - m * RL) if dc else (vp0 - (m - iq) * RAC)
            if m - ip(vp - vk, vg - vk) > 0: hi = m
            else: lo = m
        return m, ((B - m * RL) if dc else (vp0 - (m - iq) * RAC))
    iq, vp0 = solve(0.0, 0.0, 0, 0, True)
    vk0 = iq * RK
    xs = np.linspace(-vmax, vmax, n)
    ys = np.array([solve(v, vk0, iq, vp0, False)[1] for v in xs]) - vp0
    return xs, ys
def fit(xs, ys, deg):
    best = None
    vmax = xs[-1]
    for s in np.linspace(0.15, 1.2, 36) * vmax:
        t = np.tanh(xs / s)
        c = np.polynomial.chebyshev.chebfit(t, ys, deg)
        e = np.max(np.abs(np.polynomial.chebyshev.chebval(t, c) - ys))
        if best is None or e < best[0]: best = (e, s, c)
    return best
def clenshaw_code(var_in, var_out, s, c, prefix):
    lines = [f"{prefix}t = tanh({var_in} / {s!r});", f"{prefix}t2 = 2 * {prefix}t;",
             f"{prefix}b1 = 0; {prefix}b2 = 0; {prefix}b0 = 0;"]
    for k in range(len(c) - 1, 0, -1):
        lines.append(f"{prefix}b0 = {float(c[k])!r} + {prefix}t2 * {prefix}b1 - {prefix}b2; {prefix}b2 = {prefix}b1; {prefix}b1 = {prefix}b0;")
    lines.append(f"{var_out} = {float(c[0])!r} + {prefix}t * {prefix}b1 - {prefix}b2;")
    return "\n".join(lines)
if __name__ == "__main__":
    from gen_dsp import STAGES
    for st in STAGES:
        xs, ys = stage_curve(*st[1:])
        for deg in (12, 16, 20, 24):
            e, s, c = fit(xs, ys, deg)
            print(st[0], deg, "max err %.3f V of swing %.0f V (%.2f%%), s=%.2f, c0=%.3f" % (e, ys.max() - ys.min(), 100 * e / (ys.max() - ys.min()), s, c[0]))

C = np.polynomial.chebyshev
WARPS = {"alg": lambda x, s: x / np.sqrt(x * x + s * s), "rat": lambda x, s: x / (np.abs(x) + s)}
_cache = {}
def best_fit(st, deg=32):
    import warnings
    if st[0] in _cache: return _cache[st[0]]
    xs, ys = stage_curve(*st[1:], n=2401)
    best = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for wn, wf in WARPS.items():
            for s in np.geomspace(0.2, 60, 60):
                t = wf(xs, s); norm = 1 / np.max(np.abs(t)); t = t * norm
                c = C.chebfit(t, ys, deg)
                e = np.max(np.abs(C.chebval(t, c) - ys))
                if best is None or e < best[0]: best = (e, wn, float(s), float(norm), c)
    e, wn, s, norm, c = best
    c = c.copy(); c[0] -= C.chebval(0.0, c)          # quiescent point -> 0 V
    _cache[st[0]] = (wn, s, norm, c, e / (ys.max() - ys.min()))
    return _cache[st[0]]
def stage_code(st, var):
    wn, s, norm, c, rel = best_fit(st)
    p = "tb_"
    if wn == "alg":
        w = f"{p}t = {var} / sqrt({var} * {var} + {s!r}) * {norm!r};".replace(f"+ {s!r})", f"+ {s*s!r})")
    else:
        w = f"{p}t = {var} / (abs({var}) + {s!r}) * {norm!r};"
    lines = [f"// {st[0]} 12AX7 curve (Koren load-line, Chebyshev fit, max err {100*rel:.2f}%)", w,
             f"{p}t = clamp({p}t, -1, 1); {p}t2 = 2 * {p}t; {p}b1 = 0; {p}b2 = 0;"]
    for k in range(len(c) - 1, 0, -1):
        lines.append(f"{p}b0 = {float(c[k])!r} + {p}t2 * {p}b1 - {p}b2; {p}b2 = {p}b1; {p}b1 = {p}b0;")
    lines.append(f"{var} = {float(c[0])!r} + {p}t * {p}b1 - {p}b2;")
    return "\n".join(lines)
