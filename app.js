// Swell Atlas. Nessun dato qui dentro: zone, aeroporti, scala, stima voli e coste arrivano da data/*.json
const MESI=["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"];
const $=id=>document.getElementById(id);

// ---------- dati
async function loadJSON(path){
  const r=await fetch(path);
  if(!r.ok)throw new Error(path+": HTTP "+r.status);
  return r.json();
}
let ZONES,DEPS,SCALE,FLY,CLIMATE,LAND50,LAND110;
try{
  [ZONES,DEPS,SCALE,FLY,CLIMATE,LAND50,LAND110]=await Promise.all(
    ["data/zones.json","data/airports.json","data/scale.json","data/flight-estimate.json","data/climate.json","data/land-50m.json","data/land-110m.json"].map(loadJSON));
}catch(err){
  $("zn").textContent="Dati non caricati";
  $("zs").textContent="Apri il sito tramite un server (es. python3 -m http.server), non come file locale.";
  throw err;
}

// generatore deterministico per i prezzi finti della stima voli
function rnd(seed){let s=0;for(const ch of seed)s=(s*31+ch.charCodeAt(0))>>>0;return()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296}}

// Onde per settimana dalla climatologia ERA5 (data/climate.json, scripts/build_climate.py):
// 52 elementi {q: classe prevalente 0-9, h/h25/h75: altezza mediana e 25-75 percentile (m),
// t: periodo di picco mediano (s), good: % giorni Good o meglio}. null se la zona non ha dati.
function getZoneWeeks(zone){
  const c=CLIMATE.zones[zone.id];
  if(!c||!c.weeks)return null;
  const F=CLIMATE.fields,ix=k=>F.indexOf(k);
  return c.weeks.map(w=>({q:w[ix("q")],h:w[ix("h50")],h25:w[ix("h25")],h75:w[ix("h75")],t:w[ix("t50")],good:w[ix("good")]}));
}
ZONES.forEach(z=>z.wk=getZoneWeeks(z));
ZONES=ZONES.filter(z=>z.wk);   // le zone senza climatologia non compaiono

const state={week:0,zone:ZONES[0],dep:DEPS[0]};
const weekMonth=w=>Math.min(11,Math.floor(w*12/52));
const dec=x=>x.toFixed(1).replace(".",",");
const fmtH=w=>dec(w.h25)+"–"+dec(w.h75)+" m";

