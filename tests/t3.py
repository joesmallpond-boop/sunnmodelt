from run import *
fr=[60,150,400,800,1500,3000,6000]
def resp(**p):
    out=[]
    for f in fr:
        y=run(sine(f,0.002,0.4),**p); yy=y[len(y)//2:]; out.append(20*np.log10(np.sqrt(np.mean(yy**2))+1e-12))
    return np.array(out)
base=dict(channel=0,ch1_vol=2)
ref=resp(**base,cab=0)
print('freqs',fr); print('ch1 flat5.5',np.round(ref-ref[3],1))
for k in ('ch1_treble','ch1_bass','ch1_mid'):
    for v in (1,10):
        r=resp(**base,cab=0,**{k:v}); print(k,v,np.round(r-ref,1))
base2=dict(channel=1,ch2_gain=1)
ref2=resp(**base2,cab=0); print('ch2 flat',np.round(ref2-ref2[3],1))
for k in ('ch2_treble','ch2_bass','ch2_mid'):
    for v in (1,10):
        r=resp(**base2,cab=0,**{k:v}); print(k,v,np.round(r-ref2,1))
for v in (1,10):
    r=resp(**base,cab=0,presence=v); print('presence',v,np.round(r-ref,1))
for c in range(8):
    r=resp(**base,cab=c); print('cab',c,np.round(r-ref,1))
