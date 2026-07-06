/* ------------------------------------------------------------------
   Prioritetskart — energieffektivisering × nettkapasitet
   Viser bygninger farget etter kombinert prioritetsscore, med
   nettkapasitet-soner (trafoforsyningsområder) som omriss.
   ------------------------------------------------------------------ */

const BYGNINGER_URL = "data/glitre_prioritet.geojson";
const SONER_URL = "data/glitre_nettkapasitet.geojson";

const SONE_FARGE = {
  rod: "#c1622d",
  oransje: "#e0a63f",
  gul: "#e0d33f",
  gronn: "#4fa67f",
};

const state = {
  allFeatures: [],
  soner: [],
  filters: { omrade: "", type: "", minPrio: 0 },
};

// ---------- Kart ----------

const map = L.map("map", { zoomControl: false, minZoom: 6 }).setView([59.3, 8.3], 8);

L.control.zoom({ position: "bottomright" }).addTo(map);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_matter_nolabels/{z}/{x}/{y}{r}.png", {
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> bidragsytere &copy; <a href="https://carto.com/attributions">CARTO</a>',
  subdomains: "abcd",
  maxZoom: 19,
}).addTo(map);

const soneLayer = L.geoJSON(null, {
  style: (feature) => ({
    color: SONE_FARGE[feature.properties.kategori] || "#888",
    weight: 1.5,
    fillColor: SONE_FARGE[feature.properties.kategori] || "#888",
    fillOpacity: 0.08,
    dashArray: "4 3",
  }),
}).addTo(map);

soneLayer.bindTooltip(
  (layer) => {
    const p = layer.feature.properties;
    return `${p.omrade_navn}: ${p.ledig_kapasitet_mw} MW ledig kapasitet (${p.kategori})`;
  },
  { sticky: true }
);

const clusterGroup = L.markerClusterGroup({
  maxClusterRadius: 42,
  spiderfyOnMaxZoom: true,
  iconCreateFunction: (cluster) => {
    const markers = cluster.getAllChildMarkers();
    const avg = markers.reduce((sum, m) => sum + m.options.prioritet, 0) / markers.length;
    const color = scoreToColor(avg);
    return L.divIcon({
      html: `<div style="background:${color}22;border-color:${color}"><span>${cluster.getChildCount()}</span></div>`,
      className: "cluster-icon",
      iconSize: [38, 38],
    });
  },
});

map.addLayer(clusterGroup);

// ---------- Fargeskala (fjord -> amber -> ember) ----------

function scoreToColor(score) {
  const stops = [
    { p: 0, c: [79, 166, 160] },
    { p: 50, c: [224, 184, 75] },
    { p: 100, c: [193, 98, 45] },
  ];
  let a = stops[0], b = stops[1];
  if (score > 50) { a = stops[1]; b = stops[2]; }
  const t = Math.max(0, Math.min(1, (score - a.p) / (b.p - a.p)));
  const rgb = a.c.map((v, i) => Math.round(v + (b.c[i] - v) * t));
  return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function makeMarker(feature) {
  const p = feature.properties;
  const [lon, lat] = feature.geometry.coordinates;
  const color = scoreToColor(p.prioritet_score);

  const marker = L.circleMarker([lat, lon], {
    radius: 7,
    weight: 1.5,
    color: "#0f151a",
    fillColor: color,
    fillOpacity: 0.92,
    prioritet: p.prioritet_score,
  });

  marker.bindPopup(`
    <div class="popup-card">
      <h3>${escapeHtml(p.navn)}</h3>
      <div class="popup-score">
        <span class="popup-dot" style="background:${color}"></span>
        Prioritet: <strong>${p.prioritet_score}</strong> / 100
      </div>
      <div class="popup-grid">
        <span>Kommune</span><strong>${escapeHtml(p.kommune)}</strong>
        <span>Type</span><strong>${escapeHtml(p.bygningstype)}</strong>
        <span>Byggeår</span><strong>${p.byggeaar}</strong>
        <span>Energipotensial</span><strong>${p.potensial_score} / 100</strong>
        <span>Nettområde</span><strong>${escapeHtml(p.nettomrade || "–")}</strong>
        <span>Ledig kapasitet</span><strong>${p.ledig_kapasitet_mw != null ? p.ledig_kapasitet_mw + " MW" : "–"}</strong>
      </div>
      <div class="popup-source">
        ${p.kilde === "registrert" ? "Energipotensial basert på registrert energiattest" : "Energipotensial estimert"} ·
        nettkapasitet er syntetisk demo-data
      </div>
    </div>
  `);

  return marker;
}

// ---------- Filtre ----------

function populateSelect(id, values) {
  const select = document.getElementById(id);
  const current = select.value;
  const existing = new Set(Array.from(select.options).map((o) => o.value));
  [...values].filter(Boolean).sort((a, b) => a.localeCompare(b, "no")).forEach((v) => {
    if (!existing.has(v)) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      select.appendChild(opt);
    }
  });
  select.value = current;
}