// ---------- globo
const cv=$("g"),ctx=cv.getContext("2d");
const land50=topojson.feature(LAND50,LAND50.objects.land);
const land110=topojson.feature(LAND110,LAND110.objects.land);
const proj=d3.geoOrthographic().clipAngle(90).precision(.4);
const path=d3.geoPath(proj,ctx);
const grat=d3.geoGraticule10();
let W=0,H=0,DPR=1,base=1,zoom=1,dragging=false,anim=null;
proj.rotate([-state.zone.lon,-state.zone.lat*.6]);
function css(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim()}
function resize(){
  const b=$("gbox").getBoundingClientRect();DPR=Math.min(2,window.devicePixelRatio||1);
  W=b.width;H=b.height;cv.width=W*DPR;cv.height=H*DPR;
  base=Math.min(W,H)/2-14;proj.translate([W/2,H/2]).scale(base*zoom);draw();
}
function draw(){
  ctx.setTransform(DPR,0,0,DPR,0,0);ctx.clearRect(0,0,W,H);
  const r=proj.scale(),[cx,cy]=proj.translate();
  const g=ctx.createRadialGradient(cx-r*.3,cy-r*.35,r*.1,cx,cy,r);
  g.addColorStop(0,css("--ocean"));g.addColorStop(1,css("--ocean2"));
  ctx.beginPath();path({type:"Sphere"});ctx.fillStyle=g;ctx.fill();
  ctx.beginPath();path(grat);ctx.strokeStyle=css("--grat");ctx.lineWidth=1;ctx.stroke();
  ctx.beginPath();path(dragging||anim?land110:land50);ctx.fillStyle=css("--land");ctx.fill();
  ctx.strokeStyle=css("--landline");ctx.lineWidth=.6;ctx.stroke();
  // rotta volo
  const z=state.zone,d=state.dep;
  ctx.beginPath();path({type:"LineString",coordinates:[[d.lon,d.lat],[z.airport.lon,z.airport.lat]]});
  ctx.setLineDash([4,4]);ctx.strokeStyle=css("--accent");ctx.lineWidth=1.5;ctx.stroke();ctx.setLineDash([]);
  const c=proj.invert([cx,cy]);
  if(d3.geoDistance([d.lon,d.lat],c)<Math.PI/2){const p=proj([d.lon,d.lat]);ctx.beginPath();ctx.arc(p[0],p[1],3.5,0,7);ctx.fillStyle=css("--fg");ctx.fill()}
  // zone: punti piccoli colorati per qualità, crescono poco con lo zoom; la selezionata ha un anello ed è disegnata sopra le altre
  const fg=css("--fg"),k=Math.min(1.6,Math.sqrt(zoom)),shown=[];
  ZONES.forEach(zz=>{
    if(zz===state.zone||d3.geoDistance([zz.lon,zz.lat],c)>Math.PI/2-.02)return;
    shown.push(dot(zz,k,false,fg));
  });
  if(d3.geoDistance([z.lon,z.lat],c)<=Math.PI/2-.02)shown.unshift(dot(z,k,true,fg));
  // etichette: la selezionata sempre, le altre solo da zoom e solo se non si sovrappongono
  ctx.font="600 12px "+css("--f-body");ctx.fillStyle=fg;
  const boxes=[];
  shown.forEach(({zz,p,rad})=>{
    if(zz!==state.zone&&zoom<=LABEL_ZOOM)return;
    const x=p[0]+rad+4,y=p[1]+4,b=[x-2,y-12,x+ctx.measureText(zz.name).width+2,y+4];
    if(boxes.some(o=>b[0]<o[2]&&b[2]>o[0]&&b[1]<o[3]&&b[3]>o[1]))return;
    boxes.push(b);ctx.fillText(zz.name,x,y);
  });
}
const LABEL_ZOOM=1.6;
function dot(zz,k,sel,fg){
  const p=proj([zz.lon,zz.lat]),wk=zz.wk[state.week],rad=(sel?3.4:2.6)*k;
  ctx.beginPath();ctx.arc(p[0],p[1],rad,0,7);ctx.fillStyle=SCALE[wk.q].color;ctx.fill();
  ctx.lineWidth=.75;ctx.strokeStyle="rgba(0,0,0,.45)";ctx.stroke();
  if(sel){ctx.beginPath();ctx.arc(p[0],p[1],rad+4,0,7);ctx.lineWidth=1.5;ctx.strokeStyle=fg;ctx.stroke()}
  return{zz,p,rad:sel?rad+4:rad};
}
function rotateTo(z){
  if(anim)anim.stop();
  const from=proj.rotate(),to=[-z.lon,-z.lat*.6,0];
  if(to[0]-from[0]>180)to[0]-=360;if(from[0]-to[0]>180)to[0]+=360;
  const it=d3.interpolate(from,to),reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
  if(reduce){proj.rotate(to);draw();return}
  anim=d3.timer(e=>{const t=Math.min(1,e/900);proj.rotate(it(d3.easeCubicInOut(t)));if(t>=1){anim.stop();anim=null}draw()});
}
// drag
let last=null;
cv.addEventListener("pointerdown",e=>{dragging=true;last=[e.clientX,e.clientY,e.clientX,e.clientY];cv.setPointerCapture(e.pointerId);if(anim){anim.stop();anim=null}});
cv.addEventListener("pointermove",e=>{if(!dragging)return;const k=70/proj.scale(),r=proj.rotate();
  proj.rotate([r[0]+(e.clientX-last[0])*k,Math.max(-80,Math.min(80,r[1]-(e.clientY-last[1])*k)),0]);last[0]=e.clientX;last[1]=e.clientY;draw()});
cv.addEventListener("pointerup",e=>{dragging=false;const moved=Math.hypot(e.clientX-last[2],e.clientY-last[3]);
  if(moved<5)pick(e);draw()});
function pick(e){const b=cv.getBoundingClientRect(),x=e.clientX-b.left,y=e.clientY-b.top,c=proj.invert(proj.translate());let best=null,bd=22;
  ZONES.forEach(z=>{if(d3.geoDistance([z.lon,z.lat],c)>Math.PI/2)return;const p=proj([z.lon,z.lat]),dd=Math.hypot(p[0]-x,p[1]-y);if(dd<bd){bd=dd;best=z}});
  if(best)selectZone(best,false)}
function setZoom(z){zoom=Math.max(.8,Math.min(6,z));proj.scale(base*zoom);draw()}
cv.addEventListener("wheel",e=>{e.preventDefault();setZoom(zoom*(e.deltaY<0?1.12:1/1.12))},{passive:false});
$("zin").onclick=()=>setZoom(zoom*1.3);$("zout").onclick=()=>setZoom(zoom/1.3);
// pizzico
const pts=new Map();let pinch0=null;
cv.addEventListener("pointerdown",e=>pts.set(e.pointerId,[e.clientX,e.clientY]));
cv.addEventListener("pointermove",e=>{if(!pts.has(e.pointerId))return;pts.set(e.pointerId,[e.clientX,e.clientY]);
  if(pts.size===2){const [a,b]=[...pts.values()],d=Math.hypot(a[0]-b[0],a[1]-b[1]);if(!pinch0)pinch0=[d,zoom];else setZoom(pinch0[1]*d/pinch0[0])}});
const endP=e=>{pts.delete(e.pointerId);if(pts.size<2)pinch0=null};
cv.addEventListener("pointerup",endP);cv.addEventListener("pointercancel",e=>{endP(e);dragging=false});

