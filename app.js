/* ------------------------------------------------------------------
   Energipotensial — applikasjonslogikk
   Laster bygningsdata (GeoJSON), viser dem på et Leaflet-kart farget
   etter potensial-score, og lar brukeren filtrere utvalget.
   ------------------------------------------------------------------ */

const DATA_URL = "data/demo_bygninger.geojson";

const HEAT_LABELS = {
  gronn: "Grønn",
  lysegronn: "Lysegrønn",
  gul: "Gul",
  oransje: "Oransje",
  rod: "Rød",
};

const state = {
  allFeatures: [],
  filters: { fylke: "", kommune: "", type: "", kilde: "", minPot: 0 },
};

// ---------- Kart ----------

const map = L.map("map", { zoomControl: false, minZoom: 4 }).setView([64.5, 13], 5);

L.control.zoom({ position: "bottomright" }).addTo(map);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_matter_nolabels/{z}/{x}/{y}{r}.png", {
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> bidragsytere &copy; <a href="https://carto.com/attributions">CARTO</a>',
  subdomains: "abcd",
  maxZoom: 19,
}).addTo(map);

const clusterGroup = L.markerClusterGroup({
  maxClusterRadius: 46,
  spiderfyOnMaxZoom: true,
  iconCreateFunction: (cluster) => {
    const markers = cluster.getAllChildMarkers();
    const avg = markers.reduce((sum, m) => sum + m.options.potensial, 0) / markers.length;
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
    { p: 0, c: [79, 166, 160] }, // fjord
    { p: 50, c: [224, 184, 75] }, // amber
    { p: 100, c: [193, 98, 45] }, // ember
  ];
  let a = stops[0], b = stops[1];
  if (score > 50) { a = stops[1]; b = stops[2]; }
  const t = Math.max(0, Math.min(1, (score - a.p) / (b.p - a.p)));
  const rgb = a.c.map((v, i) => Math.round(v + (b.c[i] - v) * t));
  return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
}

function makeMarker(feature) {
  const p = feature.properties;
  const [lon, lat] = feature.geometry.coordinates;
  const color = scoreToColor(p.potensial_score);

  const marker = L.circleMarker([lat, lon], {
    radius: 7,
    weight: 1.5,
    color: "#0f151a",
    fillColor: color,
    fillOpacity: 0.9,
    potensial: p.potensial_score,
  });

  const heatLabel = p.oppvarmingskarakter ? HEAT_LABELS[p.oppvarmingskarakter] || p.oppvarmingskarakter : "–";

  marker.bindPopup(`
    <div class="popup-card">
      <h3>${escapeHtml(p.navn)}</h3>
      <div class="popup-score">
        <span class="popup-dot" style="background:${color}"></span>
        Potensial: <strong>${p.potensial_score}</strong> / 100
      </div>
      <div class="popup-grid">
        <span>Kommune</span><strong>${escapeHtml(p.kommune)} (${escapeHtml(p.fylke)})</strong>
        <span>Type</span><strong>${escapeHtml(p.bygningstype)}</strong>
        <span>Byggeår</span><strong>${p.byggeaar}</strong>
        <span>Areal</span><strong>${p.areal_m2} m²</strong>
        <span>Energikarakter</span><strong>${p.energikarakter || "–"}</strong>
        <span>Oppvarming</span><strong>${heatLabel}</strong>
      </div>
      <div class="popup-source">
        ${p.kilde === "registrert" ? "Basert på registrert energiattest (Enova)" : "Estimert score — ingen registrert energiattest"}
      </div>
    </div>
  `);

  return marker;
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- Filtre ----------

function populateSelect(id, values) {
  const select = document.getElementById(id);
  const current = select.value;
  const existing = new Set(Array.from(select.options).map((o) => o.value));
  [...values].sort((a, b) => a.localeCompare(b, "no")).forEach((v) => {
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
  const { fylke, kommune, type, kilde, minPot } = state.filters;

  const filtered = state.allFeatures.filter((f) => {
    const p = f.properties;
    if (fylke && p.fylke !== fylke) return false;
    if (kommune && p.kommune !== kommune) return false;
    if (type && p.bygningstype !== type) return false;
    if (kilde && p.kilde !== kilde) return false;
    if (p.potensial_score < minPot) return false;
    return true;
  });

  clusterGroup.clearLayers();
  filtered.forEach((f) => clusterGroup.addLayer(makeMarker(f)));

  updateStats(filtered);
  updateKommuneOptions();
}

function updateKommuneOptions() {
  const select = document.getElementById("filterKommune");
  const relevant = state.allFeatures.filter((f) => !state.filters.fylke || f.properties.fylke === state.filters.fylke);
  const kommuner = new Set(relevant.map((f) => f.properties.kommune));

  const current = select.value;
  select.innerHTML = '<option value="">Alle kommuner</option>';
  populateSelect("filterKommune", kommuner);
  if (kommuner.has(current)) select.value = current;
  else state.filters.kommune = "";
}

function updateStats(filtered) {
  const count = filtered.length;
  const avg = count ? Math.round(filtered.reduce((s, f) => s + f.properties.potensial_score, 0) / count) : 0;
  const high = filtered.filter((f) => f.properties.potensial_score >= 70).length;

  document.getElementById("statCount").textContent = count;
  document.getElementById("statAvg").textContent = count ? avg : "–";
  document.getElementById("statHigh").textContent = high;
}

// ---------- Init ----------

async function init() {
  const loadingEl = document.getElementById("mapLoading");
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const geojson = await res.json();
    state.allFeatures = geojson.features;

    populateSelect("filterFylke", new Set(state.allFeatures.map((f) => f.properties.fylke)));
    populateSelect("filterKommune", new Set(state.allFeatures.map((f) => f.properties.kommune)));
    populateSelect("filterType", new Set(state.allFeatures.map((f) => f.properties.bygningstype)));

    applyFilters();

    const n = state.allFeatures.length;
    document.getElementById("dataSourceNote").textContent =
      `Viser ${n} bygninger fra demo-datasettet. Bytt ut data/demo_bygninger.geojson med ekte data fra Enova og OpenStreetMap — se scripts/ og README.md.`;
  } catch (err) {
    showLoadError(err);
  } finally {
    loadingEl.hidden = true;
  }
}

function showLoadError(err) {
  const isFileProtocol = location.protocol === "file:";
  document.getElementById("dataSourceNote").textContent = "Kunne ikke laste datasettet: " + err.message;

  const overlay = document.createElement("div");
  overlay.className = "map-error-overlay";
  overlay.innerHTML = isFileProtocol
    ? `<strong>Kartlaget kunne ikke lastes.</strong><br>
       Du åpner siden direkte som fil (file://), og nettlesere blokkerer da
       henting av lokale datafiler. Kjør en enkel lokal server i prosjektmappen, f.eks.:<br>
       <code>python3 -m http.server 8000</code><br>
       og åpne <code>http://localhost:8000</code> i stedet.`
    : `<strong>Kartlaget kunne ikke lastes.</strong><br>Feil: ${err.message}`;
  document.querySelector(".map-wrap").appendChild(overlay);
}

document.getElementById("filterFylke").addEventListener("change", (e) => {
  state.filters.fylke = e.target.value;
  applyFilters();
});
document.getElementById("filterKommune").addEventListener("change", (e) => {
  state.filters.kommune = e.target.value;
  applyFilters();
});
document.getElementById("filterType").addEventListener("change", (e) => {
  state.filters.type = e.target.value;
  applyFilters();
});
document.getElementById("filterKilde").addEventListener("change", (e) => {
  state.filters.kilde = e.target.value;
  applyFilters();
});
document.getElementById("filterMinPot").addEventListener("input", (e) => {
  state.filters.minPot = Number(e.target.value);
  document.getElementById("minPotOut").textContent = e.target.value;
  applyFilters();
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
