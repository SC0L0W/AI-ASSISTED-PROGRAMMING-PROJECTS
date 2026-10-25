"""
NSCP 2015 (7th Ed.) Response Spectrum Analysis - shear-building model
Run:  pip install numpy   then   python nscp_rsa.py   (opens http://localhost:8000)
Methods: (1) NSCP 208 (Z, soil, near-source Na/Nv, Ca/Cv)  (2) Spectral-map mode (Ss, S1, Fa, Fv)
NOTE: Preliminary-design tool. Verify all coefficients against your copy of the code.
"""
import json, webbrowser, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np

G = 9.81
CA = {0.4: dict(A=.32, B=.40, C=.40, D=.44, E=.44), 0.2: dict(A=.16, B=.20, C=.24, D=.28, E=.34)}
CV = {0.4: dict(A=.32, B=.40, C=.56, D=.64, E=.96), 0.2: dict(A=.16, B=.20, C=.32, D=.40, E=.64)}
NA = {'A': ([2, 5, 10], [1.5, 1.2, 1.0]), 'B': ([2, 5, 10], [1.3, 1.0, 1.0]), 'C': ([2, 5, 10], [1, 1, 1])}
NV = {'A': ([2, 5, 10, 15], [2.0, 1.6, 1.2, 1.0]), 'B': ([2, 5, 10, 15], [1.6, 1.2, 1.0, 1.0]), 'C': ([2, 5, 10, 15], [1, 1, 1, 1])}
FA = {'A': [.8]*5, 'B': [1.0]*5, 'C': [1.2, 1.2, 1.1, 1.0, 1.0], 'D': [1.6, 1.4, 1.2, 1.1, 1.0], 'E': [2.5, 1.7, 1.2, .9, .9]}
FV = {'A': [.8]*5, 'B': [1.0]*5, 'C': [1.7, 1.6, 1.5, 1.4, 1.3], 'D': [2.4, 2.0, 1.8, 1.6, 1.5], 'E': [3.5, 3.2, 2.8, 2.4, 2.4]}
CT = {'steel': .0853, 'concrete': .0731, 'other': .0488}


def spectrum_params(p):
    """Return dict a0 (Sa at T=0), ap (plateau), cv (long-period constant) in g + info."""
    soil, I = p['soil'], p['I']
    if p['method'] == 'nscp':
        Z = p['Z']; info = {}
        if Z == 0.4:
            na = float(np.interp(p['dist'], *NA[p['source']])); nv = float(np.interp(p['dist'], *NV[p['source']]))
        else:
            na = nv = 1.0
        ca, cv = CA[Z][soil] * (na if Z == .4 else 1), CV[Z][soil] * (nv if Z == .4 else 1)
        info = dict(Z=Z, Na=na, Nv=nv, Ca=ca, Cv=cv)
        return dict(a0=ca, ap=2.5*ca, cv=cv, info=info, Ca=ca, Cv=cv, Z=Z, Nv=nv)
    ss, s1 = p['Ss'], p['S1']
    fa = float(np.interp(ss, [.25, .5, .75, 1, 1.25], FA[soil])); fv = float(np.interp(s1, [.1, .2, .3, .4, .5], FV[soil]))
    sds, sd1 = 2/3*fa*ss, 2/3*fv*s1
    return dict(a0=.4*sds, ap=sds, cv=sd1, Ca=None, Z=None, info=dict(Ss=ss, S1=s1, Fa=fa, Fv=fv, SDS=sds, SD1=sd1))


def sa(T, sp):
    Ts = sp['cv']/sp['ap']; T0 = .2*Ts
    T = np.asarray(T, float)
    return np.where(T < T0, sp['a0'] + (sp['ap']-sp['a0'])*T/T0, np.where(T <= Ts, sp['ap'], sp['cv']/np.maximum(T, 1e-9)))


