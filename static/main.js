// ---------------------------------------------------------------
// CONFIG (should match what Flask serves)
// ---------------------------------------------------------------

const LOCATION_NAME = "Cornell Weather";      // matches config.yaml
const CYCLE_INTERVAL_MS = 20000;            // ms between panel advances
const RADAR_REFRESH_MS = 2 * 60 * 1000;   // 2 minutes, matching config.yaml

// Panels in rotation order. id must match the HTML element id.
const PANELS = [
    { id: "panel-satellite-vis",  title: "GOES GeoColor" },
    { id: "panel-satellite-ir",   title: "GOES Band 13 Longwave IR" },
    { id: "panel-surface-analysis", title: "WPC Surface Analysis" },
    { id: "panel-nws-alerts",       title: "NWS Alerts Map" },
    { id: "panel-spc",             title: "SPC Severe Weather Outlook" },
    { id: "panel-noaa",             title: "Assorted NOAA Outlooks/Monitors" },
    { id: "panel-forecast-daily", title: "NWS 5-Day Forecast" },
    { id: "panel-ne-sat-1", title: "Northeast: GeoColor/Longwave IR" },
    { id: "panel-ne-sat-2", title: "Northeast: Cloud Micro/Water Vapor" },
    { id: "panel-radar",          title: "MRMS Reflectivity" },
    { id: "panel-hrrr",          title: "HRRR Model Panels" },
];

// ---------------------------------------------------------------
// UNIT CONVERSION HELPERS
// NWS API returns SI units throughout, so we convert for display
// ---------------------------------------------------------------

function cToF(c) {
    if (c === null || c === undefined) return "--";
    return (c * 9/5 + 32).toFixed(1) + "°F";
}

function kmhTomph(kmh) {
    if (kmh === null || kmh === undefined) return null;
    return Math.round(kmh / 1.609);
}

function mToMiles(m) {
    if (m === null || m === undefined) return "--";
    return (m / 1609.34).toFixed(1) + " mi";
}

function paTohPa(pa) {
    if (pa === null || pa === undefined) return "--";
    return (pa / 100).toFixed(1) + " hPa";
}

function degreesToCardinal(deg) {
    if (deg === null || deg === undefined) return "--";
    const dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                  "S","SSW","SW","WSW","W","WNW","NW","NNW"];
    return dirs[Math.round(deg / 22.5) % 16];
}

function formatWind(dir_deg, spd_ms, gust_ms) {
    if (spd_ms === null || spd_ms === undefined) return "--";
    const spd = kmhTomph(spd_ms);
    const dir = degreesToCardinal(dir_deg);
    let str = `${dir} ${spd} mph`;
    if (gust_ms) str += ` G ${kmhTomph(gust_ms)} mph`;
    return str;
}

// ---------------------------------------------------------------
// CLOCK
// ---------------------------------------------------------------

function updateClock() {
    const now = new Date();
    const utc = now.toUTCString().replace("GMT", "UTC").slice(0, -4);
    const local = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    document.getElementById("clock").textContent = `${utc} Z / ${local} EDT`;
}

// ---------------------------------------------------------------
// OBSERVATIONS
// ---------------------------------------------------------------

async function updateObservations() {
    try {
        const resp = await fetch("/api/observations");
        const obs = await resp.json();
        if (!obs) return;

        document.getElementById("obs-station").textContent   = obs.station;
        document.getElementById("obs-time").textContent      = `${obs.timestamp.slice(0, 10)} ${obs.timestamp.slice(11, 16)} Z`;
        document.getElementById("obs-temp").textContent      = cToF(obs.temp_c);
        document.getElementById("obs-dewpoint").textContent  = cToF(obs.dewpoint_c);
        document.getElementById("obs-wind").textContent      = formatWind(obs.wind_dir, obs.wind_spd_kmh, obs.wind_gust_kmh);
        document.getElementById("obs-vis").textContent       = mToMiles(obs.visibility_m);
        document.getElementById("obs-altimeter").textContent = paTohPa(obs.pressure_sl_pa);
        document.getElementById("obs-sky").textContent       = obs.sky_condition || "--";
        document.getElementById("obs-metar").textContent     = obs.raw_metar || "";
    } catch (e) {
        console.error("Failed to update observations:", e);
    }
}

// ---------------------------------------------------------------
// FORECASTS
// ---------------------------------------------------------------

