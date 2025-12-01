const trenchLayers = {};
const findLayers = {};

// =====================================
// MAP
// =====================================
const map = L.map("map", { zoomControl: false }).setView(
  [centerLat, centerLon],
  17
);

// Zoom level label
const zoomLevelLabel = document.getElementById("zoom-level-label");
function updateZoomLabel() {
  if (!zoomLevelLabel) return;
  zoomLevelLabel.textContent = map.getZoom();
}
map.on("zoomend", updateZoomLabel);
updateZoomLabel();

// =====================================
// LAYER VISIBILITY (Qt ile iletişim)
// =====================================
const layerVisibility = {};

function applyQtVisibilityToLayers() {
  const groupTrenchesVisible = layerVisibility["group_trenches"] !== false;
  const groupFindsVisible = layerVisibility["group_finds"] !== false;

  Object.entries(trenchLayers).forEach(([idStr, layer]) => {
    const id = parseInt(idStr, 10);
    const key = `trench_${id}`;
    const selfVisible = layerVisibility[key] !== false;
    const finalVisible = groupTrenchesVisible && selfVisible;
    if (finalVisible) {
      if (!map.hasLayer(layer)) layer.addTo(map);
    } else {
      if (map.hasLayer(layer)) map.removeLayer(layer);
    }
  });

  Object.entries(findLayers).forEach(([idStr, layer]) => {
    const id = parseInt(idStr, 10);
    const key = `find_${id}`;
    const selfVisible = layerVisibility[key] !== false;
    const finalVisible = groupFindsVisible && selfVisible;
    if (finalVisible) {
      if (!map.hasLayer(layer)) layer.addTo(map);
    } else {
      if (map.hasLayer(layer)) map.removeLayer(layer);
    }
  });
}

function setLayerVisibilityFromQt(layerKey, visible) {
  layerVisibility[layerKey] = visible;
  applyQtVisibilityToLayers();
}

window.setLayerVisibilityFromQt = setLayerVisibilityFromQt;
window._applyQtVisibilityToLayers = applyQtVisibilityToLayers;

// =====================================
// RASTER / TILES
// =====================================
const rasterPane = map.createPane("rasterPane");
rasterPane.style.zIndex = 350;

// Farklı altlık haritaları
const baseLayers = {
  osm: L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 22,
    attribution: "© OpenStreetMap contributors",
  }),
  osm_hot: L.tileLayer(
    "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
    {
      maxZoom: 20,
      attribution:
        "© OpenStreetMap contributors, Tiles style by Humanitarian OpenStreetMap Team",
    }
  ),
  opentopo: L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    maxZoom: 17,
    attribution:
      "© OpenStreetMap contributors, SRTM | © OpenTopoMap (CC-BY-SA)",
  }),
  carto_voyager: L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    {
      maxZoom: 20,
      attribution: "© OpenStreetMap contributors © CARTO",
    }
  ),
  carto_light: L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    {
      maxZoom: 20,
      attribution: "© OpenStreetMap contributors © CARTO",
    }
  ),
  carto_dark: L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    {
      maxZoom: 20,
      attribution: "© OpenStreetMap contributors © CARTO",
    }
  ),
  None: L.tileLayer("", {
    maxZoom: 22,
    attribution: "",
  }),
};

let currentBaseLayer = baseLayers.osm;
currentBaseLayer.addTo(map);

const overlayEntries = [];
let firstImageBounds = null;

function parseZoomRangeFromUrlTemplate(urlTemplate) {
  const re = /_z(\d+)_(\d+)\/\{z\}\/\{x\}\/\{y\}\.png$/;
  const m = urlTemplate.match(re);
  if (!m) return null;
  return {
    minZoom: parseInt(m[1], 10),
    maxZoom: parseInt(m[2], 10),
  };
}

extraLayers.forEach((l) => {
  if (l.kind === "tile" && l.url_template) {
    const zoomInfo = parseZoomRangeFromUrlTemplate(l.url_template);
    const opts = {
      attribution: l.attribution || "",
      noWrap: true,
      pane: "rasterPane",
    };
    if (zoomInfo) {
      opts.maxNativeZoom = zoomInfo.maxZoom;
    }
    const layer = L.tileLayer(l.url_template, opts).addTo(map);
    overlayEntries.push({ name: l.name, layer, kind: "tile" });
  } else if (l.kind === "image" && l.file_url) {
    const bounds = [
      [l.min_lat, l.min_lon],
      [l.max_lat, l.max_lon],
    ];
    const layer = L.imageOverlay(l.file_url, bounds, {
      opacity: 0.8,
      pane: "rasterPane",
    }).addTo(map);
    overlayEntries.push({ name: l.name, layer, kind: "image" });
    if (!firstImageBounds) firstImageBounds = bounds;
  }
});

