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

// ---------------------------------------------------------------------------
// Prompt 5: Dashboard Filters, Pagination, Group Details & Export
// ---------------------------------------------------------------------------

const filterKeyword = document.getElementById("filter-keyword");
const filterNiche = document.getElementById("filter-niche");
const filterCountry = document.getElementById("filter-country");
const filterPrivacy = document.getElementById("filter-privacy");
const filterActivity = document.getElementById("filter-activity");
const filterExtLink = document.getElementById("filter-external-link");
const filterAnalyzed = document.getElementById("filter-analyzed");
const filterMinMembers = document.getElementById("filter-min-members");
const filterMaxMembers = document.getElementById("filter-max-members");
const filterSortBy = document.getElementById("filter-sort-by");
const filterSortOrder = document.getElementById("filter-sort-order");
const filterPageSize = document.getElementById("filter-page-size");
const btnResetFilters = document.getElementById("btn-reset-filters");

const btnExportCsv = document.getElementById("btn-export-csv");
const btnExportExcel = document.getElementById("btn-export-excel");

const pageNum = document.getElementById("page-num");
const pageTotal = document.getElementById("page-total");
const pageRecordsTotal = document.getElementById("page-records-total");
const btnPrevPage = document.getElementById("btn-prev-page");
const btnNextPage = document.getElementById("btn-next-page");

// Details Modal Elements
const modalOverlay = document.getElementById("group-details-modal");
const modalCloseBtn = document.getElementById("modal-close-btn");
const modalGroupName = document.getElementById("modal-group-name");
const modalGroupUrl = document.getElementById("modal-group-url");
const modalMemberCount = document.getElementById("modal-member-count");
const modalPrivacy = document.getElementById("modal-privacy");
const modalNiche = document.getElementById("modal-niche");
const modalCountry = document.getElementById("modal-country");
const modalDiscoveredAt = document.getElementById("modal-discovered-at");
const modalSource = document.getElementById("modal-source");
const modalMatchedKeywords = document.getElementById("modal-matched-keywords");
const modalAnalysisBadge = document.getElementById("modal-analysis-badge");
const modalActivityStatus = document.getElementById("modal-activity-status");
const modalActivityScore = document.getElementById("modal-activity-score");
const modalExtLinkStatus = document.getElementById("modal-ext-link-status");
const modalAnalyzedAt = document.getElementById("modal-analyzed-at");
const modalOverallSummary = document.getElementById("modal-overall-summary");
const modalActivitySummary = document.getElementById("modal-activity-summary");
const modalRulesSummary = document.getElementById("modal-rules-summary");
const modalExtEvidence = document.getElementById("modal-ext-evidence");
const modalExternalUrls = document.getElementById("modal-external-urls");
const modalRecentPosts = document.getElementById("modal-recent-posts");
const modalRawJson = document.getElementById("modal-raw-json");

let currentFilterPage = 1;
let filterDebounceTimer = null;

function buildFilterParams(includePagination = true) {
  const params = new URLSearchParams();
  if (filterKeyword && filterKeyword.value.trim()) params.append("keyword", filterKeyword.value.trim());
  if (filterNiche && filterNiche.value.trim()) params.append("niche", filterNiche.value.trim());
  if (filterCountry && filterCountry.value.trim()) params.append("country", filterCountry.value.trim());
  if (filterPrivacy && filterPrivacy.value && filterPrivacy.value !== "all") params.append("privacy", filterPrivacy.value);
  if (filterActivity && filterActivity.value && filterActivity.value !== "all") params.append("activity_status", filterActivity.value);
  if (filterExtLink && filterExtLink.value && filterExtLink.value !== "all") params.append("external_link_status", filterExtLink.value);
  if (filterAnalyzed && filterAnalyzed.value && filterAnalyzed.value !== "all") {
    params.append("is_analyzed", filterAnalyzed.value);
  }
  if (filterMinMembers && filterMinMembers.value.trim()) {
    const minVal = parseInt(filterMinMembers.value.trim(), 10);
    if (!isNaN(minVal)) params.append("min_members", minVal);
  }
  if (filterMaxMembers && filterMaxMembers.value.trim()) {
    const maxVal = parseInt(filterMaxMembers.value.trim(), 10);
    if (!isNaN(maxVal)) params.append("max_members", maxVal);
  }
  if (filterSortBy && filterSortBy.value) params.append("sort_by", filterSortBy.value);
  if (filterSortOrder && filterSortOrder.value) params.append("sort_order", filterSortOrder.value);

  if (includePagination) {
    params.append("page", currentFilterPage);
    const pageSize = filterPageSize ? parseInt(filterPageSize.value, 10) || 20 : 20;
    params.append("page_size", pageSize);
  }
  return params;
}

