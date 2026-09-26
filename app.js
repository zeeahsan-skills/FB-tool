// DOM Elements - Browser Manager (Prompt 1)
const healthBadge = document.getElementById("api-health-badge");
const healthText = document.getElementById("api-health-text");
const statusDot = healthBadge.querySelector(".status-dot");

const dbHealthBadge = document.getElementById("db-health-badge");
const dbHealthText = document.getElementById("db-health-text");
const dbStatusDot = document.getElementById("db-status-dot");

const statusLabel = document.getElementById("browser-status-label");
const indicatorBadge = document.getElementById("browser-indicator-badge");
const headlessStatus = document.getElementById("headless-status");
const activeTitle = document.getElementById("active-title");
const activeUrl = document.getElementById("active-url");

const btnStartBrowser = document.getElementById("btn-start-browser");
const btnStopBrowser = document.getElementById("btn-stop-browser");
const btnRefresh = document.getElementById("btn-refresh-status");

// DOM Elements - Discovery Engine (Prompt 2)
const discoveryBadge = document.getElementById("discovery-indicator-badge");
const discoveryStatusLabel = document.getElementById("discovery-status-label");
const inputNiche = document.getElementById("input-niche");
const inputCountry = document.getElementById("input-country");
const keywordsContainer = document.getElementById("keywords-container");
const btnAddKeyword = document.getElementById("btn-add-keyword");
const inputMaxResults = document.getElementById("input-max-results");
const inputScrollCount = document.getElementById("input-scroll-count");
const btnStartDiscovery = document.getElementById("btn-start-discovery");
const btnStopDiscovery = document.getElementById("btn-stop-discovery");

const progressBanner = document.getElementById("discovery-progress-banner");
const progCurrentKeyword = document.getElementById("prog-current-keyword");
const progKeywordsRatio = document.getElementById("prog-keywords-ratio");
const progGroupsCount = document.getElementById("prog-groups-count");
const progressBarFill = document.getElementById("progress-bar-fill");

const resultsCountBadge = document.getElementById("results-count-badge");
const groupsTableBody = document.getElementById("groups-table-body");
const btnRefreshResults = document.getElementById("btn-refresh-results");

const btnClearLogs = document.getElementById("btn-clear-logs");
const terminalOutput = document.getElementById("terminal-output");
const inputApiBase = document.getElementById("input-api-base");

// Determine Agent API Base URL (defaults to origin if local, or localStorage / localhost if on static/cloud host)
function getApiBaseUrl() {
  if (inputApiBase && inputApiBase.value.trim()) {
    return inputApiBase.value.trim().replace(/\/+$/, "");
  }
  const saved = localStorage.getItem("fb_agent_api_base");
  if (saved) {
    if (inputApiBase) inputApiBase.value = saved;
    return saved;
  }
  // Check for environment variable injected into window
  if (window.AGENT_API_URL || window.NEXT_PUBLIC_AGENT_API_URL) {
    const envUrl = (window.AGENT_API_URL || window.NEXT_PUBLIC_AGENT_API_URL).replace(/\/+$/, "");
    if (inputApiBase) inputApiBase.value = envUrl;
    return envUrl;
  }
  // If running on non-localhost (e.g. Vercel), default to local agent address
  if (window.location.hostname !== "127.0.0.1" && window.location.hostname !== "localhost") {
    const defaultLocal = "http://127.0.0.1:8000";
    if (inputApiBase) inputApiBase.value = defaultLocal;
    return defaultLocal;
  }
  return "";
}

if (inputApiBase) {
  const initialBase = getApiBaseUrl();
  inputApiBase.value = initialBase;
  inputApiBase.addEventListener("change", () => {
    localStorage.setItem("fb_agent_api_base", inputApiBase.value.trim());
    appendLog(`Agent API base updated to: ${inputApiBase.value.trim() || "(current origin)"}`, "info");
    checkHealth();
    updateBrowserStatus();
    updateDiscoveryStatus();
  });
}

function apiUrl(path) {
  const base = getApiBaseUrl();
  return base ? `${base}${path}` : path;
}

function getTimestamp() {
  const d = new Date();
  return d.toTimeString().split(" ")[0];
}