if (firstImageBounds) {
  map.fitBounds(firstImageBounds, { padding: [20, 20] });
}

if (errorMsg && errorMsg.trim().length > 0) {
  L.popup()
    .setLatLng([centerLat, centerLon])
    .setContent("Harita verisi yüklenirken hata: " + errorMsg)
    .openOn(map);
}

// =====================================
// Z COLOR SCALE
// =====================================
let zMin = null;
let zMax = null;
findsData.forEach((f) => {
  if (f.z == null) return;
  if (zMin === null || f.z < zMin) zMin = f.z;
  if (zMax === null || f.z > zMax) zMax = f.z;
});

function getColorForZ(z) {
  if (z == null || zMin === null || zMax === null) {
    return "#888888";
  }
  let t = (z - zMin) / (zMax - zMin || 1);
  t = Math.max(0, Math.min(1, t));

  if (t < 0.33) {
    const k = t / 0.33;
    const g = Math.round(255 * k);
    return `rgb(0,${g},255)`;
  } else if (t < 0.66) {
    const k = (t - 0.33) / 0.33;
    const r = Math.round(255 * k);
    const b = Math.round(255 * (1 - k));
    return `rgb(${r},255,${b})`;
  } else {
    const k = (t - 0.66) / 0.34;
    const g = Math.round(255 * (1 - k));
    return `rgb(255,${g},0)`;
  }
}

// =====================================
// TRENCHES
// =====================================
trenchesData.forEach((t) => {
  if (!t.vertices || !t.vertices.length) return;

  const latlngs = t.vertices.map((v) => [v.lat, v.lon]);
  const poly = L.polygon(latlngs, {
    color: "#4c9be8",
    fillColor: "#4c9be8",
    weight: 2,
    fillOpacity: 0.15,
  }).addTo(map);

  const popupText =
    "<b>Açma: </b>" +
    t.code +
    (t.name ? " – " + t.name : "") +
    "<br><b>Proje: </b>" +
    (t.project || "") +
    "<br>Köşe sayısı: " +
    t.vertices.length;

  poly.bindPopup(popupText);
  trenchLayers[t.id] = poly;
});

// =====================================
// FINDS
// =====================================
findsData.forEach((f) => {
  if (f.lat == null || f.lon == null) return;

  const color = getColorForZ(f.z);

  const marker = L.circleMarker([f.lat, f.lon], {
    radius: 5,
    weight: 1,
    color: color,
    fillColor: color,
    fillOpacity: 0.9,
  }).addTo(map);

  const popupText =
    "<b>Buluntu: </b>" +
    f.code +
    "<br><b>Açma: </b>" +
    (f.trench_code || f.trench_id) +
    (f.trench_name ? " – " + f.trench_name : "") +
    "<br>" +
    (f.level_name ? "<b>Seviye: </b>" + f.level_name + "<br>" : "") +
    (f.description ? "Açıklama: " + f.description + "<br>" : "") +
    (f.z != null ? "Z: " + f.z + " m<br>" : "") +
    (f.found_at ? "Tarih: " + f.found_at : "");

  marker.bindPopup(popupText);
  findLayers[f.id] = marker;
});

