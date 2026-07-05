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
        PARSERS: "/api/parsers",
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
    };

    // =====================================================================
    // DOM References
    // =====================================================================
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const dom = {
        themeToggle:    $("#themeToggle"),
        parserSelect:   $("#parserSelect"),
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
        settingBaseUrl:   $("#settingBaseUrl"),
        settingParser:    $("#settingParser"),
        settingTimeout:   $("#settingTimeout"),
        settingRetries:   $("#settingRetries"),
        settingUserAgent: $("#settingUserAgent"),
        settingDelay:     $("#settingDelay"),

        // Nav items
        navItems: $$(".nav-item"),
    };

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
        toast.textContent = message;
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
    async function apiFetch(url, options = {}) {
        try {
            const res = await fetch(url, options);
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.error || `HTTP ${res.status}`);
            }
            return await res.json();
        } catch (err) {
            console.error(`API error [${url}]:`, err);
            throw err;
        }
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
        try {
            const stats = await apiFetch(API.STATS);
            dom.valRecords.textContent = stats.records_scraped.toLocaleString();
            dom.valPages.textContent = stats.pages_crawled.toLocaleString();
            dom.valTime.textContent = `${stats.execution_time}s`;
            dom.valDuplicates.textContent = stats.duplicates_removed.toLocaleString();

            // Status badge
            const statusText = stats.status || "idle";
            dom.valStatus.textContent = capitalize(statusText.split(":")[0]);
            dom.valStatus.className = "stat-value status-badge";
            if (statusText.startsWith("error")) {
                dom.valStatus.classList.add("error");
            } else {
                dom.valStatus.classList.add(statusText);
            }

            // Last run
            if (stats.last_run) {
                const d = new Date(stats.last_run);
                dom.valLastRun.textContent = d.toLocaleTimeString();
            } else {
                dom.valLastRun.textContent = "Never";
            }
        } catch {
            // Silent on stats load failure
        }
    }

    // =====================================================================
    // Data Table (dynamic columns)
    // =====================================================================
    async function loadData() {
        try {
            const params = state.searchQuery ? `?search=${encodeURIComponent(state.searchQuery)}` : "";
            const res = await apiFetch(`${API.DATA}${params}`);

            state.data = res.data || [];
            state.columns = res.columns || [];
            state.currentPage = 1;
            state.totalPages = Math.max(1, Math.ceil(state.data.length / ROWS_PER_PAGE));

            renderTable();
            updateCharts();
        } catch {
            // Silent on data load failure
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
        dom.tableHead.innerHTML = `<tr>${displayCols.map((col) =>
            `<th>${formatColumnName(col)}</th>`
        ).join("")}</tr>`;

        // --- Paginated rows ---
        const start = (currentPage - 1) * ROWS_PER_PAGE;
        const pageData = data.slice(start, start + ROWS_PER_PAGE);

        dom.tableBody.innerHTML = pageData.map((row) =>
            `<tr>${displayCols.map((col) => `<td>${formatCell(col, row[col])}</td>`).join("")}</tr>`
        ).join("");

        dom.recordCount.textContent = `${data.length} record${data.length !== 1 ? "s" : ""}`;

        renderPagination();
    }

    function formatColumnName(col) {
        return col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }

    function formatCell(col, value) {
        if (value === null || value === undefined) return '<span style="opacity:.4">—</span>';

        // Render ratings as stars
        if (col === "rating" && typeof value === "number") {
            return `<span class="rating-stars">${"★".repeat(value)}${"☆".repeat(5 - value)}</span>`;
        }

        // Render prices with currency
        if (col === "price") {
            return `£${value}`;
        }

        // Render URLs as links
        if (col.endsWith("_url") && typeof value === "string" && value.startsWith("http")) {
            return `<a href="${escapeHtml(value)}" target="_blank" rel="noopener">Link ↗</a>`;
        }

        // Truncate long strings
        const str = String(value);
        if (str.length > 80) {
            return `<span title="${escapeHtml(str)}">${escapeHtml(str.slice(0, 77))}…</span>`;
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
        const { data, columns } = state;
        if (!data.length) return;

        const colors = getChartColors();

        // --- Chart 1: Distribution (price or first numeric column) ---
        updateDistributionChart(data, columns, colors);

        // --- Chart 2: Ratings / category breakdown ---
        updateCategoryChart(data, columns, colors);

        // --- Chart 3: Records per page (simulated from data chunks) ---
        updatePerPageChart(data, colors);

        // --- Chart 4: Request results (success vs failed) ---
        updateRequestsChart(colors);
    }

    function updateDistributionChart(data, columns, colors) {
        const canvas = document.getElementById("chartDistribution");
        const ctx = canvas.getContext("2d");

        // Find numeric column (price, salary, etc.)
        let numericCol = null;
        let label = "Value";
        if (columns.includes("price")) { numericCol = "price"; label = "Price (£)"; }
        else if (columns.includes("salary")) { numericCol = "salary"; label = "Salary"; }

        if (state.charts.distribution) state.charts.distribution.destroy();

        if (numericCol) {
            const values = data.map((r) => parseFloat(r[numericCol]) || 0).filter((v) => v > 0);
            // Create bins
            const min = Math.floor(Math.min(...values));
            const max = Math.ceil(Math.max(...values));
            const binCount = Math.min(10, max - min + 1);
            const binSize = (max - min) / binCount;
            const bins = Array(binCount).fill(0);
            const labels = [];

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

            state.charts.distribution = new Chart(ctx, {
                type: "bar",
                data: {
                    labels,
                    datasets: [{
                        label,
                        data: bins,
                        backgroundColor: colors.blueAlpha,
                        borderColor: colors.blue,
                        borderWidth: 1,
                        borderRadius: 6,
                    }],
                },
                options: chartOptions(colors, label + " Distribution"),
            });
        } else {
            // For non-numeric data, show frequency of first column
            const col = columns[0];
            const freq = {};
            data.forEach((r) => {
                const key = String(r[col] || "").slice(0, 30);
                freq[key] = (freq[key] || 0) + 1;
            });
            const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 10);

            state.charts.distribution = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: sorted.map((s) => s[0]),
                    datasets: [{
                        label: formatColumnName(col),
                        data: sorted.map((s) => s[1]),
                        backgroundColor: colors.blueAlpha,
                        borderColor: colors.blue,
                        borderWidth: 1,
                        borderRadius: 6,
                    }],
                },
                options: chartOptions(colors, `${formatColumnName(col)} Frequency`),
            });
        }
    }

    function updateCategoryChart(data, columns, colors) {
        const canvas = document.getElementById("chartRatings");
        const ctx = canvas.getContext("2d");

        if (state.charts.ratings) state.charts.ratings.destroy();

        // Pick a categorical column
        let catCol = null;
        if (columns.includes("rating")) catCol = "rating";
        else if (columns.includes("author")) catCol = "author";
        else if (columns.includes("company")) catCol = "company";
        else if (columns.includes("category")) catCol = "category";
        else if (columns.includes("tags")) catCol = "tags";
        else catCol = columns[Math.min(1, columns.length - 1)];

        const freq = {};
        data.forEach((r) => {
            const key = String(r[catCol] || "Unknown").slice(0, 30);
            freq[key] = (freq[key] || 0) + 1;
        });
        const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 8);

        const palette = [colors.blue, colors.purple, colors.cyan, colors.green, colors.amber, colors.red, "#8b5cf6", "#ec4899"];

        state.charts.ratings = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: sorted.map((s) => s[0]),
                datasets: [{
                    data: sorted.map((s) => s[1]),
                    backgroundColor: palette.slice(0, sorted.length).map(c => c + "99"),
                    borderColor: palette.slice(0, sorted.length),
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

    async function updateRequestsChart(colors) {
        const canvas = document.getElementById("chartRequests");
        const ctx = canvas.getContext("2d");

        if (state.charts.requests) state.charts.requests.destroy();

        try {
            const stats = await apiFetch(API.STATS);
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
        } catch {
            // Ignore
        }
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
    async function loadLogs() {
        try {
            const res = await apiFetch(`${API.LOGS}?limit=200`);
            const logs = res.logs || [];

            if (!logs.length) {
                dom.logsContainer.innerHTML = '<div class="log-empty">Logs will appear here after a scrape run.</div>';
                return;
            }

            dom.logsContainer.innerHTML = logs.map((log) => `
                <div class="log-entry">
                    <span class="log-level ${log.level}">${log.level}</span>
                    <span class="log-time">${(log.timestamp || "").slice(11, 19)}</span>
                    <span class="log-message">${escapeHtml(log.message)}</span>
                </div>
            `).join("");

            dom.logsContainer.scrollTop = dom.logsContainer.scrollHeight;
        } catch {
            // Ignore
        }
    }

    // =====================================================================
    // Settings
    // =====================================================================
    async function loadSettings() {
        try {
            const config = await apiFetch(API.CONFIG);
            dom.settingBaseUrl.value = config.base_url || "";
            dom.settingParser.value = config.active_parser || "books";
            dom.settingTimeout.value = config.timeout || 30;
            dom.settingRetries.value = config.max_retries || 3;
            dom.settingUserAgent.value = config.user_agent || "";
            dom.settingDelay.value = config.request_delay || 1;
        } catch {
            // Ignore
        }
    }

    async function saveSettings() {
        const payload = {
            base_url: dom.settingBaseUrl.value,
            active_parser: dom.settingParser.value,
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
            showToast("Settings saved successfully", "success");

            // Sync parser selector
            dom.parserSelect.value = dom.settingParser.value;
            state.activeParser = dom.settingParser.value;
        } catch (err) {
            showToast(`Failed to save settings: ${err.message}`, "error");
        }
    }

    // =====================================================================
    // Scraper
    // =====================================================================
    async function runScraper() {
        showLoading();
        showToast("Scraping started…", "info");

        try {
            const res = await apiFetch(API.SCRAPE, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    parser: state.activeParser,
                }),
            });

            showToast(`Scraping complete! ${res.stats.records_scraped} records scraped.`, "success");

            // Refresh everything
            await Promise.all([loadStats(), loadData(), loadLogs()]);
        } catch (err) {
            showToast(`Scraping failed: ${err.message}`, "error");
        } finally {
            hideLoading();
        }
    }

    // =====================================================================
    // Export
    // =====================================================================
    function exportCsv() {
        window.open(API.CSV, "_blank");
    }

    function exportJson() {
        window.open(API.JSON, "_blank");
    }

    // =====================================================================
    // Parser Selection
    // =====================================================================
    async function loadParsers() {
        try {
            const res = await apiFetch(API.PARSERS);
            const parsers = res.parsers || [];
            const active = res.active || "books";

            // Update both selectors
            [dom.parserSelect, dom.settingParser].forEach((sel) => {
                sel.innerHTML = parsers.map((p) =>
                    `<option value="${p.name}" ${p.name === active ? "selected" : ""}>${p.display_name}</option>`
                ).join("");
            });

            state.activeParser = active;
        } catch {
            // Use defaults
        }
    }

    function onParserChange(e) {
        state.activeParser = e.target.value;

        // Also sync the settings parser select
        dom.settingParser.value = state.activeParser;

        // Update config on server
        apiFetch(API.CONFIG, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ active_parser: state.activeParser }),
        }).then(() => {
            showToast(`Switched to ${capitalize(state.activeParser)} parser`, "info");
        }).catch(() => {});
    }

    // =====================================================================
    // Initialization
    // =====================================================================
    function init() {
        initTheme();
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
        dom.parserSelect.addEventListener("change", onParserChange);

        // Initial data load
        loadParsers();
        loadStats();
        loadData();
        loadLogs();
        loadSettings();
    }

    // Start when DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