// ---------- voli (stima finta, la fase 4 userà OurAirports e la fase 5 i prezzi veri)
function km(a,b){return d3.geoDistance([a.lon,a.lat],[b.airport.lon,b.airport.lat])*6371}
function flight(d,z){
  const dist=km(d,z);
  const [near,far]=FLY.stopsDistanceKm,P=FLY.price;
  let stops=dist<near?(d.hub?0:1):dist<far?1:2;
  if(z.airport.nearEurope)stops=d.hub?0:1;
  const hrs=dist/FLY.speedKmh+FLY.fixedHours+stops*FLY.hoursPerStop;
  const baseP=Math.round((P.base+dist*P.perKm+stops*P.perStop)/10)*10;
  const r=rnd(d.code+z.id);
  const months=P.monthFactor.map(s=>Math.round(baseP*s*(P.noiseMin+r()*P.noiseRange)/10)*10);
  return{dist,stops,hrs,months};
}

// ---------- UI
function selectZone(z,rot=true){state.zone=z;$("arr").value=z.id;if(rot)rotateTo(z);else draw();render()}
function render(){
  const z=state.zone,w=z.wk[state.week],m=weekMonth(state.week);
  $("zn").textContent=z.name;$("zs").textContent=z.region+" · aeroporto "+z.airport.code;
  const zq=$("zq");zq.textContent=SCALE[w.q].label;zq.style.background=SCALE[w.q].color;
  $("sh").textContent=fmtH(w);$("sh").title="mediana "+dec(w.h)+" m";$("sp").textContent=Math.round(w.t)+" s";$("sg").textContent=w.good+"%";
  $("strip").innerHTML=z.wk.map((x,i)=>`<i style="background:${SCALE[x.q].color}" class="${i===state.week?"on":""}" title="Settimana ${i+1}, ${SCALE[x.q].label}" data-w="${i}"></i>`).join("");
  const f=flight(state.dep,z);
  $("fd").textContent=Math.round(f.dist).toLocaleString("it-IT")+" km";
  $("fh").textContent=(()=>{const h=Math.floor(f.hrs),mm=Math.round((f.hrs-h)*60/5)*5;return h+"h "+String(mm).padStart(2,"0")})();
  $("fh").title=f.stops?f.stops+(f.stops>1?" scali stimati":" scalo stimato"):"diretto";
  $("fp").textContent="~"+f.months[m].toLocaleString("it-IT")+" €";
  const mx=Math.max(...f.months);
  $("bars").innerHTML=f.months.map((p,i)=>`<div class="${i===m?"cur":""}" style="height:${Math.round(100*p/mx)}%" title="${MESI[i]} ~${p} €">${i===m?`<span>${p}</span>`:""}</div>`).join("");
  $("wk").textContent="Settimana "+(state.week+1)+" · "+MESI[m];
  $("wr").value=state.week;
  document.querySelectorAll("#zlist button").forEach(b=>{const zz=ZONES.find(x=>x.id===b.dataset.id);b.classList.toggle("sel",zz===z);b.querySelector("i").style.background=SCALE[zz.wk[state.week].q].color});
}
function setWeek(w){state.week=(w+52)%52;render();draw()}
$("strip").addEventListener("click",e=>{if(e.target.dataset.w)setWeek(+e.target.dataset.w)});
$("wr").addEventListener("input",e=>setWeek(+e.target.value));
["m1","m2","m3"].forEach(id=>$(id).innerHTML=MESI.map(m=>`<span>${m}</span>`).join(""));
$("legend").innerHTML=SCALE.map(s=>`<span><b style="background:${s.color}"></b>${s.label}</span>`).join("");
$("zlist").innerHTML=ZONES.map(z=>`<button data-id="${z.id}"><i></i>${z.name}</button>`).join("");
$("zlist").addEventListener("click",e=>{const b=e.target.closest("button");if(b)selectZone(ZONES.find(z=>z.id===b.dataset.id))});
$("dep").innerHTML=DEPS.map(d=>`<option value="${d.code}">${d.name} (${d.code})</option>`).join("");
$("arr").innerHTML=ZONES.map(z=>`<option value="${z.id}">${z.airport.code}, ${z.name}</option>`).join("");
$("dep").onchange=e=>{state.dep=DEPS.find(d=>d.code===e.target.value);render();draw()};
$("arr").onchange=e=>selectZone(ZONES.find(z=>z.id===e.target.value));
let timer=null;
$("play").onclick=()=>{if(timer){clearInterval(timer);timer=null;$("play").textContent="Avvia";return}
  $("play").textContent="Ferma";timer=setInterval(()=>setWeek(state.week+1),350)};
// settimana corrente come partenza
(()=>{const n=new Date(),s=new Date(n.getFullYear(),0,1);state.week=Math.min(51,Math.floor((n-s)/6048e5))})();
new ResizeObserver(resize).observe($("gbox"));
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",draw);
new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
render();resize();
