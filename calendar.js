// Calendario: scelgo un mese e vedo dove conviene andare. Usa i riepiloghi mensili di climate.json
// (build_climate.py) e la stima voli di app.js. Le zone senza climatologia sono escluse.
import {app} from "./app.js";

const $ = id => document.getElementById(id);
const load = p => fetch(p).then(r => { if(!r.ok) throw new Error(p + ": HTTP " + r.status); return r.json(); });
const [RULE, CAL] = await Promise.all([load("data/quality-rule.json"), load("data/calendar.json")]);

const {SCALE, MESI, CLIMATE} = app;
const MESI_LUNGHI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
const GOOD = SCALE.findIndex(s => s.label === "Good");
const MF = CLIMATE.monthFields, mi = k => MF.indexOf(k);
const LEVELS = Object.keys(RULE.levels).filter(k => !k.startsWith("_"));
const dec = x => x.toFixed(1).replace(".", ",");
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

// "5½ h", "24 h": a mezz'ora, scritto come lo direbbe una persona
const hours = h => { const t = Math.round(h * 2) / 2; return (t < 1 ? "meno di 1" : Math.floor(t) + (t % 1 ? "½" : "")) + " h"; };
// "4 giorni buoni su 10" invece di "38%"
const goodDays = g => { const n = Math.round(g / 10); return n === 0 ? (g > 0 ? "quasi mai buono" : "mai buono") : n === 10 ? "buono quasi ogni giorno" : `${n} giorni buoni su 10`; };
// città dell'aeroporto pulita: "Kuta, Badung" -> "Kuta", "Genova (GE)" -> "Genova"
const city = a => CAL.airportNames[a.code] || (a.city || a.name).replace(/\s*\(.*?\)/g, "").split(/[,/]/)[0].trim();

const ui = {month: new Date().getMonth(), group: "airport", view: "list", minQ: 0, maxH: Infinity, onlyFav: false, level: "",
  size: "", maxPrice: Infinity, maxCost: 3};
const {FILT} = app;
const sizeOk = (id, h) => { const s = FILT.waveSizes.find(x => x.id === id); return !s || ((s.min == null || h >= s.min) && (s.max == null || h < s.max)); };
const priceOf = e => app.monthPrices(app.state.dep, e.z, e.f)[priceMonth()];
const costLevel = e => app.COSTS.countries[e.country]?.level ?? 2;

// ---------- indice zone: dati del mese e volo stimato dalla partenza scelta (logica voli di app.js)
let index = [], indexDep = null;
function buildIndex(){
  if(indexDep === app.state.dep) return;
  indexDep = app.state.dep;
  index = app.ZONES.filter(z => CLIMATE.zones[z.id]?.months).map(z => {
    const [country, ...region] = z.region.split(", ");
    const months = CLIMATE.zones[z.id].months.map(m => m && {q: m[mi("q")], h25: m[mi("h25")], h75: m[mi("h75")],
      t: m[mi("t50")], good: m[mi("good")], offshore: m[mi("offshore")]});
    return {z, country, region: region.join(", "), airport: z.airport_main, f: app.flight(app.state.dep, z), months};
  });
}

