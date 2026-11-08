import numpy as np, subprocess, time
def run(x, **p):
    args=['./t100']+[f'{k}={v}' for k,v in p.items()]
    r=subprocess.run(args,input=np.asarray(x,np.float64).tobytes(),capture_output=True)
    return np.frombuffer(r.stdout,np.float64)
fs=48000
def sine(f,amp,dur=0.6): t=np.arange(int(fs*dur))/fs; return amp*np.sin(2*np.pi*f*t)
def thd(y,f):
    y=y[len(y)//2:]; w=np.hanning(len(y)); Y=np.abs(np.fft.rfft(y*w)); fr=np.fft.rfftfreq(len(y),1/fs)
    h=[Y[np.argmin(abs(fr-f*k))] for k in range(1,8)]; return np.sqrt(sum(v*v for v in h[1:]))/h[0]
if __name__=='__main__':
    t0=time.time(); y=run(np.zeros(4800)); print('init+4800 samples %.2fs'%(time.time()-t0), 'nan' if np.isnan(y).any() else 'ok')
    for ch in (0,1):
        for amp in (0.01,0.05,0.2,0.5):
            for cab in (0,):
                y=run(sine(440,amp),chsel=ch,cab=cab)
                yy=y[len(y)//2:]
                print(f'ch{ch+1} in={amp:5} peak={np.max(abs(yy)):.3f} rms={np.sqrt(np.mean(yy**2)):.3f} thd={thd(y,440)*100:6.1f}%')
