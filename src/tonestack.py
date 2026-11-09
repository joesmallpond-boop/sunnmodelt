import sympy as sp
s,t,m,l = sp.symbols('s t m l')
def derive(R1,R2,R3,R4,C1,C2,C3,Rs,RL):
    # Model T wiring (service manual): mid cap goes to the MID POT WIPER; the bass rheostat
    # feeds the TOP of the mid pot (Mt); mid pot bottom to ground.
    S,A,O,B,X,M,W = sp.symbols('S A O B X M W')
    Vin=1
    g = lambda R: 1/R
    yC = lambda C: s*C
    # KCL at each node: sum of currents leaving = 0
    eqs = [
      (S-Vin)*g(Rs) + (S-A)*yC(C1) + (S-X)*g(R4),
      (A-S)*yC(C1) + (A-O)*g((1-t)*R1),
      (O-A)*g((1-t)*R1) + (O-B)*g(t*R1) + O*g(RL),
      (B-O)*g(t*R1) + (B-X)*yC(C2) + (B-M)*g(l*R2),
      (X-S)*g(R4) + (X-B)*yC(C2) + (X-W)*yC(C3),
      (M-B)*g(l*R2) + (M-W)*g((1-m)*R3),
      (W-M)*g((1-m)*R3) + (W-X)*yC(C3) + W*g(m*R3),
    ]
    sol = sp.solve(eqs,[S,A,O,B,X,M,W],dict=True)[0]
    H = sp.cancel(sp.together(sol[O]))
    num,den = sp.fraction(H)
    num = sp.Poly(sp.expand(num), s); den = sp.Poly(sp.expand(den), s)
    return num, den
if __name__=='__main__':
    n,d = derive(250e3,1e6,25e3,68e3,470e-12,22e-9,22e-9,600,1e6)
    print(n.degree(), d.degree())
    print([sp.Poly(c,t,m,l).total_degree() for c in d.all_coeffs()])

def derive_nfb(R107=150e3, C41=4.7e-9, R108=47e3, R109=4.7e3, C43=0.1e-6):
    """Feedback network from the speaker output to the PI feedback node (TP52); Rp = presence rheostat."""
    Rp = sp.Symbol('Rp')
    F, G, P = sp.symbols('F G P')
    Vs = 1
    z107 = 1 / (1 / R107 + s * C41)
    eqs = [(F - Vs) / z107 + (F - G) / R108,
           (G - F) / R108 + G / R109 + (G - P) * s * C43,
           (P - G) * s * C43 + P / Rp]
    sol = sp.solve(eqs, [F, G, P], dict=True)[0]
    H = sp.cancel(sp.together(sol[G]))
    num, den = sp.fraction(H)
    return sp.Poly(sp.expand(num), s), sp.Poly(sp.expand(den), s), Rp
