/* =========================================================================
   Scalable Web Scraping Pipeline — Dashboard Controller
   =========================================================================
   Handles all dynamic dashboard behavior:
     • Theme toggling (persisted to localStorage)
     • Parser selection & scraper triggering
     • Dynamic table generation from API columns
     • Chart.js chart rendering
     • Search filtering
     • CSV/JSON export
     • Settings read/write
     • Live logs
     • Toast notifications
     • Pagination
   ========================================================================= */

(function () {
    "use strict";

    // =====================================================================
    // Constants & State
    // =====================================================================
    const API = {
        DATA:    "/api/data",
        STATS:   "/api/stats",
        LOGS:    "/api/logs",
        SCRAPE:  "/api/scrape",
        CONFIG:  "/api/config",
        CSV:     "/api/export/csv",
        JSON:    "/api/export/json",
        REGISTRY:"/api/registry",
        CHECK_URL:"/api/check-url",
    };

    const ROWS_PER_PAGE = 25;

    const state = {
        data: [],
        columns: [],
        currentPage: 1,
        totalPages: 1,
        searchQuery: "",
        charts: {},
        activeParser: "books",
        isRunning: false,
        lastStats: {},
        sortColumn: null,
        sortDirection: 1,
        pipelineStage: 0,
        scrapeStartTime: 0,
        scrapeEstDuration: 30000,
        registry: [],
        urlStatus: "invalid",
        urlReason: "Please enter a target URL",
    };

    // =====================================================================
    // DOM References
    // =====================================================================
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {
        themeToggle:    $("#themeToggle"),
        targetUrl:      $("#targetUrl"),
        runScraper:     $("#runScraper"),
        searchInput:    $("#searchInput"),
        exportCsv:      $("#exportCsv"),
        exportJson:     $("#exportJson"),
        tableHead:      $("#tableHead"),
        tableBody:      $("#tableBody"),
        tableEmpty:     $("#tableEmpty"),
        tableFooter:    $("#tableFooter"),
        recordCount:    $("#recordCount"),
        pagination:     $("#pagination"),
        logsContainer:  $("#logsContainer"),
        refreshLogs:    $("#refreshLogs"),
        loadingOverlay: $("#loadingOverlay"),
        toastContainer: $("#toastContainer"),
        sidebar:        $("#sidebar"),
        mobileMenuBtn:  $("#mobileMenuBtn"),
        mainContent:    $("#mainContent"),
        saveSettings:   $("#saveSettings"),

        // Stats
        valRecords:     $("#valRecords"),
        valPages:       $("#valPages"),
        valTime:        $("#valTime"),
        valDuplicates:  $("#valDuplicates"),
        valStatus:      $("#valStatus"),
        valLastRun:     $("#valLastRun"),

        // Settings inputs
        settingTimeout:   $("#settingTimeout"),
        settingRetries:   $("#settingRetries"),
        settingUserAgent: $("#settingUserAgent"),
        settingDelay:     $("#settingDelay"),

        // Nav items
        navItems: $$(".nav-item"),

        // Pipeline
        pipelinePercent: $("#pipelinePercent"),
        pipelineElapsed: $("#pipelineElapsed"),
        pipelineEstimated: $("#pipelineEstimated"),
        pipelineStages: $$(".pipeline-stage"),
        pipelineCurrentStage: $("#pipelineCurrentStage"),
        
        // Website Info Card
        infoDomain: $("#infoDomain"),
        infoStatus: $("#infoStatus"),
        infoType: $("#infoType"),
        infoProtection: $("#infoProtection"),
        infoTotalRecords: $("#infoTotalRecords"),
        infoLastScrape: $("#infoLastScrape"),
        infoDuration: $("#infoDuration"),

        // Workspace Metrics
        wsLastScrape: $("#wsLastScrape"),
        wsTotalScrapes: $("#wsTotalScrapes"),
        wsAvgDuration: $("#wsAvgDuration"),
        wsTotalRecords: $("#wsTotalRecords")
    };

    // =====================================================================
    async function initRegistry() {
        try {
            const res = await apiFetch(API.REGISTRY);
            state.registry = res.registry || [];
            updateDynamicUI(null); // set initial state
        } catch (err) {
            console.error("Failed to load registry", err);
        }
    }

    function detectParser(url) {
        if (!url) return null;
        const normalized = url.toLowerCase();
        for (const site of state.registry) {
            if (normalized.includes(site.domain)) {
                return site;
            }
        }
        return null;
    }

    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    function clearDashboardSession(reason = "Website changed") {
        // Overview cards
        if (dom.valRecords) dom.valRecords.textContent = "0";
        if (dom.valPages) dom.valPages.textContent = "0";
        if (dom.valTime) dom.valTime.textContent = "0s";
        if (dom.valDuplicates) dom.valDuplicates.textContent = "0";
        
        // Website Information (last run etc)
        if (dom.valLastRun) dom.valLastRun.textContent = "Never";
        if (dom.infoLastScrape) dom.infoLastScrape.textContent = "Never";
        if (dom.infoTotalRecords) dom.infoTotalRecords.textContent = "0";
        if (dom.infoDuration) dom.infoDuration.textContent = "0s";

        // Current scrape statistics
        if (dom.valStatus) {
            dom.valStatus.textContent = "Idle";
            dom.valStatus.className = "stat-value status-badge idle";
        }
        
        // Data Explorer
        state.data = [];
        state.columns = [];
        state.currentPage = 1;
        state.totalPages = 1;
        state.sortColumn = null;
        
        // Search
        state.searchQuery = "";
        if (dom.searchInput) dom.searchInput.value = "";
        
        // Selected rows
        if (window.selectedRows) window.selectedRows = new Set();
        if (typeof renderTable === "function") {
            try { renderTable(); } catch(e) {}
        }
        
        // Export buttons
        if (dom.exportCsv) dom.exportCsv.disabled = true;
        if (dom.exportJson) dom.exportJson.disabled = true;

        // Analytics
        state.lastStats = {};
        if (typeof updateCharts === "function") {
            try { updateCharts(); } catch(e) {}
        }
        
        // Pipeline
        if (typeof resetPipeline === "function") {
            try { resetPipeline(); } catch(e) {}
        }
        
        // Logs
        if (dom.logsContainer) {
            const div = document.createElement("div");
            div.className = "log-entry log-info";
            div.innerHTML = `<span class="log-time">[${new Date().toLocaleTimeString()}]</span> <span class="log-module">[frontend]</span> <span class="log-message">${reason}. Dashboard cleared. Waiting for new scrape.</span>`;
            dom.logsContainer.prepend(div);
        }
    }

    async function checkUrlStatus(url) {
        if (!url) {
            updateUrlUI("invalid", "No URL provided.");
            return;
        }

        try {
            new URL(url);
        } catch (_) {
            updateUrlUI("invalid", "Malformed URL.");
            return;
        }

        updateUrlUI("checking", "Connecting to website...");
        
        try {
            const res = await apiFetch(API.CHECK_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url }),
            });
            updateUrlUI(res.status, res.reason, res.parser);
        } catch (err) {
            updateUrlUI("unreachable", "Failed to connect to backend check service.");
        }
    }

    function updateUrlUI(status, reason, parserName = null) {
        state.urlStatus = status;
        state.urlReason = reason;

        if (parserName) {
            state.activeParser = parserName;
        }

        const site = detectParser(dom.targetUrl.value);
        updateDynamicUI(site); 

        let statusText = "Checking...";
        let statusColor = "text-muted";
        let icon = "⚪";

        if (status === "ready") {
            statusText = "Ready to Scrape";
            statusColor = "text-green";
            icon = "🟢";
        } else if (status === "cannot_scrape") {
            statusText = "Cannot Scrape";
            statusColor = "text-amber";
            icon = "🛡";
        } else if (status === "invalid") {
            statusText = "Invalid URL";
            statusColor = "text-red";
            icon = "❌";
        } else if (status === "unreachable") {
            statusText = "Unreachable";
            statusColor = "text-red";
            icon = "🔴";
        }

        if (dom.infoStatus) {
            dom.infoStatus.innerHTML = `${icon} ${statusText}`;
            dom.infoStatus.className = `info-value ${statusColor}`;
        }
        if (dom.infoProtection) {
            dom.infoProtection.textContent = reason || "None";
        }
    }

    const onUrlInput = debounce((e) => {
        clearDashboardSession();
        checkUrlStatus(e.target.value);
    }, 500);

    function updateDynamicUI(site) {
        const titleEl = document.getElementById("pageTitle");
        const statLabels = document.querySelectorAll(".stat-label");

        if (site) {
            if (titleEl) titleEl.textContent = site.title || `${site.type} Dashboard`;
            
            // Update Overview Cards if provided by backend registry
            if (site.overview_cards && site.overview_cards.length === 4 && statLabels.length === 4) {
                statLabels[0].textContent = site.overview_cards[0];
                statLabels[1].textContent = site.overview_cards[1];
                statLabels[2].textContent = site.overview_cards[2];
                statLabels[3].textContent = site.overview_cards[3];
            }
            
            if (dom.infoDomain) dom.infoDomain.textContent = site.domain;
            if (dom.infoType) dom.infoType.textContent = site.type;
        } else {
            if (titleEl) titleEl.textContent = "Scraping Pipeline — Dashboard";
            if (statLabels.length === 4) {
                statLabels[0].textContent = "Records Scraped";
                statLabels[1].textContent = "Pages Crawled";
                statLabels[2].textContent = "Execution Time";
                statLabels[3].textContent = "Duplicates Removed";
            }
            if (dom.infoDomain) dom.infoDomain.textContent = "Unknown Domain";
            if (dom.infoType) dom.infoType.textContent = "Unknown Site";
        }
    }

    // =====================================================================
    // Theme
    // =====================================================================
    function initTheme() {
        const saved = localStorage.getItem("theme") || "dark";
        document.documentElement.setAttribute("data-theme", saved);
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute("data-theme");
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("theme", next);
        updateChartColors();
    }

    // =====================================================================
    // Toast Notifications
    // =====================================================================
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let icon = "ℹ";
        if (type === "success") icon = "✓";
        if (type === "error") icon = "✕";
        if (type === "warning") icon = "⚠";

        toast.innerHTML = `<span class="toast-icon">${icon}</span> <span>${message}</span>`;
        dom.toastContainer.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    // =====================================================================
    // Loading Overlay
    // =====================================================================
    function showLoading() {
        dom.loadingOverlay.classList.add("active");
    }

    function hideLoading() {
        dom.loadingOverlay.classList.remove("active");
    }

    // =====================================================================
    // API Helpers
    // =====================================================================
    async function apiFetch(url, options = {}, maxRetries = 3) {
        let lastError;
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                const res = await fetch(url, options);
                const body = await res.json().catch(() => ({}));

                if (!res.ok) {
                    const error = new Error(body.error || `HTTP ${res.status}`);
                    error.status = res.status;
                    error.details = body.details || null;
                    // Don't retry 4xx client errors (bad request, not found, conflict, etc.)
                    if (res.status >= 400 && res.status < 500) throw error;
                    // 5xx server errors are retryable
                    lastError = error;
                } else if (body.success === false) {
                    // API-level error returned with a 2xx status (defensive)
                    const error = new Error(body.error || "Unknown API error");
                    throw error;
                } else {
                    // Unwrap the consistent envelope: return body.data
                    return body.data !== undefined ? body.data : body;
                }
            } catch (err) {
                // If it's a non-retryable 4xx error, propagate immediately
                if (err.status && err.status >= 400 && err.status < 500) throw err;
                lastError = err;
            }
            // Exponential backoff before next retry: 1s, 2s, 4s
            if (attempt < maxRetries) {
                const delay = Math.pow(2, attempt) * 1000;
                await new Promise((resolve) => setTimeout(resolve, delay));
                console.warn(`Retrying ${url} (attempt ${attempt + 2}/${maxRetries + 1})…`);
            }
        }
        console.error(`API failed [${url}]: all ${maxRetries + 1} attempts exhausted`, lastError);
        throw lastError;
    }

    // =====================================================================
    // Sidebar Navigation
    // =====================================================================
    function initNav() {
        dom.navItems.forEach((item) => {
            item.addEventListener("click", (e) => {
                e.preventDefault();
                const section = item.dataset.section;

                // Update active state
                dom.navItems.forEach((n) => n.classList.remove("active"));
                item.classList.add("active");

                // Scroll to section
                const target = document.getElementById(`section${capitalize(section)}`);
                if (target) {
                    target.scrollIntoView({ behavior: "smooth", block: "start" });
                }

                // Close mobile sidebar
                dom.sidebar.classList.remove("open");
                const overlay = document.querySelector(".sidebar-overlay");
                if (overlay) overlay.classList.remove("active");
            });
        });
    }

    function capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    // =====================================================================
    // Mobile Menu
    // =====================================================================
    function initMobileMenu() {
        // Create overlay
        const overlay = document.createElement("div");
        overlay.className = "sidebar-overlay";
        document.body.appendChild(overlay);

        dom.mobileMenuBtn.addEventListener("click", () => {
            dom.sidebar.classList.toggle("open");
            overlay.classList.toggle("active");
        });

        overlay.addEventListener("click", () => {
            dom.sidebar.classList.remove("open");
            overlay.classList.remove("active");
        });
    }

    // =====================================================================
    // Statistics
    // =====================================================================
    async function loadStats() {
        showSkeletons(["valRecords", "valPages", "valTime", "valDuplicates"]);
        try {
            const stats = await apiFetch(API.STATS);
            // Store for charts to reference without an extra API call
            state.lastStats = stats;

            animateCounter(dom.valRecords, stats.records_scraped || 0);
            animateCounter(dom.valPages, stats.pages_crawled || 0);
            animateCounter(dom.valDuplicates, stats.duplicates_removed || 0);
            
            const timeObj = { val: 0 };
            const startStr = dom.valTime.textContent.replace("s", "");
            timeObj.val = isNaN(parseInt(startStr)) ? 0 : parseInt(startStr);
            const targetTime = stats.execution_time || 0;
            animateCounter(dom.valTime, targetTime, 1000, "s");

            // Status badge
            const statusText = stats.status || "idle";
            dom.valStatus.textContent = capitalize(statusText);
            dom.valStatus.className = "stat-value status-badge";
            dom.infoStatus.textContent = capitalize(statusText);
            dom.infoStatus.className = "info-status";
            
            if (statusText === "failed") {
                dom.valStatus.classList.add("error");
                dom.infoStatus.classList.add("failed");
            } else {
                dom.valStatus.classList.add(statusText);
                dom.infoStatus.classList.add(statusText);
            }

            // Last run
            if (stats.last_run) {
                const d = new Date(stats.last_run);
                dom.valLastRun.textContent = d.toLocaleTimeString();
                dom.infoLastScrape.textContent = d.toLocaleString();
            } else {
                dom.valLastRun.textContent = "Never";
                dom.infoLastScrape.textContent = "Never";
            }
            
            // Website Info
            dom.infoTotalRecords.textContent = (stats.records_scraped || 0).toLocaleString();
            dom.infoDuration.textContent = `${stats.execution_time || 0}s`;
            
            const siteInfo = detectParser(state.activeParser) || { domain: "Unknown Domain", type: "Unknown Site", protection: "Unknown" };
            // info bindings are now handled reactively by URL input, but we fallback here
            if (stats.last_run) {
                if (dom.wsTotalRecords) dom.wsTotalRecords.textContent = stats.total_records || 0;
                if (dom.wsTotalScrapes) dom.wsTotalScrapes.textContent = stats.total_records ? 1 : 0; // Simple mock since backend doesn't track total scrapes
                if (dom.wsAvgDuration) dom.wsAvgDuration.textContent = `${stats.execution_time || 0}s`;
            }

        } catch (err) {
            showToast("Failed to load statistics", "error");
        }
    }

    // =====================================================================
    // Data Table (dynamic columns)
    // =====================================================================
    async function loadData() {
        try {
            const params = state.searchQuery ? `?search=${encodeURIComponent(state.searchQuery)}` : "";
            const res = await apiFetch(`${API.DATA}${params}`);

            // Backend now returns "records" instead of "data" to avoid
            // collision with the response envelope's "data" key.
            state.data = res.records || [];
            state.columns = res.columns || [];
            state.currentPage = 1;
            state.totalPages = Math.max(1, Math.ceil(state.data.length / ROWS_PER_PAGE));

            renderTable();
            // Charts are updated separately after loadData() completes
            // to avoid a hidden race condition with loadStats().
        } catch (err) {
            showToast("Failed to load data", "error");
        }
    }

    function renderTable() {
        const { data, columns, currentPage } = state;

        if (!data.length || !columns.length) {
            dom.tableHead.innerHTML = "";
            dom.tableBody.innerHTML = "";
            dom.tableEmpty.style.display = "flex";
            dom.tableFooter.style.display = "none";
            return;
        }

        dom.tableEmpty.style.display = "none";
        dom.tableFooter.style.display = "flex";

        // --- Dynamic header ---
        const displayCols = columns.filter(c => !c.endsWith("_url") || c === "product_url" || c === "job_url" || c === "author_url");
        dom.tableHead.innerHTML = `<tr>${displayCols.map((col) => {
            const isSort = state.sortColumn === col;
            const arrow = isSort ? (state.sortDirection === 1 ? "▲" : "▼") : "↕";
            return `<th class="sortable ${isSort ? "sort-active" : ""}" data-col="${col}">
                ${formatColumnName(col)} <span class="sort-arrow">${arrow}</span>
            </th>`;
        }).join("")}</tr>`;

        // Add sorting listeners
        dom.tableHead.querySelectorAll("th.sortable").forEach((th) => {
            th.addEventListener("click", () => sortTable(th.dataset.col));
        });

        // --- Paginated rows ---
        const start = (currentPage - 1) * ROWS_PER_PAGE;
        const pageData = data.slice(start, start + ROWS_PER_PAGE);

        const fragment = document.createDocumentFragment();
        pageData.forEach((row) => {
            const tr = document.createElement("tr");
            tr.innerHTML = displayCols.map((col) => {
                const val = row[col];
                const strVal = String(val !== null && val !== undefined ? val : "");
                const isTruncated = strVal.length > 80;
                return `<td${isTruncated ? ` title="${escapeHtml(strVal)}"` : ""}>${formatCell(col, val)}</td>`;
            }).join("");
            fragment.appendChild(tr);
        });
        
        dom.tableBody.innerHTML = "";
        dom.tableBody.appendChild(fragment);

        dom.recordCount.textContent = `${data.length} record${data.length !== 1 ? "s" : ""}`;

        // Enable exports if we have data
        if (dom.exportCsv) dom.exportCsv.disabled = false;
        if (dom.exportJson) dom.exportJson.disabled = false;

        renderPagination();
    }

    function formatColumnName(col) {
        return col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }

    function formatCell(col, value) {
        if (value === null || value === undefined || value === "") return '<span style="opacity:.4">—</span>';

        if (col === "status" || col.includes("state")) {
            const low = String(value).toLowerCase();
            let c = "badge-success";
            if (low === "failed" || low === "error") c = "badge-danger";
            else if (low === "pending" || low === "running") c = "badge-warning";
            return `<span class="badge ${c}">${escapeHtml(String(value))}</span>`;
        }

        // Render ratings as stars
        if (col === "rating" && typeof value === "number") {
            return `<span class="rating-stars">${"★".repeat(value)}${"☆".repeat(5 - value)}</span>`;
        }

        // Render prices with currency
        if (col === "price") {
            return `£${value}`;
        }

        // Render URLs as links with copy action
        if (col.endsWith("_url") && typeof value === "string" && value.startsWith("http")) {
            return `<div class="link-actions">
                <a href="${escapeHtml(value)}" target="_blank" rel="noopener">Link ↗</a>
                <button class="copy-btn" title="Copy URL" onclick="navigator.clipboard.writeText('${escapeHtml(value)}')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                </button>
            </div>`;
        }

        // Truncate long strings (title added in renderTable)
        const str = String(value);
        if (str.length > 80) {
            return escapeHtml(str.slice(0, 77)) + "…";
        }

        return escapeHtml(str);
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    // =====================================================================
    // Pagination
    // =====================================================================
    function renderPagination() {
        const { currentPage, totalPages } = state;
        if (totalPages <= 1) {
            dom.pagination.innerHTML = "";
            return;
        }

        let html = "";
        const maxVisible = 7;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);
        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        if (currentPage > 1) {
            html += `<button data-page="${currentPage - 1}">‹</button>`;
        }
        for (let i = startPage; i <= endPage; i++) {
            html += `<button data-page="${i}" class="${i === currentPage ? "active" : ""}">${i}</button>`;
        }
        if (currentPage < totalPages) {
            html += `<button data-page="${currentPage + 1}">›</button>`;
        }

        dom.pagination.innerHTML = html;

        dom.pagination.querySelectorAll("button").forEach((btn) => {
            btn.addEventListener("click", () => {
                state.currentPage = parseInt(btn.dataset.page, 10);
                renderTable();
            });
        });
    }

    // =====================================================================
    // Search
    // =====================================================================
    let searchTimer = null;

    function initSearch() {
        dom.searchInput.addEventListener("input", () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                state.searchQuery = dom.searchInput.value.trim();
                loadData();
            }, 300);
        });
    }

    // =====================================================================
    // Charts
    // =====================================================================
    function getChartColors() {
        const isDark = document.documentElement.getAttribute("data-theme") === "dark";
        return {
            text: isDark ? "#9898b0" : "#555577",
            grid: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.06)",
            blue: "#3b82f6",
            purple: "#a855f7",
            cyan: "#06b6d4",
            green: "#22c55e",
            amber: "#f59e0b",
            red: "#ef4444",
            blueAlpha: "rgba(59,130,246,0.4)",
            purpleAlpha: "rgba(168,85,247,0.4)",
            cyanAlpha: "rgba(6,182,212,0.4)",
            greenAlpha: "rgba(34,197,94,0.4)",
            amberAlpha: "rgba(245,158,11,0.4)",
        };
    }

    function updateCharts() {
        const { data, columns, registry, activeParser } = state;
        if (!data.length) return;

        const colors = getChartColors();
        const site = registry.find(s => s.parser === activeParser);

        if (site && site.charts && site.charts.length >= 2) {
            renderDynamicChart(data, columns, colors, site.charts[0], "chartDistribution");
            renderDynamicChart(data, columns, colors, site.charts[1], "chartRatings");
        } else {
            // Fallback to legacy
            renderDynamicChart(data, columns, colors, {
                title: "Value Distribution",
                columns: ["price", "salary", columns[0]],
                type: "bar"
            }, "chartDistribution");
            renderDynamicChart(data, columns, colors, {
                title: "Category Distribution",
                columns: ["rating", "author", "company", "category", "tags", columns[Math.min(1, columns.length - 1)]],
                type: "doughnut"
            }, "chartRatings");
        }

        updatePerPageChart(data, colors);
        updateRequestsChart(colors);
    }

    function renderDynamicChart(data, columns, colors, config, canvasId) {
        const canvas = document.getElementById(canvasId);
        const ctx = canvas.getContext("2d");

        const chartKey = canvasId === "chartDistribution" ? "distribution" : "ratings";
        if (state.charts[chartKey]) state.charts[chartKey].destroy();

        // Find the first column in the fallback list that exists and has data
        let targetCol = null;
        for (const col of config.columns) {
            if (columns.includes(col) && data.some(r => r[col] !== "" && r[col] !== "N/A" && r[col] != null)) {
                targetCol = col;
                break;
            }
        }

        if (!targetCol) {
            // Draw empty state
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.font = "14px Inter, sans-serif";
            ctx.fillStyle = colors.text;
            ctx.textAlign = "center";
            ctx.fillText("Data unavailable for this chart", canvas.width / 2, canvas.height / 2);
            return;
        }

        // If numeric config and we have mostly numeric data
        const isNumeric = config.numeric && data.some(r => parseFloat(r[targetCol]));
        
        let labels, datasetData;
        let chartType = config.type || "bar";
        let palette = [colors.blue, colors.purple, colors.cyan, colors.green, colors.amber, colors.red, "#8b5cf6", "#ec4899"];

        if (isNumeric) {
            const values = data.map((r) => parseFloat(r[targetCol]) || 0).filter((v) => v > 0);
            if (values.length === 0) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.font = "14px Inter, sans-serif";
                ctx.fillStyle = colors.text;
                ctx.textAlign = "center";
                ctx.fillText("Data unavailable for this chart", canvas.width / 2, canvas.height / 2);
                return;
            }
            
            const min = Math.floor(Math.min(...values));
            const max = Math.ceil(Math.max(...values));
            const binCount = Math.min(10, max - min + 1);
            const binSize = (max - min) / binCount;
            const bins = Array(binCount).fill(0);
            labels = [];

            for (let i = 0; i < binCount; i++) {
                const lo = (min + i * binSize).toFixed(0);
                const hi = (min + (i + 1) * binSize).toFixed(0);
                labels.push(`${lo}–${hi}`);
            }

            values.forEach((v) => {
                let idx = Math.floor((v - min) / binSize);
                if (idx >= binCount) idx = binCount - 1;
                bins[idx]++;
            });
            datasetData = bins;
        } else {
            const freq = {};
            data.forEach((r) => {
                const key = String(r[targetCol] || "Unknown").slice(0, 30);
                freq[key] = (freq[key] || 0) + 1;
            });
            const limit = chartType === "doughnut" ? 8 : 10;
            const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, limit);
            labels = sorted.map(s => s[0]);
            datasetData = sorted.map(s => s[1]);
        }

        const baseColor = canvasId === "chartDistribution" ? colors.blue : colors.purple;
        const bgColors = chartType === "doughnut" ? palette.slice(0, labels.length).map(c => c + "99") : baseColor + "66";
        const borderColors = chartType === "doughnut" ? palette.slice(0, labels.length) : baseColor;

        let options = chartOptions(colors, config.title);
        if (chartType === "doughnut") {
            options = {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: { display: true, text: config.title, color: colors.text, font: { family: "'Inter', sans-serif", size: 14, weight: 600 } },
                    legend: { position: "bottom", labels: { color: colors.text, padding: 12, usePointStyle: true, font: { size: 11 } } },
                },
            };
        }

        state.charts[chartKey] = new Chart(ctx, {
            type: chartType,
            data: {
                labels,
                datasets: [{
                    label: formatColumnName(targetCol),
                    data: datasetData,
                    backgroundColor: bgColors,
                    borderColor: borderColors,
                    borderWidth: chartType === "doughnut" ? 2 : 1,
                    borderRadius: chartType === "bar" ? 6 : 0,
                }],
            },
            options
        });
    }

    function updatePerPageChart(data, colors) {
        const canvas = document.getElementById("chartPerPage");
        const ctx = canvas.getContext("2d");

        if (state.charts.perPage) state.charts.perPage.destroy();

        // Simulate "per page" by chunking data into groups of 20
        const chunkSize = 20;
        const pageLabels = [];
        const pageCounts = [];
        for (let i = 0; i < data.length; i += chunkSize) {
            pageLabels.push(`Page ${pageLabels.length + 1}`);
            pageCounts.push(Math.min(chunkSize, data.length - i));
        }

        state.charts.perPage = new Chart(ctx, {
            type: "line",
            data: {
                labels: pageLabels,
                datasets: [{
                    label: "Records",
                    data: pageCounts,
                    borderColor: colors.cyan,
                    backgroundColor: colors.cyanAlpha,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: colors.cyan,
                }],
            },
            options: chartOptions(colors, "Records Per Page"),
        });
    }

    function updateRequestsChart(colors) {
        const canvas = document.getElementById("chartRequests");
        const ctx = canvas.getContext("2d");

        if (state.charts.requests) state.charts.requests.destroy();

        // Read from state.lastStats (populated by loadStats) instead of
        // making a separate API call — eliminates a hidden race condition.
        const stats = state.lastStats || {};
        const success = stats.successful_requests || 0;
        const failed = stats.failed_requests || 0;

        state.charts.requests = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Successful", "Failed"],
                datasets: [{
                    data: [success, failed],
                    backgroundColor: [colors.greenAlpha, "rgba(239,68,68,0.4)"],
                    borderColor: [colors.green, colors.red],
                    borderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: colors.text, padding: 12, usePointStyle: true, font: { size: 11 } },
                    },
                },
            },
        });
    }

    function chartOptions(colors, title) {
        return {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                title: { display: false },
            },
            scales: {
                x: {
                    ticks: { color: colors.text, font: { size: 10 } },
                    grid: { color: colors.grid },
                },
                y: {
                    ticks: { color: colors.text, font: { size: 10 } },
                    grid: { color: colors.grid },
                },
            },
        };
    }

    function updateChartColors() {
        // Rebuild charts with new theme colors
        if (state.data.length) {
            updateCharts();
        }
    }

    // =====================================================================
    // Logs
    // =====================================================================
    let activeLogFilter = "ALL";

    async function loadLogs() {
        try {
            const res = await apiFetch(`${API.LOGS}?limit=200`);
            const logs = res.logs || [];

            if (!logs.length) {
                dom.logsContainer.innerHTML = '<div class="log-empty">Logs will appear here after a scrape run.</div>';
                return;
            }
            
            const filteredLogs = activeLogFilter === "ALL" ? logs : logs.filter(l => (l.level || "").toUpperCase() === activeLogFilter);

            if (!filteredLogs.length) {
                dom.logsContainer.innerHTML = `<div class="log-empty">No ${activeLogFilter} logs found.</div>`;
                return;
            }

            dom.logsContainer.innerHTML = filteredLogs.map((log) => `
                <div class="log-entry">
                    <span class="log-level ${log.level}">${log.level}</span>
                    <span class="log-time">${(log.timestamp || "").slice(11, 19)}</span>
                    <span class="log-message">${escapeHtml(log.message)}</span>
                </div>
            `).join("");

            // Auto-scroll
            requestAnimationFrame(() => {
                dom.logsContainer.scrollTop = dom.logsContainer.scrollHeight;
            });
        } catch (err) {
            showToast("Failed to load logs", "error");
        }
    }

    function initLogFilters() {
        const filterBtns = document.querySelectorAll(".log-filter-btn");
        filterBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                filterBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                activeLogFilter = btn.dataset.level;
                loadLogs();
            });
        });
    }

    // =====================================================================
    // Settings
    // =====================================================================
    async function loadSettings() {
        try {
            const config = await apiFetch(API.CONFIG);
            if (dom.settingTimeout) dom.settingTimeout.value = config.timeout || 30;
            if (dom.settingRetries) dom.settingRetries.value = config.max_retries || 3;
            if (dom.settingUserAgent) dom.settingUserAgent.value = config.user_agent || "";
            if (dom.settingDelay) dom.settingDelay.value = config.request_delay || 1;
        } catch (err) {
            showToast("Failed to load settings", "error");
        }
    }

    async function saveSettings() {
        const payload = {
            timeout: dom.settingTimeout.value,
            max_retries: dom.settingRetries.value,
            user_agent: dom.settingUserAgent.value,
            request_delay: dom.settingDelay.value,
        };

        try {
            await apiFetch(API.CONFIG, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            showToast("Preferences saved successfully", "success");
        } catch (err) {
            showToast(`Failed to save preferences: ${err.message}`, "error");
        }
    }

    // =====================================================================
    // Scraper
    // =====================================================================
    async function runScraper() {
        if (state.isRunning) return;

        if (state.urlStatus !== "ready") {
            showToast(`Cannot start: ${state.urlReason}`, "error");
            const div = document.createElement("div");
            div.className = "log-entry log-error";
            div.innerHTML = `<span class="log-time">[${new Date().toLocaleTimeString()}]</span> <span class="log-module">[frontend]</span> <span class="log-message">Scraping aborted: ${state.urlReason}</span>`;
            if (dom.logsContainer) dom.logsContainer.prepend(div);
            return;
        }

        const url = dom.targetUrl.value.trim();
        const site = detectParser(url);
        if (!site) {
            showToast("Website not supported in registry. Try books.toscrape.com", "error");
            return;
        }

        state.activeParser = site.parser;
        state.isRunning = true;
        dom.runScraper.disabled = true;
        dom.runScraper.classList.add("loading");
        
        clearDashboardSession("New scrape started");
        showLoading();
        showToast("Scraping started…", "info");

        // Update info card immediately for visual feedback
        dom.infoDomain.textContent = site.domain;
        dom.infoType.textContent = site.type;
        dom.infoProtection.textContent = site.protection;
        dom.infoStatus.textContent = "Running";
        dom.infoStatus.className = "info-status running";

        // Start elapsed timer
        state.scrapeStartTime = Date.now();
        const estTimer = setInterval(() => {
            const elapsedMs = Date.now() - state.scrapeStartTime;
            const elapsedSec = Math.floor(elapsedMs / 1000);
            dom.pipelineElapsed.textContent = `${elapsedSec}s`;
            
            let estRemaining = Math.max(0, Math.floor(state.scrapeEstDuration / 1000) - elapsedSec);
            dom.pipelineEstimated.textContent = `~${estRemaining}s`;
            
            const prog = Math.min(95, (elapsedMs / state.scrapeEstDuration) * 100);
            dom.pipelinePercent.textContent = `${Math.floor(prog)}%`;
            
            const stageProgress = Math.floor((prog / 100) * 10);
            advancePipeline(stageProgress);
        }, 1000);

        try {
            const res = await apiFetch(API.SCRAPE, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ parser: state.activeParser }),
            }, 0);

            if (res.stats && res.stats.status === "protected") {
                dom.pipelineCurrentStage.innerHTML = `
                <div style="text-align:center; padding: 10px;">
                    <span style="font-size:2em; display:block; margin-bottom:5px;">🛡</span>
                    <strong style="color:var(--amber-500); font-size:1.1em; display:block; margin-bottom:5px;">Anti Bot Protection Detected</strong>
                    <span style="color:var(--text-muted); font-size:0.9em; display:block; margin-bottom:10px;">This website blocks automated scraping.</span>
                    <button class="btn btn-secondary" onclick="document.getElementById('targetUrl').focus()" style="font-size:0.8em;">Try Another Supported Website</button>
                </div>
            `;
            } else if (res.stats && res.stats.status === "failed") {
                dom.pipelineCurrentStage.innerHTML = `
                <div style="text-align:center; padding: 10px;">
                    <span style="font-size:2em; display:block; margin-bottom:5px;">❌</span>
                    <strong style="color:var(--red-500); font-size:1.1em; display:block; margin-bottom:5px;">Scrape Failed</strong>
                    <span style="color:var(--text-muted); font-size:0.9em; display:block; margin-bottom:10px;">${res.error || "An unknown error occurred during execution."}</span>
                    <button class="btn btn-secondary" onclick="document.getElementById('runScraper').click()" style="font-size:0.8em;">Retry Scrape</button>
                </div>
            `;
            } else {
                clearInterval(estTimer);
                dom.pipelinePercent.textContent = "100%";
                dom.pipelineEstimated.textContent = "Done";
                advancePipeline(10); // Completed

                showToast(`Scraping complete! ${res.stats.records_scraped} records scraped.`, "success");

                const actualDuration = Date.now() - state.scrapeStartTime;
                state.scrapeEstDuration = (state.scrapeEstDuration * 0.5) + (actualDuration * 0.5);

                await loadStats();
                await loadData();
                updateCharts();
                await loadLogs();
            }
            
            setTimeout(hideLoading, 1000);
        } catch (err) {
            clearInterval(estTimer);
            showToast(`Scraping failed: ${err.message}`, "error");
            hideLoading();
        } finally {
            state.isRunning = false;
            dom.runScraper.disabled = false;
            dom.runScraper.classList.remove("loading");
        }
    }

    // =====================================================================
    // Export
    // =====================================================================
    async function handleExport(url, ext) {
        if (!state.data || !state.data.length) return;
        try {
            showToast(`Generating ${ext.toUpperCase()} export...`, "info");
            const res = await fetch(url);
            if (!res.ok) throw new Error("Export failed");
            const blob = await res.blob();
            
            const a = document.createElement("a");
            const objUrl = window.URL.createObjectURL(blob);
            const ts = new Date().toISOString().split("T")[0];
            const siteName = state.activeParser ? capitalize(state.activeParser) : "Data";
            
            a.href = objUrl;
            a.download = `${siteName}_Export_${ts}.${ext}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(objUrl);
            
            showToast(`${ext.toUpperCase()} exported successfully!`, "success");
        } catch(e) {
            showToast(`Error exporting ${ext.toUpperCase()}`, "error");
        }
    }

    function exportCsv() {
        handleExport(API.CSV, "csv");
    }

    function exportJson() {
        handleExport(API.JSON, "json");
    }

    // =====================================================================
    // UI Helpers (Pipeline, Skeletons, Animations, Sorting)
    // =====================================================================
    function resetPipeline() {
        state.pipelineStage = 0;
        dom.pipelinePercent.textContent = "0 / 11 Stages Completed";
        dom.pipelineElapsed.textContent = "0s";
        dom.pipelineEstimated.textContent = `~${Math.floor(state.scrapeEstDuration / 1000)}s`;
        dom.pipelineCurrentStage.textContent = "Initializing...";
        
        dom.pipelineStages.forEach(el => {
            el.className = "pipeline-stage";
            const status = el.querySelector(".stage-status");
            const ctx = el.querySelector(".stage-context");
            const dot = el.querySelector(".stage-dot");
            if (status) status.textContent = "";
            if (ctx) ctx.textContent = "";
            if (dot) dot.classList.remove("pop");
        });
        
        $$(".stage-connector").forEach(el => el.className = "stage-connector");
        if (dom.pipelineStages[5] && dom.pipelineStages[5].nextElementSibling) {
            dom.pipelineStages[5].nextElementSibling.classList.add("bridge-down");
        }
        
        if (dom.pipelineStages.length > 0) {
            dom.pipelineStages[0].classList.add("active");
            const st = dom.pipelineStages[0].querySelector(".stage-status");
            if (st) st.textContent = "Running";
            dom.pipelineCurrentStage.textContent = dom.pipelineStages[0].querySelector(".stage-label").textContent;
            dom.pipelinePercent.textContent = "1 / 11 Stages Completed";
        }
        
        const connectors = $$(".stage-connector");
        if (connectors.length > 0) connectors[0].classList.add("active");
    }

    function advancePipeline(stageIdx) {
        if (stageIdx <= state.pipelineStage) return;
        const connectors = $$(".stage-connector");
        
        // Progress immediately the stages up to the new one
        for (let i = state.pipelineStage; i < stageIdx; i++) {
            const prev = dom.pipelineStages[i];
            const conn = connectors[i];
            
            if (prev) {
                // Step 1: Complete previous stage
                prev.className = "pipeline-stage complete";
                const st = prev.querySelector(".stage-status");
                const ctx = prev.querySelector(".stage-context");
                const dot = prev.querySelector(".stage-dot");
                if (st) st.textContent = "Done";
                if (ctx) ctx.textContent = "";
                
                // Add pop animation
                if (dot) {
                    dot.classList.add("pop");
                    setTimeout(() => dot.classList.remove("pop"), 400);
                }
            }
            if (conn) {
                conn.classList.remove("active");
                conn.classList.add("complete");
            }
        }
        
        state.pipelineStage = stageIdx;
        const total = dom.pipelineStages.length;
        dom.pipelinePercent.textContent = `${Math.min(stageIdx + 1, total)} / ${total} Stages Completed`;
        
        const nextStage = dom.pipelineStages[stageIdx];
        const nextConn = connectors[stageIdx];
        
        if (nextStage) {
            if (stageIdx === total - 1) {
                nextStage.className = "pipeline-stage complete";
                const st = nextStage.querySelector(".stage-status");
                const dot = nextStage.querySelector(".stage-dot");
                if (st) st.textContent = "Done";
                if (dot) {
                    dot.classList.add("pop");
                    setTimeout(() => dot.classList.remove("pop"), 400);
                }
                dom.pipelineCurrentStage.textContent = "Completed";
            } else {
                // Staggered Animation Sequence
                // Step 2: Connector animates to blue
                if (nextConn) setTimeout(() => nextConn.classList.add("active"), 150);
                
                // Step 3: Next stage scales slightly (preparing)
                setTimeout(() => nextStage.classList.add("preparing"), 300);
                
                // Step 4 & 5: Active glow & pulse
                setTimeout(() => nextStage.classList.add("active"), 450);
                
                // Step 6: Status to Running
                setTimeout(() => {
                    const st = nextStage.querySelector(".stage-status");
                    const ctx = nextStage.querySelector(".stage-context");
                    if (st) st.textContent = "Running";
                    if (ctx) {
                        if (stageIdx === 3) ctx.textContent = "Page " + Math.floor(Math.random() * 5 + 1) + " / 50";
                        else if (stageIdx === 4) ctx.textContent = Math.floor(Math.random() * 200 + 100) + " Records";
                        else if (stageIdx === 5 || stageIdx === 6) ctx.textContent = "Removing duplicates";
                        else if (stageIdx === 7 || stageIdx === 8) ctx.textContent = "Writing output";
                        else ctx.textContent = "";
                    }
                    dom.pipelineCurrentStage.textContent = nextStage.querySelector(".stage-label").textContent;
                }, 600);
            }
        }
    }

    function showSkeletons(ids) {
        ids.forEach(id => {
            if (dom[id]) dom[id].innerHTML = '<span class="skeleton-line"></span>';
        });
    }

    function animateCounter(el, target, duration = 1000, suffix = "") {
        if (!el) return;
        const startStr = el.textContent.replace(/,/g, "").replace(suffix, "");
        const start = parseInt(startStr) || 0;
        const change = target - start;
        if (change === 0) {
            el.textContent = target.toLocaleString() + suffix;
            return;
        }

        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
            const current = Math.floor(start + change * ease);
            el.textContent = current.toLocaleString() + suffix;

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                el.textContent = target.toLocaleString() + suffix;
            }
        }
        requestAnimationFrame(update);
    }

    function sortTable(col) {
        if (state.sortColumn === col) {
            state.sortDirection *= -1;
        } else {
            state.sortColumn = col;
            state.sortDirection = 1;
        }
        
        state.data.sort((a, b) => {
            let valA = a[col];
            let valB = b[col];
            if (valA === null || valA === undefined) valA = "";
            if (valB === null || valB === undefined) valB = "";
            
            if (!isNaN(valA) && !isNaN(valB) && valA !== "" && valB !== "") {
                return (Number(valA) - Number(valB)) * state.sortDirection;
            }
            return String(valA).localeCompare(String(valB)) * state.sortDirection;
        });

        state.currentPage = 1;
        renderTable();
    }

    // =====================================================================
    // Initialization
    // =====================================================================
    function init() {
        initTheme();
        initRegistry();
        initNav();
        initMobileMenu();
        initSearch();

        // Event listeners
        dom.themeToggle.addEventListener("click", toggleTheme);
        dom.runScraper.addEventListener("click", runScraper);
        dom.exportCsv.addEventListener("click", exportCsv);
        dom.exportJson.addEventListener("click", exportJson);
        dom.refreshLogs.addEventListener("click", loadLogs);
        dom.saveSettings.addEventListener("click", saveSettings);
        dom.targetUrl.addEventListener("input", onUrlInput);

        // Initial data load
        loadSettings();
        initLogFilters();
        
        // Load stats and data in parallel, then render charts once both are ready.
        // This ensures updateCharts() has access to both state.data and state.lastStats.
        Promise.all([loadStats(), loadData()])
            .then(() => updateCharts())
            .catch(() => {}); // Individual errors already handled with toasts
        loadLogs();
        
        // Initial button state
        clearDashboardSession("Application loaded");
    }

    // Start when DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
