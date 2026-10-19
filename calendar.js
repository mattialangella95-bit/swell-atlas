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

const ui = {month: new Date().getMonth(), group: "airport", view: "list", minQ: 0, maxH: Infinity, onlyFav: false, level: ""};

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

const isFav = e => app.user.favs.has(e.z.id) || (e.z.aliases || []).some(a => app.user.favs.has(a));
const tooBig = m => { const max = RULE.levels[ui.level]?.maxHeight; return max != null && m && m.h75 > max; };

function filtered(){
  return index.filter(e => {
    const m = e.months[ui.month];
    return m && m.q >= ui.minQ && e.f.hrs <= ui.maxH && (!ui.onlyFav || isFav(e));
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
  const by = new Map(), m = ui.month;
  for(const e of list){
    const key = ui.group === "airport" ? e.airport.code : ui.group === "country" ? e.country : bandOf(e.f.hrs);
    if(!by.has(key)) by.set(key, []);
    by.get(key).push(e);
  }
  const out = [...by].map(([key, items]) => {
    items.sort((a, b) => b.months[m].good - a.months[m].good || b.months[m].q - a.months[m].q);
    const mean = items.reduce((s, e) => s + e.months[m].good, 0) / items.length;
    return {key, items, mean};
  });
  // per ore di volo l'ordine è quello delle fasce, altrimenti si parte dal gruppo che rende di più nel mese
  out.sort(ui.group === "distance" ? (a, b) => a.key - b.key : (a, b) => b.mean - a.mean);
  return out;
}

function groupTitle(g){
  const e = g.items[0];
  if(ui.group === "airport") return `${esc(city(e.airport))} <small>${e.airport.code} · ${hours(e.f.hrs)} di volo</small>`;
  if(ui.group === "country") return esc(g.key);
  return bandLabel(g.key);
}

function groupNote(g){
  const m = ui.month, best = g.items[0], good = g.items.filter(e => e.months[m].q >= GOOD).length, n = g.items.length;
  if(n === 1) return "";
  const head = good ? `${good} ${good === 1 ? "zona buona" : "zone buone"} su ${n}` : `${n} zone, nessuna buona questo mese`;
  return `${head}. La migliore è ${esc(best.z.name)}.`;
}

// ---------- vista mese
function row(e){
  const m = e.months[ui.month], s = SCALE[m.q];
  const where = ui.group === "country" ? e.region : [e.region || e.country, ui.group === "airport" ? "" : city(e.airport)].filter(Boolean).join(" · ");
  const pr = app.monthPrices(app.state.dep, e.z, e.f)[ui.month];
  const price = `circa ${pr.value.toLocaleString("it-IT")} € ${pr.real ? "indicativi" : "(stima)"}`;
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
  const head = `<thead><tr><th class="cal-zone"></th>${MESI.map((n, i) => `<th class="${i === ui.month ? "cur" : ""}" title="${MESI_LUNGHI[i]}">${n[0]}</th>`).join("")}</tr></thead>`;
  const body = gs.map(g => `<tr class="cal-grow"><th colspan="13">${groupTitle(g)}</th></tr>` + g.items.map(e =>
    `<tr data-id="${e.z.id}"><th class="cal-zone">${esc(e.z.name)}</th>${e.months.map((m, i) => m
      ? `<td class="${i === ui.month ? "cur" : ""}" style="background:${SCALE[m.q].color}" title="${esc(e.z.name)}, ${MESI_LUNGHI[i]}: ${SCALE[m.q].label}, ${goodDays(m.good)}${tooBig(m) ? ", onde impegnative per il tuo livello" : ""}">${tooBig(m) ? "!" : ""}</td>`
      : `<td></td>`).join("")}</tr>`).join("")).join("");
  return `<div class="cal-year"><table>${head}<tbody>${body}</tbody></table></div>
    <p class="cal-legend">${SCALE.map(s => `<span><i style="background:${s.color}"></i>${s.label}</span>`).join("")}</p>`;
}

function render(){
  buildIndex();
  const list = filtered(), gs = groups(list);
  $("cal-month-name").textContent = MESI_LUNGHI[ui.month];
  document.querySelectorAll("#cal-months button").forEach((b, i) => b.setAttribute("aria-pressed", i === ui.month));
  document.querySelectorAll("#cal-group button").forEach(b => b.setAttribute("aria-pressed", b.dataset.g === ui.group));
  document.querySelectorAll("#cal-view button").forEach(b => b.setAttribute("aria-pressed", b.dataset.v === ui.view));
  const missing = app.ZONES.length - index.length;
  $("cal-info").textContent = `Partendo da ${app.state.dep.label}. ` + (missing ? `Per ora ${index.length} zone con dati, le altre ${missing} stanno arrivando.` : `${list.length} zone.`);
  const active = [ui.minQ > 0, ui.maxH < Infinity, ui.onlyFav, !!ui.level].filter(Boolean).length;
  $("cal-filter-count").textContent = active ? `(${active})` : "";
  $("cal-body").innerHTML = list.length ? (ui.view === "list" ? renderList(gs) : renderYear(gs))
    : `<p class="cal-note">Nessuna zona con questi filtri.</p>`;
}

// ---------- controlli
$("cal-months").innerHTML = MESI.map((n, i) => `<button data-m="${i}" title="${MESI_LUNGHI[i]}">${n}</button>`).join("");
$("cal-minq").innerHTML = SCALE.map((s, i) => `<option value="${i}">${i ? s.label : "qualsiasi"}</option>`).join("");
$("cal-maxh").innerHTML = `<option value="">qualsiasi</option>` + CAL.maxHoursOptions.map(h => `<option value="${h}">${h} ore</option>`).join("");
$("cal-level").innerHTML = `<option value="">non indicato</option>` + LEVELS.map(l => `<option value="${l}">${l}</option>`).join("");

$("cal-months").onclick = e => { const b = e.target.closest("button"); if(b){ ui.month = +b.dataset.m; render(); } };
$("cal-group").onclick = e => { const b = e.target.closest("button"); if(b){ ui.group = b.dataset.g; render(); } };
$("cal-view").onclick = e => { const b = e.target.closest("button"); if(b){ ui.view = b.dataset.v; render(); } };
$("cal-minq").onchange = e => { ui.minQ = +e.target.value; render(); };
$("cal-maxh").onchange = e => { ui.maxH = e.target.value ? +e.target.value : Infinity; render(); };
$("cal-level").onchange = e => { ui.level = e.target.value; render(); };
$("cal-fav").onchange = e => { ui.onlyFav = e.target.checked; render(); };
$("cal-body").onclick = e => {
  const el = e.target.closest("[data-id]");
  if(!el) return;
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
