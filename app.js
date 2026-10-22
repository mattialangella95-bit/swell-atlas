// Swell Atlas. Nessun dato qui dentro: zone, aeroporti, scala, stima voli e coste arrivano da data/*.json
const MESI=["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"];
const $=id=>document.getElementById(id);

// ---------- dati
async function loadJSON(path){
  const r=await fetch(path);
  if(!r.ok)throw new Error(path+": HTTP "+r.status);
  return r.json();
}
let ZONES,DEPS,SCALE,FLY,CLIMATE,LAND50,LAND110,COUNTRIES,RULE,COSTS,FILT;
try{
  [ZONES,DEPS,SCALE,FLY,CLIMATE,LAND50,LAND110,COUNTRIES,RULE,COSTS,FILT]=await Promise.all(
    ["data/zones.json","data/airports.json","data/scale.json","data/flight-estimate.json","data/climate.json","data/land-50m.json","data/land-110m.json","data/countries-110m.json",
     "data/quality-rule.json","data/costs.json","data/filters.json"].map(loadJSON));
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
ZONES.forEach(z=>z.wk=getZoneWeeks(z));   // null = dati in arrivo (in grigio)

// partenza: l'ultima scelta resta nel browser
const DEP_KEY="swellatlas.partenza";
function savedDep(){try{return DEPS.find(d=>d.code===localStorage.getItem(DEP_KEY))}catch(e){return null}}
const TRIP_KEY="swellatlas.viaggio";
function savedTrip(){try{return localStorage.getItem(TRIP_KEY)==="a"?"a":"ar"}catch(e){return "ar"}}
const state={week:0,zone:ZONES.find(z=>z.wk)||ZONES[0],dep:savedDep()||DEPS.find(d=>d.code==="GOA")||DEPS[0],
  trip:savedTrip(),mf:{level:"",size:""}};   // trip: "ar" andata e ritorno, "a" solo andata; mf: filtri della pagina Mondo
const TODAY_WEEK=(()=>{const n=new Date(),s=new Date(n.getFullYear(),0,1);return Math.min(51,Math.floor((n-s)/6048e5))})();
// costo della vita del paese (data/costs.json): "€", "€€", "€€€"
const costOf=n=>COSTS.countries[n]?"€".repeat(COSTS.countries[n].level):"";
const costTitle=n=>COSTS.countries[n]?`Costo della vita ${FILT.costLevels[COSTS.countries[n].level]} (indicativo, Banca Mondiale${COSTS.countries[n].manual?", stimato a mano":""})`:"";
const weekMonth=w=>Math.min(11,Math.floor(w*12/52));
const dec=x=>x.toFixed(1).replace(".",",");
const fmtH=w=>dec(w.h25)+"–"+dec(w.h75)+" m";

// ---------- globo
const cv=$("g"),ctx=cv.getContext("2d");
const land50=topojson.feature(LAND50,LAND50.objects.land);
const land110=topojson.feature(LAND110,LAND110.objects.land);
const countries=topojson.feature(COUNTRIES,COUNTRIES.objects.countries).features;   // per scegliere un paese toccando la mappa
const proj=d3.geoOrthographic().clipAngle(90).precision(.4);
const path=d3.geoPath(proj,ctx);
const grat=d3.geoGraticule10();
let W=0,H=0,DPR=1,base=1,zoom=1,dragging=false,anim=null;
proj.rotate([-state.zone.lon,-state.zone.lat*.6]);
function css(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim()}
function resize(){
  const b=$("gbox").getBoundingClientRect();DPR=Math.min(2,window.devicePixelRatio||1);
  if(b.width<40||b.height<40)return;   // riquadro non ancora misurato (ridimensionamenti): niente da disegnare
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
  // paese scelto toccando la mappa
  if(state.place?.feature){ctx.beginPath();path(state.place.feature);ctx.fillStyle=css("--halo");ctx.fill();ctx.strokeStyle=css("--accent");ctx.lineWidth=1.2;ctx.stroke()}
  // rotta volo
  const z=state.zone,d=state.dep;
  ctx.beginPath();path({type:"LineString",coordinates:[[d.lon,d.lat],[z.airport_main.lon,z.airport_main.lat]]});
  ctx.setLineDash([4,4]);ctx.strokeStyle=css("--accent");ctx.lineWidth=1.5;ctx.stroke();ctx.setLineDash([]);
  const c=proj.invert([cx,cy]);
  if(d3.geoDistance([d.lon,d.lat],c)<Math.PI/2){const p=proj([d.lon,d.lat]);ctx.beginPath();ctx.arc(p[0],p[1],3.5,0,7);ctx.fillStyle=css("--fg");ctx.fill()}
  // zone: punti piccoli colorati per qualità, crescono poco con lo zoom; la selezionata ha un anello ed è disegnata sopra le altre
  const fg=css("--fg"),k=Math.min(1.6,Math.sqrt(zoom)),shown=[];
  ZONES.forEach(zz=>{
    if(zz===state.zone||!visible(zz)||d3.geoDistance([zz.lon,zz.lat],c)>Math.PI/2-.02)return;
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
  const p=proj([zz.lon,zz.lat]),rad=(sel?3.4:2.6)*k;
  ctx.beginPath();ctx.arc(p[0],p[1],rad,0,7);ctx.fillStyle=zoneColor(zz);ctx.fill();
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
  if(best)selectCountry(countryOf(best),{zone:best,fly:false});   // uno spot: si apre lui, il suo paese va nelle tendine
  else{const n=countryAt(proj.invert([x,y]));if(n)selectCountry(n)}}   // un paese: il globo ci gira sopra e si apre lo spot migliore
// ---------- paese scelto (tendine o tocco sul globo): globo sugli spot del paese, lo spot migliore della settimana aperto
const countryOf=z=>z.region.split(", ")[0];
const weekGood=z=>z.wk?z.wk[state.week].good:-1,weekQ=z=>z.wk?z.wk[state.week].q:-1;
const bestFirst=(a,b)=>weekGood(b)-weekGood(a)||weekQ(b)-weekQ(a)||a.name.localeCompare(b.name,"it");
const zonesOf=n=>ZONES.filter(z=>countryOf(z)===n&&visible(z)).sort(bestFirst);
// paese sotto il dito: quello dei confini toccati (la zona più vicina al tocco tra le sue); per le isole piccole
// che a questa scala non hanno confini (Maldive, Barbados...) quello della zona più vicina entro 500 km
function countryAt(ll){
  if(!ll)return null;
  const f=countries.find(c=>d3.geoContains(c,ll)),dist=z=>d3.geoDistance(ll,[z.lon,z.lat]);
  let zs=f?ZONES.filter(z=>d3.geoContains(f,[z.airport_local.lon,z.airport_local.lat])||d3.geoContains(f,[z.lon,z.lat])):[];
  if(!zs.length)zs=ZONES.filter(z=>dist(z)*6371<=500);
  return zs.length?countryOf(zs.sort((a,b)=>dist(a)-dist(b))[0]):null;
}
function selectCountry(n,{zone=null,fly=true}={}){
  const zs=zonesOf(n);
  if(!zs.length)return;
  state.country=n;
  const z=zone||zs[0];
  state.place={feature:countries.find(c=>d3.geoContains(c,[z.airport_local.lon,z.airport_local.lat]))||null};
  state.zone=z;$("arr").value=z.id;
  if(fly)flyTo(zs);else draw();
  render();
}
// rotazione e zoom per inquadrare tutti gli spot del paese
function flyTo(zs){
  if(anim)anim.stop();
  const pts=zs.map(z=>[z.lon,z.lat]),c=d3.geoCentroid({type:"MultiPoint",coordinates:pts});
  const spread=Math.max(.12,...pts.map(p=>d3.geoDistance(c,p)));
  const z1=Math.max(1,Math.min(4,.55/Math.sin(Math.min(spread,1.4))));
  const from=proj.rotate(),to=[-c[0],-c[1],0];
  if(to[0]-from[0]>180)to[0]-=360;if(from[0]-to[0]>180)to[0]+=360;
  const it=d3.interpolate(from,to),iz=d3.interpolate(zoom,z1);
  if(matchMedia("(prefers-reduced-motion: reduce)").matches){proj.rotate(to);setZoom(z1);return}
  anim=d3.timer(e=>{const t=Math.min(1,e/1100),k=d3.easeCubicInOut(t);proj.rotate(it(k));zoom=iz(k);proj.scale(base*zoom);if(t>=1){anim.stop();anim=null}draw()});
}
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

// agganci per profile.js e feedback.js: filtro zone visibili (es. solo preferiti) e callback dopo ogni render
const hooks={filter:null,render:[],user:[],prices:null};
// filtri della pagina Mondo (settimana scelta): livello = altezza al 75° percentile entro il massimo del livello;
// misura = altezza mediana nella fascia. La zona aperta resta sempre visibile.
const sizeOk=(id,h)=>{const s=FILT.waveSizes.find(x=>x.id===id);return !s||((s.min==null||h>=s.min)&&(s.max==null||h<s.max))};
function mondoOk(z){
  if(!state.mf.level&&!state.mf.size)return true;
  const w=z.wk?.[state.week];if(!w)return false;
  const max=RULE.levels[state.mf.level]?.maxHeight;
  return (max==null||w.h75<=max)&&sizeOk(state.mf.size,w.h);
}
const visible=z=>z===state.zone||((!hooks.filter||hooks.filter(z))&&mondoOk(z));
// prezzi del mese: prices.js li sostituisce con quelli rilevati; senza, la stima di flight()
// prezzi del mese: prices.js li sostituisce con quelli rilevati (andata e ritorno); senza, la stima di flight().
// Solo andata: per ora sempre stima, come frazione dell'andata e ritorno (oneWayFactor in flight-estimate.json).
function monthPrices(dep,z,f){
  const ar=hooks.prices?hooks.prices(dep,z,f):f.months.map(value=>({value,real:false}));
  return state.trip==="a"?ar.map(p=>({value:Math.round(p.value*FLY.oneWayFactor/10)*10,real:false})):ar;
}
const tripShort=()=>state.trip==="a"?"solo andata":"A/R";
function zoneColor(z){return z.wk?SCALE[z.wk[state.week].q].color:css("--nodata")}

// ---------- voli: ore e scali stimati da distanza e parametri (data/flight-estimate.json); prezzi ancora finti
function km(a,b){return d3.geoDistance([a.lon,a.lat],[b.lon,b.lat])*6371}
function flight(d,z){
  const to=z.airport_main,dist=km(d,to),P=FLY.price;
  const bands=FLY.stopsByDistance[FLY.hubs.includes(d.code)?"fromHub":"fromOther"];
  let stops=bands.find(b=>b.maxKm===null||dist<=b.maxKm).stops;
  stops=Math.min(FLY.maxStops,stops+(FLY.extraStops[to.code]||0));
  const hrs=dist*(1+FLY.detourPerStop*stops)/FLY.speedKmh+FLY.legFixedHours*(stops+1)+FLY.connectionHours*stops;
  const baseP=Math.round((P.base+dist*P.perKm+stops*P.perStop)/10)*10;
  const r=rnd(d.code+z.id);
  const months=P.monthFactor.map(s=>Math.round(baseP*s*(P.noiseMin+r()*P.noiseRange)/10)*10);
  return{dist,stops,hrs,months};
}

// ---------- UI
function selectZone(z,rot=true){state.zone=z;$("arr").value=z.id;if(rot)rotateTo(z);else draw();render()}
function render(){
  const z=state.zone,m=weekMonth(state.week),main=z.airport_main,local=z.airport_local;
  $("zn").textContent=z.name;
  const cn=countryOf(z);
  $("zs").textContent=z.region+" · aeroporto "+main.code+(local.code!==main.code?" (il più vicino è "+local.code+")":"")+(costOf(cn)?" · vita "+costOf(cn):"");
  $("zs").title=costTitle(cn);
  const zq=$("zq");
  if(z.wk){
    const w=z.wk[state.week];
    zq.textContent=SCALE[w.q].label;zq.style.background=SCALE[w.q].color;
    $("sh").textContent=fmtH(w);$("sh").title="mediana "+dec(w.h)+" m";$("sp").textContent=Math.round(w.t)+" s";$("sg").textContent=w.good+"%";
    $("strip").innerHTML=z.wk.map((x,i)=>`<i style="background:${SCALE[x.q].color}" class="${i===state.week?"on":""}${i===TODAY_WEEK?" today":""}" title="Settimana ${i+1}${i===TODAY_WEEK?" (questa)":""}, ${SCALE[x.q].label}" data-w="${i}"></i>`).join("");
  }else{
    zq.textContent="Dati in arrivo";zq.style.background=css("--nodata");
    ["sh","sp","sg"].forEach(id=>{$(id).textContent="—";$(id).title=""});
    $("strip").innerHTML=Array.from({length:52},(_,i)=>`<i style="background:var(--nodata)" class="${i===state.week?"on":""}${i===TODAY_WEEK?" today":""}" title="Settimana ${i+1}, dati in arrivo" data-w="${i}"></i>`).join("");
  }
  const f=flight(state.dep,z);
  $("fd").textContent=Math.round(f.dist).toLocaleString("it-IT")+" km";
  $("fh").textContent=(()=>{const t=Math.round(f.hrs*12)*5;return Math.floor(t/60)+"h "+String(t%60).padStart(2,"0")})();   // arrotondato a 5 minuti
  $("fs").textContent=f.stops?f.stops+(f.stops>1?" scali stimati":" scalo stimato"):"diretto stimato";
  // prezzi: rilevati (prices.js, swell_prices) dove ci sono, altrimenti la stima; sempre indicativi
  const pm=monthPrices(state.dep,z,f),cur=pm[m],eur=v=>v.toLocaleString("it-IT")+" €";
  $("fp").textContent="circa "+eur(cur.value);
  $("bars-t").textContent="Prezzo indicativo "+(state.trip==="a"?"di sola andata":"andata e ritorno")+", mese per mese";
  document.querySelectorAll("#trip button").forEach(b=>b.setAttribute("aria-pressed",b.dataset.t===state.trip));
  $("fps").textContent=tripShort()+" · "+(cur.real?"indicativo, rilevato il "+new Date(cur.observed).toLocaleDateString("it-IT",{day:"numeric",month:"short"}):"stima");
  const mx=Math.max(...pm.map(p=>p.value));
  $("bars").innerHTML=pm.map((p,i)=>`<div class="${i===m?"cur":""} ${p.real?"":"est"}" style="height:${Math.round(100*p.value/mx)}%" title="${MESI[i]}: circa ${eur(p.value)}, ${p.real?"indicativo (ricerche recenti su Aviasales)":"stima"}">${i===m?`<span>${p.value}</span>`:""}</div>`).join("");
  $("wk").textContent="Settimana "+(state.week+1)+" · "+MESI[m]+(state.week===TODAY_WEEK?" · questa settimana":"");
  $("wr").value=state.week;
  if(state.country&&countryOf(z)!==state.country)state.country=countryOf(z);   // spot scelto da fuori (arrivo, calendario)
  updateFinder();
  hooks.render.forEach(f=>f(z));
}
function setWeek(w){state.week=(w+52)%52;if(state.mf.level||state.mf.size)onMondoFilter();else{render();draw()}}
// barra colorata dell'anno come un cursore: tocco o trascinamento del dito
let stripDrag=false;
const stripAt=e=>{const b=$("strip").getBoundingClientRect();setWeek(Math.max(0,Math.min(51,Math.floor((e.clientX-b.left)/b.width*52))))};
$("strip").addEventListener("pointerdown",e=>{stripDrag=true;$("strip").setPointerCapture(e.pointerId);stripAt(e)});
$("strip").addEventListener("pointermove",e=>{if(stripDrag)stripAt(e)});
["pointerup","pointercancel"].forEach(t=>$("strip").addEventListener(t,()=>stripDrag=false));
// prezzo andata e ritorno o solo andata, ricordato nel browser
$("trip").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;state.trip=b.dataset.t;try{localStorage.setItem(TRIP_KEY,state.trip)}catch(x){}
  render();document.dispatchEvent(new CustomEvent("swell:prezzi"))});
// filtri della pagina Mondo, sotto la timeline
$("mf-level").innerHTML=`<option value="">tutti i livelli</option>`+Object.keys(RULE.levels).filter(k=>!k.startsWith("_")).map(l=>`<option value="${l}">${l}</option>`).join("");
$("mf-size").innerHTML=`<option value="">qualsiasi</option>`+FILT.waveSizes.map(s=>`<option value="${s.id}">${s.label}</option>`).join("");
function onMondoFilter(){
  state.mf={level:$("mf-level").value,size:$("mf-size").value};
  const n=[state.mf.level,state.mf.size].filter(Boolean).length,shown=ZONES.filter(visible).length;
  $("mf-count").textContent=n?`(${n})`:"";
  $("mf-note").textContent=n?`${shown} spot su ${ZONES.length} nella settimana ${state.week+1}. Cambia settimana e il filtro si aggiorna.`:"";
  if(state.country&&!zonesOf(state.country).length)state.country=null;
  render();draw();
}
$("mf-level").onchange=onMondoFilter;$("mf-size").onchange=onMondoFilter;
$("wr").addEventListener("input",e=>setWeek(+e.target.value));
["m1","m2","m3"].forEach(id=>$(id).innerHTML=MESI.map(m=>`<span>${m}</span>`).join(""));
$("legend").innerHTML=SCALE.map(s=>`<span><b style="background:${s.color}"></b>${s.label}</span>`).join("");
// ---------- tendine Paese / Spot e spot del paese sotto il globo
const goodTxt=g=>{const n=Math.round(g/10);return n===0?(g>0?"quasi mai buono":"mai buono"):n===10?"buono quasi ogni giorno":`${n} giorni buoni su 10`};
const esc=x=>String(x).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function updateFinder(){
  const names=[...new Set(ZONES.filter(visible).map(countryOf))].sort((a,b)=>a.localeCompare(b,"it"));
  $("sel-country").innerHTML=`<option value="">Scegli un paese…</option>`+names.map(n=>`<option value="${esc(n)}">${esc(n)} (${zonesOf(n).length})${costOf(n)?" · "+costOf(n):""}</option>`).join("");
  $("sel-country").value=state.country||"";
  const zs=state.country?zonesOf(state.country):[];
  $("sel-spot").disabled=!zs.length;
  $("sel-spot").innerHTML=zs.length?zs.map(z=>`<option value="${z.id}">${esc(z.name)}${z.wk?" · "+goodTxt(weekGood(z)):""}</option>`).join(""):`<option>prima scegli un paese</option>`;
  if(zs.includes(state.zone))$("sel-spot").value=state.zone.id;
  $("pl-t").textContent=state.country?`Spot in ${state.country}`:"Spot per paese";
  $("pl-info").textContent=state.country?`Dal migliore al peggiore nella settimana ${state.week+1}.`:"Scegli un paese dalla tendina sopra il globo, oppure toccalo sul globo.";
  $("zlist").innerHTML=zs.map(z=>{const w=z.wk?.[state.week],s=w?SCALE[w.q]:null;
    return `<button class="cal-row${z===state.zone?" sel":""}" data-id="${z.id}" style="--q:${s?s.color:"var(--nodata)"}">
      <span class="cal-main"><b>${esc(z.name)}</b> <span class="cal-where">${esc(z.region.split(", ").slice(1).join(", "))}</span></span>
      <span class="cal-good">${w?goodTxt(w.good):"dati in arrivo"}</span>
      <span class="cal-detail">${w?`<span class="q" style="--q:${s.color}">${s.label}</span> · onde ${dec(w.h25)}–${dec(w.h75)} m`:""}</span></button>`}).join("");
}
function buildZoneList(){render()}
$("sel-country").addEventListener("change",e=>{if(e.target.value)selectCountry(e.target.value);else{state.country=null;state.place=null;render();draw()}});
$("sel-spot").addEventListener("change",e=>{const z=ZONES.find(x=>x.id===e.target.value);if(z)selectZone(z)});
$("zlist").addEventListener("click",e=>{const b=e.target.closest("[data-id]");if(b){selectZone(ZONES.find(z=>z.id===b.dataset.id));$("gbox").scrollIntoView({behavior:"smooth",block:"start"})}});
// partenza: campo con ricerca per nome o codice IATA (datalist), tutti gli aeroporti italiani large e medium
const depText=d=>`${d.label} (${d.code})`;
$("deps").innerHTML=DEPS.map(d=>`<option value="${depText(d)}" label="${d.name}"></option>`).join("");
$("dep").value=depText(state.dep);
function findDep(v){
  v=v.trim();const code=(v.match(/\(([A-Za-z]{3})\)$/)||[,v])[1].toUpperCase();
  return DEPS.find(d=>d.code===code)||DEPS.find(d=>depText(d).toLowerCase()===v.toLowerCase());
}
function setDep(d){state.dep=d;$("dep").value=depText(d);try{localStorage.setItem(DEP_KEY,d.code)}catch(e){}render();draw()}
$("dep").addEventListener("change",e=>{const d=findDep(e.target.value);if(d)setDep(d);else e.target.value=depText(state.dep)});
$("dep").addEventListener("focus",e=>e.target.select());
$("arr").innerHTML=ZONES.map(z=>`<option value="${z.id}">${z.airport_main.code}, ${z.name}${z.wk?"":" (dati in arrivo)"}</option>`).join("");
$("arr").onchange=e=>selectZone(ZONES.find(z=>z.id===e.target.value));
let timer=null;
$("play").onclick=()=>{if(timer){clearInterval(timer);timer=null;$("play").textContent="Avvia";return}
  $("play").textContent="Ferma";timer=setInterval(()=>setWeek(state.week+1),350)};
// settimana corrente come partenza
(()=>{const n=new Date(),s=new Date(n.getFullYear(),0,1);state.week=Math.min(51,Math.floor((n-s)/6048e5))})();
new ResizeObserver(resize).observe($("gbox"));
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",draw);
new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
buildZoneList();resize();

export const app={state,ZONES,DEPS,SCALE,MESI,CLIMATE,COSTS,FILT,DEP_KEY,hooks,depText,findDep,setDep,selectZone,flight,monthPrices,tripShort,costOf,costTitle,
  user:{loggedIn:false,favs:new Set(),level:null},   // aggiornato da profile.js, letto da calendar.js
  project:ll=>proj(ll),   // coordinate -> punto sullo schermo del globo
  refresh(){buildZoneList();render();draw()}};