function formatDate(dateStr) {
  if (!dateStr) return "Unknown";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch (e) {
    return dateStr;
  }
}

async function fetchFilteredGroups() {
  try {
    const params = buildFilterParams(true);
    const res = await fetch(apiUrl(`/api/groups/filter?${params.toString()}`));
    if (!res.ok) {
      // Fallback: If filtered endpoint fails or older agent, try discovery results
      return await fetchDiscoveryResultsFallback();
    }

    const data = await res.json();
    const total = data.total || 0;
    if (resultsCountBadge) resultsCountBadge.textContent = total;
    if (pageRecordsTotal) pageRecordsTotal.textContent = total;
    if (pageNum) pageNum.textContent = data.page || currentFilterPage;
    if (pageTotal) pageTotal.textContent = Math.max(1, data.total_pages || 1);

    if (btnPrevPage) btnPrevPage.disabled = currentFilterPage <= 1;
    if (btnNextPage) btnNextPage.disabled = currentFilterPage >= (data.total_pages || 1);

    if (!data.groups || data.groups.length === 0) {
      groupsTableBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="10">No groups match your current filters. Adjust your search or launch a discovery run above.</td>
        </tr>`;
      return;
    }

    groupsTableBody.innerHTML = "";
    data.groups.forEach((g) => {
      const tr = document.createElement("tr");

      // Privacy Tag
      const priv = g.privacy || "Unknown";
      const privLower = priv.toLowerCase();
      const privClass = privLower === "public" ? "public" : privLower === "private" ? "private" : "unknown";

      // Matched Keywords badges
      let kwBadges = "Unknown";
      if (Array.isArray(g.matched_keywords) && g.matched_keywords.length > 0) {
        kwBadges = g.matched_keywords.map((k) => `<span class="kw-badge">${escapeHtml(k)}</span>`).join("");
      } else if (g.keyword) {
        kwBadges = `<span class="kw-badge">${escapeHtml(g.keyword)}</span>`;
      }

      // Member text
      const membersDisplay = g.member_count !== null && g.member_count !== undefined
        ? Number(g.member_count).toLocaleString()
        : (g.member_count_text || "Unknown");

      // Activity Status Badge
      const act = g.activity_status || "Unknown";
      const actLower = act.toLowerCase();
      const actClass = actLower === "active" ? "active" : actLower === "moderate" ? "moderate" : actLower === "inactive" ? "inactive" : "unknown";

      // External Link Status Badge
      const ext = g.external_link_status || "Unknown";
      const extLower = ext.toLowerCase();
      const extClass = extLower === "allowed" ? "allowed" : extLower === "restricted" ? "restricted" : extLower === "prohibited" ? "prohibited" : "unknown";

      tr.innerHTML = `
        <td><strong>${escapeHtml(g.name || "Unknown Group")}</strong></td>
        <td>${escapeHtml(membersDisplay)}</td>
        <td><span class="privacy-tag ${privClass}">${escapeHtml(priv)}</span></td>
        <td>${escapeHtml(g.niche || "Unknown")}</td>
        <td>${escapeHtml(g.country || "Unknown")}</td>
        <td><div class="keywords-badge-list">${kwBadges}</div></td>
        <td><span style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(formatDate(g.discovered_at))}</span></td>
        <td><span class="badge-activity ${actClass}">${escapeHtml(act)}</span></td>
        <td><span class="badge-ext-link ${extClass}">${escapeHtml(ext)}</span></td>
        <td>
          <div style="display:flex; align-items:center; gap:0.4rem;">
            <button type="button" class="btn-detail btn-view-group" data-id="${escapeHtml(g.id || '')}">Details</button>
            <a href="${escapeHtml(g.url)}" target="_blank" rel="noopener noreferrer" class="btn-table-action" title="Open on Facebook">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                <polyline points="15 3 21 3 21 9"></polyline>
                <line x1="10" y1="14" x2="21" y2="3"></line>
              </svg>
            </a>
          </div>
        </td>
      `;
      groupsTableBody.appendChild(tr);
    });

    // Attach click listeners to Details buttons
    document.querySelectorAll(".btn-view-group").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-id");
        if (id) openGroupDetails(id);
      });
    });
  } catch (err) {
    appendLog(`Error loading filtered groups: ${err.message}`, "error");
  }
}

async function fetchDiscoveryResultsFallback() {
  try {
    const res = await fetch(apiUrl("/api/discovery/results"));
    if (!res.ok) return;
    const data = await res.json();
    if (resultsCountBadge) resultsCountBadge.textContent = data.total;
    if (!data.groups || data.groups.length === 0) {
      groupsTableBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="10">No groups discovered yet. Launch a discovery search above.</td>
        </tr>`;
      return;
    }
  } catch (err) {
    // silent
  }
}