// ---------- periodo "dal ... al ...": i dati sono per settimana, ogni settimana pesa quanti giorni cadono nel periodo
const DAY = 864e5;
function rangeDays(){
  const a = new Date(ui.range.from + "T00:00:00Z"), b = new Date(ui.range.to + "T00:00:00Z");
  if(b < a) b.setUTCFullYear(b.getUTCFullYear() + 1);   // es. dal 28 dicembre al 10 gennaio
  const out = [];
  for(let d = a; d <= b && out.length < 366; d = new Date(+d + DAY)) out.push(d);
  return out;
}
let weights = null, midMonth = 0;   // settimana -> giorni nel periodo; mese a metà periodo (per il prezzo)
function computeWeights(){
  weights = null;
  if(!ui.range) return;
  const days = rangeDays();
  weights = new Map();
  for(const d of days){
    const w = Math.min(51, Math.floor((d - Date.UTC(d.getUTCFullYear(), 0, 1)) / DAY / 7));
    weights.set(w, (weights.get(w) || 0) + 1);
  }
  midMonth = days[Math.floor(days.length / 2)].getUTCMonth();
}
function aggregate(wk){
  let W = 0, good = 0, h25 = 0, h75 = 0, t = 0;
  const qs = [];
  for(const [w, n] of weights){
    const x = wk[w];
    W += n; good += n * x.good; h25 += n * x.h25; h75 += n * x.h75; t += n * x.t; qs.push([x.q, n]);
  }
  qs.sort((a, b) => a[0] - b[0]);
  let acc = 0, q = qs[0][0];
  for(const [v, n] of qs){ acc += n; if(acc >= W / 2){ q = v; break; } }   // classe del giorno tipico nel periodo
  return {q, good: Math.round(good / W), h25: h25 / W, h75: h75 / W, t: t / W};
}
// dati della selezione: il mese scelto oppure il periodo
const sel = e => weights ? (e.agg ||= aggregate(e.z.wk)) : e.months[ui.month];
const priceMonth = () => weights ? midMonth : ui.month;
function rangeLabel(){
  const d = rangeDays(), a = d[0], b = d[d.length - 1];
  const m = x => MESI_LUNGHI[x.getUTCMonth()];
  return a.getUTCMonth() === b.getUTCMonth() && d.length < 40 ? `dal ${a.getUTCDate()} al ${b.getUTCDate()} ${m(b)}` : `dal ${a.getUTCDate()} ${m(a)} al ${b.getUTCDate()} ${m(b)}`;
}

const isFav = e => app.user.favs.has(e.z.id) || (e.z.aliases || []).some(a => app.user.favs.has(a));
const tooBig = m => { const max = RULE.levels[ui.level]?.maxHeight; return max != null && m && m.h75 > max; };

function filtered(){
  return index.filter(e => {
    const m = sel(e);
    return m && m.q >= ui.minQ && e.f.hrs <= ui.maxH && (!ui.onlyFav || isFav(e)) && sizeOk(ui.size, (m.h25 + m.h75) / 2)
      && priceOf(e).value <= ui.maxPrice && costLevel(e) <= ui.maxCost;
  });
}

function bandOf(h){
  const b = CAL.flightBandsHours, i = b.findIndex(x => h <= x);
  return i < 0 ? b.length : i;
}
function bandLabel(i){
  const b = CAL.flightBandsHours;
  return i === 0 ? `Fino a ${b[0]} ore di volo` : i === b.length ? `Più di ${b[b.length - 1]} ore di volo` : `Da ${b[i - 1]} a ${b[i]} ore di volo`;
}

function groups(list){
  const by = new Map();
  for(const e of list){
    const key = ui.group === "airport" ? e.airport.code : ui.group === "country" ? e.country : bandOf(e.f.hrs);
    if(!by.has(key)) by.set(key, []);
    by.get(key).push(e);
  }
  const out = [...by].map(([key, items]) => {
    items.sort((a, b) => sel(b).good - sel(a).good || sel(b).q - sel(a).q);
    const mean = items.reduce((s, e) => s + sel(e).good, 0) / items.length;
    return {key, items, mean};
  });
  // per ore di volo l'ordine è quello delle fasce, altrimenti si parte dal gruppo che rende di più nel mese
  out.sort(ui.group === "distance" ? (a, b) => a.key - b.key : (a, b) => b.mean - a.mean);
  return out;
}

function groupTitle(g){
  const e = g.items[0];
  if(ui.group === "airport") return `${esc(city(e.airport))} <small>${e.airport.code} · ${hours(e.f.hrs)} di volo</small>`;
  if(ui.group === "country") return `${esc(g.key)}${app.costOf(g.key) ? ` <small title="${esc(app.costTitle(g.key))}">vita ${app.costOf(g.key)}</small>` : ""}`;
  return bandLabel(g.key);
}

function groupNote(g){
  const best = g.items[0], good = g.items.filter(e => sel(e).q >= GOOD).length, n = g.items.length;
  if(n === 1) return "";
  const head = good ? `${good} ${good === 1 ? "zona buona" : "zone buone"} su ${n}` : `${n} zone, nessuna buona ${weights ? "in questo periodo" : "questo mese"}`;
  return `${head}. La migliore è ${esc(best.z.name)}.`;
}

