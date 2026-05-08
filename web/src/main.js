import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './styles.css';

const SITES = [
  { id: 'partner_site_1', name: 'Partner Site 1', note: 'orchard-specific example' },
  { id: 'fresno_site_1', name: 'Fresno Site 1', note: 'public boundary, cautious interpretation' },
  { id: 'kern_site_1', name: 'Kern Site 1', note: 'small-boundary low-priority result' },
  { id: 'kings_site_1', name: 'Kings Site 1', note: 'public boundary, cautious interpretation' },
  { id: 'stanislaus_site_1', name: 'Stanislaus Site 1', note: 'public boundary, cautious interpretation' },
  { id: 'tulare_site_1', name: 'Tulare Site 1', note: 'public boundary, cautious interpretation' }
];

const CLASS_META = {
  'Scout first': {
    color: '#b42318',
    label: 'Problematic priority signal',
    status: 'Yes. Visit first and compare against a strong nearby reference.',
    action: 'Send a scout to the selected coordinate, then check field memory and records before assigning cause.'
  },
  Monitor: {
    color: '#f79009',
    label: 'Possible concern',
    status: 'Maybe. Weaker or less persistent signal. Inspect if nearby or after Scout first zones.',
    action: 'Check during field rounds and compare against stable or strong canopy.'
  },
  'Stable context': {
    color: '#a6c8a0',
    label: 'No priority signal',
    status: 'No. This layer does not flag it as problematic.',
    action: 'Use as normal context unless field memory or records say otherwise.'
  },
  'Strong reference': {
    color: '#1a7f37',
    label: 'Comparison reference',
    status: 'No. Use this as a stronger within-site comparison zone.',
    action: 'Compare Scout first or Monitor zones against this area before deciding follow-up.'
  }
};