// =====================================
// LEGEND
// =====================================
const legend = L.control({ position: "bottomright" });
legend.onAdd = function () {
  const div = L.DomUtil.create("div", "info legend");
  div.innerHTML = `
    <div class="legend-card collapsed">
      <div class="legend-header">
        <span style="color: var(--legend-header-text);">Lejant</span>
        <span class="toggle-icon">▸</span>
      </div>
    
      <div class="legend-body">
    
        <div class="legend-row">
          <span class="legend-swatch" style="background:#4c9be8;"></span>
          <span class="legend-label" style="color: var(--legend-text);">Açmalar</span>
        </div>
    
        <div class="legend-row">
          <span class="legend-swatch round" style="background:#d62728;"></span>
          <span class="legend-label" style="color: var(--legend-text);">Buluntular</span>
        </div>
    
        <div class="legend-scale-title" style="color: var(--legend-scale-title);">
          Z Skala
        </div>
    
        <div class="legend-scale-bar"></div>
    
        ${
          zMin !== null && zMax !== null
            ? `<div class="legend-z-text" style="color: var(--legend-z-text);">
               Z min: ${zMin.toFixed(2)} m<br>
               Z max: ${zMax.toFixed(2)} m
             </div>`
            : ""
        }
    
      </div>
    </div>
  `;
  setTimeout(() => {
    const card = div.querySelector(".legend-card");
    const header = div.querySelector(".legend-header");
    const icon = div.querySelector(".toggle-icon");
    header.addEventListener("click", () => {
      const isCollapsed = card.classList.toggle("collapsed");
      if (icon) icon.textContent = isCollapsed ? "▸" : "▾";
    });
  }, 0);
  return div;
};
legend.addTo(map);

// =====================================
// LAYER PANEL
// =====================================
const layerPanel = document.getElementById("layer-panel");
const layerPanelHeader = document.getElementById("layer-panel-header");
const layerListEl = document.getElementById("layer-list");

layerPanelHeader.addEventListener("click", () => {
  const isCollapsed = layerPanel.classList.toggle("collapsed");
  const icon = layerPanelHeader.querySelector(".toggle-icon");
  if (icon) icon.textContent = isCollapsed ? "▸" : "▾";
});

let dragSrcEl = null;

function buildLayerPanel() {
  layerListEl.innerHTML = "";

  overlayEntries.forEach((entry) => {
    const item = document.createElement("div");
    item.className = "layer-item";
    item.dataset.layerName = entry.name;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "layer-checkbox";
    checkbox.checked = true;

    const label = document.createElement("div");
    label.className = "layer-label";
    label.textContent = entry.name;

    const sliderWrap = document.createElement("div");
    sliderWrap.className = "layer-slider";
    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = "100";
    slider.value = "100";
    slider.title = "Opacity";
    sliderWrap.appendChild(slider);

    const handle = document.createElement("div");
    handle.className = "layer-handle";
    handle.textContent = "⋮⋮";
    handle.draggable = true;

    item.appendChild(checkbox);
    item.appendChild(label);
    item.appendChild(sliderWrap);
    item.appendChild(handle);

    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        entry.layer.addTo(map);
        updateLayerOrderFromDom();
      } else {
        map.removeLayer(entry.layer);
      }
    });

    slider.addEventListener("input", () => {
      const val = parseInt(slider.value, 10) / 100;
      if (entry.layer.setOpacity) {
        entry.layer.setOpacity(val);
      } else if (entry.layer._image) {
        entry.layer._image.style.opacity = val;
      }
    });

    ["mousedown", "touchstart", "click"].forEach((evt) => {
      slider.addEventListener(
        evt,
        (e) => {
          e.stopPropagation();
        },
        { passive: true }
      );
    });

    label.addEventListener("click", () => {
      checkbox.checked = !checkbox.checked;
      checkbox.dispatchEvent(new Event("change"));
    });

    handle.addEventListener("dragstart", (e) => {
      dragSrcEl = item;
      item.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });

    handle.addEventListener("dragend", () => {
      if (dragSrcEl) dragSrcEl.classList.remove("dragging");
      dragSrcEl = null;
      updateLayerOrderFromDom();
    });

    item.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (!dragSrcEl || dragSrcEl === item) return;
      const rect = item.getBoundingClientRect();
      const midY = rect.top + rect.height / 2;
      const parent = item.parentNode;
      if (e.clientY < midY) {
        parent.insertBefore(dragSrcEl, item);
      } else {
        parent.insertBefore(dragSrcEl, item.nextSibling);
      }
    });

    item.addEventListener("drop", (e) => {
      e.preventDefault();
      updateLayerOrderFromDom();
    });

    layerListEl.appendChild(item);
  });
}
(window.vectorLayers || []).forEach((v) => {
  fetch(v.file_url)
    .then((r) => r.json())
    .then((geo) => {
      const layer = L.geoJSON(geo).addTo(map);
      overlayEntries.push({
        name: v.name,
        layer,
        kind: "vector",
      });
      updateLayerOrderFromDom();
    })
    .catch((err) => {
      console.error("Vektör layer yüklenemedi:", v.name, err);
    });
});