// ---------- vista mese
function row(e){
  const m = sel(e), s = SCALE[m.q];
  const where = ui.group === "country" ? e.region : [e.region || e.country, ui.group === "airport" ? "" : city(e.airport)].filter(Boolean).join(" · ");
  const pr = priceOf(e);
  const price = `circa ${pr.value.toLocaleString("it-IT")} € ${app.tripShort()} ${pr.real ? "indicativi" : "(stima)"}`;
  const detail = [`<span class="q" style="--q:${s.color}">${s.label}</span>`, `onde ${dec(m.h25)}–${dec(m.h75)} m`,
    ui.group === "airport" ? "" : `${hours(e.f.hrs)} di volo`, price].filter(Boolean).join(" · ");
  return `<button class="cal-row" data-id="${e.z.id}" style="--q:${s.color}">
    <span class="cal-main"><b>${esc(e.z.name)}</b> <span class="cal-where">${esc(where)}</span></span>
    <span class="cal-good">${goodDays(m.good)}</span>
    <span class="cal-detail">${detail}${tooBig(m) ? ` · <em>onde impegnative per il tuo livello</em>` : ""}</span>
  </button>`;
}
function renderList(gs){
  return gs.map(g => { const note = groupNote(g); return `<section class="cal-group">
    <h3>${groupTitle(g)}</h3>${note ? `<p class="cal-note">${note}</p>` : ""}
    ${g.items.map(row).join("")}
  </section>`; }).join("");
}

// ---------- vista anno: zone per 12 mesi, righe raggruppate, intestazioni fisse
function renderYear(gs){
  const cur = weights ? new Set(rangeDays().map(d => d.getUTCMonth())) : new Set([ui.month]);
  const head = `<thead><tr><th class="cal-zone"></th>${MESI.map((n, i) => `<th class="${cur.has(i) ? "cur" : ""}" title="${MESI_LUNGHI[i]}">${n[0]}</th>`).join("")}</tr></thead>`;
  const body = gs.map(g => `<tr class="cal-grow"><th colspan="13">${groupTitle(g)}</th></tr>` + g.items.map(e =>
    `<tr data-id="${e.z.id}"><th class="cal-zone">${esc(e.z.name)}</th>${e.months.map((m, i) => m
      ? `<td class="${cur.has(i) ? "cur" : ""}" style="background:${SCALE[m.q].color}" title="${esc(e.z.name)}, ${MESI_LUNGHI[i]}: ${SCALE[m.q].label}, ${goodDays(m.good)}${tooBig(m) ? ", onde impegnative per il tuo livello" : ""}">${tooBig(m) ? "!" : ""}</td>`
      : `<td></td>`).join("")}</tr>`).join("")).join("");
  return `<div class="cal-year"><table>${head}<tbody>${body}</tbody></table></div>
    <p class="cal-legend">${SCALE.map(s => `<span><i style="background:${s.color}"></i>${s.label}</span>`).join("")}</p>`;
}

function render(){
  buildIndex();
  computeWeights();
  index.forEach(e => e.agg = null);
  const list = filtered(), gs = groups(list);
  $("cal-t").innerHTML = weights ? `Dove andare <span id="cal-month-name">${rangeLabel()}</span>` : `Dove andare ${/^[aeiou]/.test(MESI_LUNGHI[ui.month]) ? "ad" : "a"} <span id="cal-month-name">${MESI_LUNGHI[ui.month]}</span>`;
  document.querySelectorAll("#cal-months button").forEach((b, i) => b.setAttribute("aria-pressed", !weights && i === ui.month));
  $("cal-range-clear").hidden = !weights;
  document.querySelectorAll("#cal-group button").forEach(b => b.setAttribute("aria-pressed", b.dataset.g === ui.group));
  document.querySelectorAll("#cal-view button").forEach(b => b.setAttribute("aria-pressed", b.dataset.v === ui.view));
  const missing = app.ZONES.length - index.length;
  $("cal-info").textContent = `Partendo da ${app.state.dep.label}. ` + (missing ? `Per ora ${index.length} zone con dati, le altre ${missing} stanno arrivando.` : `${list.length} zone.`);
  const active = [ui.minQ > 0, ui.maxH < Infinity, ui.onlyFav, !!ui.level, !!ui.size, ui.maxPrice < Infinity, ui.maxCost < 3].filter(Boolean).length;
  $("cal-filter-count").textContent = active ? `(${active})` : "";
  $("cal-body").innerHTML = list.length ? (ui.view === "list" ? renderList(gs) : renderYear(gs))
    : `<p class="cal-note">Nessuna zona con questi filtri.</p>`;
}