async function updateForecasts() {
    try {
        const resp = await fetch("/api/forecast");
        const data = await resp.json();
        if (!data) return;

        // --- 12-hour strip (left column) ---
        const shortEl = document.getElementById("forecast-short-content");
        shortEl.innerHTML = "";
        for (const period of data.hourly) {
            const time = new Date(period.startTime)
                .toLocaleTimeString([], { hour: "numeric" });
            const pop  = period.probabilityOfPrecipitation?.value;
            const row  = document.createElement("div");
            row.className = "forecast-row";
            row.innerHTML = `
                <span class="forecast-time">${time}</span>
                <span class="forecast-desc">${period.shortForecast}</span>
                <span class="forecast-temp">${period.temperature}°${period.temperatureUnit}</span>
                <span class="forecast-pop">${pop !== null ? pop + "%" : ""}</span>
            `;
            shortEl.appendChild(row);
        }

        // --- 5-day cards (cycling panel) ---
        const dailyEl = document.getElementById("forecast-daily-content");
        dailyEl.innerHTML = "";

        const periods = data.daily;
        for (const period of periods) {
            const pop = period.probabilityOfPrecipitation?.value;
            const card = document.createElement("div");
            const relhum = period.relativeHumidity?.value;
            card.className = `daily-card ${period.isDaytime ? "day-period" : "night-period"}`;
            card.innerHTML = `
                <div class="daily-row">
                    <div class="daily-left">
                        <div class="daily-name">${period.name}</div>
                        <div class="daily-desc">${period.shortForecast}</div>
                    </div>
                    <div class="daily-right">
                        <div class="daily-temp">${period.temperature}°${period.temperatureUnit}</div>
                        ${pop !== null ? `<div class="daily-pop">Chance of Precip: ${pop}%</div>` : ""}
                        <div class="daily-other">Wind: ${period.windDirection} @ ${period.windSpeed}</div>
                    </div>
                </div>
            `;
            dailyEl.appendChild(card);
        }
    } catch (e) {
        console.error("Failed to update forecasts:", e);
    }
}

// ---------------------------------------------------------------
// SATELLITE LOOPS
// Frames are base64-encoded JPEGs served as JSON arrays.
// We preload all frames into Image objects, then flip through
// them on a short interval to create the animation.
// ---------------------------------------------------------------

const loopState = {
    vis: { frames: [], idx: 0, type: "base64"},
    ir:  { frames: [], idx: 0, type: "base64" },
    radar: {frames: [], idx: 0, type: "base64"},
    model: { frames: [], idx: 0, type: "url" },
    ne_vis: { frames: [], idx: 0, type: "base64"},
    ne_ir: { frames: [], idx: 0, type: "base64"},
    ne_cloud: { frames: [], idx: 0, type: "base64"},
    ne_band9: { frames: [], idx: 0, type: "base64"},
};

function animateLoop(stateKey, imgElementId) {
    const state = loopState[stateKey];
    if (state.frames.length === 0) {
        // No frames yet — check again in 10 seconds
        setTimeout(() => animateLoop(stateKey, imgElementId), 10000);
        return;
    }

    // Hide loading message if present
    const loadingEl = document.getElementById(
        imgElementId.replace("-img", "-loading")
    );
    if (loadingEl) loadingEl.style.display = "none";

    const el = document.getElementById(imgElementId);
    const frame = state.frames[state.idx];

    el.src = state.type === "base64"
        ? "data:image/jpeg;base64," + frame
        : frame;

    const isLast = state.idx === state.frames.length - 1;
    const delay  = isLast ? 1200 : 200;

    state.idx = isLast ? 0 : state.idx + 1;
    setTimeout(() => animateLoop(stateKey, imgElementId), delay);
}

async function updateSatellite() {
    try {
        const bust = Date.now();
        const [visResp, irResp] = await Promise.all([
            fetch("/api/satellite_vis?t=${bust}"),
            fetch("/api/satellite_ir?t=${bust}"),
        ]);
        const visData = await visResp.json();
        const irData  = await irResp.json();

        // Update frames in place — animation continues uninterrupted
        if (visData.frames?.length) {
            loopState.vis.frames = visData.frames;
            loopState.vis.idx = 0;
        }
        if (irData.frames?.length)  {
            loopState.ir.frames  = irData.frames;
            loopState.ir.idx = 0;
        }

    } catch (e) {
        console.error("Failed to update satellite:", e);
    }
}

async function updateNeSat() {
    try {
        const bust = Date.now();
        const [visResp, irResp, cloud, band9] = await Promise.all([
            fetch(`/api/ne-sat/vis?t=${bust}`),
            fetch(`/api/ne-sat/ir?t=${bust}`),
            fetch(`/api/ne-sat/cloud?t=${bust}`),   // replace with your actual route
            fetch(`/api/ne-sat/band9?t=${bust}`),
        ]);
        const [visData, irData, cloudData, band9Data] = await Promise.all([
            visResp.json(), irResp.json(), cloud.json(), band9.json()
        ]);

        if (visData.frames?.length)  { loopState.ne_vis.frames = visData.frames;  loopState.ne_vis.idx = 0; }
        if (irData.frames?.length)   { loopState.ne_ir.frames  = irData.frames;   loopState.ne_ir.idx  = 0; }
        if (cloudData.frames?.length)    { loopState.ne_cloud.frames   = cloudData.frames;    loopState.ne_cloud.idx   = 0; }
        if (band9Data.frames?.length)    { loopState.ne_band9.frames   = band9Data.frames;    loopState.ne_band9.idx   = 0; }
    } catch (e) {
        console.error("Failed to update NE satellite:", e);
    }
}