function updateLayerOrderFromDom() {
  const items = Array.from(layerListEl.querySelectorAll(".layer-item"));
  const total = items.length;

  items.forEach((item, index) => {
    const name = item.dataset.layerName;
    const entry = overlayEntries.find((e) => e.name === name);
    if (!entry || !map.hasLayer(entry.layer)) return;

    const z = 100 + (total - 1 - index);
    if (typeof entry.layer.setZIndex === "function") {
      entry.layer.setZIndex(z);
    } else if (entry.layer._image) {
      entry.layer._image.style.zIndex = z;
    }
  });
}

buildLayerPanel();
updateLayerOrderFromDom();

// =====================================
// SLIDERS
// =====================================
let DEPTH_MIN = null;
let DEPTH_MAX = null;

(function initDepthRangeFromFinds() {
  if (zMin === null || zMax === null) return;
  DEPTH_MIN = zMin;
  DEPTH_MAX = zMax;

  const depthMinInput = document.getElementById("depth-min");
  const depthMaxInput = document.getElementById("depth-max");
  const depthLabel = document.getElementById("depth-range-label");

  if (depthMinInput && depthMaxInput) {
    depthMinInput.min = DEPTH_MIN;
    depthMinInput.max = DEPTH_MAX;
    depthMaxInput.min = DEPTH_MIN;
    depthMaxInput.max = DEPTH_MAX;

    depthMinInput.value = DEPTH_MIN;
    depthMaxInput.value = DEPTH_MAX;

    if (depthLabel) {
      depthLabel.textContent =
        DEPTH_MIN.toFixed(2) + " – " + DEPTH_MAX.toFixed(2);
    }

    updateDepthBarBackground(DEPTH_MIN, DEPTH_MAX);
  }
})();

function updateDepthBarBackground(zFrom, zTo) {
  const row = document.getElementById("depth-slider-row");
  if (!row || DEPTH_MIN === null || DEPTH_MAX === null) return;

  const total = DEPTH_MAX - DEPTH_MIN || 1;
  const startPct = ((zFrom - DEPTH_MIN) / total) * 100;
  const endPct = ((zTo - DEPTH_MIN) / total) * 100;

  const styles = getComputedStyle(document.documentElement);
  const bg =
    styles.getPropertyValue("--filter-bg").trim() || "rgba(255,255,255,0.06)";
  const accentSoft =
    styles.getPropertyValue("--color-accent-soft").trim() ||
    styles.getPropertyValue("--color-accent").trim() ||
    "rgba(255,255,255,0.65)";

  row.style.background = `
    linear-gradient(
      to right,
      ${bg} 0%,
      ${bg} ${startPct}%,
      ${accentSoft} ${startPct}%,
      ${accentSoft} ${endPct}%,
      ${bg} ${endPct}%,
      ${bg} 100%
    )
  `;
}

// =====================================
// DATE PARSER
// =====================================
function autoFormatDateInput(input) {
  // Sadece rakamları al
  let v = input.value.replace(/\D/g, "");
  if (v.length > 8) v = v.slice(0, 8);

  let formatted = "";

  if (v.length <= 2) {
    // 1–2 hane: GG
    formatted = v;
  } else if (v.length <= 4) {
    // 3–4 hane: GG.AA
    formatted = v.slice(0, 2) + "." + v.slice(2);
  } else {
    // 5–8 hane: GG.AA.YYYY
    formatted = v.slice(0, 2) + "." + v.slice(2, 4) + "." + v.slice(4);
  }

  input.value = formatted;
}

function parseDateLoose(str) {
  if (!str) return null;
  let s = String(str).trim();
  if (!s) return null;

  const spaceIndex = s.indexOf(" ");
  if (spaceIndex !== -1) {
    s = s.slice(0, spaceIndex);
  }

  let m = s.match(/^(\d{1,2})[.\-\/](\d{1,2})[.\-\/](\d{4})$/);
  if (m) {
    const d = parseInt(m[1], 10);
    const mo = parseInt(m[2], 10);
    const y = parseInt(m[3], 10);
    const dt = new Date(y, mo - 1, d);
    if (!isNaN(dt.getTime())) return dt;
  }

  m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (m) {
    const y = parseInt(m[1], 10);
    const mo = parseInt(m[2], 10);
    const d = parseInt(m[3], 10);
    const dt = new Date(y, mo - 1, d);
    if (!isNaN(dt.getTime())) return dt;
  }

  return null;
}