async function openGroupDetails(groupId) {
  try {
    const res = await fetch(apiUrl(`/api/groups/${groupId}/details`));
    if (!res.ok) {
      appendLog(`Failed to load details for group ${groupId}`, "error");
      return;
    }

    const data = await res.json();
    const group = data.group || {};
    const analysis = data.analysis || null;

    // Populate Group Overview
    modalGroupName.textContent = group.name || "Unknown Group";
    modalGroupUrl.href = group.url || "#";
    modalGroupUrl.textContent = group.url ? "Open on Facebook ↗" : "No URL";

    modalMemberCount.textContent = group.member_count !== null && group.member_count !== undefined
      ? Number(group.member_count).toLocaleString()
      : (group.member_count_text || "Unknown");
    modalPrivacy.textContent = group.privacy || "Unknown";
    modalNiche.textContent = group.niche || "Unknown";
    modalCountry.textContent = group.country || "Unknown";
    modalDiscoveredAt.textContent = group.discovered_at ? new Date(group.discovered_at).toLocaleString() : "Unknown";
    modalSource.textContent = group.discovery_source || "facebook_search";

    // Matched Keywords
    if (Array.isArray(group.matched_keywords) && group.matched_keywords.length > 0) {
      modalMatchedKeywords.innerHTML = group.matched_keywords
        .map((k) => `<span class="kw-badge">${escapeHtml(k)}</span>`)
        .join("");
    } else if (group.keyword) {
      modalMatchedKeywords.innerHTML = `<span class="kw-badge">${escapeHtml(group.keyword)}</span>`;
    } else {
      modalMatchedKeywords.textContent = "None recorded";
    }

    // Gemini Analysis Fields
    if (analysis) {
      modalAnalysisBadge.className = "badge-status running";
      modalAnalysisBadge.textContent = "Analyzed";
      modalActivityStatus.textContent = analysis.activity_status || "Unknown";
      modalActivityScore.textContent = analysis.activity_score !== null && analysis.activity_score !== undefined
        ? `${analysis.activity_score} / 100`
        : "—";
      modalExtLinkStatus.textContent = analysis.external_link_status || "Unknown";
      modalAnalyzedAt.textContent = analysis.created_at ? new Date(analysis.created_at).toLocaleString() : "—";
      modalOverallSummary.textContent = analysis.summary || "No summary provided.";
      modalActivitySummary.textContent = analysis.activity_summary || "No activity summary recorded.";
      modalRulesSummary.textContent = analysis.rules_summary || "No group rules found or extracted.";

      // Raw evidence
      modalExtEvidence.textContent = analysis.external_link_evidence || "No specific link evidence provided.";

      if (Array.isArray(analysis.external_urls) && analysis.external_urls.length > 0) {
        modalExternalUrls.innerHTML = analysis.external_urls
          .map((u) => `<div style="padding:0.2rem 0;"><a href="${escapeHtml(u)}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;">${escapeHtml(u)}</a></div>`)
          .join("");
      } else {
        modalExternalUrls.textContent = "None detected";
      }

      if (Array.isArray(analysis.recent_post_evidence) && analysis.recent_post_evidence.length > 0) {
        modalRecentPosts.innerHTML = analysis.recent_post_evidence
          .map((p) => `<div style="padding:0.3rem 0; border-bottom:1px solid rgba(255,255,255,0.05);">${escapeHtml(typeof p === 'object' ? JSON.stringify(p) : p)}</div>`)
          .join("");
      } else {
        modalRecentPosts.textContent = "No post evidence recorded";
      }

      modalRawJson.textContent = JSON.stringify(analysis.raw_evidence || {}, null, 2);
    } else {
      modalAnalysisBadge.className = "badge-status";
      modalAnalysisBadge.textContent = "Not Analyzed";
      modalActivityStatus.textContent = group.activity_status || "Unknown";
      modalActivityScore.textContent = "—";
      modalExtLinkStatus.textContent = group.external_link_status || "Unknown";
      modalAnalyzedAt.textContent = "—";
      modalOverallSummary.textContent = "This group has not yet been processed by the Gemini analysis pipeline.";
      modalActivitySummary.textContent = "—";
      modalRulesSummary.textContent = "—";
      modalExtEvidence.textContent = "—";
      modalExternalUrls.textContent = "None detected";
      modalRecentPosts.textContent = "No post evidence recorded";
      modalRawJson.textContent = "{}";
    }

    modalOverlay.classList.remove("hidden");
  } catch (err) {
    appendLog(`Error loading details: ${err.message}`, "error");
  }
}

