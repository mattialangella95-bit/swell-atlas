// Accesso con link via mail (magic link di Supabase Auth). Senza configurazione o senza login
// l'app funziona tutta; l'account serve solo per preferiti e profilo.
import {SUPABASE_URL, SUPABASE_ANON_KEY} from "./supabase-config.js";

const SUPABASE_JS = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/+esm";
const $ = id => document.getElementById(id);
export const configured = !!(SUPABASE_URL && SUPABASE_ANON_KEY);

let client = null, user = null;
const listeners = [];

export async function supabase(){
  if(!configured) return null;
  if(!client){
    const {createClient} = await import(SUPABASE_JS);
    client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {auth:{persistSession:true, detectSessionInUrl:true}});
  }
  return client;
}

export const currentUser = () => user;
export function onUser(f){ listeners.push(f); if(user) f(user); }   // chi arriva tardi riceve subito l'utente già noto
function setUser(u){
  if((u?.id || null) === (user?.id || null)) return;
  user = u;
  listeners.forEach(f => f(user));
}

// il link porta di nuovo qui (GitHub Pages o localhost): l'indirizzo va tra i redirect consentiti
const redirectTo = () => location.origin + location.pathname;

export async function sendLink(email){
  const sb = await supabase();
  const {error} = await sb.auth.signInWithOtp({email, options:{emailRedirectTo: redirectTo()}});
  if(error) throw error;
}
export async function signOut(){ const sb = await supabase(); if(sb) await sb.auth.signOut(); }

// ---------- finestra di accesso
export function openLogin(){
  $("login-msg").textContent = "";
  $("dlg-login").showModal();
  $("login-email").focus();
}
$("login-form").addEventListener("submit", async e => {
  if(e.submitter?.value === "cancel") return;
  e.preventDefault();
  const email = $("login-email").value.trim();
  $("login-send").disabled = true;
  $("login-msg").textContent = "Invio in corso…";
  try{
    await sendLink(email);
    $("login-msg").textContent = "Fatto: controlla la mail e apri il link da questo browser.";
  }catch(err){
    $("login-msg").textContent = "Non è andata: " + (err.message || err);
  }finally{ $("login-send").disabled = false; }
});

// sessione esistente o appena arrivata dal link
export const ready = (async () => {
  const sb = await supabase().catch(err => { console.error("Supabase non caricato", err); return null; });
  if(!sb) return;
  const {data} = await sb.auth.getSession();
  setUser(data.session?.user || null);
  sb.auth.onAuthStateChange((_event, session) => setUser(session?.user || null));
  if(location.hash.includes("access_token")) history.replaceState(null, "", location.pathname + location.search);
})();