function applyFilters() {
  const { omrade, type, minPrio } = state.filters;

  const filtered = state.allFeatures.filter((f) => {
    const p = f.properties;
    if (omrade && p.nettomrade !== omrade) return false;
    if (type && p.bygningstype !== type) return false;
    if (p.prioritet_score < minPrio) return false;
    return true;
  });

  clusterGroup.clearLayers();
  filtered.forEach((f) => clusterGroup.addLayer(makeMarker(f)));

  updateStats(filtered);
}

function updateStats(filtered) {
  const count = filtered.length;
  const avg = count ? Math.round(filtered.reduce((s, f) => s + f.properties.prioritet_score, 0) / count) : 0;
  const high = filtered.filter((f) => f.properties.prioritet_score >= 70).length;

  document.getElementById("statCount").textContent = count;
  document.getElementById("statAvg").textContent = count ? avg : "–";
  document.getElementById("statHigh").textContent = high;
}

// ---------- Init ----------

async function init() {
  const loadingEl = document.getElementById("mapLoading");
  try {
    const [bygRes, sonerRes] = await Promise.all([fetch(BYGNINGER_URL), fetch(SONER_URL)]);
    if (!bygRes.ok) throw new Error(`Bygninger: HTTP ${bygRes.status}`);
    if (!sonerRes.ok) throw new Error(`Nettkapasitet: HTTP ${sonerRes.status}`);

    const bygGeojson = await bygRes.json();
    const sonerGeojson = await sonerRes.json();

    state.allFeatures = bygGeojson.features;
    state.soner = sonerGeojson.features;

    soneLayer.addData(sonerGeojson);

    populateSelect("filterOmrade", new Set(state.allFeatures.map((f) => f.properties.nettomrade)));
    populateSelect("filterType", new Set(state.allFeatures.map((f) => f.properties.bygningstype)));

    applyFilters();

    document.getElementById("dataSourceNote").textContent =
      `Viser ${state.allFeatures.length} bygninger koblet mot ${state.soner.length} nettkapasitet-soner. ` +
      `Bygningsdata: samme metodikk som Energipotensial-kartet. Nettkapasitet: syntetisk demo — se scripts/ for hvordan du bytter til ekte tall.`;
  } catch (err) {
    document.getElementById("dataSourceNote").textContent = "Kunne ikke laste datasettet: " + err.message;
  } finally {
    loadingEl.hidden = true;
  }
}

document.getElementById("filterOmrade").addEventListener("change", (e) => {
  state.filters.omrade = e.target.value;
  applyFilters();
});
document.getElementById("filterType").addEventListener("change", (e) => {
  state.filters.type = e.target.value;
  applyFilters();
});
document.getElementById("filterMinPrio").addEventListener("input", (e) => {
  state.filters.minPrio = Number(e.target.value);
  document.getElementById("minPrioOut").textContent = e.target.value;
  applyFilters();
});
document.getElementById("toggleSoner").addEventListener("change", (e) => {
  if (e.target.checked) {
    map.addLayer(soneLayer);
  } else {
    map.removeLayer(soneLayer);
  }
});

const panelToggle = document.getElementById("panelToggle");
const sidebar = document.getElementById("sidebar");
panelToggle.addEventListener("click", () => {
  const open = sidebar.classList.toggle("open");
  panelToggle.setAttribute("aria-expanded", String(open));
});

const methodDialog = document.getElementById("methodDialog");
document.getElementById("methodLink").addEventListener("click", (e) => {
  e.preventDefault();
  methodDialog.showModal();
});
document.getElementById("closeMethod").addEventListener("click", () => methodDialog.close());

init();
