// Profilo e preferiti su Supabase (tabelle swell_profiles e swell_favorites, ognuno vede solo i suoi).
// Il livello surf per ora si salva e basta: servirà per adattare la scala qualità.
import {app} from "./app.js";
import {supabase, configured, onUser, currentUser, openLogin, signOut, ready} from "./auth.js";

const $ = id => document.getElementById(id);
const favs = new Map();   // zone_id -> nota
let profile = null;

// id vecchi di zone confluite in un'altra (alias in zones.json) -> id attuale, così i preferiti non si perdono
const alias = new Map(app.ZONES.flatMap(z => (z.aliases || []).map(a => [a, z.id])));
const currentId = id => alias.get(id) || id;
const zoneById = id => app.ZONES.find(z => z.id === currentId(id));
const depByCode = code => app.DEPS.find(d => d.code === code);

if(configured){ $("btn-account").hidden = false; $("fav").hidden = false; }
$("btn-account").onclick = () => currentUser() ? openProfile() : openLogin();

onUser(async u => {
  favs.clear(); profile = null;
  if(u){ await loadProfile(u); await loadFavs(); }
  $("only-fav-box").hidden = !u;
  if(!u){ $("only-fav").checked = false; app.hooks.filter = null; }
  $("btn-account").textContent = u ? (profile?.display_name || "Profilo") : "Accedi";
  publishUser();
  app.refresh();
});

// preferiti e livello per le altre viste (calendario)
function publishUser(){
  app.user = {loggedIn: !!currentUser(), favs: new Set(favs.keys()), level: profile?.surf_level || null};
  app.hooks.user.forEach(f => f(app.user));
}

async function loadProfile(u){
  const sb = await supabase();
  let {data, error} = await sb.from("swell_profiles").select("*").eq("id", u.id).maybeSingle();
  if(error) return console.error(error);
  if(!data){
    // primo accesso: crea il profilo e copia la partenza già scelta in questo browser
    let saved = null;
    try{ saved = localStorage.getItem(app.DEP_KEY); }catch(e){}
    const r = await sb.from("swell_profiles").insert({id: u.id, home_airport: depByCode(saved) ? saved : null}).select().single();
    if(r.error) return console.error(r.error);
    data = r.data;
  }
  profile = data;
  const d = depByCode(profile.home_airport);
  if(d && d !== app.state.dep) app.setDep(d);
}

async function loadFavs(){
  const sb = await supabase();
  const {data, error} = await sb.from("swell_favorites").select("zone_id,note").order("created_at");
  if(error) return console.error(error);
  data.forEach(r => favs.set(currentId(r.zone_id), r.note || ""));
}

async function toggleFav(z){
  const u = currentUser();
  if(!u) return openLogin();
  const sb = await supabase();
  const ids = [z.id, ...(z.aliases || [])];   // toglie anche righe salvate con un id vecchio
  const q = favs.has(z.id)
    ? sb.from("swell_favorites").delete().eq("user_id", u.id).in("zone_id", ids)
    : sb.from("swell_favorites").insert({user_id: u.id, zone_id: z.id});
  const {error} = await q;
  if(error) return console.error(error);
  if(favs.has(z.id)) favs.delete(z.id); else favs.set(z.id, "");
  publishUser();
  app.refresh();
}

// ---------- stella sulla scheda e filtro "solo preferiti" (lista e globo; la zona aperta resta visibile)
$("fav").onclick = () => toggleFav(app.state.zone);
app.hooks.render.push(z => {
  const on = favs.has(z.id), b = $("fav");
  b.textContent = on ? "★" : "☆";
  b.setAttribute("aria-pressed", on);
  b.title = on ? "Togli dai preferiti" : (currentUser() ? "Aggiungi ai preferiti" : "Accedi per salvare i preferiti");
});
$("only-fav").onchange = e => {
  app.hooks.filter = e.target.checked ? (z => favs.has(z.id) || z === app.state.zone) : null;
  app.refresh();
};

// ---------- pannello profilo
$("pf-airport").innerHTML = `<option value="">—</option>` + app.DEPS.map(d => `<option value="${d.code}">${app.depText(d)}</option>`).join("");

function renderFavs(){
  const ul = $("pf-favs");
  ul.innerHTML = favs.size ? "" : `<li class="note">Nessun preferito: usa la stella sulla scheda di una zona.</li>`;
  for(const [id, note] of favs){
    const z = zoneById(id);
    const li = document.createElement("li");
    li.innerHTML = `<button type="button" class="btn go"></button><input class="fav-note" maxlength="500" placeholder="nota"><button type="button" class="btn rm" title="Togli">✕</button>`;
    li.querySelector(".go").textContent = z ? z.name : id;
    li.querySelector(".fav-note").value = note;
    li.querySelector(".go").onclick = () => { if(z){ $("dlg-profile").close(); app.selectZone(z); } };
    li.querySelector(".rm").onclick = async () => { if(z) await toggleFav(z); else favs.delete(id); renderFavs(); };
    li.querySelector(".fav-note").onchange = async e => {
      const sb = await supabase();
      const ids = [id, ...(z?.aliases || [])];
      const {error} = await sb.from("swell_favorites").update({note: e.target.value || null}).eq("user_id", currentUser().id).in("zone_id", ids);
      if(!error) favs.set(id, e.target.value);
    };
    ul.append(li);
  }
}

function openProfile(){
  $("profile-email").textContent = currentUser()?.email || "";
  $("pf-name").value = profile?.display_name || "";
  $("pf-airport").value = profile?.home_airport || "";
  $("pf-level").value = profile?.surf_level || "";
  $("profile-msg").textContent = "";
  renderFavs();
  $("dlg-profile").showModal();
}

$("profile-form").addEventListener("submit", async e => {
  if(e.submitter?.id === "pf-logout"){ await signOut(); return; }
  if(e.submitter?.value === "cancel") return;
  e.preventDefault();
  const row = {display_name: $("pf-name").value.trim() || null, home_airport: $("pf-airport").value || null, surf_level: $("pf-level").value || null};
  const sb = await supabase();
  const {data, error} = await sb.from("swell_profiles").update(row).eq("id", currentUser().id).select().single();
  if(error){ $("profile-msg").textContent = "Non salvato: " + error.message; return; }
  profile = data;
  publishUser();
  $("btn-account").textContent = profile.display_name || "Profilo";
  const d = depByCode(profile.home_airport);
  if(d) app.setDep(d);
  $("profile-msg").textContent = "Salvato.";
});

ready.then(() => app.refresh());
