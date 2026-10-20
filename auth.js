// Accesso con email e password (Supabase Auth), come Piano alimentare. Senza configurazione o senza login
// l'app funziona tutta; l'account serve solo per preferiti e profilo.
import {SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY} from "./supabase-config.js";

const SUPABASE_JS = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.116.0/+esm";
const $ = id => document.getElementById(id);
export const configured = !!(SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY);
// si legge prima che la libreria ripulisca l'indirizzo: arrivo dalla mail "Password dimenticata?"
const fromRecovery = /type=recovery/.test(location.hash + location.search);

let client = null, user = null;
const listeners = [];

export function supabase(){
  if(!configured) return Promise.resolve(null);
  // si memorizza la promessa, non il risultato: chiamate contemporanee (auth, profilo, prezzi) usano un solo client
  client ||= import(SUPABASE_JS).then(({createClient}) =>
    createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {auth:{persistSession:true, detectSessionInUrl:true}}));
  return client;
}

export const currentUser = () => user;
export function onUser(f){ listeners.push(f); if(user) f(user); }   // chi arriva tardi riceve subito l'utente già noto
function setUser(u){
  if((u?.id || null) === (user?.id || null)) return;
  user = u;
  listeners.forEach(f => f(user));
}

// le mail di conferma e di recupero riportano qui (GitHub Pages o localhost): l'indirizzo va tra i redirect consentiti
const redirectTo = () => location.origin + location.pathname;

export async function signOut(){ const sb = await supabase(); if(sb) await sb.auth.signOut(); }
export async function changePassword(password){
  const sb = await supabase();
  const {error} = await sb.auth.updateUser({password});
  if(error) throw error;
}

// messaggi in italiano, come in Piano alimentare
export function authErrorText(e){
  const m = (e?.message || "").toLowerCase();
  if(m.includes("invalid login")) return "Email o password sbagliate.";
  if(m.includes("not confirmed")) return "Prima conferma la mail: controlla la posta (anche lo spam), poi torna qui e premi Entra.";
  if(m.includes("already registered")) return "Esiste già un account con questa email: premi Entra.";
  if(m.includes("different")) return "La nuova password deve essere diversa da quella attuale.";
  if(m.includes("password")) return "La password deve avere almeno 6 caratteri.";
  if(m.includes("rate") || e?.status === 429) return "Troppi tentativi, riprova tra qualche minuto.";
  if(m.includes("fetch") || m.includes("network")) return "Nessuna connessione a internet.";
  return "Qualcosa non ha funzionato: " + (e?.message || "errore sconosciuto");
}

// ---------- finestra di accesso: email e password
const msg = (t, el = "login-msg") => { $(el).textContent = t; };
const values = () => ({email: $("login-email").value.trim(), password: $("login-password").value});
const busy = b => document.querySelectorAll("#login-form button").forEach(x => x.disabled = b);

export function openLogin(){
  msg("");
  $("dlg-login").showModal();
  $("login-email").focus();
}
$("login-close").onclick = () => $("dlg-login").close();

$("login-form").addEventListener("submit", async e => {
  e.preventDefault();
  const {email, password} = values();
  if(!email || !password) return msg("Scrivi email e password.");
  busy(true); msg("Entro…");
  const sb = await supabase();
  const {error} = await sb.auth.signInWithPassword({email, password});
  busy(false);
  if(error) return msg(authErrorText(error));
  $("dlg-login").close();
});

$("login-signup").onclick = async () => {
  const {email, password} = values();
  if(!email || !password) return msg("Scrivi email e una password per il nuovo account.");
  if(password.length < 6) return msg("La password deve avere almeno 6 caratteri.");
  busy(true); msg("Creo l'account…");
  const sb = await supabase();
  const {data, error} = await sb.auth.signUp({email, password, options: {emailRedirectTo: redirectTo()}});
  busy(false);
  if(error) return msg(authErrorText(error));
  if(data?.user && Array.isArray(data.user.identities) && data.user.identities.length === 0)
    return msg("Esiste già un account con questa email: premi Entra.");
  if(!data?.session) return msg("Ti ho mandato una mail di conferma. Aprila (va bene anche dal telefono), poi torna qui e premi Entra.");
  $("dlg-login").close();
};

$("login-forgot").onclick = async () => {
  const {email} = values();
  if(!email) return msg("Scrivi la tua email, poi premi di nuovo «Password dimenticata?».");
  busy(true); msg("Invio la mail…");
  const sb = await supabase();
  const {error} = await sb.auth.resetPasswordForEmail(email, {redirectTo: redirectTo()});
  busy(false);
  msg(error ? authErrorText(error) : "Ti ho mandato una mail: aprila e scegli la nuova password. Poi entra con email e password.");
};

// arrivo dalla mail di recupero: si sceglie subito la nuova password
$("newpw-form").addEventListener("submit", async e => {
  e.preventDefault();
  const pw = $("newpw").value;
  if(pw.length < 6) return msg("La password deve avere almeno 6 caratteri.", "newpw-msg");
  try{
    await changePassword(pw);
    msg("Password salvata. Da ora entri con email e password, anche da altri browser.", "newpw-msg");
    setTimeout(() => $("dlg-newpw").close(), 1800);
  }catch(err){ msg(authErrorText(err), "newpw-msg"); }
});

// sessione esistente o appena arrivata da una mail (conferma o recupero)
export const ready = (async () => {
  const sb = await supabase().catch(err => { console.error("Supabase non caricato", err); return null; });
  if(!sb) return;
  const {data} = await sb.auth.getSession();
  setUser(data.session?.user || null);
  if(fromRecovery && data.session){ msg("", "newpw-msg"); $("dlg-newpw").showModal(); }
  sb.auth.onAuthStateChange((event, session) => {
    // come in Piano alimentare: niente altre chiamate Supabase dentro il callback, si rimanda di un giro
    setTimeout(() => {
      setUser(session?.user || null);
      if(event === "PASSWORD_RECOVERY" && !$("dlg-newpw").open){ msg("", "newpw-msg"); $("dlg-newpw").showModal(); }
    }, 0);
  });
  if(location.hash.includes("access_token")) history.replaceState(null, "", location.pathname + location.search);
})();