// Event Listeners for Filters
function onFilterInputChange() {
  if (filterDebounceTimer) clearTimeout(filterDebounceTimer);
  filterDebounceTimer = setTimeout(() => {
    currentFilterPage = 1;
    fetchFilteredGroups();
  }, 350);
}

[filterKeyword, filterNiche, filterCountry, filterMinMembers, filterMaxMembers].forEach((el) => {
  if (el) el.addEventListener("input", onFilterInputChange);
});

[filterPrivacy, filterActivity, filterExtLink, filterAnalyzed, filterSortBy, filterSortOrder, filterPageSize].forEach((el) => {
  if (el) {
    el.addEventListener("change", () => {
      currentFilterPage = 1;
      fetchFilteredGroups();
    });
  }
});

if (btnResetFilters) {
  btnResetFilters.addEventListener("click", () => {
    if (filterKeyword) filterKeyword.value = "";
    if (filterNiche) filterNiche.value = "";
    if (filterCountry) filterCountry.value = "";
    if (filterPrivacy) filterPrivacy.value = "all";
    if (filterActivity) filterActivity.value = "all";
    if (filterExtLink) filterExtLink.value = "all";
    if (filterAnalyzed) filterAnalyzed.value = "all";
    if (filterMinMembers) filterMinMembers.value = "";
    if (filterMaxMembers) filterMaxMembers.value = "";
    if (filterSortBy) filterSortBy.value = "discovered_at";
    if (filterSortOrder) filterSortOrder.value = "desc";
    currentFilterPage = 1;
    appendLog("Filters reset to default values.", "info");
    fetchFilteredGroups();
  });
}

// Pagination Event Listeners
if (btnPrevPage) {
  btnPrevPage.addEventListener("click", () => {
    if (currentFilterPage > 1) {
      currentFilterPage--;
      fetchFilteredGroups();
    }
  });
}

if (btnNextPage) {
  btnNextPage.addEventListener("click", () => {
    currentFilterPage++;
    fetchFilteredGroups();
  });
}

// Export Handlers
if (btnExportCsv) {
  btnExportCsv.addEventListener("click", () => {
    const params = buildFilterParams(false);
    appendLog("Exporting filtered groups to CSV...", "info");
    window.location.href = apiUrl(`/api/export/csv?${params.toString()}`);
  });
}

if (btnExportExcel) {
  btnExportExcel.addEventListener("click", () => {
    const params = buildFilterParams(false);
    appendLog("Exporting filtered groups to Excel (.xlsx)...", "info");
    window.location.href = apiUrl(`/api/export/excel?${params.toString()}`);
  });
}

// Modal Close Handlers
if (modalCloseBtn) {
  modalCloseBtn.addEventListener("click", () => {
    modalOverlay.classList.add("hidden");
  });
}

if (modalOverlay) {
  modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) {
      modalOverlay.classList.add("hidden");
    }
  });
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && modalOverlay && !modalOverlay.classList.contains("hidden")) {
    modalOverlay.classList.add("hidden");
  }
});

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

function fetchDiscoveryResults() {
  return fetchFilteredGroups();
}

btnStartBrowser.addEventListener("click", startBrowser);
btnStopBrowser.addEventListener("click", stopBrowser);
btnRefresh.addEventListener("click", async () => {
  appendLog("Refreshing agent state...", "info");
  await checkHealth();
  await checkDatabaseStatus();
  await updateBrowserStatus();
  await updateDiscoveryStatus();
  await fetchFilteredGroups();
});

btnStartDiscovery.addEventListener("click", startDiscovery);
btnStopDiscovery.addEventListener("click", stopDiscovery);
btnRefreshResults.addEventListener("click", fetchFilteredGroups);

btnClearLogs.addEventListener("click", () => {
  terminalOutput.innerHTML = "";
  appendLog("Terminal cleared.", "info");
});

// Initial boot & polling
checkHealth();
checkDatabaseStatus();
updateBrowserStatus();
updateDiscoveryStatus();
fetchFilteredGroups();

setInterval(checkHealth, 10000);
setInterval(checkDatabaseStatus, 10000);
setInterval(updateBrowserStatus, 4000);
setInterval(updateDiscoveryStatus, 2500);
setInterval(fetchFilteredGroups, 5000);

