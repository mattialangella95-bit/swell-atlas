// Novità: alla prima apertura dopo un aggiornamento si mostrano quelle non ancora viste, poi mai più
// (come in Piano alimentare, ma ricordato nel browser: qui quasi tutti entrano senza account).
// Testi in data/news.json, mostrati solo come testo. Il link "Novità" in fondo le riapre.
const $ = id => document.getElementById(id);
const KEY = "swellatlas.novita";
const {news} = await fetch("data/news.json").then(r => r.json());
const el = (tag, cls, text) => { const e = document.createElement(tag); if(cls) e.className = cls; if(text != null) e.textContent = text; return e; };

function show(list){
  const body = $("news-body");
  body.replaceChildren();
  for(const n of list){
    body.append(el("h3", null, n.title));
    if(n.intro) body.append(el("p", null, n.intro));
    const ul = el("ul");
    n.items.forEach(t => ul.append(el("li", null, t)));
    body.append(ul);
    if(n.note) body.append(el("p", "note", n.note));
  }
  if(!$("dlg-news").open) $("dlg-news").showModal();
}
$("news-ok").onclick = () => $("dlg-news").close();
$("news-link").onclick = () => show(news.slice(0, 3));

// se il browser non permette di ricordarlo (es. navigazione privata) non si mostra: comparirebbe a ogni apertura
let seen = null, canRemember = true;
try{ seen = localStorage.getItem(KEY); localStorage.setItem(KEY + ".prova", "1"); localStorage.removeItem(KEY + ".prova"); }catch(e){ canRemember = false; }
const unseen = canRemember ? news.filter(n => !seen || n.id > seen).slice(0, 3) : [];
if(unseen.length){
  localStorage.setItem(KEY, news[0].id);   // segnata subito: non torna più, anche se si chiude con Esc
  // dopo il caricamento del globo, e solo se non c'è già un'altra finestra aperta
  setTimeout(() => { if(!document.querySelector("dialog[open]")) show(unseen); }, 1200);
}
