import numpy as np, math, json
from scipy.optimize import least_squares
from scipy.signal import freqz
from gen_dsp import rbj
fs=48000
T={
 "4x12 Greenback":[(50,-9),(70,-3),(100,2),(200,0),(400,-2),(1000,0),(2000,4),(3000,3),(4000,0),(5000,-4),(6000,-10),(8000,-24),(10000,-35),(14000,-45)],
 "4x12 V30":[(50,-9),(70,-3),(120,3),(250,0),(500,-2),(1000,0),(1500,2),(2500,3),(3500,6),(4500,1),(6000,-8),(8000,-22),(10000,-35),(14000,-45)],
 "1x15 Bass":[(30,-9),(45,-2),(80,5),(200,1),(500,-3),(1000,0),(1500,2),(2500,-3),(3500,-15),(5000,-30),(8000,-45)],
 "2x12 V30":[(50,-14),(70,-6),(130,2),(300,0),(1000,0),(2000,2),(3300,5),(4500,0),(6000,-8),(8000,-22),(10000,-34),(14000,-45)],
 "2x10":[(50,-18),(80,-7),(150,1),(400,0),(1000,0),(2000,3),(4000,3),(6000,-4),(8000,-15),(10000,-28),(14000,-42)],
 "1x12 Open":[(50,-16),(70,-8),(150,0),(400,0),(900,-2),(1500,1),(2500,4),(4000,0),(5500,-8),(8000,-25),(11000,-38)],
 "1x8":[(70,-20),(120,-10),(250,0),(500,1),(1000,3),(2000,1),(3000,2),(4500,-8),(6000,-20),(9000,-36)],
}
types=[1,3,3,3,3,2,2,2]
def resp(params,f):
    H=np.ones(len(f),complex)
    for tp,(fc,q,g) in zip(types,params.reshape(-1,3)):
        b,a=rbj(tp,fc,q,g,fs); _,h=freqz(b,a,worN=f,fs=fs); H*=h
    return 20*np.log10(abs(H))
out={}
for name,tg in T.items():
    tf=np.array([p[0] for p in tg],float); tv=np.array([p[1] for p in tg],float)
    f=np.geomspace(max(30,tf[0]),min(tf[-1],20000),120); tgt=np.interp(np.log(f),np.log(tf),tv)
    i1k=np.argmin(abs(f-1000))
    # init
    peaks=sorted(tg,key=lambda p:-abs(p[1]) if 150<p[0]<5000 else 0)[:4]
    x0=[tf[1],0.8,0]+sum([[p[0],1.2,p[1]] for p in sorted(peaks)],[])+[5000,0.7,0,6500,0.7,0,8000,0.6,0]
    lo=[20,0.4,-0.01]+[60,0.3,-12]*4+[1500,0.4,-0.01]*3; hi=[400,2,0.01]+[9000,6,12]*4+[16000,3,0.01]*3
    x0=np.clip(x0,np.array(lo)+1e-6,np.array(hi)-1e-6)
    def err(x):
        r=resp(np.array(x),f); return (r-r[i1k])-tgt
    sol=least_squares(err,x0,bounds=(lo,hi))
    p=sol.x.reshape(-1,3); rms=np.sqrt(np.mean(sol.fun**2))
    print(name,'rms err %.2f dB'%rms)
    out[name]=[(t,round(float(a),1),round(float(b),3),round(float(c),2)) for t,(a,b,c) in zip(types,p)]
json.dump(out,open('cabs.json','w'),indent=0)