BASE_PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>NSCP 2015 Response Spectrum Analysis</title>
<style>
:root{--bg:#f6f7f9;--c:#fff;--t:#1d2733;--m:#667;--b:#d9dee5;--a:#0b5cab;--ok:#18794e;--no:#c62828}
@media(prefers-color-scheme:dark){:root{--bg:#10151b;--c:#19212a;--t:#e6ebf0;--m:#97a3b0;--b:#2b3744;--a:#5aa7f0;--ok:#4cc38a;--no:#ff7b72}}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--t)}
header{padding:16px 24px;background:var(--a);color:#fff}header h1{margin:0;font-size:20px}header p{margin:2px 0 0;opacity:.85;font-size:12px}
main{display:grid;grid-template-columns:330px 1fr;gap:16px;padding:16px;max-width:1500px;margin:auto}
@media(max-width:900px){main{grid-template-columns:1fr}}
.card{background:var(--c);border:1px solid var(--b);border-radius:8px;padding:14px;margin-bottom:14px}
h2{font-size:14px;margin:0 0 10px;color:var(--a)}label{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:5px 0;color:var(--m)}
input,select{width:140px;padding:4px 6px;border:1px solid var(--b);border-radius:4px;background:var(--bg);color:var(--t)}
button{width:100%;padding:10px;background:var(--a);color:#fff;border:0;border-radius:6px;font-weight:600;cursor:pointer}
table{border-collapse:collapse;width:100%;font-size:12px}th,td{border-bottom:1px solid var(--b);padding:4px 6px;text-align:right}th{color:var(--m)}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}.kv div{background:var(--bg);padding:8px;border-radius:6px}
.kv b{display:block;font-size:17px}.kv span{color:var(--m);font-size:11px}.ok{color:var(--ok)}.no{color:var(--no)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:14px}canvas{width:100%;height:300px}
.scroll{overflow-x:auto}small{color:var(--m)}
</style></head><body>
<header><h1>Response Spectrum Analysis &mdash; NSCP 2015 (7th Ed.) Sec. 208</h1><p>Multi-storey shear-building model &bull; modal analysis &bull; CQC combination &bull; static base-shear scaling &bull; drift check</p></header>
<main><aside>
<div class="card"><h2>Seismic Hazard</h2>
<label>Method<select id="method" onchange="tog()"><option value="nscp">NSCP 208 (Zone/Ca/Cv)</option><option value="map">Spectral map (Ss, S1)</option></select></label>
<div id="nscp"><label>Seismic zone Z<select id="Z"><option value="0.4">Zone 4 (Z=0.40)</option><option value="0.2">Zone 2 (Z=0.20)</option></select></label>
<label>Fault source type<select id="source"><option>A</option><option selected>B</option><option>C</option></select></label>
<label>Dist. to fault (km)<input id="dist" type="number" value="10"></label></div>
<div id="map" style="display:none"><label>Ss (g) from map<input id="Ss" type="number" step=".01" value="1.5"></label><label>S1 (g) from map<input id="S1" type="number" step=".01" value="0.6"></label>
<small>Enter MCE/design-level values read from your hazard map (PHIVOLCS/ASEP PSHA). Fa, Fv per ASCE 7-10 tables; SDS=&#8532;FaSs.</small></div>
<label>Soil profile<select id="soil"><option value="A">S<sub>A</sub></option><option>B</option><option>C</option><option selected>D</option><option>E</option></select></label>
<label>Importance I<select id="I"><option value="1">Standard 1.00</option><option value="1.25">Special 1.25</option><option value="1.5">Essential 1.50</option></select></label></div>
<div class="card"><h2>Structure</h2>
<label>System<select id="sys"><option value="concrete">Concrete MRF</option><option value="steel">Steel MRF</option><option value="other">Other / Dual</option></select></label>
<label>R factor<select id="R"><option value="8.5">SMRF / Dual 8.5</option><option value="5.5">IMRF 5.5</option><option value="4.5">OMRF 4.5</option><option value="4.5">Shear wall (bearing) 4.5</option></select></label>
<label>No. of storeys<input id="n" type="number" value="10" min="1" max="60"></label>
<label>1st storey h (m)<input id="h1" type="number" step=".1" value="4.0"></label><label>Typical h (m)<input id="h" type="number" step=".1" value="3.2"></label>
<label>Typ. floor weight (kN)<input id="W" type="number" value="4000"></label><label>Roof weight (kN)<input id="Wr" type="number" value="3200"></label>
<label>Typ. storey stiffness (kN/m)<input id="k" type="number" value="400000"></label><label>1st storey k factor<input id="k1f" type="number" step=".1" value="1.2"></label>
<label>Damping &xi;<input id="xi" type="number" step=".01" value="0.05"></label>
<label>Irregular structure?<select id="irr"><option value="0">No (scale to 90% V)</option><option value="1">Yes (scale to 100% V)</option></select></label>
<label>Static T limit<select id="useT1"><option value="1">min(T1, Cu&middot;Ta)</option><option value="0">Ta only</option></select></label>
<button onclick="run()">Run Analysis</button> <button style="margin-top:6px;background:#556" onclick="window.print()">Print / Save PDF</button></div></aside>
<section id="out"><div class="card">Set inputs and press <b>Run Analysis</b>.</div></section></main>
<script>
const $=i=>document.getElementById(i);
function tog(){const m=$('method').value;$('nscp').style.display=m=='nscp'?'':'none';$('map').style.display=m=='map'?'':'none'}
const f=(x,d=3)=>(+x).toFixed(d);
function plot(cv,series,o){const c=cv,r=devicePixelRatio||1,W=c.clientWidth,H=c.clientHeight;c.width=W*r;c.height=H*r;const g=c.getContext('2d');g.scale(r,r);
const css=getComputedStyle(document.body),tc=css.color,P={l:50,r:14,t:26,b:38};
let xs=series.flatMap(s=>s.x),ys=series.flatMap(s=>s.y);let x0=Math.min(0,...xs),x1=Math.max(...xs),y0=o.y0??Math.min(0,...ys),y1=Math.max(...ys)*1.05;
const X=v=>P.l+(v-x0)/(x1-x0||1)*(W-P.l-P.r),Y=v=>H-P.b-(v-y0)/(y1-y0||1)*(H-P.t-P.b);
g.font='11px sans-serif';g.fillStyle=tc;g.strokeStyle='#8886';g.textAlign='center';
for(let i=0;i<=5;i++){let vx=x0+(x1-x0)*i/5,vy=y0+(y1-y0)*i/5;g.beginPath();g.moveTo(X(vx),P.t);g.lineTo(X(vx),H-P.b);g.moveTo(P.l,Y(vy));g.lineTo(W-P.r,Y(vy));g.stroke();g.fillText(f(vx,o.dx??2),X(vx),H-P.b+14);g.textAlign='right';g.fillText(f(vy,o.dy??2),P.l-4,Y(vy)+4);g.textAlign='center'}
g.font='bold 12px sans-serif';g.fillText(o.title,W/2,14);g.font='11px sans-serif';g.fillText(o.xl,W/2,H-4);
g.save();g.translate(11,H/2);g.rotate(-Math.PI/2);g.fillText(o.yl,0,0);g.restore();
series.forEach((s,i)=>{g.strokeStyle=g.fillStyle=s.c;g.lineWidth=s.pts?0:2;g.setLineDash(s.dash||[]);if(!s.pts){g.beginPath();s.x.forEach((v,j)=>j?g.lineTo(X(v),Y(s.y[j])):g.moveTo(X(v),Y(s.y[j])));g.stroke()}
else s.x.forEach((v,j)=>{g.beginPath();g.arc(X(v),Y(s.y[j]),4,0,7);g.fill()});g.setLineDash([]);g.textAlign='left';g.fillRect(W-P.r-150,P.t+4+i*13,10,3);g.fillStyle=tc;g.fillText(s.n,W-P.r-136,P.t+9+i*13);g.textAlign='center'})}
async function run(){
const p={method:$('method').value,Z:+$('Z').value,source:$('source').value,dist:+$('dist').value,Ss:+$('Ss').value,S1:+$('S1').value,soil:$('soil').value,I:+$('I').value,
sys:$('sys').value,R:+$('R').value,n:+$('n').value,h1:+$('h1').value,h:+$('h').value,W:+$('W').value,Wr:+$('Wr').value,k:+$('k').value,k1f:+$('k1f').value,xi:+$('xi').value,irregular:$('irr').value=='1',useT1:$('useT1').value=='1'};
const r=await fetch('/api/analyze',{method:'POST',body:JSON.stringify(p)});const d=await r.json();if(d.error){$('out').innerHTML='<div class="card no">'+d.error+'</div>';return}
const kv=(a,b)=>`<div><b>${b}</b><span>${a}</span></div>`;
const pi=Object.entries(d.params).map(([k,v])=>kv(k,f(v))).join('');
$('out').innerHTML=`<div class="card"><h2>Design Spectrum &amp; Base Shear</h2><div class="kv">${pi}${kv('T0 (s)',f(d.T0))}${kv('Ts (s)',f(d.Ts))}${kv('Total weight W (kN)',f(d.Wt,0))}${kv('Ta (s)',f(d.Ta))}${kv('T used static (s)',f(d.Tst))}${kv('Cs',f(d.Cs,4))}
${kv('Static V (kN)',f(d.Vst,1))}${kv('RSA V unscaled (kN)',f(d.Vdyn_unscaled,1))}${kv('Required (kN) '+(d.irregular?'100%':'90%')+' V',f(d.req,1))}${kv('Scale factor',f(d.sf,3))}${kv('RSA V scaled (kN)',f(d.Vdyn,1))}
<div><b class="${d.massOK?'ok':'no'}">${d.massOK?'OK':'&lt;90%'}</b><span>Modal mass participation</span></div><div><b class="${d.ok?'ok':'no'}">${d.ok?'PASS':'FAIL'}</b><span>Drift limit ${f(d.lim*100,1)}% h</span></div></div></div>
<div class="charts"><div class="card"><canvas id="c1"></canvas></div><div class="card"><canvas id="c2"></canvas></div><div class="card"><canvas id="c3"></canvas></div><div class="card"><canvas id="c4"></canvas></div></div>
<div class="card scroll"><h2>Modal Properties</h2><table><tr><th>Mode</th><th>T (s)</th><th>f (Hz)</th><th>&omega; (rad/s)</th><th>Sa/g</th><th>&Gamma;</th><th>Eff. mass</th><th>Cumulative</th></tr>
${d.modes.map(m=>`<tr><td>${m.n}</td><td>${f(m.T,4)}</td><td>${f(m.f)}</td><td>${f(m.w)}</td><td>${f(m.Sa,4)}</td><td>${f(m.gam,3)}</td><td>${f(m.mass*100,1)}%</td><td>${f(m.cum*100,1)}%</td></tr>`).join('')}</table></div>
<div class="card scroll"><h2>Story Results (top to bottom; &Delta;M = 0.7R&Delta;s)</h2><table><tr><th>Story</th><th>h (m)</th><th>W (kN)</th><th>k (kN/m)</th><th>Static F</th><th>Static V</th><th>RSA F</th><th>RSA V</th><th>Disp. (mm)</th><th>&Delta;s (mm)</th><th>&Delta;M (mm)</th><th>&Delta;M/h</th><th>Check</th></tr>
${[...d.stories].reverse().map(s=>`<tr><td>${s.s}</td><td>${f(s.h,2)}</td><td>${f(s.W,0)}</td><td>${f(s.k,0)}</td><td>${f(s.Fst,1)}</td><td>${f(s.Vst,1)}</td><td>${f(s.Fdyn,1)}</td><td>${f(s.Vdyn,1)}</td><td>${f(s.u,1)}</td><td>${f(s.d,2)}</td><td>${f(s.dM,1)}</td><td>${f(s.ratio,4)}</td><td class="${s.ok?'ok':'no'}">${s.ok?'OK':'NG'}</td></tr>`).join('')}</table></div>
<div class="card"><small>Assumptions: planar shear-building (rigid floors, no torsion/accidental eccentricity, no P-&Delta;), fixed base, all modes combined by CQC. Preliminary-design aid only; confirm with a full 3-D model (e.g. STAAD/ETABS) and verify all coefficients, R values and scaling percentages against NSCP 2015 Sec. 208 before use. Spectral-map mode follows ASCE 7-style Fa/Fv and is not part of NSCP 2015 Sec. 208.</small></div>`;
const S=d.spec,st=d.stories,fl=[0,...st.map(s=>s.s)];
plot($('c1'),[{n:'Elastic',x:S.T,y:S.elastic,c:'#0b5cab'},{n:'Design (I/R)',x:S.T,y:S.design,c:'#e67e22'},{n:'Modes',x:d.modes.map(m=>m.T),y:d.modes.map(m=>m.Sa),c:'#c62828',pts:1}],{title:'Response Spectrum',xl:'Period T (s)',yl:'Sa / g',dx:1,dy:2});
plot($('c2'),[{n:'Static ELF',x:[...st.map(s=>s.Vst),0].reverse(),y:[...fl].reverse().map(v=>v),c:'#0b5cab'},{n:'RSA scaled',x:[...st.map(s=>s.Vdyn),0].reverse(),y:[...fl].reverse(),c:'#c62828'}],{title:'Story Shear (kN)',xl:'Shear (kN)',yl:'Storey level',dx:0,dy:0,y0:0});
plot($('c3'),[{n:'Max inelastic drift',x:st.map(s=>s.ratio*100),y:st.map(s=>s.s),c:'#0b5cab'},{n:'Limit',x:[d.lim*100,d.lim*100],y:[1,st.length],c:'#c62828',dash:[5,4]}],{title:'Story Drift Ratio (%)',xl:'\u0394M / h (%)',yl:'Storey',dx:2,dy:0,y0:0});
plot($('c4'),d.modes.slice(0,3).map((m,i)=>({n:'Mode '+m.n+' T='+f(m.T,2)+'s',x:[0,...m.shape],y:fl,c:['#0b5cab','#e67e22','#18794e'][i]})),{title:'Mode Shapes',xl:'Normalized amplitude',yl:'Storey',dx:1,dy:0,y0:0})}
tog();run();
</script></body></html>"""




"""
NSCP 2015 Response Spectrum Analysis - 3D FRAME MODEL with ACCIDENTAL TORSION
Run:  python rsa.py  (single self-contained file)   -> http://localhost:8001
Model: regular grid of 3D beam-column elements (6 DOF/node), rigid floor diaphragms (3 DOF/floor
after static condensation), fixed base, cracked-section factors, CQC modal combination.
Accidental torsion: +/- ecc% of plan dimension (NSCP 208 / UBC-97 1630.6) applied as static torque
on the scaled RSA story forces, added to the dynamic response; Ax and torsional-irregularity check.
"""
import json, webbrowser, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np


def beam_k(E, Gm, A, Iy, Iz, J, L):
    k = np.zeros((12, 12)); a, t = E*A/L, Gm*J/L
    k[0, 0] = k[6, 6] = a; k[0, 6] = k[6, 0] = -a
    k[3, 3] = k[9, 9] = t; k[3, 9] = k[9, 3] = -t
    for I, (v1, v2), (r1, r2), s in ((Iz, (1, 7), (5, 11), 1), (Iy, (2, 8), (4, 10), -1)):
        c = E*I/L**3
        k[v1, v1] = k[v2, v2] = 12*c; k[v1, v2] = k[v2, v1] = -12*c
        k[r1, r1] = k[r2, r2] = 4*E*I/L; k[r1, r2] = k[r2, r1] = 2*E*I/L
        for r in (r1, r2):
            k[v1, r] = k[r, v1] = s*6*c*L; k[v2, r] = k[r, v2] = -s*6*c*L
    return k


def section(b, d, f):  # b width (local z), d depth (local y)
    return b*d, f*d*b**3/12, f*b*d**3/12, .141*max(b, d)*min(b, d)**3  # A, Iy, Iz, J


def b1f(fc): return float(np.clip(.85-.05*(fc-28)/7, .65, .85))


def col_diagram(h, cov, db, nbar, dt, fc, fy):
    """Uniaxial P-M diagram of a square tied column, perimeter bars (N, mm -> kN, kN-m). Returns nominal & factored curves."""
    if nbar % 4 or nbar < 4: raise ValueError('Column bar count must be a multiple of 4')
    k = nbar//4+1; Ab = np.pi*db*db/4; ce = cov+dt+db/2; y = np.linspace(ce, h-ce, k)
    As = np.full(k, 2*Ab); As[[0, -1]] = k*Ab; Ast = As.sum()
    c = np.r_[np.linspace(.02, 3, 500)*h, 1e3*h]; a = np.minimum(b1f(fc)*c, h)
    eps = .003*(c[:, None]-y[None, :])/c[:, None]; fs = np.clip(2e5*eps, -fy, fy)
    F = As*(fs-.85*fc*(y[None, :] < a[:, None]))
    Pn = (.85*fc*h*a+F.sum(1))/1e3; Mn = (.85*fc*h*a*(h/2-a/2)+(F*(h/2-y)).sum(1))/1e6
    phi = np.clip(.65+(-eps[:, -1]-.002)*250/3, .65, .9)
    Pn, Mn, phi = np.r_[-Ast*fy/1e3, Pn], np.r_[0, Mn], np.r_[.9, phi]
    P0 = (.85*fc*(h*h-Ast)+fy*Ast)/1e3; cap = .65*.8*P0; Pp = phi*Pn; Mp = phi*Mn
    o = np.argsort(Pp); Pp, Mp = Pp[o], Mp[o]; Mcap = np.interp(cap, Pp, Mp); m = Pp < cap
    Pp, Mp = np.r_[Pp[m], cap], np.r_[Mp[m], Mcap]; o = np.argsort(Pn)
    return dict(Pp=Pp, Mp=Mp, Pn=Pn[o], Mn=Mn[o], Ast=Ast, rho=Ast/h/h, lo=Pp[0], cap=cap)


def beam_m(As, b, d, fc, fy):
    a = As*fy/(.85*fc*b); c = a/b1f(fc); et = .003*(d-c)/c; phi = float(np.clip(.65+(et-.002)*250/3, .65, .9))
    Mn = As*fy*(d-a/2)/1e6; ap = 1.25*As*fy/(.85*fc*b)
    return dict(Mn=Mn, phiMn=phi*Mn, Mpr=1.25*As*fy*(d-ap/2)/1e6, et=et)


def analyze3d(p):
    nx, ny, n = int(p['nx']), int(p['ny']), int(p['n']); Lx, Ly = p['Lx'], p['Ly']
    I, R, xi = p['I'], p['R'], p['xi']; Bx, By = nx*Lx, ny*Ly; nf = (nx+1)*(ny+1); nn = nf*(n+1)
    if nn > 900: raise ValueError('Model too large: keep (nx+1)(ny+1)(n+1) <= 900')
    sp = spectrum_params(p)
    h = np.array([p['h1']]+[p['h']]*(n-1)); z = np.r_[0, np.cumsum(h)]
    E = 4700*np.sqrt(p['fc'])*1000; Gm = E/2.4
    nid = lambda f, i, j: f*nf+j*(nx+1)+i
    X = np.array([i*Lx-Bx/2 for f in range(n+1) for j in range(ny+1) for i in range(nx+1)])
    Y = np.array([j*Ly-By/2 for f in range(n+1) for j in range(ny+1) for i in range(nx+1)])
    Z = np.array([z[f] for f in range(n+1) for _ in range(nf)])
    K = np.zeros((6*nn, 6*nn)); cs = p['cc']/1000; bb, bd = p['bb']/1000, p['bd']/1000
    secC, secB = section(cs, cs, p['cf']), section(bb, bd, p['bf'])
    EL = []
    def add(a, b, ex, ey, ez, sec):
        L = np.linalg.norm([X[b]-X[a], Y[b]-Y[a], Z[b]-Z[a]]); A, Iy, Iz, J = sec
        Rm = np.array([ex, ey, ez], float); T12 = np.kron(np.eye(4), Rm)
        d = np.r_[6*a:6*a+6, 6*b:6*b+6]; kl = beam_k(E, Gm, A, Iy, Iz, J, L); K[np.ix_(d, d)] += T12.T @ kl @ T12
        q = a % nf if ex != (0, 0, 1) else b % nf
        EL.append(dict(d=d, Kt=kl @ T12, L=L, col=ex == (0, 0, 1), f=b//nf, i=q % (nx+1), j=q//(nx+1), ax='X' if ex == (1, 0, 0) else 'Y', qa=a % nf, qb=b % nf))
    for f in range(1, n+1):
        for j in range(ny+1):
            for i in range(nx+1):
                add(nid(f-1, i, j), nid(f, i, j), (0, 0, 1), (1, 0, 0), (0, 1, 0), secC)
                if i < nx: add(nid(f, i, j), nid(f, i+1, j), (1, 0, 0), (0, 0, 1), (0, -1, 0), secB)
                if j < ny: add(nid(f, i, j), nid(f, i, j+1), (0, 1, 0), (0, 0, 1), (1, 0, 0), secB)
    nr = 3*n+3*nf*n; T = np.zeros((6*nn, nr))
    for f in range(1, n+1):
        for q in range(nf):
            nd = f*nf+q; g = 6*nd; m0 = 3*(f-1); ind = 3*n+3*((f-1)*nf+q)
            T[g, m0] = 1; T[g, m0+2] = -Y[nd]; T[g+1, m0+1] = 1; T[g+1, m0+2] = X[nd]; T[g+5, m0+2] = 1
            T[g+2, ind] = T[g+3, ind+1] = T[g+4, ind+2] = 1
    Kr = T.T @ K @ T; a_, b_ = slice(0, 3*n), slice(3*n, nr)
    C = -np.linalg.solve(Kr[b_, b_], Kr[b_, a_]); Kc = Kr[a_, a_] + Kr[a_, b_] @ C
    W = np.array([p['w']*Bx*By]*(n-1)+[p['wr']*Bx*By]); m = W/G; Iz_m = m*(Bx**2+By**2)/12
    Md = np.zeros(3*n); Md[0::3] = Md[1::3] = m; Md[2::3] = Iz_m
    w2, V = np.linalg.eigh(Kc/np.sqrt(np.outer(Md, Md))); w = np.sqrt(np.maximum(w2, 1e-9)); Tp = 2*np.pi/w
    Phi = V/np.sqrt(Md)[:, None]; nm = 3*n
    rx, ry, rr = np.zeros(nm), np.zeros(nm), np.zeros(nm); rx[0::3] = 1; ry[1::3] = 1; rr[2::3] = 1
    rho = np.array([[8*xi**2*(1+Tp[j]/Tp[i])*(Tp[j]/Tp[i])**1.5/((1-(Tp[j]/Tp[i])**2)**2+4*xi**2*(Tp[j]/Tp[i])*(1+Tp[j]/Tp[i])**2)
                     for j in range(nm)] for i in range(nm)])
    cq = lambda A: np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', A, rho, A), 0))
    Sad = sa(Tp, sp)*I/R*G
    gam = {d: Phi.T @ (Md*r) for d, r in (('X', rx), ('Y', ry), ('R', rr))}
    mass = {d: gam[d]**2/(Md*r).sum() if d != 'R' else gam[d]**2/Iz_m.sum() for d, r in (('X', rx), ('Y', ry), ('R', rr))}
    modes = [dict(n=j+1, T=Tp[j], type=max('XYR', key=lambda d: mass[d][j]).replace('R', 'Torsion')+('' if max('XYR', key=lambda d: mass[d][j]) == 'R' else ' trans.'),
                  X=mass['X'][j], Y=mass['Y'][j], R=mass['R'][j], Sa=float(sa(Tp[j], sp))) for j in range(min(nm, 3*min(n, 6)))]
    cx = np.array([-Bx/2, Bx/2, -Bx/2, Bx/2]); cy = np.array([-By/2, -By/2, By/2, By/2])
    Wt = W.sum(); hn = z[-1]; Ta = CT[p['sys']]*hn**.75; cu = 1.3 if sp['Z'] == .4 else 1.4
    wh = W*z[1:]; res = {}; allok = True; Ed = {}
    KT = np.array([e['Kt'] for e in EL]); DD = np.array([e['d'] for e in EL]); ne = len(EL)
    def mforce(u):  # (3n,k) master disp -> (ne,12,k) local member end forces
        U = T @ np.vstack([u, C @ u]); return np.einsum('eij,ejm->eim', KT, U[DD])
    for d, dn, Lp in ((0, 'X', By), (1, 'Y', Bx)):
        Gd = gam[dn]; jd = int(np.argmax(mass[dn]))
        Tst = min(Tp[jd], cu*Ta) if p['useT1'] else Ta
        Cs = min(sp['cv']/Tst, sp['ap'])*I/R
        Cmin = .11*sp['Ca']*I if sp['Ca'] else max(.044*sp['ap']*I, .01)
        if sp['Z'] == .4: Cmin = max(Cmin, .8*.4*sp['Nv']*I/R)
        Cs = max(Cs, Cmin); Vst = Cs*Wt; Ft = min(.07*Tst*Vst, .25*Vst) if Tst > .7 else 0
        Fs = (Vst-Ft)*wh/wh.sum(); Fs[-1] += Ft; Vs_st = np.cumsum(Fs[::-1])[::-1]
        Fm = Md[:, None]*Phi*(Gd*Sad)[None, :]; um = Phi*(Gd*Sad/w**2)[None, :]
        Fd = cq(Fm[d::3]); Vm = np.cumsum(Fm[d::3][::-1], axis=0)[::-1]; Vd = cq(Vm)
        sf = max(1.0, (1.0 if p['irregular'] else .9)*Vst/Vd[0]); req = (1.0 if p['irregular'] else .9)*Vst
        Ma = Fd*sf*p['ecc']/100*Lp if p['accid'] else np.zeros(n)
        Fa = np.zeros(nm); Fa[2::3] = Ma; ua = np.linalg.solve(Kc, Fa)
        def corner(u):  # u (3n,k) -> (n,4,k) displacement along d at 4 plan corners
            ux = u[d::3][:, None, :]; rz = u[2::3][:, None, :]
            return ux - cy[None, :, None]*rz if d == 0 else ux + cx[None, :, None]*rz
        dr = lambda c: c - np.concatenate([np.zeros((1,)+c.shape[1:]), c[:-1]], 0)
        cd = cq(dr(corner(um)).reshape(-1, nm)).reshape(n, 4)*sf; ds = dr(corner(ua[:, None]))[:, :, 0]
        dtr = ds-ds.mean(1, keepdims=True); da = np.abs(ds.mean(1, keepdims=True))  # rotation part (+/-) and translation part
        edge = (lambda t, s: t[:, cy*s > 0].max(1)) if d == 0 else (lambda t, s: t[:, cx*s > 0].max(1))
        cases = []
        for sg in (1, -1):  # worst of +/- accidental eccentricity
            t = cd+sg*dtr+da; a_, b2 = edge(t, 1), edge(t, -1)
            cases.append((t, np.maximum(a_, b2), np.maximum(a_, b2)/np.maximum((a_+b2)/2, 1e-12)))
        dtot = np.maximum(cases[0][0], cases[1][0]); dmax = np.maximum(cases[0][1], cases[1][1])
        tr = np.maximum(cases[0][2], cases[1][2]); dM = .7*R*dtot; ratio = dM/h[:, None]
        Ax = np.clip((tr/1.2)**2, 1, 3); lim = .025 if Tp[jd] < .7 else .020; ok = bool(ratio.max() <= lim); allok &= ok
        ucm = cq(um[d::3])*sf*1000
        Ed[dn] = cq(mforce(um).reshape(-1, nm)).reshape(ne, 12)*sf+np.abs(mforce(ua[:, None])[:, :, 0])
        res[dn] = dict(T=Tp[jd], Tst=Tst, Cs=Cs, Vst=Vst, Vdyn0=Vd[0], req=req, sf=sf, lim=lim, ok=ok, tors_irr=bool((tr > 1.2).any()),
                       st=[dict(s=i+1, Fst=Fs[i], Vst=Vs_st[i], Fd=Fd[i]*sf, Vd=Vd[i]*sf, Ma=Ma[i], ucm=ucm[i], dmax=dmax[i]*1000,
                                ratio=ratio[i].max(), tr=tr[i], Ax=Ax[i]) for i in range(n)])
    # ---- member design forces: 100%+30% orthogonal, LRFD combos (NSCP 203.3): 1.2D+L+E, 0.9D+E ----
    Ee = np.maximum(Ed['X']+.3*Ed['Y'], .3*Ed['X']+Ed['Y'])*p['rho']
    Evf = .5*sp['Ca']*I if sp['Ca'] else .2*sp['ap']*I; wD, wL = p['wD'], p['wL']
    PD, PL = np.zeros((n+1, nf)), np.zeros((n+1, nf))
    for e in EL:
        if e['col']: PD[e['f'], e['qb']] += 24*cs*cs*h[e['f']-1]
        else:
            for q in (e['qa'], e['qb']): PD[e['f'], q] += wD*e['L']/2; PL[e['f'], q] += wL*e['L']/2
    PD, PL = np.cumsum(PD[::-1], 0)[::-1], np.cumsum(PL[::-1], 0)[::-1]
    mem = []
    for k, e in enumerate(EL):
        F = Ee[k]; L = e['L']
        if e['col']:
            pd, pl, pe = PD[e['f'], e['i']+e['j']*(nx+1)], PL[e['f'], e['i']+e['j']*(nx+1)], max(F[0], F[6])
            mem.append(dict(t='C', s=e['f'], id=f"C({e['i']+1},{e['j']+1})", Pmax=(1.2+Evf)*pd+pl+pe, Pmin=(.9-Evf)*pd-pe, Vx=max(F[1], F[7]),
                            Vy=max(F[2], F[8]), Mx=max(F[4], F[10]), My=max(F[5], F[11])))
        else:
            Em, Ev = max(F[5], F[11]), max(F[1], F[7]); MD = wD*L*L/12
            mem.append(dict(t='B', s=e['f'], id=f"B{e['ax']} {e['i']+1}-{e['i']+2} @{e['j']+1}" if e['ax'] == 'X' else f"BY {e['j']+1}-{e['j']+2} @{e['i']+1}",
                            Mh=1.2*MD+wL*L*L/12+Em, Ms=max(Em-.9*MD, 0), Mm=(1.2*wD+wL)*L*L/24, Vu=1.2*wD*L/2+wL*L/2+Ev))
    # ---- RC section checks (ACI 318-14 / NSCP 2015 Ch.4, special moment frame) ----
    fy, fyt, cov, hc = p['fy'], p['fyt'], p['cov'], p['cc']; Ag = hc*hc; sq = np.sqrt(p['fc']); fc = p['fc']
    cd = col_diagram(hc, cov, p['cdb'], int(p['cn']), p['cdt'], fc, fy); dcol = hc-cov-p['cdt']-p['cdb']/2
    Atie = np.pi*p['cdt']**2/4; Av = p['clg']*Atie; Vs_c = Av*fyt*dcol/p['css']/1e3
    bw, hb = p['bb'], p['bd']; db_ = hb-cov-p['bsd']-p['bbd']/2
    Ast_t, Ast_b = p['bt']*np.pi*p['btd']**2/4, p['bbn']*np.pi*p['bbd']**2/4
    bt, bbm = beam_m(Ast_t, bw, db_, fc, fy), beam_m(Ast_b, bw, db_, fc, fy); Avb = p['bsl']*np.pi*p['bsd']**2/4
    Vs_b = Avb*fyt*db_/p['bss']/1e3
    Mnc_of = lambda P: float(np.interp(P, cd['Pn'], cd['Mn']))
    cinfo = {}
    for k, e in enumerate(EL):
        m = mem[k]
        if e['col']:
            q = e['i']+e['j']*(nx+1); cinfo[(e['f'], q)] = m; lu = h[e['f']-1]-hb/1000; r = []
            for Pu in (m['Pmax'], m['Pmin']):
                M0 = float(np.interp(Pu, cd['Pp'], cd['Mp'])) if cd['lo'] <= Pu <= cd['cap'] else 0
                r.append(9.99 if M0 <= 0 else (m['Mx']/M0)**1.5+(m['My']/M0)**1.5)
            Pr = np.linspace(max(m['Pmin'], cd['lo']), min(m['Pmax'], cd['Pn'][-1]), 20); Mmax = max(Mnc_of(x) for x in Pr)
            Ve = 2.5*Mmax/lu; Vd = max(max(m['Vx'], m['Vy']), Ve)
            Vc = 0 if (Ve >= .5*Vd and m['Pmin'] < Ag*fc/20e3) else .17*(1+max(m['Pmin'], 0)*1e3/(14*Ag))*sq*hc*dcol/1e3
            m.update(dPM=max(r), dV=Vd/(.75*(Vc+Vs_c)), Ve=Vd)
        else:
            L = e['L']; Ln = L-hc/1000; wu = 1.2*wD+wL
            Ve = (bt['Mpr']+bbm['Mpr'])/Ln+wu*Ln/2; Vd = max(m['Vu'], Ve)
            Vc = 0 if (bt['Mpr']+bbm['Mpr'])/Ln >= .5*Ve else .17*sq*bw*db_/1e3
            m.update(dMh=m['Mh']/bt['phiMn'], dMs=m['Ms']/bbm['phiMn'], dMm=m['Mm']/bbm['phiMn'], dV=Vd/(.75*(Vc+Vs_b)), Ve=Vd)
            m['dM'] = max(m['dMh'], m['dMs'], m['dMm'])
    nb = {'X': np.zeros((n+1, nf)), 'Y': np.zeros((n+1, nf))}
    for e in EL:
        if not e['col']: nb[e['ax']][e['f'], e['qa']] += 1; nb[e['ax']][e['f'], e['qb']] += 1
    joints = []
    for f in range(1, n):
        for q in range(nf):
            Mc = sum(min(Mnc_of(max(cinfo[(ff, q)]['Pmin'], cd['lo'])), Mnc_of(cinfo[(ff, q)]['Pmax'])) for ff in (f, f+1))
            for dn in 'XY':
                if nb[dn][f, q]:
                    Mb = bt['Mn']+bbm['Mn'] if nb[dn][f, q] >= 2 else max(bt['Mn'], bbm['Mn'])
                    joints.append(dict(s=f, id=f"J({q % (nx+1)+1},{q//(nx+1)+1}) {dn}", r=Mc/Mb))
    bc = hc-2*cov; Ash_req = max(.3*p['css']*bc*fc/fyt*(Ag/bc**2-1), .09*p['css']*bc*fc/fyt)
    sb = (bw-2*(cov+p['bsd'])-p['btd'])/max(p['bt']-1, 1); sbb = (bw-2*(cov+p['bsd'])-p['bbd'])/max(p['bbn']-1, 1)
    rmin = max(.25*sq/fy, 1.4/fy)*bw*db_
    checks = [(f"Column steel ratio {cd['rho']*100:.2f}% (1%-6%)", .01 <= cd['rho'] <= .06),
              (f"Tie spacing {p['css']:.0f} mm <= min(h/4, 6db, 150) = {min(hc/4, 6*p['cdb'], 150):.0f} mm", p['css'] <= min(hc/4, 6*p['cdb'], 150)),
              (f"Confinement Ash provided {p['clg']*Atie:.0f} >= required {Ash_req:.0f} mm2", p['clg']*Atie >= Ash_req),
              (f"Beam As top {Ast_t:.0f} / bottom {Ast_b:.0f} mm2 >= As,min {rmin:.0f} mm2", min(Ast_t, Ast_b) >= rmin),
              (f"Beam strain et top {bt['et']:.4f} / bottom {bbm['et']:.4f} >= 0.004 (tension-controlled)", min(bt['et'], bbm['et']) >= .004),
              (f"Beam M+ at face {bbm['Mn']:.0f} >= 0.5 M- {bt['Mn']:.0f} kN-m", bbm['Mn'] >= .5*bt['Mn']),
              (f"Stirrup spacing {p['bss']:.0f} mm <= min(d/4, 6db, 150) = {min(db_/4, 6*p['bbd'], 150):.0f} mm (2h end zones)", p['bss'] <= min(db_/4, 6*p['bbd'], 150)),
              (f"Beam bars fit one layer (clear {min(sb, sbb)-p['btd']:.0f} mm >= max(25, db))", min(sb, sbb)-max(p['btd'], p['bbd']) >= 25 or min(p['bt'], p['bbn']) < 2)]
    rc = dict(checks=[dict(t=t, ok=bool(o)) for t, o in checks], phiMnc0=float(np.interp(0, cd['Pp'], cd['Mp'])), phiMnt=bt['phiMn'], phiMnb=bbm['phiMn'], Ast=cd['Ast'], d=db_, bt_et=bt['et'])
    Tg = np.linspace(0, max(4, Tp[0]*1.3), 300)
    return dict(params=sp['info'], Wt=Wt, hn=hn, Ta=Ta, E=E/1000, nm=nm, ok=bool(allok), accid=p['accid'], ecc=p['ecc'], irregular=p['irregular'],
                massOK=bool(min(mass['X'].sum(), mass['Y'].sum()) >= .9), res=res, modes=modes, mem=mem, Evf=Evf, rc=rc, joints=joints, nstory=n,
                spec=dict(T=Tg.tolist(), el=sa(Tg, sp).tolist(), de=(sa(Tg, sp)*I/R).tolist()))


P = BASE_PAGE
HEAD = P[:P.index('<style>')].replace('Response Spectrum Analysis', '3D RSA').replace('NSCP 2015 3D RSA', 'NSCP 2015 3D RSA') \
    + P[P.index('<style>'):P.index('</style>')+8]
PLOT = P[P.index('function plot('):P.index('async function run')]
HAZ = P[P.index('<div class="card"><h2>Seismic Hazard'):P.index('<div class="card"><h2>Structure')]
BODY = r"""<header><h1>3D Frame Response Spectrum Analysis &mdash; NSCP 2015 Sec. 208</h1><p>3D beam-column model &bull; rigid diaphragms &bull; CQC &bull; accidental torsion &bull; Ax &bull; torsional irregularity &bull; drift</p></header>
<main><aside>""" + HAZ + r"""<div class="card"><h2>3D Frame</h2>
<label>System<select id="sys"><option value="concrete">Concrete MRF</option><option value="steel">Steel MRF</option><option value="other">Other</option></select></label>
<label>R factor<select id="R"><option value="8.5">SMRF 8.5</option><option value="5.5">IMRF 5.5</option><option value="4.5">OMRF 4.5</option></select></label>
<label>Bays in X / Y<span><input id="nx" type="number" value="4" style="width:64px"> <input id="ny" type="number" value="3" style="width:64px"></span></label>
<label>Bay length X / Y (m)<span><input id="Lx" type="number" step=".1" value="6" style="width:64px"> <input id="Ly" type="number" step=".1" value="5" style="width:64px"></span></label>
<label>Storeys<input id="n" type="number" value="8"></label><label>1st h / typ. h (m)<span><input id="h1" type="number" step=".1" value="4" style="width:64px"> <input id="h" type="number" step=".1" value="3.2" style="width:64px"></span></label>
<label>Column size (mm)<input id="cc" type="number" value="600"></label><label>Beam b x d (mm)<span><input id="bb" type="number" value="300" style="width:64px"> <input id="bd" type="number" value="550" style="width:64px"></span></label>
<label>f'c (MPa)<input id="fc" type="number" value="28"></label><label>Cracked I col / beam<span><input id="cf" type="number" step=".05" value=".7" style="width:64px"> <input id="bf" type="number" step=".05" value=".35" style="width:64px"></span></label>
<label>Seismic wt floor / roof (kPa)<span><input id="w" type="number" step=".5" value="9" style="width:64px"> <input id="wr" type="number" step=".5" value="7" style="width:64px"></span></label>
<label>Damping &xi;<input id="xi" type="number" step=".01" value=".05"></label>
<label>Beam DL / LL (kN/m)<span><input id="wD" type="number" value="25" style="width:64px"> <input id="wL" type="number" value="8" style="width:64px"></span></label><label>Redundancy &rho;<input id="rho" type="number" step=".1" value="1"></label>
<label>fy / fyt (MPa)<span><input id="fy" type="number" value="420" style="width:64px"> <input id="fyt" type="number" value="275" style="width:64px"></span></label><label>Cover (mm)<input id="cov" type="number" value="40"></label>
<label>Col bars (no., dia)<span><input id="cn" type="number" value="12" style="width:64px"> <input id="cdb" type="number" value="25" style="width:64px"></span></label>
<label>Col ties dia/legs/s<span><input id="cdt" type="number" value="12" style="width:42px"> <input id="clg" type="number" value="3" style="width:42px"> <input id="css" type="number" value="100" style="width:42px"></span></label>
<label>Beam top bars (no., dia)<span><input id="bt" type="number" value="5" style="width:64px"> <input id="btd" type="number" value="22" style="width:64px"></span></label><label>Beam bot bars (no., dia)<span><input id="bbn" type="number" value="3" style="width:64px"> <input id="bbd" type="number" value="22" style="width:64px"></span></label>
<label>Stirrup dia/legs/s<span><input id="bsd" type="number" value="10" style="width:42px"> <input id="bsl" type="number" value="2" style="width:42px"> <input id="bss" type="number" value="100" style="width:42px"></span></label>
<label>Accidental torsion<select id="accid"><option value="1">Include</option><option value="0">Exclude</option></select></label><label>Eccentricity (% of dim.)<input id="ecc" type="number" value="5"></label>
<label>Irregular?<select id="irr"><option value="0">No (90% V)</option><option value="1">Yes (100% V)</option></select></label>
<label>Static T limit<select id="useT1"><option value="1">min(T1, Cu&middot;Ta)</option><option value="0">Ta only</option></select></label>
<button onclick="run()">Run 3D Analysis</button><button style="margin-top:6px;background:#556" onclick="window.print()">Print / Save PDF</button></div></aside>
<section id="out"><div class="card">Press <b>Run 3D Analysis</b>.</div></section></main><script>
const $=i=>document.getElementById(i),f=(x,d=3)=>(+x).toFixed(d);function tog(){const m=$('method').value;$('nscp').style.display=m=='nscp'?'':'none';$('map').style.display=m=='map'?'':'none'}
""" + PLOT + r"""
const tbl=(h,r)=>'<table><tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr>'+r.map(x=>'<tr>'+x.map(y=>'<td>'+y+'</td>').join('')+'</tr>').join('')+'</table>';
function showDF(){const d=window.D,N=d.nstory,g=(a,k,m)=>a.length?Math[m](...a.map(x=>x[k])):0,S=[],c=x=>`<span class="${x<=1?'ok':'no'}">${f(x,2)}</span>`;
for(let s=N;s>=1;s--){const M=d.mem.filter(m=>m.s==s),C=M.filter(m=>m.t=='C'),B=M.filter(m=>m.t=='B'),J=d.joints.filter(j=>j.s==s);
S.push([s,f(g(C,'Pmax','max'),0),f(g(C,'Pmin','min'),0),f(g(C,'Mx','max'),0),f(g(B,'Mh','max'),0),f(g(B,'Vu','max'),0),c(g(C,'dPM','max')),c(g(C,'dV','max')),c(g(B,'dM','max')),c(g(B,'dV','max')),J.length?c(1.2/Math.min(...J.map(j=>j.r))):'-'])}
$('dfs').innerHTML='<b>Detailing checks</b>'+tbl(['Check','Status'],d.rc.checks.map(k=>[k.t,`<span class="${k.ok?'ok':'no'}">${k.ok?'OK':'NG'}</span>`]))+'<br><b>Governing demand and DCR per storey</b> (kN, kN-m; DCR &le; 1 passes)'+tbl(['Story','Col Pu max','Col Pu min','Col Mu','Beam Mu-','Beam Vu','Col P-M DCR','Col V DCR','Beam M DCR','Beam V DCR','SCWB DCR'],S);
const s=+$('sel').value||1,M=d.mem.filter(m=>m.s==s),r=(a,k)=>f(a[k],1);
$('dft').innerHTML='<b>Columns, story '+s+'</b>'+tbl(['ID','Pu max','Pu min','Vux','Vuy','Mux','Muy','P-M DCR','V DCR'],M.filter(m=>m.t=='C').map(m=>[m.id,r(m,'Pmax'),r(m,'Pmin'),r(m,'Vx'),r(m,'Vy'),r(m,'Mx'),r(m,'My'),c(m.dPM),c(m.dV)]))+'<br><b>Beams, floor '+s+' (Ve = capacity shear)</b>'+tbl(['ID','Mu- (supp)','Mu+ (supp)','Mu+ (mid)','Vu','Ve','M- DCR','M+ DCR','V DCR'],M.filter(m=>m.t=='B').map(m=>[m.id,r(m,'Mh'),r(m,'Ms'),r(m,'Mm'),r(m,'Vu'),r(m,'Ve'),c(m.dMh),c(Math.max(m.dMs,m.dMm)),c(m.dV)]))+'<br><b>Strong-column/weak-beam joints, floor '+s+'</b> (&Sigma;Mnc/&Sigma;Mnb &ge; 1.2)'+tbl(['Joint','Ratio','Status'],d.joints.filter(j=>j.s==s).map(j=>[j.id,f(j.r,2),`<span class="${j.r>=1.2?'ok':'no'}">${j.r>=1.2?'OK':'NG'}</span>`]))}
async function run(){const v=i=>+$(i).value;
const p={method:$('method').value,Z:v('Z'),source:$('source').value,dist:v('dist'),Ss:v('Ss'),S1:v('S1'),soil:$('soil').value,I:v('I'),sys:$('sys').value,R:v('R'),nx:v('nx'),ny:v('ny'),Lx:v('Lx'),Ly:v('Ly'),n:v('n'),h1:v('h1'),h:v('h'),cc:v('cc'),bb:v('bb'),bd:v('bd'),fc:v('fc'),cf:v('cf'),bf:v('bf'),w:v('w'),wr:v('wr'),xi:v('xi'),wD:v('wD'),wL:v('wL'),rho:v('rho'),fy:v('fy'),fyt:v('fyt'),cov:v('cov'),cn:v('cn'),cdb:v('cdb'),cdt:v('cdt'),clg:v('clg'),css:v('css'),bt:v('bt'),btd:v('btd'),bbn:v('bbn'),bbd:v('bbd'),bsd:v('bsd'),bsl:v('bsl'),bss:v('bss'),accid:v('accid')==1,ecc:v('ecc'),irregular:v('irr')==1,useT1:v('useT1')==1};
$('out').innerHTML='<div class="card">Analyzing...</div>';
const d=await (await fetch('/api/analyze',{method:'POST',body:JSON.stringify(p)})).json();if(d.error){$('out').innerHTML='<div class="card no">'+d.error+'</div>';return}
const kv=(a,b)=>`<div><b>${b}</b><span>${a}</span></div>`,pi=Object.entries(d.params).map(([k,x])=>kv(k,f(x))).join('');
const dirs=['X','Y'].map(k=>{const r=d.res[k];return `<div class="card"><h2>Direction ${k}</h2><div class="kv">${kv('T governing (s)',f(r.T))}${kv('Static V (kN)',f(r.Vst,1))}${kv('RSA V unscaled (kN)',f(r.Vdyn0,1))}${kv('Scale factor',f(r.sf,3))}
<div><b class="${r.ok?'ok':'no'}">${r.ok?'PASS':'FAIL'}</b><span>Drift limit ${f(r.lim*100,1)}%h</span></div><div><b class="${r.tors_irr?'no':'ok'}">${r.tors_irr?'YES':'NO'}</b><span>Torsional irregularity (&delta;max/&delta;avg&gt;1.2)</span></div></div></div>`}).join('');
$('out').innerHTML=`<div class="card"><h2>Hazard &amp; Model</h2><div class="kv">${pi}${kv('W total (kN)',f(d.Wt,0))}${kv('Ta (s)',f(d.Ta))}${kv('E (MPa)',f(d.E,0))}${kv('DOFs (dynamic)',d.nm)}${kv('Accidental torsion',d.accid?d.ecc+'%':'off')}<div><b class="${d.massOK?'ok':'no'}">${d.massOK?'OK':'<90%'}</b><span>Mass participation (all modes)</span></div></div></div>${dirs}
<div class="charts"><div class="card"><canvas id="c1"></canvas></div><div class="card"><canvas id="c2"></canvas></div><div class="card"><canvas id="c3"></canvas></div><div class="card"><canvas id="c4"></canvas></div></div>
<div class="card scroll"><h2>Modes</h2>${tbl(['Mode','T (s)','Type','Sa/g','UX %','UY %','RZ %'],d.modes.map(m=>[m.n,f(m.T,4),m.type,f(m.Sa,3),f(m.X*100,1),f(m.Y*100,1),f(m.R*100,1)]))}</div>
${['X','Y'].map(k=>`<div class="card scroll"><h2>Story results &mdash; ${k} (RSA scaled, with accidental torsion)</h2>${tbl(['Story','Static V','RSA F','RSA V','Mt acc. (kN-m)','CM disp (mm)','Max corner drift (mm)','&Delta;M/h','&delta;max/&delta;avg','Ax'],[...d.res[k].st].reverse().map(s=>[s.s,f(s.Vst,1),f(s.Fd,1),f(s.Vd,1),f(s.Ma,1),f(s.ucm,1),f(s.dmax,2),f(s.ratio,4),f(s.tr,3),f(s.Ax,2)]))}</div>`).join('')}
<div class="card scroll"><h2>Member Design Forces &amp; RC Section Checks &mdash; LRFD 1.2D+L+&rho;E+Ev, 0.9D&minus;&rho;E&minus;Ev</h2><div id="dfs"></div><p>Story <select id="sel" onchange="showDF()">${Array.from({length:d.nstory},(_,i)=>'<option>'+(i+1)+'</option>').join('')}</select></p><div id="dft"></div></div><div class="card"><small>Assumptions: regular orthogonal frame grid, rigid diaphragms, fixed base, uniform floor mass at plan centre (no inherent eccentricity), accidental torsion applied as static torque on scaled RSA story forces and added to dynamic corner drifts. E = CQC member forces (scaled) + accidental-torsion forces, 100%+30% orthogonal; Ev = 0.5CaID; gravity from uniform beam loads (fixed-end, wL&sup2;/12) and column axial by tributary beam shears; gravity column moments, walls, slab flexibility and P-&Delta; are not modelled. RC checks: uniform reinforcement for all columns/beams, square columns with perimeter bars, singly-reinforced beam flexure (compression steel ignored), Bresler-type biaxial check (exponent 1.5), capacity-based shear (Mpr=1.25fy), SCWB at floors below roof; no joint shear, development length or deflection checks. Verify coefficients, R, scaling %, Ax and irregularity rules against NSCP 2015 Sec. 208 before use.</small></div>`;
window.D=d;showDF();const S=d.spec,N=d.nstory,fl=[0,...Array.from({length:N},(_,i)=>i+1)],X=d.res.X.st,Y=d.res.Y.st,rv=a=>[...a].reverse();
plot($('c1'),[{n:'Elastic',x:S.T,y:S.el,c:'#0b5cab'},{n:'Design (I/R)',x:S.T,y:S.de,c:'#e67e22'},{n:'Modes',x:d.modes.map(m=>m.T),y:d.modes.map(m=>m.Sa),c:'#c62828',pts:1}],{title:'Response Spectrum',xl:'T (s)',yl:'Sa/g',dx:1});
plot($('c2'),[{n:'Static X',x:rv([...X.map(s=>s.Vst),0]),y:rv(fl),c:'#0b5cab',dash:[4,3]},{n:'RSA X',x:rv([...X.map(s=>s.Vd),0]),y:rv(fl),c:'#0b5cab'},{n:'Static Y',x:rv([...Y.map(s=>s.Vst),0]),y:rv(fl),c:'#e67e22',dash:[4,3]},{n:'RSA Y',x:rv([...Y.map(s=>s.Vd),0]),y:rv(fl),c:'#e67e22'}],{title:'Story Shear (kN)',xl:'kN',yl:'Storey',dx:0,dy:0,y0:0});
plot($('c3'),[{n:'X max corner',x:X.map(s=>s.ratio*100),y:X.map(s=>s.s),c:'#0b5cab'},{n:'Y max corner',x:Y.map(s=>s.ratio*100),y:Y.map(s=>s.s),c:'#e67e22'},{n:'Limit',x:[d.res.X.lim*100,d.res.X.lim*100],y:[1,N],c:'#c62828',dash:[5,4]}],{title:'Inelastic Drift \u0394M/h (%)',xl:'%',yl:'Storey',dy:0,y0:0});
plot($('c4'),[{n:'X \u03b4max/\u03b4avg',x:X.map(s=>s.tr),y:X.map(s=>s.s),c:'#0b5cab'},{n:'Y \u03b4max/\u03b4avg',x:Y.map(s=>s.tr),y:Y.map(s=>s.s),c:'#e67e22'},{n:'1.2 limit',x:[1.2,1.2],y:[1,N],c:'#c62828',dash:[5,4]}],{title:'Torsional Ratio',xl:'\u03b4max/\u03b4avg',yl:'Storey',dy:0,y0:0})}
tog();run();</script></body></html>"""
PAGE = HEAD + '<body>' + BODY


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(PAGE.encode())
    def do_POST(self):
        try: out = analyze3d(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        except Exception as e: out = {'error': f'Error: {e}'}
        self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(json.dumps(out, default=float).encode())


if __name__ == '__main__':
    srv = HTTPServer(('127.0.0.1', 8001), H); print('3D RSA at http://localhost:8001')
    threading.Timer(1, lambda: webbrowser.open('http://localhost:8001')).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: pass