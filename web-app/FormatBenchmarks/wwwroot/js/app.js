/**
 * Format Benchmarks - Frontend Applicatie
 * =========================================
 * Beheert de UI, API communicatie, Chart.js grafieken en data export.
 */

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

const App = {
    currentRun: null,
    allRuns: [],
    charts: {},

    // Kleurenschema per format
    formatColors: {
        'JSON':         { bg: 'rgba(243, 156, 18, 0.75)', border: 'rgb(243, 156, 18)' },
        'BSON':         { bg: 'rgba(39, 174, 96, 0.75)',  border: 'rgb(39, 174, 96)' },
        'Protobuf':     { bg: 'rgba(52, 152, 219, 0.75)', border: 'rgb(52, 152, 219)' },
        "Cap'n Proto":  { bg: 'rgba(155, 89, 182, 0.75)', border: 'rgb(155, 89, 182)' },
        'MessagePack':  { bg: 'rgba(231, 76, 60, 0.75)',  border: 'rgb(231, 76, 60)' },
        'Apache Avro':  { bg: 'rgba(26, 188, 156, 0.75)', border: 'rgb(26, 188, 156)' },
        'FlatBuffers':  { bg: 'rgba(241, 196, 15, 0.75)', border: 'rgb(241, 196, 15)' },
    },

    // Vergelijking state
    compareRunA: null,
    compareRunB: null,

    // ==================== Initialisatie ====================

    init() {
        document.getElementById('run-btn').addEventListener('click', () => this.runBenchmark());
        document.getElementById('compare-btn')?.addEventListener('click', () => this.openCompareModal());

        // Enter toets in input velden triggert ook de benchmark
        document.querySelectorAll('#iterations, #warmup').forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.runBenchmark();
            });
        });
    },

    // ==================== Configuratie ====================

    getConfig() {
        return {
            iterations: parseInt(document.getElementById('iterations').value) || 1000,
            warmup: parseInt(document.getElementById('warmup').value) || 100,
            formats: Array.from(document.querySelectorAll('input[name="format"]:checked'))
                .map(cb => cb.value),
            sizes: Array.from(document.querySelectorAll('input[name="size"]:checked'))
                .map(cb => cb.value),
            language: document.querySelector('input[name="language"]:checked')?.value || 'python',
        };
    },

    selectAllFormats(select) {
        document.querySelectorAll('input[name="format"]')
            .forEach(cb => cb.checked = select);
    },

    // ==================== Benchmark Uitvoering ====================

    async runBenchmark() {
        const config = this.getConfig();

        if (config.formats.length === 0) {
            this.showError('Selecteer minimaal één message format.');
            return;
        }
        if (config.sizes.length === 0) {
            this.showError('Selecteer minimaal één payload grootte.');
            return;
        }

        this.showLoading(true);
        this.hideError();
        document.getElementById('welcome-section').classList.add('d-none');
        document.getElementById('results-section').classList.add('d-none');

        try {
            const response = await fetch('/api/benchmark/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config),
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || `HTTP ${response.status}`);
            }

            const run = await response.json();

            if (run.status === 'failed') {
                throw new Error(run.errorMessage || 'Benchmark uitvoering mislukt');
            }

            this.currentRun = run;
            this.allRuns.push(run);
            this.displayResults(run);
        } catch (error) {
            this.showError(`Benchmark fout: ${error.message}`);
            // Toon welcome section weer als er geen resultaten zijn
            if (!this.currentRun) {
                document.getElementById('welcome-section').classList.remove('d-none');
            }
        } finally {
            this.showLoading(false);
        }
    },

    // ==================== Resultaten Weergave ====================

    displayResults(run) {
        document.getElementById('results-section').classList.remove('d-none');
        document.getElementById('welcome-section').classList.add('d-none');

        // Systeem informatie
        const sys = run.systemInfo || {};
        const lang = (sys.language || 'python').toLowerCase();
        const langLabel = lang === 'go' ? 'Go' : 'Python';
        const langBadgeClass = lang === 'go' ? 'bg-info' : 'bg-warning text-dark';
        const versionLabel = lang === 'go'
            ? (sys.goVersion || 'N/A')
            : (sys.pythonVersion || 'N/A');
        document.getElementById('system-info').innerHTML = `
            <span><span class="badge ${langBadgeClass}">${langLabel}</span></span>
            <span><strong>Platform:</strong> ${sys.platform || 'N/A'}</span>
            <span><strong>${langLabel}:</strong> ${versionLabel}</span>
            <span><strong>CPU:</strong> ${sys.processor || 'N/A'}</span>
            <span><strong>Cores:</strong> ${sys.cpuCount || 'N/A'}</span>
            <span><strong>Iteraties:</strong> ${run.config?.iterations || 'N/A'}</span>
        `;

        // Size tabs instellen
        const sizeOrder = ['small', 'medium', 'large'];
        const sizes = [...new Set(run.results.map(r => r.payloadSizeLabel))]
            .sort((a, b) => sizeOrder.indexOf(a) - sizeOrder.indexOf(b));
        this.setupSizeTabs(sizes);

        // Toon charts voor eerste grootte
        if (sizes.length > 0) {
            this.switchSizeTab(sizes[0]);
        }

        // Data tabel
        this.createDataTable(run.results);

        // Run history bijwerken
        this.updateRunHistory();
    },

    // ==================== Size Tabs ====================

    setupSizeTabs(sizes) {
        const container = document.getElementById('size-tabs');
        container.innerHTML = '';

        // "Alle" tab
        const allBtn = document.createElement('button');
        allBtn.className = 'btn btn-outline-primary btn-sm size-tab';
        allBtn.dataset.size = '__all__';
        allBtn.textContent = 'Alle';
        allBtn.addEventListener('click', () => this.switchSizeTab('__all__'));
        container.appendChild(allBtn);

        sizes.forEach((size, i) => {
            const btn = document.createElement('button');
            btn.className = `btn btn-outline-primary btn-sm size-tab ${i === 0 ? 'active' : ''}`;
            btn.dataset.size = size;
            btn.textContent = this.capitalize(size);
            btn.addEventListener('click', () => this.switchSizeTab(size));
            container.appendChild(btn);
        });
    },

    switchSizeTab(size) {
        // Update actieve tab styling
        document.querySelectorAll('.size-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.size === size);
        });

        if (!this.currentRun) return;

        const results = size === '__all__'
            ? this.currentRun.results
            : this.currentRun.results.filter(r => r.payloadSizeLabel === size);

        this.createCharts(results, size === '__all__');
    },

    // ==================== Chart.js Grafieken ====================

    createCharts(results, isAllSizes = false) {
        this.createBarChart('serialize-chart', 'Serialisatie Tijd (ms)',
            results, r => r.serializeTimeMs.mean, isAllSizes);
        this.createBarChart('deserialize-chart', 'Deserialisatie Tijd (ms)',
            results, r => r.deserializeTimeMs.mean, isAllSizes);
        this.createBarChart('roundtrip-chart', 'Round-Trip Tijd (ms)',
            results, r => r.roundTripTimeMs.mean, isAllSizes);
        this.createBarChart('size-chart', 'Payload Grootte (bytes)',
            results, r => r.serializedSizeBytes, isAllSizes, true);
        this.createBarChart('memory-chart', 'Geheugen Piek (bytes)',
            results, r => r.memoryUsage?.totalPeakBytes || 0, isAllSizes, true);
        this.createCompressionChart('compression-chart', results, isAllSizes);
        this.createBarChart('throughput-chart', 'Doorvoer (msg/sec)',
            results, r => r.throughput?.serializeMsgPerSec || 0, isAllSizes, false, 'msg/sec');
        this.createBarChart('throughput-mb-chart', 'Doorvoer (MB/sec)',
            results, r => r.throughput?.serializeMbPerSec || 0, isAllSizes, false, 'MB/sec');
    },

    createBarChart(canvasId, title, results, valueExtractor, isGrouped = false, isSize = false, unit = null) {
        // Verwijder bestaande chart
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const ctx = document.getElementById(canvasId).getContext('2d');

        let chartData;

        if (isGrouped && results.length > 0) {
            // Gegroepeerde weergave: formats op x-as, grootte als datasets
            chartData = this.buildGroupedChartData(results, valueExtractor);
        } else {
            // Enkele weergave: één bar per format
            chartData = this.buildSimpleChartData(results, valueExtractor);
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: isGrouped,
                        labels: { color: '#b0b0b0', font: { size: 11 } }
                    },
                    title: {
                        display: true,
                        text: title,
                        font: { size: 15, weight: 'bold' },
                        color: '#e0e0e0',
                        padding: { bottom: 15 }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const val = ctx.parsed.y;
                                if (unit) return `${val.toLocaleString()} ${unit}`;
                                if (isSize) return `${val.toLocaleString()} bytes`;
                                return `${val.toFixed(4)} ms`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.06)' },
                        ticks: {
                            color: '#b0b0b0',
                            callback: (val) => isSize ? val.toLocaleString() : val
                        },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#b0b0b0', font: { size: 11 } },
                    }
                },
                animation: { duration: 500 }
            }
        });
    },

    buildSimpleChartData(results, valueExtractor) {
        const labels = results.map(r => r.format);
        const data = results.map(valueExtractor);
        const bgColors = results.map(r =>
            (this.formatColors[r.format] || { bg: 'rgba(128,128,128,0.7)' }).bg);
        const borderColors = results.map(r =>
            (this.formatColors[r.format] || { border: 'rgb(128,128,128)' }).border);

        return {
            labels,
            datasets: [{
                data,
                backgroundColor: bgColors,
                borderColor: borderColors,
                borderWidth: 2,
                borderRadius: 6,
            }]
        };
    },

    buildGroupedChartData(results, valueExtractor) {
        const formats = [...new Set(results.map(r => r.format))];
        const sizes = [...new Set(results.map(r => r.payloadSizeLabel))];

        const sizeAlpha = { small: '0.5', medium: '0.75', large: '1.0' };

        const datasets = sizes.map(size => ({
            label: this.capitalize(size),
            data: formats.map(fmt => {
                const match = results.find(r => r.format === fmt && r.payloadSizeLabel === size);
                return match ? valueExtractor(match) : 0;
            }),
            backgroundColor: formats.map(fmt => {
                const color = this.formatColors[fmt];
                if (!color) return `rgba(128,128,128,${sizeAlpha[size] || '0.7'})`;
                return color.bg.replace(/[\d.]+\)$/, `${sizeAlpha[size] || '0.7'})`);
            }),
            borderColor: formats.map(fmt =>
                (this.formatColors[fmt] || { border: 'rgb(128,128,128)' }).border),
            borderWidth: 1.5,
            borderRadius: 4,
        }));

        return { labels: formats, datasets };
    },

    createCompressionChart(canvasId, results, isGrouped = false) {
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        // Voor grouped (alle sizes) neem we alleen de eerste size voor leesbaarheid
        const targetResults = isGrouped
            ? (() => {
                const sizes = [...new Set(results.map(r => r.payloadSizeLabel))];
                return results.filter(r => r.payloadSizeLabel === sizes[0]);
            })()
            : results;

        const formats = targetResults.map(r => r.format);
        const originalData = targetResults.map(r => r.compression?.originalBytes || r.serializedSizeBytes);
        const gzipData = targetResults.map(r => r.compression?.gzipBytes || 0);
        const zstdData = targetResults.map(r => r.compression?.zstdBytes || 0);
        const hasZstd = zstdData.some(v => v > 0);

        const datasets = [
            {
                label: 'Origineel',
                data: originalData,
                backgroundColor: 'rgba(149, 165, 166, 0.7)',
                borderColor: 'rgb(149, 165, 166)',
                borderWidth: 1.5, borderRadius: 4,
            },
            {
                label: 'Gzip',
                data: gzipData,
                backgroundColor: 'rgba(46, 204, 113, 0.7)',
                borderColor: 'rgb(46, 204, 113)',
                borderWidth: 1.5, borderRadius: 4,
            },
        ];

        if (hasZstd) {
            datasets.push({
                label: 'Zstandard',
                data: zstdData,
                backgroundColor: 'rgba(52, 152, 219, 0.7)',
                borderColor: 'rgb(52, 152, 219)',
                borderWidth: 1.5, borderRadius: 4,
            });
        }

        const sizeLabel = isGrouped
            ? ` (${this.capitalize(targetResults[0]?.payloadSizeLabel || '')})`
            : '';

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: { labels: formats, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: '#b0b0b0', font: { size: 11 } } },
                    title: {
                        display: true,
                        text: `Compressie Vergelijking (bytes)${sizeLabel}`,
                        font: { size: 15, weight: 'bold' },
                        color: '#e0e0e0',
                        padding: { bottom: 15 },
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()} bytes`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.06)' },
                        ticks: { color: '#b0b0b0', callback: (v) => v.toLocaleString() },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#b0b0b0', font: { size: 11 } },
                    }
                },
                animation: { duration: 500 }
            }
        });
    },

    // ==================== Data Tabel ====================

    createDataTable(results) {
        const tbody = document.getElementById('results-table-body');
        tbody.innerHTML = '';

        // Sorteer: per grootte, dan per format
        const sorted = [...results].sort((a, b) => {
            const sizeOrder = { small: 0, medium: 1, large: 2 };
            const sizeDiff = (sizeOrder[a.payloadSizeLabel] || 0) - (sizeOrder[b.payloadSizeLabel] || 0);
            if (sizeDiff !== 0) return sizeDiff;
            return a.format.localeCompare(b.format);
        });

        sorted.forEach(r => {
            const color = this.formatColors[r.format] || { bg: 'rgba(128,128,128,0.7)' };
            const memPeak = r.memoryUsage?.totalPeakBytes;
            const memDisplay = memPeak != null ? this.formatBytes(memPeak) : 'N/A';
            const gzipBytes = r.compression?.gzipBytes;
            const gzipRatio = r.compression?.gzipRatio;
            const comprDisplay = gzipBytes != null
                ? `${this.formatBytes(gzipBytes)} (${(gzipRatio * 100).toFixed(0)}%)`
                : 'N/A';
            const throughput = r.throughput?.serializeMsgPerSec;
            const tpDisplay = throughput != null
                ? `${Math.round(throughput).toLocaleString()}`
                : 'N/A';
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="format-badge" style="background:${color.bg}">${r.format}</span>
                </td>
                <td>${this.capitalize(r.payloadSizeLabel)}</td>
                <td>${r.serializedSizeBytes.toLocaleString()}</td>
                <td>${r.serializeTimeMs.mean.toFixed(4)}</td>
                <td>${r.deserializeTimeMs.mean.toFixed(4)}</td>
                <td>${r.roundTripTimeMs.mean.toFixed(4)}</td>
                <td>${r.serializeTimeMs.p95.toFixed(4)}</td>
                <td>${r.deserializeTimeMs.p95.toFixed(4)}</td>
                <td>${r.roundTripTimeMs.stdDev.toFixed(4)}</td>
                <td>${memDisplay}</td>
                <td>${comprDisplay}</td>
                <td>${tpDisplay}</td>
            `;
            tbody.appendChild(row);
        });
    },

    // ==================== Export ====================

    exportJSON() {
        if (!this.currentRun) {
            this.showError('Geen resultaten om te exporteren.');
            return;
        }
        const blob = new Blob(
            [JSON.stringify(this.currentRun, null, 2)],
            { type: 'application/json' }
        );
        this.downloadBlob(blob, `benchmark_${this.currentRun.id}.json`);
    },

    async exportCSV() {
        if (!this.currentRun) {
            this.showError('Geen resultaten om te exporteren.');
            return;
        }
        try {
            const response = await fetch(
                `/api/benchmark/export/${this.currentRun.id}?format=csv`
            );
            if (!response.ok) throw new Error('CSV export mislukt');
            const blob = await response.blob();
            this.downloadBlob(blob, `benchmark_${this.currentRun.id}.csv`);
        } catch (error) {
            this.showError(error.message);
        }
    },

    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    // ==================== Run History ====================

    updateRunHistory() {
        const container = document.getElementById('run-history');
        if (this.allRuns.length === 0) {
            container.innerHTML = '<span class="text-muted">Nog geen vorige runs.</span>';
            return;
        }

        container.innerHTML = this.allRuns.map((run, i) => {
            const time = new Date(run.timestamp).toLocaleTimeString('nl-NL');
            const formats = run.results.map(r => r.format);
            const uniqueFormats = [...new Set(formats)];
            const statusClass = run.status === 'completed' ? 'completed' : 'failed';
            const lang = (run.systemInfo?.language || 'python').toLowerCase();
            const langLabel = lang === 'go' ? 'Go' : 'Python';
            const langBadge = lang === 'go'
                ? '<span class="badge bg-info me-1">Go</span>'
                : '<span class="badge bg-warning text-dark me-1">Python</span>';

            return `
                <div class="run-history-item d-flex justify-content-between align-items-center"
                     onclick="App.loadRun(${i})">
                    <div>
                        <span class="status-dot ${statusClass}"></span>
                        ${langBadge}
                        <strong>Run #${i + 1}</strong> — ${time}
                    </div>
                    <div class="text-muted">
                        ${uniqueFormats.length} formats, ${run.results.length} tests
                    </div>
                </div>
            `;
        }).join('');
    },

    loadRun(index) {
        if (index >= 0 && index < this.allRuns.length) {
            this.currentRun = this.allRuns[index];
            this.displayResults(this.currentRun);
        }
    },

    // ==================== UI Helpers ====================

    showLoading(show) {
        document.getElementById('loading').classList.toggle('d-none', !show);
        document.getElementById('run-btn').disabled = show;
        if (show) {
            document.getElementById('run-btn').innerHTML =
                '<span class="spinner-border spinner-border-sm me-2"></span>Bezig...';
        } else {
            document.getElementById('run-btn').innerHTML =
                '<i class="bi bi-play-fill"></i> Start Benchmark';
        }
    },

    showError(msg) {
        const el = document.getElementById('error-alert');
        document.getElementById('error-message').textContent = msg;
        el.classList.remove('d-none');
        // Auto-hide na 10 seconden
        setTimeout(() => el.classList.add('d-none'), 10000);
    },

    hideError() {
        document.getElementById('error-alert').classList.add('d-none');
    },

    capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    },

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i];
    },

    // ==================== Run Vergelijking ====================

    openCompareModal() {
        if (this.allRuns.length < 2) {
            this.showError('Minimaal 2 runs nodig om te vergelijken. Voer eerst meerdere benchmarks uit.');
            return;
        }

        const modal = document.getElementById('compare-modal');
        const selectA = document.getElementById('compare-run-a');
        const selectB = document.getElementById('compare-run-b');

        // Vul selects met runs
        const optionsHtml = this.allRuns.map((run, i) => {
            const time = new Date(run.timestamp).toLocaleTimeString('nl-NL');
            const formats = [...new Set(run.results.map(r => r.format))];
            const lang = (run.systemInfo?.language || 'python').toLowerCase();
            const langLabel = lang === 'go' ? 'Go' : 'Python';
            return `<option value="${i}">Run #${i + 1} [${langLabel}] — ${time} (${formats.length} formats)</option>`;
        }).join('');

        selectA.innerHTML = optionsHtml;
        selectB.innerHTML = optionsHtml;

        // Standaard: laatste twee runs
        selectA.value = this.allRuns.length - 2;
        selectB.value = this.allRuns.length - 1;

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    executeCompare() {
        const idxA = parseInt(document.getElementById('compare-run-a').value);
        const idxB = parseInt(document.getElementById('compare-run-b').value);

        if (idxA === idxB) {
            this.showError('Selecteer twee verschillende runs om te vergelijken.');
            return;
        }

        this.compareRunA = this.allRuns[idxA];
        this.compareRunB = this.allRuns[idxB];

        // Sluit modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('compare-modal'));
        if (modal) modal.hide();

        this.displayComparison();
    },

    displayComparison() {
        const runA = this.compareRunA;
        const runB = this.compareRunB;
        if (!runA || !runB) return;

        // Toon vergelijking sectie
        document.getElementById('compare-section').classList.remove('d-none');
        document.getElementById('results-section').classList.add('d-none');
        document.getElementById('welcome-section').classList.add('d-none');

        const idxA = this.allRuns.indexOf(runA);
        const idxB = this.allRuns.indexOf(runB);
        document.getElementById('compare-title').textContent =
            `Run #${idxA + 1} vs Run #${idxB + 1}`;

        // Vind gemeenschappelijke formats + sizes
        const formatsA = new Set(runA.results.map(r => `${r.format}|${r.payloadSizeLabel}`));
        const commonResults = runB.results.filter(r => formatsA.has(`${r.format}|${r.payloadSizeLabel}`));

        // Bouw vergelijkingsgrafieken
        this.createCompareChart('compare-serialize-chart', 'Serialisatie Tijd (ms)',
            runA, runB, idxA, idxB, r => r.serializeTimeMs.mean);
        this.createCompareChart('compare-deserialize-chart', 'Deserialisatie Tijd (ms)',
            runA, runB, idxA, idxB, r => r.deserializeTimeMs.mean);
        this.createCompareChart('compare-roundtrip-chart', 'Round-Trip Tijd (ms)',
            runA, runB, idxA, idxB, r => r.roundTripTimeMs.mean);
        this.createCompareChart('compare-throughput-chart', 'Doorvoer (msg/sec)',
            runA, runB, idxA, idxB, r => r.throughput?.serializeMsgPerSec || 0, false, 'msg/sec');

        // Vergelijkingstabel
        this.createCompareTable(runA, runB, idxA, idxB);
    },

    createCompareChart(canvasId, title, runA, runB, idxA, idxB, valueExtractor, isSize = false, unit = null) {
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        // Gemeenschappelijke format+size combinaties (gebruik 'small' als default filter)
        const sizes = [...new Set([...runA.results.map(r => r.payloadSizeLabel), ...runB.results.map(r => r.payloadSizeLabel)])];
        const targetSize = sizes.includes('small') ? 'small' : sizes[0];

        const resultsA = runA.results.filter(r => r.payloadSizeLabel === targetSize);
        const resultsB = runB.results.filter(r => r.payloadSizeLabel === targetSize);
        const allFormats = [...new Set([...resultsA.map(r => r.format), ...resultsB.map(r => r.format)])];

        const dataA = allFormats.map(fmt => {
            const match = resultsA.find(r => r.format === fmt);
            return match ? valueExtractor(match) : 0;
        });
        const dataB = allFormats.map(fmt => {
            const match = resultsB.find(r => r.format === fmt);
            return match ? valueExtractor(match) : 0;
        });

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: allFormats,
                datasets: [
                    {
                        label: `Run #${idxA + 1}`,
                        data: dataA,
                        backgroundColor: 'rgba(52, 152, 219, 0.7)',
                        borderColor: 'rgb(52, 152, 219)',
                        borderWidth: 2,
                        borderRadius: 4,
                    },
                    {
                        label: `Run #${idxB + 1}`,
                        data: dataB,
                        backgroundColor: 'rgba(231, 76, 60, 0.7)',
                        borderColor: 'rgb(231, 76, 60)',
                        borderWidth: 2,
                        borderRadius: 4,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: '#b0b0b0' } },
                    title: {
                        display: true,
                        text: `${title} (${this.capitalize(targetSize)})`,
                        font: { size: 15, weight: 'bold' },
                        color: '#e0e0e0',
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const val = ctx.parsed.y;
                                if (unit) return `${ctx.dataset.label}: ${val.toLocaleString()} ${unit}`;
                                if (isSize) return `${ctx.dataset.label}: ${val.toLocaleString()} bytes`;
                                return `${ctx.dataset.label}: ${val.toFixed(4)} ms`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.06)' },
                        ticks: { color: '#b0b0b0' },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#b0b0b0', font: { size: 11 } },
                    }
                },
                animation: { duration: 500 }
            }
        });
    },

    createCompareTable(runA, runB, idxA, idxB) {
        const tbody = document.getElementById('compare-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        const mapKey = r => `${r.format}|${r.payloadSizeLabel}`;
        const mapA = Object.fromEntries(runA.results.map(r => [mapKey(r), r]));
        const mapB = Object.fromEntries(runB.results.map(r => [mapKey(r), r]));
        const allKeys = [...new Set([...Object.keys(mapA), ...Object.keys(mapB)])].sort();

        allKeys.forEach(key => {
            const a = mapA[key];
            const b = mapB[key];
            if (!a || !b) return; // Skip als niet in beide runs

            const color = this.formatColors[a.format] || { bg: 'rgba(128,128,128,0.7)' };
            const diff = (valA, valB) => {
                if (valA === 0) return '—';
                const pct = ((valB - valA) / valA * 100);
                const cls = pct < 0 ? 'text-success' : pct > 0 ? 'text-danger' : 'text-muted';
                const sign = pct > 0 ? '+' : '';
                return `<span class="${cls}">${sign}${pct.toFixed(1)}%</span>`;
            };

            const row = document.createElement('tr');
            row.innerHTML = `
                <td><span class="format-badge" style="background:${color.bg}">${a.format}</span></td>
                <td>${this.capitalize(a.payloadSizeLabel)}</td>
                <td>${a.serializeTimeMs.mean.toFixed(4)}</td>
                <td>${b.serializeTimeMs.mean.toFixed(4)}</td>
                <td>${diff(a.serializeTimeMs.mean, b.serializeTimeMs.mean)}</td>
                <td>${a.roundTripTimeMs.mean.toFixed(4)}</td>
                <td>${b.roundTripTimeMs.mean.toFixed(4)}</td>
                <td>${diff(a.roundTripTimeMs.mean, b.roundTripTimeMs.mean)}</td>
            `;
            tbody.appendChild(row);
        });
    },

    closeCompare() {
        document.getElementById('compare-section').classList.add('d-none');
        if (this.currentRun) {
            document.getElementById('results-section').classList.remove('d-none');
        } else {
            document.getElementById('welcome-section').classList.remove('d-none');
        }
        this.compareRunA = null;
        this.compareRunB = null;
    },
};