function getDateRangeFromInputs() {
  const fromEl = document.getElementById("date-from");
  const toEl = document.getElementById("date-to");

  let from = null;
  let to = null;

  if (fromEl && fromEl.value) {
    from = parseDateLoose(fromEl.value);
    if (from) from.setHours(0, 0, 0, 0);
  }
  if (toEl && toEl.value) {
    to = parseDateLoose(toEl.value);
    if (to) to.setHours(23, 59, 59, 999);
  }

  return { from, to };
}

// =====================================
// FILTER
// =====================================
function getDepthRangeFromSliders() {
  const depthMinInput = document.getElementById("depth-min");
  const depthMaxInput = document.getElementById("depth-max");
  const depthLabel = document.getElementById("depth-range-label");

  if (!depthMinInput || !depthMaxInput) {
    return { zFrom: null, zTo: null };
  }

  let zFrom = parseFloat(depthMinInput.value);
  let zTo = parseFloat(depthMaxInput.value);

  if (isNaN(zFrom) || DEPTH_MIN === null) zFrom = DEPTH_MIN;
  if (isNaN(zTo) || DEPTH_MAX === null) zTo = DEPTH_MAX;

  if (zFrom > zTo) {
    const t = zFrom;
    zFrom = zTo;
    zTo = t;
  }

  if (depthLabel && zFrom != null && zTo != null) {
    depthLabel.textContent = zFrom.toFixed(2) + " – " + zTo.toFixed(2);
  }

  updateDepthBarBackground(zFrom, zTo);
  return { zFrom, zTo };
}

function findMatchesDateRange(find, from, to) {
  if (!from && !to) return true;

  const raw = find.found_at;
  if (!raw) return true;

  const d = parseDateLoose(raw);
  if (!d) return true;

  if (from && d < from) return false;
  if (to && d > to) return false;
  return true;
}

function findMatchesDepthRange(find, zFrom, zTo) {
  if (zFrom == null || zTo == null) return true;
  const z = typeof find.z === "number" ? find.z : parseFloat(find.z);
  if (isNaN(z)) return false;

  if (z < zFrom) return false;
  if (z > zTo) return false;
  return true;
}

function applyFilter(rawQuery) {
  const q = (rawQuery || "").trim().toLowerCase();
  const { from, to } = getDateRangeFromInputs();
  const { zFrom, zTo } = getDepthRangeFromSliders();

  const hasDateFilter = !!(from || to);
  const hasDepthFilter = zFrom != null && zTo != null;

  Object.values(trenchLayers).forEach((l) => map.removeLayer(l));
  Object.values(findLayers).forEach((l) => map.removeLayer(l));

  if (!q && !hasDateFilter && !hasDepthFilter) {
    Object.values(trenchLayers).forEach((l) => l.addTo(map));
    Object.values(findLayers).forEach((l) => l.addTo(map));
    return;
  }

  const tokens = q.split(/\s+/).filter(Boolean);

  const visibleFindIds = [];
  const visibleTrenchIds = new Set();

  findsData.forEach((f) => {
    if (!findMatchesDateRange(f, from, to)) return;
    if (!findMatchesDepthRange(f, zFrom, zTo)) return;

    let text = "";
    if (f.code) text += " " + f.code;
    if (f.description) text += " " + f.description;
    if (f.trench_code) text += " " + f.trench_code;
    if (f.trench_name) text += " " + f.trench_name;
    if (f.level_name) text += " " + f.level_name;

    const t = text.toLowerCase();
    const textOk = !tokens.length || tokens.every((tok) => t.includes(tok));

    if (textOk) {
      visibleFindIds.push(f.id);
      if (f.trench_id != null) visibleTrenchIds.add(f.trench_id);
    }
  });

  trenchesData.forEach((tData) => {
    let text = "";
    if (tData.code) text += " " + tData.code;
    if (tData.name) text += " " + tData.name;
    if (tData.project) text += " " + tData.project;

    const tt = text.toLowerCase();
    const textOk = !tokens.length || tokens.every((tok) => tt.includes(tok));

    if (textOk) {
      visibleTrenchIds.add(tData.id);
    }
  });

  if (!visibleFindIds.length && !visibleTrenchIds.size) {
    if (!hasDateFilter && !hasDepthFilter) {
      Object.values(findLayers).forEach((l) => l.addTo(map));
      Object.values(trenchLayers).forEach((l) => l.addTo(map));
    }
    return;
  }

  visibleFindIds.forEach((id) => {
    const layer = findLayers[id];
    if (layer) layer.addTo(map);
  });

  visibleTrenchIds.forEach((tid) => {
    const layer = trenchLayers[tid];
    if (layer) layer.addTo(map);
  });
}