const app = document.querySelector('#app');
app.innerHTML = `
  <header class="shell header">
    <div>
      <p class="eyebrow">F3 Innovate Data Challenge #2</p>
      <h1>Orchard Stress Field Quick Start</h1>
      <p class="lede">
        Open a site, hover for coordinates, select a zone, then launch Google Maps to scout the chosen point.
        The layer prioritizes field follow-up; it does not diagnose disease, irrigation failure, soil, nutrients, or yield loss.
      </p>
    </div>
    <a class="github-link" href="https://github.com/tienonic/f3innovate-project-submission" target="_blank" rel="noreferrer">
      Public GitHub
    </a>
  </header>

  <main class="shell page-grid">
    <section class="quickstart" aria-labelledby="quickstart-title">
      <div class="section-head">
        <p class="eyebrow">Field workflow</p>
        <h2 id="quickstart-title">Quick Start</h2>
      </div>
      <ol class="steps">
        <li><span>1</span><p>Choose the orchard/site from the selector and let the zone map load.</p></li>
        <li><span>2</span><p>Start with red <strong>Scout first</strong> zones, then orange <strong>Monitor</strong> zones if time allows.</p></li>
        <li><span>3</span><p>Hover anywhere on the map to read the latitude and longitude under the cursor.</p></li>
        <li><span>4</span><p>Click a zone to see whether the model flags it as problematic, plus area, persistence, confidence, and follow-up guidance.</p></li>
        <li><span>5</span><p>Use <strong>Yes, open route</strong> to launch Google Maps directions to the selected coordinate.</p></li>
        <li><span>6</span><p>In the field, compare weak canopy against stable or strong reference canopy and write down what was actually observed.</p></li>
      </ol>
    </section>

    <section class="translation" aria-labelledby="translation-title">
      <div class="section-head">
        <p class="eyebrow">Crew language</p>
        <h2 id="translation-title">Translation Guide</h2>
      </div>
      <div class="translation-grid">
        <div><strong>Scout first</strong><span>Revisar primero</span><p>Repeated weaker canopy signal. Visit first.</p></div>
        <div><strong>Monitor</strong><span>Monitorear</span><p>Check if nearby or after priority zones.</p></div>
        <div><strong>Stable context</strong><span>Contexto estable</span><p>No scouting priority from this signal alone.</p></div>
        <div><strong>Strong reference</strong><span>Referencia fuerte</span><p>Use for comparison against weaker zones.</p></div>
        <div><strong>Field verification</strong><span>Verificacion en campo</span><p>The field visit determines cause, not the satellite layer.</p></div>
        <div><strong>Known context</strong><span>Contexto conocido</span><p>Use when records or field memory explain the signal.</p></div>
      </div>
    </section>

    <section class="map-section" aria-labelledby="map-title">
      <div class="map-toolbar">
        <div>
          <p class="eyebrow">Interactive map</p>
          <h2 id="map-title">Select A Zone</h2>
        </div>
        <label class="site-picker">
          <span>Site</span>
          <select id="siteSelect"></select>
        </label>
      </div>

      <div class="map-layout">
        <div class="map-wrap">
          <div id="map" aria-label="Interactive orchard stress map"></div>
          <div class="coordinate-readout">
            <span>Cursor</span>
            <strong id="cursorCoords">Move over map</strong>
          </div>
        </div>

        <aside class="detail-panel" aria-live="polite">
          <div id="siteSummary" class="summary-block"></div>
          <div class="legend" aria-label="Zone class legend">
            <div><span style="background:#b42318"></span>Scout first</div>
            <div><span style="background:#f79009"></span>Monitor</div>
            <div><span style="background:#a6c8a0"></span>Stable context</div>
            <div><span style="background:#1a7f37"></span>Strong reference</div>
          </div>
          <div id="zoneDetails" class="zone-details">
            <p class="empty-state">Click a colored zone or a top work-order row to select a field coordinate.</p>
          </div>
        </aside>
      </div>
    </section>

    <section class="work-orders" aria-labelledby="work-orders-title">
      <div class="section-head">
        <p class="eyebrow">Navigation shortlist</p>
        <h2 id="work-orders-title">Top Field Stops</h2>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Zone</th>
              <th>Class</th>
              <th>Acres</th>
              <th>Persistence</th>
              <th>Coordinate</th>
              <th>Route</th>
            </tr>
          </thead>
          <tbody id="workOrderRows"></tbody>
        </table>
      </div>
    </section>

    <section class="howto" aria-labelledby="howto-title">
      <div class="section-head">
        <p class="eyebrow">Detailed use</p>
        <h2 id="howto-title">How To Use It In The Field</h2>
      </div>
      <div class="howto-grid">
        <article>
          <h3>Before walking</h3>
          <p>Pick the site and scan the red and orange zones. Start with larger, persistent red zones or the top field stops table.</p>
        </article>
        <article>
          <h3>At the coordinate</h3>
          <p>Use the Google Maps route as a starting point only. Follow legal access, gates, rows, and farm rules rather than blindly following the line.</p>
        </article>
        <article>
          <h3>What to check</h3>
          <p>Compare canopy, irrigation distribution, visible pest or disease symptoms, soil or water movement, PCA notes, block maps, and recent field memory.</p>
        </article>
        <article>
          <h3>After scouting</h3>
          <p>Label the visit as confirmed concern, known context, no-action area, or needs revisit. Use that feedback to tune thresholds next season.</p>
        </article>
      </div>
    </section>
  </main>
`;

const state = {
  summaries: [],
  workOrders: [],
  selectedSite: 'partner_site_1',
  zoneLayer: null,
  selectedLayer: null,
  selectedMarker: null,
  selectedCoordinate: null
};

const map = L.map('map', {
  scrollWheelZoom: true,
  zoomSnap: 0.25
});

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 20,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const siteSelect = document.querySelector('#siteSelect');
const cursorCoords = document.querySelector('#cursorCoords');
const zoneDetails = document.querySelector('#zoneDetails');
const siteSummary = document.querySelector('#siteSummary');
const workOrderRows = document.querySelector('#workOrderRows');

SITES.forEach((site) => {
  const option = document.createElement('option');
  option.value = site.id;
  option.textContent = `${site.name} - ${site.note}`;
  siteSelect.appendChild(option);
});
siteSelect.value = state.selectedSite;

map.on('mousemove', (event) => {
  cursorCoords.textContent = formatCoord(event.latlng.lat, event.latlng.lng);
});

siteSelect.addEventListener('change', async (event) => {
  state.selectedSite = event.target.value;
  await loadSite(state.selectedSite);
});

init().catch((error) => {
  zoneDetails.innerHTML = `<p class="error">Map failed to load: ${escapeHtml(error.message)}</p>`;
});

async function init() {
  const [summariesText, workOrdersText] = await Promise.all([
    fetchText('/data/tables/spatial_zone_summary.csv'),
    fetchText('/data/tables/grower_work_orders.csv')
  ]);
  state.summaries = parseCsv(summariesText);
  state.workOrders = parseCsv(workOrdersText);
  await loadSite(state.selectedSite);
}

