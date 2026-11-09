import re, math
code=open('../src/t100.genexpr').read()
def block(nm):
    i=code.index(f'Lh_{nm}_ut = Lsm_'); j=code.index(f'Lh_{nm}_a3 = ',i); j=code.index(';',j)+1; return code[i:j]
tokre=re.compile(r'\s*(\d+\.\d*|\d+|[A-Za-z_]\w*|\*\*|[-+*/(),=<>])')
def tokenize(s):
    out=[];pos=0;s=s.strip()
    while pos<len(s):
        m=tokre.match(s,pos)
        if not m: raise ValueError(s[pos:pos+20])
        out.append(m.group(1)); pos=m.end()
    return out
class P:
    def __init__(s,toks,env,mode): s.t=toks;s.i=0;s.env=env;s.mode=mode
    def peek(s): return s.t[s.i] if s.i<len(s.t) else None
    def nx(s): s.i+=1; return s.t[s.i-1]
    def expr(s):
        if s.mode.get('rightassoc'):
            a=s.term()
            if s.peek() in('+','-'):
                op=s.nx(); b=s.expr(); return a+b if op=='+' else a-b
            return a
        a=s.term()
        while s.peek() in('+','-'):
            op=s.nx(); b=s.term(); a=a+b if op=='+' else a-b
        return a
    def term(s):
        a=s.unary()
        while s.peek() in('*','/'):
            op=s.nx(); b=s.unary(); a=a*b if op=='*' else a/b
        return a
    def unary(s):
        if s.peek()=='-':
            s.nx()
            if s.mode.get('neg_low'):
                return -s.term()
            if s.mode.get('neg_drop_paren') and s.peek()=='(':
                return s.unary()
            return -s.unary()
        return s.atom()
    def atom(s):
        t=s.nx()
        if t=='(':
            v=s.expr(); assert s.nx()==')'; return v
        if re.match(r'\d',t):
            v=float(t)
            if s.mode.get('f32lit'):
                import numpy as np; v=float(np.float32(v))
            return v
        if s.peek()=='(':
            s.nx(); args=[s.expr()]
            while s.peek()==',': s.nx(); args.append(s.expr())
            assert s.nx()==')'
            return {'pow':pow,'clamp':lambda x,a,b:min(max(x,a),b),'abs':abs}[t](*args)
        return s.env[t]
def run(nm,mode,fs=48000,knob=5.5):
    env={'fs2':2*fs}
    knobs={'ts1':('ch1_treble','ch1_mid','ch1_bass'),'ts2':('ch2_treble','ch2_mid','ch2_bass')}[nm]
    for k in knobs: env['Lsm_'+k]=knob
    for st in block(nm).split(';'):
        st=re.sub(r'//.*','',st).strip()
        if not st: continue
        lhs,rhs=st.split('=',1)
        p=P(tokenize(rhs),env,mode); env[lhs.strip()]=p.expr()
    return env[f'Lh_{nm}_a1']
for name,mode in [('normal',{}),('rightassoc',{'rightassoc':1}),('neg_low',{'neg_low':1}),('neg_drop',{'neg_drop_paren':1}),('f32',{'f32lit':1})]:
    print(name,[round(run(nm,mode),6) for nm in ('ts1','ts2')],'gen: -0.657197 -0.451312')

def run2(nm,over,fs=48000):
    env={'fs2':2*fs}
    knobs={'ts1':('ch1_treble','ch1_mid','ch1_bass'),'ts2':('ch2_treble','ch2_mid','ch2_bass')}[nm]
    for k in knobs: env['Lsm_'+k]=5.5
    for st in block(nm).split(';'):
        st=re.sub(r'//.*','',st).strip()
        if not st: continue
        lhs,rhs=st.split('=',1); lhs=lhs.strip()
        env[lhs]=P(tokenize(rhs),env,{}).expr()
        if lhs in over: env[lhs]=over[lhs]
    return env[f'Lh_{nm}_a1']
import itertools
cands=[0.0,0.002,0.998,1.0,-1.0,2.0,5.5,0.5,4.5,10.0,48000.0,44100.0,96000.0]
res=[]
for pt,pm,pl in itertools.product(cands,repeat=3):
    o={'pt':pt,'pm1':pm,'pl':pl}
    try:
        a=run2('ts1',o); b=run2('ts2',o)
    except ZeroDivisionError: continue
    res.append((abs(a+0.657197)+abs(b+0.451312),pt,pm,pl,a,b))
res.sort(); print(res[:5])