async function updateRadar() {
    try {
        const bust = Date.now();
        const resp = await fetch(`/api/radar?t=${bust}`);
        const data = await resp.json();
        if (data.frames?.length) {
            loopState.radar.frames = data.frames;
            loopState.radar.idx = 0;
        }
    } catch (e) {
        console.error("Failed to update radar:", e);
    }
}

async function updateModel() {
    try {
        const bust = Date.now();
        const resp = await fetch(`/api/hrrr_surface?t=${bust}`);
        const data = await resp.json();
        if (data.urls?.length) {
            loopState.model.frames = data.urls.map(url => `${url}?t=${bust}`);
            loopState.model.idx = 0;
        }
    } catch (e) {
        console.error("Failed to update model:", e);
    }
}

function startLoops() {
    animateLoop("vis", "satellite-vis-img");
    animateLoop("ir",  "satellite-ir-img");
}

// ---------------------------------------------------------------
// CYCLING PANEL LOGIC
// ---------------------------------------------------------------

let currentPanelIdx = 0;
let cycleTimer = null;
let isPaused = false;

function buildDots() {
    const dotsEl = document.getElementById("cycle-dots");
    dotsEl.innerHTML = "";
    PANELS.forEach((_, i) => {
        const dot = document.createElement("div");
        dot.className = "cycle-dot" + (i === 0 ? " active" : "");
        dot.addEventListener("click", () => goToPanel(i));
        dotsEl.appendChild(dot);
    });
}

function goToPanel(idx) {
    // Hide current
    document.getElementById(PANELS[currentPanelIdx].id)
        .classList.remove("active");
    document.querySelectorAll(".cycle-dot")[currentPanelIdx]
        .classList.remove("active");

    // Show new
    currentPanelIdx = idx;
    document.getElementById(PANELS[currentPanelIdx].id)
        .classList.add("active");
    document.querySelectorAll(".cycle-dot")[currentPanelIdx]
        .classList.add("active");
    document.getElementById("cycle-title").textContent =
        PANELS[currentPanelIdx].title;
}

function advancePanel() {
    goToPanel((currentPanelIdx + 1) % PANELS.length);
}

function startCycleTimer() {
    cycleTimer = setInterval(advancePanel, CYCLE_INTERVAL_MS);
}

function togglePause() {
    isPaused = !isPaused;
    const statusEl = document.getElementById("cycle-status");
    if (isPaused) {
        clearInterval(cycleTimer);
        statusEl.textContent = "⏸";
    } else {
        startCycleTimer();
        statusEl.textContent = "▶";
    }
}

// ---------------------------------------------------------------
// INIT
// ---------------------------------------------------------------

document.addEventListener("DOMContentLoaded", async () => {
    // Set location name in header
    document.getElementById("location-name").textContent = LOCATION_NAME;
    document.getElementById("sub-name").textContent = "Welcome to the Mac Lab!"

    // Clock — update every second
    updateClock();
    setInterval(updateClock, 1000);

    // Build cycling UI
    buildDots();
    goToPanel(0);
    startCycleTimer();

    // Spacebar to pause/resume, arrow keys to advance/go back
    document.addEventListener("keydown", e => {
        if (e.code === "Space") { e.preventDefault(); togglePause(); }
        if (e.code === "ArrowRight") goToPanel((currentPanelIdx + 1) % PANELS.length);
        if (e.code === "ArrowLeft")  goToPanel((currentPanelIdx - 1 + PANELS.length) % PANELS.length);
    });

    // Click cycle-status button to pause too
    document.getElementById("cycle-status")
        .addEventListener("click", togglePause);

    // Initial data fetches
    updateObservations();
    updateForecasts();
    await updateSatellite();  // fetch initial frames
    await updateNeSat();
        animateLoop("ne_vis", "ne-sat-vis-img");
        animateLoop("ne_ir",  "ne-sat-ir-img");
        animateLoop("ne_cloud",   "ne-sat-cloud-img");
        animateLoop("ne_band9",   "ne-sat-band9-img");
        setInterval(updateNeSat, 5 * 60 * 1000);
    await updateRadar();
        animateLoop("radar", "radar-img");
        setInterval(updateRadar, RADAR_REFRESH_MS);
    await updateModel();
        animateLoop("model", "hrrr-img");
        setInterval(updateModel, 6 * 60 * 60 * 1000);  // every 6 hours
        
    startLoops();             // start animation

    // Refresh data periodically
    // These mirror the backend scheduler intervals, but the
    // frontend re-fetches from Flask (not the source directly)
    setInterval(updateObservations, 5  * 60 * 1000);
    setInterval(updateForecasts,    30 * 60 * 1000);
    setInterval(updateSatellite,    5  * 60 * 1000);
});