// =====================================
// EVENTS
// =====================================
const filterInput = document.getElementById("filter-input");
if (filterInput) {
  filterInput.addEventListener("keyup", (e) => {
    if (e.key === "Enter") {
      applyFilter(filterInput.value);
    }
  });
  filterInput.addEventListener("input", () => {
    applyFilter(filterInput.value);
  });
}

const dateFromInput = document.getElementById("date-from");
const dateToInput = document.getElementById("date-to");

if (dateFromInput) {
  dateFromInput.addEventListener("input", () => {
    autoFormatDateInput(dateFromInput);
  });
}

if (dateToInput) {
  dateToInput.addEventListener("input", () => {
    autoFormatDateInput(dateToInput);
  });
}

const clearDateBtn = document.getElementById("date-filter-clear");

if (dateFromInput) {
  dateFromInput.addEventListener("change", () => {
    applyFilter(filterInput ? filterInput.value : "");
  });
}

if (dateToInput) {
  dateToInput.addEventListener("change", () => {
    applyFilter(filterInput ? filterInput.value : "");
  });
}

if (clearDateBtn) {
  clearDateBtn.addEventListener("click", () => {
    dateFromInput.value = "";
    dateToInput.value = "";
    applyFilter(filterInput ? filterInput.value : "");
  });
}

const zoomInBtn = document.getElementById("zoom-in-btn");
const zoomOutBtn = document.getElementById("zoom-out-btn");

if (zoomInBtn) zoomInBtn.addEventListener("click", () => map.zoomIn());
if (zoomOutBtn) zoomOutBtn.addEventListener("click", () => map.zoomOut());

const depthMinInput = document.getElementById("depth-min");
const depthMaxInput = document.getElementById("depth-max");

if (depthMinInput)
  depthMinInput.addEventListener("input", () => applyFilter(filterInput.value));
if (depthMaxInput)
  depthMaxInput.addEventListener("input", () => applyFilter(filterInput.value));

// Altlık seçimi
const basemapSelect = document.getElementById("basemap-select");

if (basemapSelect) {
  basemapSelect.addEventListener("change", () => {
    const key = basemapSelect.value;
    const nextLayer = baseLayers[key];
    if (!nextLayer || nextLayer === currentBaseLayer) return;

    // Eski altlığı kaldır, yenisini ekle
    if (currentBaseLayer) {
      map.removeLayer(currentBaseLayer);
    }
    nextLayer.addTo(map);
    currentBaseLayer = nextLayer;
  });

  // Açılışta default değeri senkronize et
  basemapSelect.value = "osm";
}

// =====================================
// PUBLIC API (Qt için)
// =====================================
window.focusOnTrench = function (trenchId) {
  const layer = trenchLayers[trenchId];
  if (layer) {
    map.fitBounds(layer.getBounds(), { padding: [30, 30] });
    layer.openPopup();
  }
};

window.focusOnFind = function (findId) {
  const layer = findLayers[findId];
  if (layer) {
    map.setView(layer.getLatLng(), 19);
    layer.openPopup();
  }
};

window.focusOnAllTrenches = function () {
  const ids = Object.keys(trenchLayers);
  if (!ids.length) return;
  let bounds = null;
  ids.forEach((id) => {
    const b = trenchLayers[id].getBounds();
    bounds = bounds ? bounds.extend(b) : b;
  });
  if (bounds) {
    map.fitBounds(bounds, { padding: [30, 30] });
  }
};

window.focusOnAllFinds = function () {
  const ids = Object.keys(findLayers);
  if (!ids.length) return;
  const latlngs = ids.map((id) => findLayers[id].getLatLng());
  let bounds = null;
  latlngs.forEach((ll) => {
    bounds = bounds ? bounds.extend(ll) : L.latLngBounds(ll, ll);
  });
  if (bounds) {
    map.fitBounds(bounds, { padding: [30, 30] });
  }
};

window.applyFilter = applyFilter;
