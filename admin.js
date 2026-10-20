// Segnalazioni dentro l'app, solo per gli admin (tabella swell_admins, regole in 20261020120000_swell_admin.sql).
// I testi arrivano da chiunque: si mostrano solo come testo (textContent), mai come HTML.
import {app} from "./app.js";
import {supabase, onUser} from "./auth.js";

const $ = id => document.getElementById(id);
const KINDS = {bug: "Qualcosa non funziona", miglioria: "Idea o miglioria", dato_zona: "Dato sbagliato su una zona"};
const STATES = {nuova: "nuova", letta: "letta", risolta: "risolta"};
const zoneOf = id => app.ZONES.find(z => z.id === id || (z.aliases || []).includes(id));
const el = (tag, cls, text) => { const e = document.createElement(tag); if(cls) e.className = cls; if(text != null) e.textContent = text; return e; };

let isAdmin = false;

onUser(async u => {
  isAdmin = false;
  $("pf-admin").hidden = true;
  if(!u) return;
  const sb = await supabase();
  const {data, error} = await sb.rpc("swell_is_admin");
  if(error) return;   // migrazione admin non ancora eseguita: niente pannello
  isAdmin = !!data;
  $("pf-admin").hidden = !isAdmin;
  if(isAdmin) updateCount();
});

async function updateCount(){
  const sb = await supabase();
  const {count} = await sb.from("swell_feedback").select("id", {count: "exact", head: true}).eq("status", "nuova");
  $("pf-admin-open").textContent = count ? `Segnalazioni (${count} ${count === 1 ? "nuova" : "nuove"})` : "Segnalazioni";
}

async function load(){
  const sb = await supabase();
  let q = sb.from("swell_feedback").select("id,created_at,kind,zone_id,message,app_state,user_id,status,page,user_agent")
    .order("created_at", {ascending: false}).limit(200);
  if($("adm-new").checked) q = q.eq("status", "nuova");
  const {data, error} = await q;
  const ul = $("adm-list");
  ul.replaceChildren();
  $("adm-msg").textContent = error ? "Non riesco a leggerle: " + error.message : data.length ? "" : "Nessuna segnalazione.";
  if(error) return;
  for(const r of data){
    const li = el("li"), z = zoneOf(r.zone_id), st = r.app_state || {};
    const when = new Date(r.created_at).toLocaleString("it-IT", {day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"});
    li.append(el("div", "adm-meta", `#${r.id} · ${when} · ${KINDS[r.kind] || r.kind} · ${r.user_id ? "utente registrato" : "anonima"} · ${STATES[r.status] || r.status}`));
    li.append(el("div", "adm-text", r.message));
    li.append(el("div", "adm-meta", `${z ? "Zona " + z.name : r.zone_id ? "Zona " + r.zone_id : "Nessuna zona"} · settimana ${st.settimana ?? "—"}, partenza ${st.partenza ?? "—"}` +
      (/iPhone|Android/.test(r.user_agent || "") ? " · da telefono" : "")));
    const act = el("div", "adm-actions");
    if(z){ const b = el("button", "btn", "Apri la zona"); b.onclick = () => { $("dlg-admin").close(); $("dlg-profile").close(); app.selectZone(z); }; act.append(b); }
    for(const s of ["letta", "risolta", "nuova"]){
      if(s === r.status) continue;
      const b = el("button", "btn", s === "nuova" ? "Rimetti come nuova" : "Segna come " + s);
      b.onclick = async () => {
        const {error} = await sb.from("swell_feedback").update({status: s}).eq("id", r.id);
        if(error){ $("adm-msg").textContent = "Non aggiornata: " + error.message; return; }
        await load(); updateCount();
      };
      act.append(b);
    }
    li.append(act);
    ul.append(li);
  }
}

$("pf-admin-open").onclick = () => { if(!isAdmin) return; $("dlg-admin").showModal(); load(); };
$("adm-new").onchange = load;
$("adm-close").onclick = () => $("dlg-admin").close();
