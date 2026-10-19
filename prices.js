// Prezzi voli indicativi (fase 5): ultima rilevazione da Supabase (vista swell_prices_latest, lettura
// pubblica con la publishable key, nessun login). Dove manca resta la stima di app.js. Mai offerte prenotabili.
import {app} from "./app.js";
import {supabase, configured} from "./auth.js";

const cache = new Map();     // partenza -> Map(destinazione -> 12 mesi {value, min, median, offers, observed} | null)
const loading = new Set();

function firstOfMonth(){ const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`; }

async function load(origin){
  if(!configured || cache.has(origin) || loading.has(origin)) return;
  loading.add(origin);
  const by = new Map();
  try{
    const sb = await supabase();
    for(let from = 0; ; from += 1000){   // PostgREST restituisce al massimo 1000 righe per volta
      const {data, error} = await sb.from("swell_prices_latest")
        .select("destination,month,price_min,price_median,offers,observed_at")
        .eq("origin", origin).gte("month", firstOfMonth()).range(from, from + 999);
      if(error) throw error;
      for(const r of data){
        if(!by.has(r.destination)) by.set(r.destination, new Array(12).fill(null));
        by.get(r.destination)[+r.month.slice(5, 7) - 1] = {value: r.price_median || r.price_min, min: r.price_min,
          median: r.price_median, offers: r.offers, observed: r.observed_at};
      }
      if(data.length < 1000) break;
    }
  }catch(err){ console.warn("prezzi rilevati non disponibili, resta la stima", err?.message || err); }
  cache.set(origin, by);
  loading.delete(origin);
  if(by.size){ app.refresh(); document.dispatchEvent(new CustomEvent("swell:prezzi")); }
}

// 12 mesi: {value, real, ...}; real = rilevato, altrimenti stima di flight()
app.hooks.prices = (dep, z, f) => {
  load(dep.code);
  const real = cache.get(dep.code)?.get(z.airport_main.code);
  return f.months.map((est, i) => real?.[i] ? {...real[i], real: true} : {value: est, real: false});
};
load(app.state.dep.code);
