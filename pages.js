// Due pagine: Mondo (globo, scheda, timeline, zone per paese) e Calendario. La pagina sta nell'indirizzo (#calendario).
import {app} from "./app.js";

const PAGES = ["mondo", "calendario"];
const $ = id => document.getElementById(id);

export function showPage(name, push = true){
  if(!PAGES.includes(name)) name = "mondo";
  for(const p of PAGES) $("page-" + p).hidden = p !== name;
  document.querySelectorAll(".pages a").forEach(a => a.setAttribute("aria-current", a.dataset.page === name ? "page" : "false"));
  if(push && location.hash !== "#" + name) history.replaceState(null, "", "#" + name);
  if(name === "mondo") app.refresh();   // il globo era nascosto: si ridisegna con le misure giuste
}
app.hooks.showPage = showPage;

document.querySelector(".pages").addEventListener("click", e => {
  const a = e.target.closest("a[data-page]");
  if(!a) return;
  e.preventDefault();
  showPage(a.dataset.page);
  window.scrollTo({top: 0});
});
window.addEventListener("hashchange", () => showPage(location.hash.slice(1), false));
showPage(location.hash.slice(1) || "mondo", false);
