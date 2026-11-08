from run import *
for g in (0,1,2,3,5,8,10):
    y=run(sine(440,0.05),chsel=1,ch2_gain=g); yy=y[len(y)//2:]
    print(f'ch2 gain {g}: rms={np.sqrt(np.mean(yy**2)):.3f} thd={thd(y,440)*100:5.1f}%')
imp=np.zeros(fs); imp[100]=1.0
for pres in (0,10):
  for pw in (0,1):
    for ch in (0,1):
        y=run(imp,presence=pres,power=pw,chsel=ch,cab=0,ch2_gain=0)
        tail=np.max(abs(y[fs//2:])); print(f'pres={pres} power={pw} ch={ch}: peak={np.max(abs(y)):.4f} tail={tail:.2e}')
# full-on stress: loud noise then silence
rng=np.random.default_rng(0); n=np.concatenate([rng.standard_normal(fs)*0.8,np.zeros(fs)])
for pw in (0,1):
    y=run(n,ch1_vol=10,ch2_vol=10,ch2_gain=10,presence=10,power=pw,chsel=1)
    print('stress power',pw,'max',np.max(abs(y)),'tail',np.max(abs(y[-fs//2:])), 'nan',np.isnan(y).any())
