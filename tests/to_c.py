import re,sys
src=open(sys.argv[1]).read()
glob=[];body=[];params=[]
for line in src.split('\n'):
    mP=re.match(r'Param (\w+)\(([-\d.e]+)',line); mD=re.match(r'Data (\w+)\((\d+)\)',line); mH=re.match(r'History (\w+)\(([-\d.e]+)\)',line)
    if mP: glob.append(f'double {mP[1]} = {mP[2]};'); params.append(mP[1])
    elif mD: glob.append(f'static double {mD[1]}[{mD[2]}];')
    elif mH: glob.append(f'static double {mH[1]} = {mH[2]};')
    else: body.append(line)
b='\n'.join(body)
gl={re.match(r'.*?(\w+)\s*(=|\[)',g)[1] for g in glob}
names=set(re.findall(r'\b([A-Za-z_]\w*)\s*=(?!=)',b))-gl-{'out1','out2'}
c='''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define peek(d,i) (d[(int)(i)])
#define poke(d,v,i) (d[(int)(i)]=(v))
#define clamp(x,a,b) fmin(fmax((x),(a)),(b))
#define dbtoa(x) pow(10.0,(x)/20.0)
#define abs fabs
#define min fmin
#define fixnan(x) (isnan(x)?0.0:(x))
#define max fmax
#define pi 3.14159265358979323846
double samplerate=48000;
'''+'\n'.join(glob)+'''
void tick(double in1,double in2,double*o1,double*o2){
double out1=0,out2=0;
double '''+', '.join(sorted(names))+''';
'''+b+'''
*o1=out1;*o2=out2;}
int main(int argc,char**argv){
 for(int k=1;k<argc;k++){char*e=strchr(argv[k],'=');*e=0;double v=atof(e+1);
'''+'\n'.join(f'  if(!strcmp(argv[k],"{p}")){p}=v;' for p in params)+'''
  if(!strcmp(argv[k],"sr"))samplerate=v;}
 double x,o1,o2;
 while(fread(&x,8,1,stdin)==1){tick(x,x,&o1,&o2);fwrite(&o1,8,1,stdout);}
 return 0;}
'''
open(sys.argv[2],'w').write(c)
