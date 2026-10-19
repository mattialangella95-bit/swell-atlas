// Segnalazioni: chiunque può inviarle, anche senza login (tabella swell_feedback, solo inserimento).
// Si leggono da scripts/feedback.py con la chiave di servizio, mai dall'app.
import {app} from "./app.js";
import {supabase, configured, currentUser} from "./auth.js";

const $ = id => document.getElementById(id);

$("btn-feedback").onclick = () => {
  $("fb-zone").innerHTML = `<option value="">Nessuna zona in particolare</option>` +
    app.ZONES.map(z => `<option value="${z.id}">${z.name} · ${z.region}</option>`).join("");
  $("fb-zone").value = app.state.zone.id;   // zona corrente precompilata
  $("fb-msg").textContent = configured ? "" : "Le segnalazioni non sono ancora attive su questo sito.";
  $("fb-send").disabled = !configured;
  $("dlg-feedback").showModal();
  $("fb-text").focus();
};

$("fb-form").addEventListener("submit", async e => {
  if(e.submitter?.value === "cancel") return;
  e.preventDefault();
  const s = app.state;
  const row = {
    user_id: currentUser()?.id || null,
    kind: $("fb-kind").value,
    zone_id: $("fb-zone").value || null,
    message: $("fb-text").value.trim(),
    page: location.origin + location.pathname,
    app_state: {settimana: s.week + 1, zona: s.zone.id, partenza: s.dep.code},
    user_agent: navigator.userAgent.slice(0, 500),
  };
  if(!row.message) return;
  $("fb-send").disabled = true;
  $("fb-msg").textContent = "Invio in corso…";
  try{
    const sb = await supabase();
    const {error} = await sb.from("swell_feedback").insert(row);   // senza select: la tabella non si legge
    if(error) throw error;
    $("fb-msg").textContent = "Grazie, segnalazione inviata.";
    $("fb-text").value = "";
    setTimeout(() => $("dlg-feedback").open && $("dlg-feedback").close(), 1800);
  }catch(err){
    $("fb-msg").textContent = "Non inviata: " + (err.message || err);
  }finally{ $("fb-send").disabled = false; }
});