async function loadSite(siteId) {
  clearSelected();
  updateSummary(siteId);
  updateWorkOrders(siteId);

  const geojson = await fetchJson(`/data/geodata/${siteId}_zones.geojson`);
  if (state.zoneLayer) {
    state.zoneLayer.removeFrom(map);
  }

  state.zoneLayer = L.geoJSON(geojson, {
    style: zoneStyle,
    onEachFeature: bindZoneEvents
  }).addTo(map);

  const bounds = state.zoneLayer.getBounds();
  if (bounds.isValid()) {
    map.fitBounds(bounds.pad(0.08));
  }
}

function bindZoneEvents(feature, layer) {
  const props = feature.properties || {};
  const zoneClass = props.zone_class || 'Stable context';
  const meta = CLASS_META[zoneClass] || CLASS_META['Stable context'];

  layer.bindTooltip(`${zoneClass} | ${Number(props.acres_est || 0).toFixed(2)} acres`, {
    sticky: true,
    direction: 'top'
  });

  layer.on('mouseover', () => {
    if (layer !== state.selectedLayer) {
      layer.setStyle({ weight: 3, fillOpacity: 0.64 });
    }
  });

  layer.on('mouseout', () => {
    if (layer !== state.selectedLayer) {
      layer.setStyle(zoneStyle(feature));
    }
  });

  layer.on('click', () => {
    const center = layer.getBounds().getCenter();
    selectZone({
      source: 'map',
      siteId: props.site || state.selectedSite,
      zoneId: `${props.site || state.selectedSite}_patch_${String(props.patch_id || '').padStart(3, '0')}`,
      zoneClass,
      acres: Number(props.acres_est || 0),
      persistence: Number(props.mean_persistence || 0),
      confidence: Number(props.mean_confidence || 0),
      underperformance: Number(props.mean_score || 0),
      lat: center.lat,
      lon: center.lng,
      recommendation: props.recommendation || meta.action
    }, layer);
  });
}

function zoneStyle(feature) {
  const zoneClass = feature.properties?.zone_class || 'Stable context';
  const meta = CLASS_META[zoneClass] || CLASS_META['Stable context'];
  return {
    color: '#ffffff',
    weight: 1,
    opacity: 0.9,
    fillColor: meta.color,
    fillOpacity: zoneClass === 'Stable context' ? 0.46 : 0.58
  };
}

function selectZone(zone, layer = null) {
  if (state.selectedLayer && state.selectedLayer !== layer) {
    state.selectedLayer.setStyle(zoneStyle(state.selectedLayer.feature));
  }

  state.selectedLayer = layer;
  if (layer) {
    layer.setStyle({ color: '#111827', weight: 4, fillOpacity: 0.76 });
    layer.bringToFront();
  }

  state.selectedCoordinate = { lat: Number(zone.lat), lon: Number(zone.lon) };
  if (state.selectedMarker) {
    state.selectedMarker.removeFrom(map);
  }

  state.selectedMarker = L.circleMarker([zone.lat, zone.lon], {
    radius: 6,
    color: '#111827',
    fillColor: '#ffffff',
    fillOpacity: 1,
    weight: 2
  }).addTo(map);

  renderZoneDetails(zone);
}

function clearSelected() {
  if (state.selectedLayer) {
    state.selectedLayer.setStyle(zoneStyle(state.selectedLayer.feature));
  }
  state.selectedLayer = null;
  state.selectedCoordinate = null;
  if (state.selectedMarker) {
    state.selectedMarker.removeFrom(map);
  }
  state.selectedMarker = null;
  zoneDetails.innerHTML = '<p class="empty-state">Click a colored zone or a top work-order row to select a field coordinate.</p>';
}

function renderZoneDetails(zone) {
  const meta = CLASS_META[zone.zoneClass] || CLASS_META['Stable context'];
  const mapsUrl = googleMapsUrl(zone.lat, zone.lon);
  zoneDetails.innerHTML = `
    <div class="status-pill" style="--zone-color:${meta.color}">
      <span></span>${escapeHtml(meta.label)}
    </div>
    <h3>${escapeHtml(zone.zoneId || 'Selected zone')}</h3>
    <dl>
      <div><dt>Problematic?</dt><dd>${escapeHtml(meta.status)}</dd></div>
      <div><dt>Coordinate</dt><dd>${formatCoord(zone.lat, zone.lon)}</dd></div>
      <div><dt>Area</dt><dd>${formatNumber(zone.acres, 2)} acres</dd></div>
      <div><dt>Persistence</dt><dd>${formatNumber(zone.persistence, 2)}</dd></div>
      <div><dt>Confidence</dt><dd>${formatNumber(zone.confidence, 2)}</dd></div>
      <div><dt>Relative underperformance</dt><dd>${formatNumber(zone.underperformance, 2)}</dd></div>
    </dl>
    <p>${escapeHtml(zone.recommendation || meta.action)}</p>
    <div class="route-card">
      <span>Open selected coordinate in Google Maps?</span>
      <a href="${mapsUrl}" target="_blank" rel="noreferrer">Yes, open route</a>
    </div>
  `;
}

