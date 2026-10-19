// Calendario: scelgo un mese e vedo dove conviene andare. Usa i riepiloghi mensili di climate.json
// (build_climate.py) e la stima voli di app.js. Le zone senza climatologia sono escluse.
import {app} from "./app.js";

const $ = id => document.getElementById(id);
const load = p => fetch(p).then(r => { if(!r.ok) throw new Error(p + ": HTTP " + r.status); return r.json(); });
const [RULE, CAL] = await Promise.all([load("data/quality-rule.json"), load("data/calendar.json")]);

const {SCALE, MESI, CLIMATE} = app;
const GOOD = SCALE.findIndex(s => s.label === "Good");
const MF = CLIMATE.monthFields, mi = k => MF.indexOf(k);
const LEVELS = Object.keys(RULE.levels).filter(k => !k.startsWith("_"));
const dec = x => x.toFixed(1).replace(".", ",");
const fmtHours = h => { const t = Math.round(h * 2) / 2; return (Number.isInteger(t) ? t : dec(t)) + " h"; };
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

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
  return i === 0 ? `Entro ${b[0]} h di volo` : i === b.length ? `Oltre ${b[b.length - 1]} h di volo` : `${b[i - 1]}-${b[i]} h di volo`;
}

function groups(list){
  const by = new Map(), m = ui.month;
  for(const e of list){
    const key = ui.group === "airport" ? e.airport.code : ui.group === "country" ? e.z.region : bandOf(e.f.hrs);
    if(!by.has(key)) by.set(key, []);
    by.get(key).push(e);
  }
  const out = [...by].map(([key, items]) => {
    items.sort((a, b) => b.months[m].good - a.months[m].good || b.months[m].q - a.months[m].q);
    const mean = items.reduce((s, e) => s + e.months[m].good, 0) / items.length;
    const label = ui.group === "airport" ? `${key} · ${items[0].airport.name}` : ui.group === "country" ? key : bandLabel(key);
    return {key, label, items, mean};
  });
  // per distanza l'ordine è quello delle fasce, altrimenti per qualità media del gruppo nel mese
  out.sort(ui.group === "distance" ? (a, b) => a.key - b.key : (a, b) => b.mean - a.mean);
  return out;
}

function summary(g){
  const m = ui.month, good = g.items.filter(e => e.months[m].q >= GOOD).length, best = g.items[0];
  const hrs = g.items.map(e => e.f.hrs), lo = Math.min(...hrs), hi = Math.max(...hrs);
  const fly = Math.abs(hi - lo) < .5 ? fmtHours(lo) : `${fmtHours(lo).replace(" h", "")}-${fmtHours(hi)}`;
  return `${good} ${good === 1 ? "zona" : "zone"} Good+ · migliore ${esc(best.z.name)} (${best.months[m].good}%) · volo ~${fly}`;
}

// ---------- vista elenco
function row(e){
  const m = e.months[ui.month], s = SCALE[m.q];
  return `<button class="cal-row" data-id="${e.z.id}">
    <span class="cal-name">${esc(e.z.name)}<small>${esc(e.region || e.country)}</small></span>
    <span class="chip" style="background:${s.color}">${s.label}</span>
    <span class="cal-num" title="giorni Good o meglio">${m.good}%</span>
    <span class="cal-num" title="altezza 25-75%, al largo">${dec(m.h25)}–${dec(m.h75)} m</span>
    <span class="cal-num" title="ore di volo stimate da ${esc(app.state.dep.code)}">~${fmtHours(e.f.hrs)}</span>
    ${tooBig(m) ? `<span class="cal-warn">onde impegnative per il tuo livello</span>` : ""}
  </button>`;
}
function renderList(gs){
  return gs.map(g => `<section class="cal-group">
    <h3>${esc(g.label)}</h3><p class="cal-sum">${summary(g)}</p>
    ${g.items.map(row).join("")}
  </section>`).join("");
}

// ---------- vista anno: zone per 12 mesi, righe raggruppate, intestazioni fisse
function renderYear(gs){
  const head = `<thead><tr><th class="cal-zone">Zona</th>${MESI.map((n, i) => `<th class="${i === ui.month ? "cur" : ""}">${n}</th>`).join("")}</tr></thead>`;
  const body = gs.map(g => `<tr class="cal-grow"><th colspan="13">${esc(g.label)}</th></tr>` + g.items.map(e =>
    `<tr data-id="${e.z.id}"><th class="cal-zone">${esc(e.z.name)}</th>${e.months.map((m, i) => m
      ? `<td class="${i === ui.month ? "cur" : ""}" style="background:${SCALE[m.q].color}" title="${MESI[i]}: ${SCALE[m.q].label}, ${m.good}% giorni Good+${tooBig(m) ? ", onde impegnative per il tuo livello" : ""}">${tooBig(m) ? "!" : ""}</td>`
      : `<td></td>`).join("")}</tr>`).join("")).join("");
  return `<div class="cal-year"><table>${head}<tbody>${body}</tbody></table></div>`;
}

function render(){
  buildIndex();
  const list = filtered(), gs = groups(list);
  document.querySelectorAll("#cal-months button").forEach((b, i) => b.setAttribute("aria-pressed", i === ui.month));
  document.querySelectorAll("#cal-group button").forEach(b => b.setAttribute("aria-pressed", b.dataset.g === ui.group));
  document.querySelectorAll("#cal-view button").forEach(b => b.setAttribute("aria-pressed", b.dataset.v === ui.view));
  const missing = app.ZONES.length - index.length;
  $("cal-info").textContent = `${MESI[ui.month]} da ${app.depText(app.state.dep)}: ${list.length} zone` +
    (missing ? ` (altre ${missing} senza dati, ancora in arrivo)` : "");
  $("cal-body").innerHTML = list.length ? (ui.view === "list" ? renderList(gs) : renderYear(gs))
    : `<p class="note">Nessuna zona con questi filtri.</p>`;
}

// ---------- controlli
$("cal-months").innerHTML = MESI.map((n, i) => `<button class="btn" data-m="${i}">${n}</button>`).join("");
$("cal-minq").innerHTML = SCALE.map((s, i) => `<option value="${i}">${i ? s.label + " o meglio" : "Tutte"}</option>`).join("");
$("cal-maxh").innerHTML = `<option value="">Qualsiasi</option>` + CAL.maxHoursOptions.map(h => `<option value="${h}">Entro ${h} h</option>`).join("");
$("cal-level").innerHTML = `<option value="">Nessuno</option>` + LEVELS.map(l => `<option value="${l}">${l[0].toUpperCase() + l.slice(1)}</option>`).join("");

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

// con login: preferiti e livello dal profilo; senza login il livello si sceglie qui
app.hooks.user.push(u => {
  $("cal-fav-box").hidden = !u.loggedIn;
  if(!u.loggedIn){ ui.onlyFav = false; $("cal-fav").checked = false; }
  if(u.level && LEVELS.includes(u.level)){ ui.level = u.level; $("cal-level").value = u.level; }
  render();
});
// la partenza cambia la stima voli: si ricalcola al prossimo render dell'app
app.hooks.render.push(() => { if(indexDep !== app.state.dep) render(); });

render();
