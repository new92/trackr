/* Trackr dashboard — no third-party scripts, cookies or external map tiles. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const t = JSON.parse($("ui-labels").textContent);
  const lang = document.documentElement.lang;
  const refreshSeconds = Math.max(10, Number(document.body.dataset.refreshSeconds) || 45);
  const SVG_NS = "http://www.w3.org/2000/svg";
  const locale = { el: "el-GR", en: "en-GB", fr: "fr-FR", de: "de-DE", es: "es-ES" }[lang] || "en-GB";
  const state = { data: null, selected: "25is-martiou", filter: "all", query: "", favorites: new Set(), notifications: false, loading: false };

  function storageRead(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
  }
  function storageWrite(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage may be disabled */ }
  }
  const savedFavorites = storageRead("trackr:v3:favorites", []);
  state.favorites = new Set(Array.isArray(savedFavorites) ? savedFavorites.filter((s) => typeof s === "string") : []);
  state.notifications = storageRead("trackr:v3:alerts", false) === true;
  if (typeof Notification === "undefined" || Notification.permission !== "granted") state.notifications = false;
  const savedTheme = storageRead("trackr:v3:theme", "dark");
  document.body.dataset.theme = savedTheme === "light" ? "light" : "dark";

  function showToast(message) {
    const node = $("toast");
    node.textContent = message;
    node.hidden = false;
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => { node.hidden = true; }, 5500);
  }
  function text(id, value) { $(id).textContent = String(value); }
  function stateLabel(value) { return t[value] || t.unknown; }
  function indicatorClass(status) {
    return status === "operational" ? "good" : (status === "closed" || status === "out_of_service") ? "bad" : "neutral";
  }
  function formatTime(iso) {
    if (!iso) return "—";
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Athens" }).format(date) + " (Athens)";
  }
  function sectionLabel(section) {
    return section === "shared" ? t.shared : section === "nea-elvetia" ? t.nea_elvetia : t.kalamaria;
  }
  function stationName(station) { return station.name || (lang === "el" ? station.name_el : station.name_en); }

  function updateStatus(data) {
    const value = data.service?.state || "unknown";
    const hero = $("service-status");
    const visualState = data.stale ? "unknown" : value;
    hero.className = "hero-status " + visualState;
    hero.closest(".status-hero").dataset.level = data.stale || value === "unknown" ? "unknown" :
      ["limited", "disrupted", "mixed", "closed"].includes(value) ? "problem" : "operational";
    text("service-label", data.status === "unavailable" ? t.unavailable : data.stale ? t.stale : stateLabel(value));
    text("service-description", data.service?.message || t.unknown_note);
    text("last-updated", `${t.last_updated}: ${formatTime(data.fetched_at)}`);
    $("stale-banner").hidden = !data.stale;
    text("stale-text", data.status === "unavailable" ? t.no_data : t.stale_warning);

    const summary = data.summary;
    text("stations-stat", summary.stations_operational);
    text("stations-total", `${t.total} ${summary.stations_total}`);
    text("lifts-stat", summary.elevators_operational);
    text("lifts-total", `${t.total} ${summary.elevators_total}`);
    text("closed-stat", summary.stations_closed);
    text("unknown-count", summary.stations_unknown ? `${summary.stations_unknown} ${t.unknown.toLowerCase()}` : "");
    text("station-count", data.stations.length);

    $("announcement-panel").hidden = !data.announcement;
    text("announcement-text", data.announcement || "");
    const link = $("announcement-link");
    if (data.announcement_url) {
      try {
        const url = new URL(data.announcement_url);
        if (url.protocol === "https:" && ["www.thessmetro.gr", "thessmetro.gr"].includes(url.hostname)) {
          link.href = url.href;
          link.hidden = false;
        } else { link.hidden = true; }
      } catch { link.hidden = true; }
    } else { link.hidden = true; }
  }

  function svgElement(name, attrs = {}, content = "") {
    const node = document.createElementNS(SVG_NS, name);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
    if (content) node.textContent = content;
    return node;
  }
  const compactNames = {
    "new-railway-station": { en: "Railway Station", el: "Ν. Σιδ. Σταθμός" },
    "25is-martiou": { en: "25is Martiou", el: "25ης Μαρτίου" },
  };
  function compactName(s) {
    return (compactNames[s.id] && compactNames[s.id][lang === "el" ? "el" : "en"]) || stationName(s);
  }
  function mapPosition(index) {
    if (index <= 10) return { x: 83 + index * 78, y: 130, branch: "shared" };
    if (index <= 12) return { x: 83 + index * 78, y: 130, branch: "nea-elvetia" };
    return { x: 863, y: 220 + (index - 13) * 91, branch: "kalamaria" };
  }
  function selectStation(id) {
    state.selected = id;
    renderSelected();
    renderMap();
    renderStations();
  }
  function renderMap() {
    const svg = $("network-map");
    svg.replaceChildren();
    svg.appendChild(svgElement("path", { d: "M83,130 H1019", class: "map-line shared" }));
    svg.appendChild(svgElement("path", { d: "M863,130 V584", class: "map-line branch" }));
    svg.appendChild(svgElement("text", { x: 65, y: 49, class: "map-caption" }, t.shared.toUpperCase()));
    svg.appendChild(svgElement("text", { x: 1030, y: 92, class: "map-caption", "text-anchor": "middle" }, t.nea_elvetia.toUpperCase()));
    svg.appendChild(svgElement("text", { x: 905, y: 200, class: "map-caption" }, t.kalamaria.toUpperCase()));
    if (!state.data) return;
    state.data.stations.forEach((station, index) => {
      const position = mapPosition(index);
      const status = station.status;
      const group = svgElement("g", {
        class: `station-node station-node--${status}${state.selected === station.id ? " station-node--selected" : ""}`,
        transform: `translate(${position.x} ${position.y})`,
        role: "button", tabindex: "0", "aria-label": `${stationName(station)}: ${stateLabel(status)}`,
        "aria-pressed": String(state.selected === station.id),
      });
      group.appendChild(svgElement("circle", { r: state.selected === station.id ? 12 : 10, cx: 0, cy: 0 }));
      const isBranch = position.branch === "kalamaria";
      const alternate = index % 2 === 0;
      const label = svgElement("text", {
        x: isBranch ? 36 : 0,
        y: isBranch ? 5 : alternate ? -27 : 37,
        "text-anchor": isBranch ? "start" : "middle",
        class: "map-label",
      }, compactName(station));
      group.appendChild(label);
      group.appendChild(svgElement("title", {}, `${stationName(station)}: ${stateLabel(status)}`));
      group.addEventListener("click", () => selectStation(station.id));
      group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectStation(station.id); }
      });
      svg.appendChild(group);
    });
  }

  function detailPill(title, value) {
    const node = document.createElement("span");
    node.className = "detail-pill";
    const dot = document.createElement("i");
    dot.className = `legend-dot ${indicatorClass(value)}`;
    const strong = document.createElement("b");
    strong.textContent = title;
    const label = document.createTextNode(": " + stateLabel(value));
    node.append(dot, strong, label);
    return node;
  }
  function renderSelected() {
    const station = state.data?.stations.find((entry) => entry.id === state.selected);
    const wrapper = $("selected-description");
    wrapper.replaceChildren();
    if (!station) { text("selected-name", "—"); text("selected-line", ""); wrapper.textContent = t.details_hint; return; }
    text("selected-name", stationName(station));
    text("selected-line", sectionLabel(station.section));
    wrapper.append(
      detailPill(t.station_status, station.status),
      detailPill(t.elevator_status, station.elevator?.status || "unknown"),
    );
    if (station.elevator?.message) {
      const message = document.createElement("span");
      message.className = "detail-pill";
      message.textContent = station.elevator.message;
      wrapper.append(message);
    }
    if (state.data?.stale) {
      const warning = document.createElement("span");
      warning.className = "detail-pill";
      warning.textContent = t.stale;
      wrapper.append(warning);
    }
  }

  function toggleFavorite(id) {
    if (state.favorites.has(id)) state.favorites.delete(id);
    else state.favorites.add(id);
    storageWrite("trackr:v3:favorites", [...state.favorites]);
    renderStations();
  }
  function matches(station) {
    const query = state.query.trim().toLocaleLowerCase(locale);
    if (query && ![station.name, station.name_en, station.name_el].some((s) => String(s || "").toLocaleLowerCase(locale).includes(query))) return false;
    if (state.filter === "favorites" && !state.favorites.has(station.id)) return false;
    if (state.filter === "issues" && station.status !== "closed" && station.elevator?.status !== "out_of_service") return false;
    return true;
  }
  function renderStations() {
    const list = $("station-list");
    list.replaceChildren();
    const stations = state.data?.stations.filter(matches) || [];
    if (!stations.length) { const p = document.createElement("p"); p.className = "empty-state"; p.textContent = t.no_matches; list.append(p); return; }
    stations.forEach((station) => {
      const actualIndex = state.data.stations.findIndex((s) => s.id === station.id);
      const row = document.createElement("div");
      row.className = `station-row${station.id === state.selected ? " selected" : ""}`;
      const hit = document.createElement("button");
      hit.className = "station-hit";
      hit.type = "button";
      hit.setAttribute("aria-pressed", String(station.id === state.selected));
      hit.setAttribute("aria-label", `${stationName(station)}, ${stateLabel(station.status)}`);
      const number = document.createElement("span"); number.className = "station-number"; number.textContent = String(actualIndex + 1).padStart(2, "0");
      const main = document.createElement("span"); main.className = "station-main";
      const name = document.createElement("strong"); name.textContent = stationName(station);
      const section = document.createElement("small"); section.textContent = sectionLabel(station.section);
      main.append(name, section);
      const stat = document.createElement("span"); stat.className = `station-state ${station.status}`;
      const dot = document.createElement("i"); dot.className = `legend-dot ${indicatorClass(station.status)}`;
      stat.append(dot, document.createTextNode(stateLabel(station.status)));
      hit.append(number, main, stat);
      hit.addEventListener("click", () => selectStation(station.id));
      const favorite = document.createElement("button");
      favorite.type = "button";
      favorite.className = `favorite-star${state.favorites.has(station.id) ? " active" : ""}`;
      favorite.textContent = state.favorites.has(station.id) ? "★" : "☆";
      favorite.setAttribute("aria-label", `${state.favorites.has(station.id) ? t.unfavorite : t.favorite}: ${stationName(station)}`);
      favorite.setAttribute("aria-pressed", String(state.favorites.has(station.id)));
      favorite.addEventListener("click", () => toggleFavorite(station.id));
      row.append(hit, favorite);
      list.append(row);
    });
  }

  function maybeAlert(oldData, newData) {
    if (!state.notifications || !oldData || oldData.stale || newData.stale || !oldData.fetched_at || oldData.fetched_at === newData.fetched_at) return;
    if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
    if (oldData.service?.state === "operational" && ["disrupted", "limited", "mixed"].includes(newData.service?.state)) {
      new Notification(`Trackr · ${t.service_update}`, { body: stateLabel(newData.service.state) });
    }
    newData.stations.forEach((station) => {
      if (!state.favorites.has(station.id)) return;
      const old = oldData.stations.find((s) => s.id === station.id);
      if (!old) return;
      const messages = [];
      if (old.status === "operational" && station.status === "closed") messages.push(t.station_closed_alert);
      if (old.elevator?.status === "operational" && station.elevator?.status === "out_of_service") messages.push(t.lift_down_alert);
      if (messages.length) new Notification(`Trackr · ${stationName(station)}`, { body: messages.join("; ") });
    });
  }

  async function loadData(manual = false) {
    if (state.loading) return;
    state.loading = true;
    $("refresh-button").disabled = true;
    try {
      const url = `/api?lang=${encodeURIComponent(lang)}${manual ? "&refresh=1" : ""}`;
      const response = await fetch(url, { cache: "no-store", headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok && response.status !== 503) throw new Error("Unexpected API response");
      if (!payload || !Array.isArray(payload.stations) || !payload.summary) throw new Error("Invalid payload");
      const previous = state.data;
      state.data = payload;
      updateStatus(payload);
      renderMap(); renderSelected(); renderStations();
      maybeAlert(previous, payload);
    } catch {
      showToast(t.error_reload);
      if (state.data) { state.data.stale = true; updateStatus(state.data); renderSelected(); }
      else {
        text("service-label", t.unavailable);
        text("service-description", t.no_data);
        $("stale-banner").hidden = false;
        text("stale-text", t.no_data);
      }
    } finally { state.loading = false; $("refresh-button").disabled = false; }
  }

  function nearestDistance(lat, lon, s) {
    const rad = (deg) => deg * Math.PI / 180;
    const dLat = rad(s.lat - lat), dLon = rad(s.lng - lon);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat)) * Math.cos(rad(s.lat)) * Math.sin(dLon / 2) ** 2;
    return 6371.0088 * 2 * Math.asin(Math.min(1, Math.sqrt(a)));
  }
  function locate() {
    if (!navigator.geolocation) { showToast(t.geolocation_denied); return; }
    $("nearest-button").disabled = true;
    navigator.geolocation.getCurrentPosition((position) => {
      $("nearest-button").disabled = false;
      const stations = state.data?.stations || [];
      if (!stations.length) { showToast(t.no_data); return; }
      const lat = position.coords.latitude, lng = position.coords.longitude;
      const sorted = stations.map((s) => ({ station: s, km: nearestDistance(lat, lng, s) })).sort((a, b) => a.km - b.km);
      const result = sorted[0];
      text("nearest-info", `${stationName(result.station)} · ${result.km.toFixed(2)} ${t.distance}. ${t.nearest_no_live}`);
      selectStation(result.station.id);
    }, () => { $("nearest-button").disabled = false; showToast(t.geolocation_denied); }, { enableHighAccuracy: false, maximumAge: 60000, timeout: 10000 });
  }

  function updateNotificationButton() { text("notification-label", state.notifications ? t.alerts_disable : t.alerts_enable); }
  async function toggleNotifications() {
    if (state.notifications) { state.notifications = false; storageWrite("trackr:v3:alerts", false); showToast(t.alert_off); updateNotificationButton(); return; }
    if (typeof Notification === "undefined" || !window.isSecureContext) { showToast(t.alert_unsupported); return; }
    try {
      const permission = await Notification.requestPermission();
      if (permission === "granted") {
        state.notifications = true; storageWrite("trackr:v3:alerts", true); showToast(t.alert_on);
      } else showToast(t.alert_unsupported);
    } catch { showToast(t.alert_unsupported); }
    updateNotificationButton();
  }

  $("refresh-button").addEventListener("click", () => loadData(true));
  $("notifications-button").addEventListener("click", toggleNotifications);
  $("nearest-button").addEventListener("click", locate);
  $("station-search").addEventListener("input", (event) => { state.query = event.target.value; renderStations(); });
  document.querySelectorAll(".filter").forEach((button) => button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    document.querySelectorAll(".filter").forEach((item) => {
      const active = item === button;
      item.classList.toggle("active", active);
      item.setAttribute("aria-pressed", String(active));
    });
    renderStations();
  }));
  $("language-selector").addEventListener("change", (event) => {
    const url = new URL(window.location.href);
    url.searchParams.set("lang", event.target.value);
    window.location.assign(url.href);
  });
  $("theme-toggle").addEventListener("click", () => {
    const theme = document.body.dataset.theme === "light" ? "dark" : "light";
    document.body.dataset.theme = theme;
    storageWrite("trackr:v3:theme", theme);
  });
  updateNotificationButton();
  loadData();
  setInterval(() => { if (!document.hidden) loadData(); }, refreshSeconds * 1000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) loadData(); });
})();