function updateSummary(siteId) {
  const summary = state.summaries.find((row) => row.site === siteId);
  const site = SITES.find((item) => item.id === siteId);
  if (!summary) {
    siteSummary.innerHTML = `<h3>${escapeHtml(site?.name || siteId)}</h3>`;
    return;
  }

  siteSummary.innerHTML = `
    <h3>${escapeHtml(site?.name || siteId)}</h3>
    <p>${escapeHtml(site?.note || '')}</p>
    <div class="summary-grid">
      <div><span>Eligible canopy</span><strong>${formatNumber(summary.eligible_canopy_acres_est, 2)} ac</strong></div>
      <div><span>Scout first</span><strong>${formatNumber(summary.investigate_acres_est, 2)} ac</strong></div>
      <div><span>Monitor</span><strong>${formatNumber(summary.monitor_acres_est, 2)} ac</strong></div>
      <div><span>Zone patches</span><strong>${formatNumber(summary.zone_vector_patches, 0)}</strong></div>
    </div>
  `;
}

function updateWorkOrders(siteId) {
  const rows = state.workOrders
    .filter((row) => row.site_id === siteId)
    .sort((a, b) => Number(a.work_order_rank) - Number(b.work_order_rank));

  if (!rows.length) {
    workOrderRows.innerHTML = '<tr><td colspan="7">No field stops available for this site.</td></tr>';
    return;
  }

  workOrderRows.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.work_order_rank)}</td>
      <td><button class="zone-button" type="button" data-zone-id="${escapeHtml(row.zone_id)}">${escapeHtml(row.zone_id)}</button></td>
      <td><span class="class-dot" style="--zone-color:${CLASS_META[row.priority_class]?.color || '#64748b'}"></span>${escapeHtml(row.priority_class)}</td>
      <td>${formatNumber(row.approx_area_acres, 2)}</td>
      <td>${formatNumber(row.persistence_score, 2)}</td>
      <td>${formatCoord(row.centroid_lat, row.centroid_lon)}</td>
      <td><a class="text-link" href="${googleMapsUrl(row.centroid_lat, row.centroid_lon)}" target="_blank" rel="noreferrer">Google Maps</a></td>
    </tr>
  `).join('');

  workOrderRows.querySelectorAll('.zone-button').forEach((button) => {
    button.addEventListener('click', () => {
      const row = rows.find((item) => item.zone_id === button.dataset.zoneId);
      if (!row) return;
      const zone = {
        source: 'work-order',
        siteId: row.site_id,
        zoneId: row.zone_id,
        zoneClass: row.priority_class,
        acres: Number(row.approx_area_acres),
        persistence: Number(row.persistence_score),
        confidence: Number(row.valid_observation_count) / 8,
        underperformance: Number(row.mean_relative_underperformance),
        lat: Number(row.centroid_lat),
        lon: Number(row.centroid_lon),
        recommendation: row.suggested_first_action || row.comparison_instruction
      };
      selectZone(zone);
      map.setView([zone.lat, zone.lon], Math.max(map.getZoom(), 17), { animate: true });
    });
  });
}

async function fetchText(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return response.text();
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return response.json();
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"' && inQuotes && next === '"') {
      cell += '"';
      i += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      row.push(cell);
      cell = '';
    } else if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') i += 1;
      row.push(cell);
      if (row.some((value) => value.length > 0)) rows.push(row);
      row = [];
      cell = '';
    } else {
      cell += char;
    }
  }

  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }

  const [header, ...body] = rows;
  return body.map((values) => Object.fromEntries(header.map((key, index) => [key, values[index] ?? ''])));
}

function googleMapsUrl(lat, lon) {
  return `https://www.google.com/maps/dir/?api=1&destination=${Number(lat).toFixed(7)},${Number(lon).toFixed(7)}&travelmode=driving`;
}

function formatCoord(lat, lon) {
  return `${Number(lat).toFixed(7)}, ${Number(lon).toFixed(7)}`;
}

function formatNumber(value, digits) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '0';
  return number.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