function appendLog(message, type = "info") {
  const entry = document.createElement("div");
  entry.className = `log-entry ${type}`;
  entry.innerHTML = `<span class="log-time">[${getTimestamp()}]</span> ${message}`;
  terminalOutput.appendChild(entry);
  terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

// ---------------------------------------------------------------------------
// Health & Browser Controls
// ---------------------------------------------------------------------------

const agentOfflineAlert = document.getElementById("agent-offline-alert");
const btnRetryAgentConn = document.getElementById("btn-retry-agent-conn");

if (btnRetryAgentConn) {
  btnRetryAgentConn.addEventListener("click", () => {
    appendLog("Retrying connection to local agent...", "info");
    checkHealth();
    updateBrowserStatus();
    updateDiscoveryStatus();
  });
}

async function checkHealth() {
  try {
    const res = await fetch(apiUrl("/api/health"));
    if (res.ok) {
      const data = await res.json();
      healthText.textContent = `API Online (${data.environment})`;
      statusDot.classList.add("active");
      if (agentOfflineAlert) agentOfflineAlert.classList.add("hidden");
    } else {
      healthText.textContent = "API Error";
      statusDot.classList.remove("active");
      if (agentOfflineAlert) agentOfflineAlert.classList.remove("hidden");
    }
  } catch (err) {
    healthText.textContent = "API Offline";
    statusDot.classList.remove("active");
    if (agentOfflineAlert) agentOfflineAlert.classList.remove("hidden");
  }
}

async function updateBrowserStatus() {
  try {
    const res = await fetch(apiUrl("/api/browser/status"));
    if (!res.ok) throw new Error("Status check returned error");

    const data = await res.json();
    headlessStatus.textContent = data.headless ? "Headless (Hidden)" : "Headed (Visible)";

    if (data.running) {
      statusLabel.textContent = "Browser Active";
      indicatorBadge.className = "badge-status running";
      btnStartBrowser.disabled = true;
      btnStopBrowser.disabled = false;

      activeTitle.textContent = data.current_title || "Blank or loading...";
      activeUrl.textContent = data.current_url || "about:blank";
    } else {
      statusLabel.textContent = "Browser Stopped";
      indicatorBadge.className = "badge-status";
      btnStartBrowser.disabled = false;
      btnStopBrowser.disabled = true;

      activeTitle.textContent = "—";
      activeUrl.textContent = "—";
    }
  } catch (err) {
    statusLabel.textContent = "Status Unknown";
    indicatorBadge.className = "badge-status";
  }
}

async function startBrowser() {
  btnStartBrowser.disabled = true;
  appendLog("Starting Playwright browser and navigating to Facebook...", "info");

  try {
    const res = await fetch(apiUrl("/api/browser/start?open_fb=true"), { method: "POST" });
    const data = await res.json();

    if (res.ok) {
      appendLog("Browser successfully launched in visible mode.", "success");
      if (data.facebook) {
        appendLog(`Facebook opened: "${data.facebook.title}" (${data.facebook.url})`, "success");
        appendLog("If manual login is needed, complete it inside the browser window.", "warning");
      }
    } else {
      appendLog(`Failed to start browser: ${data.detail || "Unknown error"}`, "error");
    }
  } catch (err) {
    appendLog(`Network error starting browser: ${err.message}`, "error");
  } finally {
    await updateBrowserStatus();
  }
}

async function stopBrowser() {
  btnStopBrowser.disabled = true;
  appendLog("Stopping browser and persisting session...", "info");

  try {
    const res = await fetch(apiUrl("/api/browser/stop"), { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      appendLog("Browser cleanly closed. Session data saved.", "success");
    } else {
      appendLog(`Failed to stop browser: ${data.detail || "Unknown error"}`, "error");
    }
  } catch (err) {
    appendLog(`Network error stopping browser: ${err.message}`, "error");
  } finally {
    await updateBrowserStatus();
  }
}

// ---------------------------------------------------------------------------
// Dynamic Keywords Pill Management
// ---------------------------------------------------------------------------

function createKeywordPill(value = "") {
  const div = document.createElement("div");
  div.className = "keyword-pill-item";

  const input = document.createElement("input");
  input.type = "text";
  input.className = "form-input keyword-input";
  input.value = value;
  input.placeholder = "Keyword...";

  const btnRemove = document.createElement("button");
  btnRemove.type = "button";
  btnRemove.className = "btn-remove-kw";
  btnRemove.innerHTML = "&times;";
  btnRemove.title = "Remove";
  btnRemove.addEventListener("click", () => div.remove());

  div.appendChild(input);
  div.appendChild(btnRemove);
  keywordsContainer.appendChild(div);
  input.focus();
}

function getKeywords() {
  const inputs = keywordsContainer.querySelectorAll(".keyword-input");
  const list = [];
  inputs.forEach((inp) => {
    const val = inp.value.trim();
    if (val) list.push(val);
  });
  return list;
}

// Attach remove listener to initial pills
keywordsContainer.querySelectorAll(".btn-remove-kw").forEach((btn) => {
  btn.addEventListener("click", (e) => e.target.closest(".keyword-pill-item").remove());
});

btnAddKeyword.addEventListener("click", () => createKeywordPill(""));

// ---------------------------------------------------------------------------
// Group Discovery Controls & Polling (Prompt 2)
// ---------------------------------------------------------------------------

async function updateDiscoveryStatus() {
  try {
    const res = await fetch(apiUrl("/api/discovery/status"));
    if (!res.ok) return;

    const data = await res.json();
    discoveryStatusLabel.textContent = data.status.toUpperCase();

    if (data.running) {
      discoveryBadge.className = "badge-status running";
      btnStartDiscovery.disabled = true;
      btnStopDiscovery.disabled = false;
      progressBanner.classList.remove("hidden");

      progCurrentKeyword.textContent = data.current_keyword || "Searching...";
      progKeywordsRatio.textContent = `${data.keywords_completed} / ${data.keywords_total} keywords`;
      progGroupsCount.textContent = data.groups_found;

      const pct = data.keywords_total > 0 ? (data.keywords_completed / data.keywords_total) * 100 : 0;
      progressBarFill.style.width = `${Math.min(100, Math.max(5, pct))}%`;
    } else {
      discoveryBadge.className = "badge-status";
      btnStartDiscovery.disabled = false;
      btnStopDiscovery.disabled = true;

      if (data.status === "completed" || data.status === "stopped") {
        progKeywordsRatio.textContent = `${data.keywords_completed} / ${data.keywords_total} keywords`;
        progGroupsCount.textContent = data.groups_found;
        progressBarFill.style.width = data.status === "completed" ? "100%" : "0%";
      } else {
        progressBanner.classList.add("hidden");
      }
    }
  } catch (err) {
    // silent catch on network blip
  }
}

async function fetchDiscoveryResults() {
  try {
    const res = await fetch(apiUrl("/api/discovery/results"));
    if (!res.ok) return;

    const data = await res.json();
    resultsCountBadge.textContent = data.total;

    if (!data.groups || data.groups.length === 0) {
      groupsTableBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="5">No groups discovered yet. Launch a discovery search above.</td>
        </tr>`;
      return;
    }

    groupsTableBody.innerHTML = "";
    data.groups.forEach((g) => {
      const tr = document.createElement("tr");

      // Privacy Tag class
      const privLower = (g.privacy || "unknown").toLowerCase();
      const privClass = privLower === "public" ? "public" : privLower === "private" ? "private" : "unknown";

      // Matched Keywords badges
      const kwBadges = (g.matched_keywords || [g.keyword])
        .map((k) => `<span class="kw-badge">${k}</span>`)
        .join("");

      // Member text
      const membersDisplay = g.member_count_text || (g.member_count ? g.member_count.toLocaleString() : "Unknown");

      tr.innerHTML = `
        <td><strong>${escapeHtml(g.name)}</strong></td>
        <td>${escapeHtml(membersDisplay)}</td>
        <td><span class="privacy-tag ${privClass}">${escapeHtml(g.privacy || "Unknown")}</span></td>
        <td><div class="keywords-badge-list">${kwBadges}</div></td>
        <td>
          <a href="${escapeHtml(g.url)}" target="_blank" rel="noopener noreferrer" class="btn-table-action">
            <span>Open</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" y1="14" x2="21" y2="3"></line>
            </svg>
          </a>
        </td>
      `;
      groupsTableBody.appendChild(tr);
    });
  } catch (err) {
    appendLog(`Error loading results: ${err.message}`, "error");
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function startDiscovery() {
  const niche = inputNiche.value.trim();
  const country = inputCountry.value.trim();
  const keywords = getKeywords();
  const maxResults = parseInt(inputMaxResults.value, 10) || 50;
  const scrollCount = parseInt(inputScrollCount.value, 10) || 5;

  if (!niche) {
    alert("Please enter a Niche.");
    return;
  }
  if (!country) {
    alert("Please enter a Country / Region.");
    return;
  }
  if (keywords.length === 0) {
    alert("Please enter at least one keyword.");
    return;
  }

  btnStartDiscovery.disabled = true;
  appendLog(`Initiating Discovery: Niche="${niche}", Country="${country}", Keywords=[${keywords.join(", ")}]`, "info");

  try {
    const res = await fetch(apiUrl("/api/discovery/start"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        niche: niche,
        country: country,
        keywords: keywords,
        max_results_per_keyword: maxResults,
        scroll_count: scrollCount,
      }),
    });

    const data = await res.json();
    if (res.ok) {
      appendLog("Group discovery background engine successfully launched.", "success");
      await updateDiscoveryStatus();
    } else {
      appendLog(`Discovery start failed: ${data.detail || "Unknown error"}`, "error");
    }
  } catch (err) {
    appendLog(`Network error starting discovery: ${err.message}`, "error");
  } finally {
    await updateDiscoveryStatus();
  }
}

async function stopDiscovery() {
  btnStopDiscovery.disabled = true;
  appendLog("Halting group discovery. Discovered groups will be preserved...", "info");

  try {
    const res = await fetch(apiUrl("/api/discovery/stop"), { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      appendLog(`Discovery stopped cleanly. Total groups saved: ${data.groups_found}`, "warning");
    } else {
      appendLog(`Stop discovery error: ${data.detail || "Unknown error"}`, "error");
    }
  } catch (err) {
    appendLog(`Network error stopping discovery: ${err.message}`, "error");
  } finally {
    await updateDiscoveryStatus();
    await fetchDiscoveryResults();
  }
}

// ---------------------------------------------------------------------------
// Event Listeners & Periodic Polling
// ---------------------------------------------------------------------------

async function checkDatabaseStatus() {
  if (!dbHealthBadge || !dbHealthText || !dbStatusDot) return;
  try {
    const res = await fetch(apiUrl("/api/database/status"));
    if (res.ok) {
      const data = await res.json();
      if (data.configured && data.connected) {
        dbHealthText.textContent = "Supabase Active";
        dbStatusDot.className = "status-dot active";
      } else if (data.configured && !data.connected) {
        dbHealthText.textContent = "DB Unreachable";
        dbStatusDot.className = "status-dot warning";
      } else {
        dbHealthText.textContent = "DB Not Configured";
        dbStatusDot.className = "status-dot";
      }
    } else {
      dbHealthText.textContent = "DB Error";
      dbStatusDot.className = "status-dot error";
    }
  } catch (err) {
    dbHealthText.textContent = "DB Offline";
    dbStatusDot.className = "status-dot";
  }
}

btnStartBrowser.addEventListener("click", startBrowser);
btnStopBrowser.addEventListener("click", stopBrowser);
btnRefresh.addEventListener("click", async () => {
  appendLog("Refreshing agent state...", "info");
  await checkHealth();
  await checkDatabaseStatus();
  await updateBrowserStatus();
  await updateDiscoveryStatus();
  await fetchDiscoveryResults();
});

btnStartDiscovery.addEventListener("click", startDiscovery);
btnStopDiscovery.addEventListener("click", stopDiscovery);
btnRefreshResults.addEventListener("click", fetchDiscoveryResults);

btnClearLogs.addEventListener("click", () => {
  terminalOutput.innerHTML = "";
  appendLog("Terminal cleared.", "info");
});

// Initial boot & polling
checkHealth();
checkDatabaseStatus();
updateBrowserStatus();
updateDiscoveryStatus();
fetchDiscoveryResults();

setInterval(checkHealth, 10000);
setInterval(checkDatabaseStatus, 10000);
setInterval(updateBrowserStatus, 4000);
setInterval(updateDiscoveryStatus, 2500);
setInterval(fetchDiscoveryResults, 4000);
