import re, json, struct
from PIL import Image, ImageDraw, ImageFont
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src')); import build_amxd as B
S=2
im=Image.new('RGB',(B.W*S,B.H*S)); d=ImageDraw.Draw(im)
col=(0,0,0); size=9; bold=False; pos=(0,0)
def F(sz,b):
    try: return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'%('-Bold' if b else ''),int(sz*S))
    except: return ImageFont.load_default()
for c in B.cmds:
    a=c.split(' '); op=a[0]
    if op in('paintrect','paintoval','frameoval'):
        l,t,r,b,R,G,Bc=map(float,a[1:8]); box=[l*S,t*S,r*S-1,b*S-1]
        if op=='paintrect': d.rectangle(box,fill=(int(R),int(G),int(Bc)))
        elif op=='paintoval': d.ellipse(box,fill=(int(R),int(G),int(Bc)))
        else: d.ellipse(box,outline=(int(R),int(G),int(Bc)))
    elif op=='linesegment':
        x1,y1,x2,y2,R,G,Bc=map(float,a[1:8]); d.line([x1*S,y1*S,x2*S,y2*S],fill=(int(R),int(G),int(Bc)),width=S)
    elif op=='frgb': col=tuple(map(int,a[1:4]))
    elif op=='font': size=float(a[2])
    elif op=='textface': bold=a[1]=='bold'
    elif op=='moveto': pos=(float(a[1]),float(a[2]))
    elif op=='write':
        f=F(size,bold); txt=' '.join(a[1:]); d.text((pos[0]*S,pos[1]*S),txt,fill=col,font=f,anchor='ls')
# overlay controls
for b in B.boxes:
    b=b['box']
    if not b.get('presentation') or b['maxclass']=='lcd': continue
    x,y,w,h=[v*S for v in b['presentation_rect']]
    mc=b['maxclass']
    if mc=='live.dial':
        vo=b['saved_attribute_attributes']['valueof']; v=vo['parameter_initial'][0]; f=(v-vo['parameter_mmin'])/(vo['parameter_mmax']-vo['parameter_mmin'])
        import math
        if b.get('showname')==0:
            cx,cy=x+w/2,y+h/2; ang=math.radians(-150+300*f)-math.pi/2
            d.line([cx,cy,cx+10*S*math.cos(ang),cy+10*S*math.sin(ang)],fill=(250,250,250),width=2*S)
        else:
            d.text((x+w/2,y+6*S),vo['parameter_longname'],fill=(200,200,200),font=F(9,False),anchor='mm')
            d.arc([x+w/2-14*S,y+14*S,x+w/2+14*S,y+42*S],120,120+300*f,fill=(255,160,40),width=2*S)
            d.arc([x+w/2-14*S,y+14*S,x+w/2+14*S,y+42*S],120+300*f,420,fill=(90,90,90),width=2*S)
            d.text((x+w/2,y+h-4*S),'%.1f dB'%v,fill=(200,200,200),font=F(9,False),anchor='mm')
    elif mc=='live.text':
        d.rectangle([x,y,x+w,y+h],fill=(40,40,40),outline=(120,120,120)); d.text((x+w/2,y+h/2),b['texton'] if b['saved_attribute_attributes']['valueof']['parameter_initial'][0] else b['text'],fill=(230,230,230),font=F(b.get('fontsize',9),False),anchor='mm')
    elif mc=='panel':
        d.ellipse([x,y,x+w,y+h],fill=(240,30,20))
    elif mc=='live.menu':
        d.rectangle([x,y,x+w,y+h],fill=(30,30,30),outline=(90,90,90)); d.text((x+4*S,y+h/2),B.CAB_NAMES[1]+'  ▾',fill=(230,230,230),font=F(9,False),anchor='lm')
    elif mc=='live.tab':
        d.rectangle([x,y,x+w/2,y+h],fill=(70,70,70)); d.rectangle([x+w/2,y,x+w,y+h],fill=(255,160,40))
        d.text((x+w/4,y+h/2),'Club 25W',fill=(230,230,230),font=F(8,False),anchor='mm'); d.text((x+3*w/4,y+h/2),'Arena 100W',fill=(20,20,20),font=F(8,False),anchor='mm')
im.save('preview.png')