// ---------- controlli
$("cal-months").innerHTML = MESI.map((n, i) => `<button data-m="${i}" title="${MESI_LUNGHI[i]}">${n}</button>`).join("");
$("cal-minq").innerHTML = SCALE.map((s, i) => `<option value="${i}">${i ? s.label : "qualsiasi"}</option>`).join("");
$("cal-maxh").innerHTML = `<option value="">qualsiasi</option>` + CAL.maxHoursOptions.map(h => `<option value="${h}">${h} ore</option>`).join("");
$("cal-level").innerHTML = `<option value="">non indicato</option>` + LEVELS.map(l => `<option value="${l}">${l}</option>`).join("");
$("cal-size").innerHTML = `<option value="">qualsiasi</option>` + FILT.waveSizes.map(s => `<option value="${s.id}">${s.label}</option>`).join("");
$("cal-price").innerHTML = `<option value="">qualsiasi</option>` + FILT.maxPriceOptions.map(v => `<option value="${v}">${v} €</option>`).join("");
$("cal-cost").innerHTML = `<option value="3">qualsiasi</option><option value="2">fino a €€</option><option value="1">solo €</option>`;
$("cal-size").onchange = e => { ui.size = e.target.value; render(); };
$("cal-price").onchange = e => { ui.maxPrice = e.target.value ? +e.target.value : Infinity; render(); };
$("cal-cost").onchange = e => { ui.maxCost = +e.target.value; render(); };

$("cal-months").onclick = e => { const b = e.target.closest("button"); if(b){ ui.month = +b.dataset.m; clearRange(); render(); } };
function clearRange(){ ui.range = null; $("cal-from").value = ""; $("cal-to").value = ""; }
function onRange(){
  const from = $("cal-from").value, to = $("cal-to").value;
  if(from && to){ ui.range = {from, to}; render(); }
}
$("cal-from").onchange = () => { if($("cal-from").value && !$("cal-to").value) $("cal-to").value = $("cal-from").value; onRange(); };
$("cal-to").onchange = onRange;
$("cal-range-clear").onclick = () => { clearRange(); render(); };
$("cal-group").onclick = e => { const b = e.target.closest("button"); if(b){ ui.group = b.dataset.g; render(); } };
$("cal-view").onclick = e => { const b = e.target.closest("button"); if(b){ ui.view = b.dataset.v; render(); } };
$("cal-minq").onchange = e => { ui.minQ = +e.target.value; render(); };
$("cal-maxh").onchange = e => { ui.maxH = e.target.value ? +e.target.value : Infinity; render(); };
$("cal-level").onchange = e => { ui.level = e.target.value; render(); };
$("cal-fav").onchange = e => { ui.onlyFav = e.target.checked; render(); };
$("cal-body").onclick = e => {
  const el = e.target.closest("[data-id]");
  if(!el) return;
  app.hooks.showPage?.("mondo");
  app.selectZone(app.ZONES.find(z => z.id === el.dataset.id));   // apre la scheda e ruota il globo
  $("gbox").scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start"});
};

// con login: preferiti e livello dal profilo; senza login il livello si sceglie nei filtri
app.hooks.user.push(u => {
  $("cal-fav-box").hidden = !u.loggedIn;
  if(!u.loggedIn){ ui.onlyFav = false; $("cal-fav").checked = false; }
  if(u.level && LEVELS.includes(u.level)){ ui.level = u.level; $("cal-level").value = u.level; }
  render();
});
// prezzi rilevati arrivati da Supabase (prices.js)
document.addEventListener("swell:prezzi", () => render());
// la partenza cambia la stima voli: si ricalcola al prossimo render dell'app
app.hooks.render.push(() => { if(indexDep !== app.state.dep) render(); });

render();
