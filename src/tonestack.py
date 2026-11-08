import sympy as sp
s,t,m,l = sp.symbols('s t m l')
def derive(R1,R2,R3,R4,C1,C2,C3,Rs,RL):
    S,A,O,B,X,M = sp.symbols('S A O B X M')
    Vin=1
    g = lambda R: 1/R
    yC = lambda C: s*C
    # KCL at each node: sum of currents leaving = 0
    eqs = [
      (S-Vin)*g(Rs) + (S-A)*yC(C1) + (S-X)*g(R4),
      (A-S)*yC(C1) + (A-O)*g((1-t)*R1),
      (O-A)*g((1-t)*R1) + (O-B)*g(t*R1) + O*g(RL),
      (B-O)*g(t*R1) + (B-X)*yC(C2) + (B-M)*g(l*R2),
      (X-S)*g(R4) + (X-B)*yC(C2) + (X-M)*yC(C3),
      (M-B)*g(l*R2) + (M-X)*yC(C3) + M*g(m*R3),
    ]
    sol = sp.solve(eqs,[S,A,O,B,X,M],dict=True)[0]
    H = sp.cancel(sp.together(sol[O]))
    num,den = sp.fraction(H)
    num = sp.Poly(sp.expand(num), s); den = sp.Poly(sp.expand(den), s)
    return num, den
if __name__=='__main__':
    n,d = derive(250e3,1e6,25e3,68e3,470e-12,22e-9,22e-9,600,1e6)
    print(n.degree(), d.degree())
    print([sp.Poly(c,t,m,l).total_degree() for c in d.all_coeffs()])
