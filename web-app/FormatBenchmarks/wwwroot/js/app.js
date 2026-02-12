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
    uiLanguage: 'en',
    translations: {
        en: {
            cfgTitle: 'Configuration',
            payloadTitle: 'Payload Size',
            parametersTitle: 'Parameters',
            iterationsLabel: 'Iterations',
            warmupLabel: 'Warmup iterations',
            runtimeLanguageTitle: 'Runtime Language',
            compareRunsBtn: 'Compare Runs',
            selectAllBtn: 'Select All',
            selectNoneBtn: 'Select None',
            loadingRunning: '<i class="bi bi-hourglass-split"></i> Running benchmarks...',
            loadingInfo: 'This may take a while depending on the number of iterations.',
            welcomeSubtitle: 'Compare performance across different (binary) message formats.',
            welcomeHelp: 'Select the desired formats and parameters in the configuration panel and click <strong>"Start Benchmark"</strong> to begin.',
            featurePayload: 'Compare serialized payload sizes',
            featureSerializationTitle: 'Serialization',
            featureSerialization: 'Measure (de)serialization speed',
            featureRoundtrip: 'Total serialization cycle',
            featureMemoryTitle: 'Memory',
            featureMemory: 'Peak memory & round-trip analysis',
            featureCompressionTitle: 'Compression',
            featureCompression: 'Gzip & Zstandard comparison',
            featureThroughputTitle: 'Throughput',
            systemInfoTitle: 'System Information',
            payloadSizeFilterLabel: 'Payload size:',
            resultsTableTitle: 'Results Table',
            thSize: 'Size',
            thSerAvg: 'Ser. avg (ms)',
            thDeserAvg: 'Deser. avg (ms)',
            thRtAvg: 'Round-Trip avg (ms)',
            thMemPeak: 'Memory Peak',
            thGzipComp: 'Gzip Compression',
            thThroughput: 'Throughput (msg/s)',
            runHistoryTitle: 'Previous Runs',
            compareHeaderPrefix: 'Run Comparison:',
            closeCompareBtn: 'Close',
            compareDetailsTitle: 'Comparison Details',
            cmpThSize: 'Size',
            compareModalTitle: 'Compare Runs',
            compareRunALabel: 'Run A (baseline)',
            compareRunBLabel: 'Run B (comparison)',
            compareCancelBtn: 'Cancel',
            compareExecuteBtn: 'Compare',
            compareModeCommon: 'Common Results',
            compareModeCombined: 'Combined Results',
            noFormatSelected: 'Select at least one message format.',
            noSizeSelected: 'Select at least one payload size.',
            benchmarkFailed: 'Benchmark execution failed',
            benchmarkError: 'Benchmark error: {message}',
            platform: 'Platform',
            cpu: 'CPU',
            cores: 'Cores',
            iterations: 'Iterations',
            all: 'All',
            chartSerialize: 'Serialization Time (ms)',
            chartDeserialize: 'Deserialization Time (ms)',
            chartRoundTrip: 'Round-Trip Time (ms)',
            chartPayloadSize: 'Payload Size (bytes)',
            chartMemoryPeak: 'Memory Peak (bytes)',
            chartThroughputMsg: 'Throughput (msg/sec)',
            chartThroughputMb: 'Throughput (MB/sec)',
            chartThroughputDeserMsg: 'Deserialization Throughput (msg/sec)',
            chartThroughputDeserMb: 'Deserialization Throughput (MB/sec)',
            chartGzipBytes: 'Gzip Compressed Size (bytes)',
            chartGzipRatio: 'Gzip Compression Ratio (%)',
            chartZstdBytes: 'Zstandard Compressed Size (bytes)',
            chartZstdRatio: 'Zstandard Compression Ratio (%)',
            original: 'Original',
            compressionComparison: 'Compression Comparison (bytes)',
            noResultsExport: 'No results to export.',
            csvExportFailed: 'CSV export failed',
            noPreviousRuns: 'No previous runs yet.',
            running: 'Running...',
            startBenchmark: '<i class="bi bi-play-fill"></i> Start Benchmark',
            needTwoRuns: 'At least 2 runs are required to compare. Run more benchmarks first.',
            compareSelectDifferent: 'Select two different runs to compare.',
            runLabel: 'Run',
            tests: 'tests',
            formats: 'formats',
            sizeSmall: 'Small',
            sizeMedium: 'Medium',
            sizeLarge: 'Large'
        },
        nl: {
            cfgTitle: 'Configuratie',
            payloadTitle: 'Payload Grootte',
            parametersTitle: 'Parameters',
            iterationsLabel: 'Iteraties',
            warmupLabel: 'Warmup iteraties',
            runtimeLanguageTitle: 'Taal / Runtime',
            compareRunsBtn: 'Vergelijk Runs',
            selectAllBtn: 'Alles selecteren',
            selectNoneBtn: 'Niets selecteren',
            loadingRunning: '<i class="bi bi-hourglass-split"></i> Benchmarks worden uitgevoerd...',
            loadingInfo: 'Dit kan even duren afhankelijk van het aantal iteraties.',
            welcomeSubtitle: 'Vergelijk de performantie van verschillende (binary) message formats.',
            welcomeHelp: 'Selecteer de gewenste formats en parameters in het configuratiepaneel en klik op <strong>"Start Benchmark"</strong> om te beginnen.',
            featurePayload: 'Vergelijk geserialiseerde groottes',
            featureSerializationTitle: 'Serialisatie',
            featureSerialization: 'Meet (de)serialisatie snelheid',
            featureRoundtrip: 'Totale serialisatie cyclus',
            featureMemoryTitle: 'Geheugen',
            featureMemory: 'Peak memory & round-trip analyse',
            featureCompressionTitle: 'Compressie',
            featureCompression: 'Gzip & Zstandard vergelijking',
            featureThroughputTitle: 'Doorvoer',
            systemInfoTitle: 'Systeem Informatie',
            payloadSizeFilterLabel: 'Payload grootte:',
            resultsTableTitle: 'Resultaten Tabel',
            thSize: 'Grootte',
            thSerAvg: 'Ser. gem. (ms)',
            thDeserAvg: 'Deser. gem. (ms)',
            thRtAvg: 'Round-Trip gem. (ms)',
            thMemPeak: 'Geheugen Piek',
            thGzipComp: 'Gzip Compressie',
            thThroughput: 'Doorvoer (msg/s)',
            runHistoryTitle: 'Vorige Runs',
            compareHeaderPrefix: 'Run Vergelijking:',
            closeCompareBtn: 'Sluiten',
            compareDetailsTitle: 'Vergelijking Details',
            cmpThSize: 'Grootte',
            compareModalTitle: 'Runs Vergelijken',
            compareRunALabel: 'Run A (basis)',
            compareRunBLabel: 'Run B (vergelijking)',
            compareCancelBtn: 'Annuleren',
            compareExecuteBtn: 'Vergelijken',
            compareModeCommon: 'Gemeenschappelijke Resultaten',
            compareModeCombined: 'Gecombineerde Resultaten',
            noFormatSelected: 'Selecteer minimaal één message format.',
            noSizeSelected: 'Selecteer minimaal één payload grootte.',
            benchmarkFailed: 'Benchmark uitvoering mislukt',
            benchmarkError: 'Benchmark fout: {message}',
            platform: 'Platform',
            cpu: 'CPU',
            cores: 'Cores',
            iterations: 'Iteraties',
            all: 'Alle',
            chartSerialize: 'Serialisatie Tijd (ms)',
            chartDeserialize: 'Deserialisatie Tijd (ms)',
            chartRoundTrip: 'Round-Trip Tijd (ms)',
            chartPayloadSize: 'Payload Grootte (bytes)',
            chartMemoryPeak: 'Geheugen Piek (bytes)',
            chartThroughputMsg: 'Doorvoer (msg/sec)',
            chartThroughputMb: 'Doorvoer (MB/sec)',
            chartThroughputDeserMsg: 'Deserialisatie Doorvoer (msg/sec)',
            chartThroughputDeserMb: 'Deserialisatie Doorvoer (MB/sec)',
            chartGzipBytes: 'Gzip Gecomprimeerde Grootte (bytes)',
            chartGzipRatio: 'Gzip Compressie Ratio (%)',
            chartZstdBytes: 'Zstandard Gecomprimeerde Grootte (bytes)',
            chartZstdRatio: 'Zstandard Compressie Ratio (%)',
            original: 'Origineel',
            compressionComparison: 'Compressie Vergelijking (bytes)',
            noResultsExport: 'Geen resultaten om te exporteren.',
            csvExportFailed: 'CSV export mislukt',
            noPreviousRuns: 'Nog geen vorige runs.',
            running: 'Bezig...',
            startBenchmark: '<i class="bi bi-play-fill"></i> Start Benchmark',
            needTwoRuns: 'Minimaal 2 runs nodig om te vergelijken. Voer eerst meerdere benchmarks uit.',
            compareSelectDifferent: 'Selecteer twee verschillende runs om te vergelijken.',
            runLabel: 'Run',
            tests: 'tests',
            formats: 'formats',
            sizeSmall: 'Klein',
            sizeMedium: 'Middel',
            sizeLarge: 'Groot'
        }
    },

    // Color scheme per format
    formatColors: {
        'JSON':         { bg: 'rgba(243, 156, 18, 0.75)', border: 'rgb(243, 156, 18)' },
        'BSON':         { bg: 'rgba(39, 174, 96, 0.75)',  border: 'rgb(39, 174, 96)' },
        'Protobuf':     { bg: 'rgba(52, 152, 219, 0.75)', border: 'rgb(52, 152, 219)' },
        "Cap'n Proto":  { bg: 'rgba(155, 89, 182, 0.75)', border: 'rgb(155, 89, 182)' },
        'MessagePack':  { bg: 'rgba(231, 76, 60, 0.75)',  border: 'rgb(231, 76, 60)' },
        'Apache Avro':  { bg: 'rgba(26, 188, 156, 0.75)', border: 'rgb(26, 188, 156)' },
        'FlatBuffers':  { bg: 'rgba(241, 196, 15, 0.75)', border: 'rgb(241, 196, 15)' },
    },

    // Comparison state
    compareRunA: null,
    compareRunB: null,
    compareData: null,
    compareSelectedSize: '__all__',

    // ==================== Initialization ====================

    init() {
        document.getElementById('run-btn').addEventListener('click', () => this.runBenchmark());
        document.getElementById('compare-btn')?.addEventListener('click', () => this.openCompareModal());
        document.getElementById('ui-language')?.addEventListener('change', (e) => {
            this.setUiLanguage(e.target.value);
        });

        const savedLanguage = localStorage.getItem('uiLanguage') || 'en';
        this.setUiLanguage(savedLanguage);

        // Enter key in input fields also triggers benchmark
        document.querySelectorAll('#iterations, #warmup').forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.runBenchmark();
            });
        });
    },

    t(key, params = {}) {
        const active = this.translations[this.uiLanguage] || this.translations.en;
        let value = active[key] ?? this.translations.en[key] ?? key;
        Object.entries(params).forEach(([paramKey, paramValue]) => {
            value = value.replace(`{${paramKey}}`, String(paramValue));
        });
        return value;
    },

    setUiLanguage(language) {
        this.uiLanguage = language === 'nl' ? 'nl' : 'en';
        localStorage.setItem('uiLanguage', this.uiLanguage);

        const languageSelect = document.getElementById('ui-language');
        if (languageSelect) languageSelect.value = this.uiLanguage;

        document.documentElement.lang = this.uiLanguage;
        this.applyStaticTranslations();

        if (this.currentRun) {
            this.displayResults(this.currentRun);
        } else {
            this.updateRunHistory();
        }

        if (this.compareRunA && this.compareRunB) {
            this.displayComparison();
        }
    },

    applyStaticTranslations() {
        const textMappings = {
            'cfg-title': 'cfgTitle',
            'payload-title': 'payloadTitle',
            'parameters-title': 'parametersTitle',
            'iterations-label': 'iterationsLabel',
            'warmup-label': 'warmupLabel',
            'runtime-language-title': 'runtimeLanguageTitle',
            'compare-runs-btn': 'compareRunsBtn',
            'select-all-btn': 'selectAllBtn',
            'select-none-btn': 'selectNoneBtn',
            'loading-info': 'loadingInfo',
            'welcome-subtitle': 'welcomeSubtitle',
            'feature-payload': 'featurePayload',
            'feature-serialization-title': 'featureSerializationTitle',
            'feature-serialization': 'featureSerialization',
            'feature-roundtrip': 'featureRoundtrip',
            'feature-memory-title': 'featureMemoryTitle',
            'feature-memory': 'featureMemory',
            'feature-compression-title': 'featureCompressionTitle',
            'feature-compression': 'featureCompression',
            'feature-throughput-title': 'featureThroughputTitle',
            'system-info-title': 'systemInfoTitle',
            'payload-size-filter-label': 'payloadSizeFilterLabel',
            'compare-payload-size-filter-label': 'payloadSizeFilterLabel',
            'results-table-title': 'resultsTableTitle',
            'th-size': 'thSize',
            'th-ser-avg': 'thSerAvg',
            'th-deser-avg': 'thDeserAvg',
            'th-rt-avg': 'thRtAvg',
            'th-mem-peak': 'thMemPeak',
            'th-gzip-comp': 'thGzipComp',
            'th-throughput': 'thThroughput',
            'run-history-title': 'runHistoryTitle',
            'compare-header-prefix': 'compareHeaderPrefix',
            'close-compare-btn': 'closeCompareBtn',
            'compare-details-title': 'compareDetailsTitle',
            'cmp-th-size': 'cmpThSize',
            'compare-modal-title': 'compareModalTitle',
            'compare-run-a-label': 'compareRunALabel',
            'compare-run-b-label': 'compareRunBLabel',
            'compare-cancel-btn': 'compareCancelBtn',
            'compare-execute-btn': 'compareExecuteBtn'
        };

        Object.entries(textMappings).forEach(([id, key]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = this.t(key);
        });

        const loadingRunning = document.getElementById('loading-running');
        if (loadingRunning) loadingRunning.innerHTML = this.t('loadingRunning');

        const welcomeHelp = document.getElementById('welcome-help');
        if (welcomeHelp) welcomeHelp.innerHTML = this.t('welcomeHelp');

        const runButton = document.getElementById('run-btn');
        if (runButton && !runButton.disabled) {
            runButton.innerHTML = this.t('startBenchmark');
        }
    },

    // ==================== Configuration ====================

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

    // ==================== Benchmark Execution ====================

    async runBenchmark() {
        const config = this.getConfig();

        if (config.formats.length === 0) {
            this.showError(this.t('noFormatSelected'));
            return;
        }
        if (config.sizes.length === 0) {
            this.showError(this.t('noSizeSelected'));
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
                throw new Error(run.errorMessage || this.t('benchmarkFailed'));
            }

            this.currentRun = run;
            this.allRuns.push(run);
            this.displayResults(run);
        } catch (error) {
            this.showError(this.t('benchmarkError', { message: error.message }));
            // Show welcome section again if there are no results
            if (!this.currentRun) {
                document.getElementById('welcome-section').classList.remove('d-none');
            }
        } finally {
            this.showLoading(false);
        }
    },

    // ==================== Results Display ====================

    displayResults(run) {
        document.getElementById('results-section').classList.remove('d-none');
        document.getElementById('welcome-section').classList.add('d-none');

        // System information
        const sys = run.systemInfo || {};
        const lang = (sys.language || 'python').toLowerCase();
        const langLabel = lang === 'go' ? 'Go' : 'Python';
        const langBadgeClass = lang === 'go' ? 'bg-info' : 'bg-warning text-dark';
        const versionLabel = lang === 'go'
            ? (sys.goVersion || 'N/A')
            : (sys.pythonVersion || 'N/A');
        document.getElementById('system-info').innerHTML = `
            <span><span class="badge ${langBadgeClass}">${langLabel}</span></span>
            <span><strong>${this.t('platform')}:</strong> ${sys.platform || 'N/A'}</span>
            <span><strong>${langLabel}:</strong> ${versionLabel}</span>
            <span><strong>${this.t('cpu')}:</strong> ${sys.processor || 'N/A'}</span>
            <span><strong>${this.t('cores')}:</strong> ${sys.cpuCount || 'N/A'}</span>
            <span><strong>${this.t('iterations')}:</strong> ${run.config?.iterations || 'N/A'}</span>
        `;

        // Set up size tabs
        const sizeOrder = ['small', 'medium', 'large'];
        const sizes = [...new Set(run.results.map(r => r.payloadSizeLabel))]
            .sort((a, b) => sizeOrder.indexOf(a) - sizeOrder.indexOf(b));
        this.setupSizeTabs(sizes);

        // Show charts for first size
        if (sizes.length > 0) {
            this.switchSizeTab(sizes[0]);
        } else {
            this.createDataTable([]);
        }

        // Update run history
        this.updateRunHistory();
    },

    // ==================== Size Tabs ====================

    setupSizeTabs(sizes) {
        const container = document.getElementById('size-tabs');
        container.innerHTML = '';

        // "All" tab
        const allBtn = document.createElement('button');
        allBtn.className = 'btn btn-outline-primary btn-sm size-tab';
        allBtn.dataset.size = '__all__';
        allBtn.textContent = this.t('all');
        allBtn.addEventListener('click', () => this.switchSizeTab('__all__'));
        container.appendChild(allBtn);

        sizes.forEach((size, i) => {
            const btn = document.createElement('button');
            btn.className = `btn btn-outline-primary btn-sm size-tab ${i === 0 ? 'active' : ''}`;
            btn.dataset.size = size;
            btn.textContent = this.localizeSizeLabel(size);
            btn.addEventListener('click', () => this.switchSizeTab(size));
            container.appendChild(btn);
        });
    },

    switchSizeTab(size) {
        // Update active tab styling
        document.querySelectorAll('.size-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.size === size);
        });

        if (!this.currentRun) return;

        const results = size === '__all__'
            ? this.currentRun.results
            : this.currentRun.results.filter(r => r.payloadSizeLabel === size);

        this.createCharts(results, size === '__all__');
        this.createDataTable(results);
    },

    // ==================== Chart.js Charts ====================

    createCharts(results, isAllSizes = false) {
        this.createBarChart('serialize-chart', this.t('chartSerialize'),
            results, r => r.serializeTimeMs.mean, isAllSizes);
        this.createBarChart('deserialize-chart', this.t('chartDeserialize'),
            results, r => r.deserializeTimeMs.mean, isAllSizes);
        this.createBarChart('roundtrip-chart', this.t('chartRoundTrip'),
            results, r => r.roundTripTimeMs.mean, isAllSizes);
        this.createBarChart('size-chart', this.t('chartPayloadSize'),
            results, r => r.serializedSizeBytes, isAllSizes, true);
        this.createBarChart('memory-chart', this.t('chartMemoryPeak'),
            results, r => r.memoryUsage?.totalPeakBytes || 0, isAllSizes, true);
        this.createCompressionChart('compression-chart', results, isAllSizes);
        this.createBarChart('throughput-chart', this.t('chartThroughputMsg'),
            results, r => r.throughput?.serializeMsgPerSec || 0, isAllSizes, false, 'msg/sec');
        this.createBarChart('throughput-mb-chart', this.t('chartThroughputMb'),
            results, r => r.throughput?.serializeMbPerSec || 0, isAllSizes, false, 'MB/sec');
    },

    createBarChart(canvasId, title, results, valueExtractor, isGrouped = false, isSize = false, unit = null) {
        // Remove existing chart
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const ctx = document.getElementById(canvasId).getContext('2d');

        let chartData;

        if (isGrouped && results.length > 0) {
            // Grouped view: formats on x-axis, sizes as datasets
            chartData = this.buildGroupedChartData(results, valueExtractor);
        } else {
            // Single view: one bar per format
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
            label: this.localizeSizeLabel(size),
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

        // For grouped (all sizes), use only the first size for readability
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
                label: this.t('original'),
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
            ? ` (${this.localizeSizeLabel(targetResults[0]?.payloadSizeLabel || '')})`
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
                        text: `${this.t('compressionComparison')}${sizeLabel}`,
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

    // ==================== Data Table ====================

    createDataTable(results) {
        const tbody = document.getElementById('results-table-body');
        tbody.innerHTML = '';

        // Sort: by size, then by format
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
                <td>${this.localizeSizeLabel(r.payloadSizeLabel)}</td>
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
            this.showError(this.t('noResultsExport'));
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
            this.showError(this.t('noResultsExport'));
            return;
        }
        try {
            const response = await fetch(
                `/api/benchmark/export/${this.currentRun.id}?format=csv`
            );
            if (!response.ok) throw new Error(this.t('csvExportFailed'));
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
            container.innerHTML = `<span class="text-muted">${this.t('noPreviousRuns')}</span>`;
            return;
        }

        container.innerHTML = this.allRuns.map((run, i) => {
            const locale = this.uiLanguage === 'nl' ? 'nl-NL' : 'en-US';
            const time = new Date(run.timestamp).toLocaleTimeString(locale);
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
                        <strong>${this.t('runLabel')} #${i + 1}</strong> — ${time}
                    </div>
                    <div class="text-muted">
                        ${uniqueFormats.length} ${this.t('formats')}, ${run.results.length} ${this.t('tests')}
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
                `<span class="spinner-border spinner-border-sm me-2"></span>${this.t('running')}`;
        } else {
            document.getElementById('run-btn').innerHTML = this.t('startBenchmark');
        }
    },

    showError(msg) {
        const el = document.getElementById('error-alert');
        document.getElementById('error-message').textContent = msg;
        el.classList.remove('d-none');
        // Auto-hide after 10 seconds
        setTimeout(() => el.classList.add('d-none'), 10000);
    },

    hideError() {
        document.getElementById('error-alert').classList.add('d-none');
    },

    capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    },

    localizeSizeLabel(size) {
        const normalized = (size || '').toLowerCase();
        if (normalized === 'small') return this.t('sizeSmall');
        if (normalized === 'medium') return this.t('sizeMedium');
        if (normalized === 'large') return this.t('sizeLarge');
        return this.capitalize(size || '');
    },

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i];
    },

    // ==================== Run Comparison ====================

    openCompareModal() {
        if (this.allRuns.length < 2) {
            this.showError(this.t('needTwoRuns'));
            return;
        }

        const modal = document.getElementById('compare-modal');
        const selectA = document.getElementById('compare-run-a');
        const selectB = document.getElementById('compare-run-b');

        // Fill selects with runs
        const optionsHtml = this.allRuns.map((run, i) => {
            const locale = this.uiLanguage === 'nl' ? 'nl-NL' : 'en-US';
            const time = new Date(run.timestamp).toLocaleTimeString(locale);
            const formats = [...new Set(run.results.map(r => r.format))];
            const lang = (run.systemInfo?.language || 'python').toLowerCase();
            const langLabel = lang === 'go' ? 'Go' : 'Python';
            return `<option value="${i}">${this.t('runLabel')} #${i + 1} [${langLabel}] — ${time} (${formats.length} ${this.t('formats')})</option>`;
        }).join('');

        selectA.innerHTML = optionsHtml;
        selectB.innerHTML = optionsHtml;

        // Default: last two runs
        selectA.value = this.allRuns.length - 2;
        selectB.value = this.allRuns.length - 1;

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    executeCompare() {
        const idxA = parseInt(document.getElementById('compare-run-a').value);
        const idxB = parseInt(document.getElementById('compare-run-b').value);

        if (idxA === idxB) {
            this.showError(this.t('compareSelectDifferent'));
            return;
        }

        this.compareRunA = this.allRuns[idxA];
        this.compareRunB = this.allRuns[idxB];

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('compare-modal'));
        if (modal) modal.hide();

        this.displayComparison();
    },

    displayComparison() {
        const runA = this.compareRunA;
        const runB = this.compareRunB;
        if (!runA || !runB) return;

        // Show comparison section
        document.getElementById('compare-section').classList.remove('d-none');
        document.getElementById('results-section').classList.add('d-none');
        document.getElementById('welcome-section').classList.add('d-none');

        const idxA = this.allRuns.indexOf(runA);
        const idxB = this.allRuns.indexOf(runB);
        const comparison = this.buildComparisonData(runA, runB);
        this.compareData = comparison;
        const modeLabel = comparison.sameLanguage
            ? this.t('compareModeCommon')
            : this.t('compareModeCombined');
        document.getElementById('compare-title').textContent =
            `${this.t('runLabel')} #${idxA + 1} vs ${this.t('runLabel')} #${idxB + 1} (${modeLabel})`;

        const sizeOrder = { small: 0, medium: 1, large: 2 };
        const sizes = [...new Set(comparison.entries.map(entry => entry.payloadSizeLabel))]
            .sort((a, b) => (sizeOrder[a] ?? 99) - (sizeOrder[b] ?? 99));

        this.setupCompareSizeTabs(sizes);

        const preferredSize =
            (this.compareSelectedSize === '__all__' || sizes.includes(this.compareSelectedSize))
                ? this.compareSelectedSize
                : (sizes.includes('small') ? 'small' : (sizes[0] || '__all__'));

        this.switchCompareSizeTab(preferredSize, idxA, idxB);
    },

    setupCompareSizeTabs(sizes) {
        const container = document.getElementById('compare-size-tabs');
        if (!container) return;

        container.innerHTML = '';

        const allBtn = document.createElement('button');
        allBtn.className = 'btn btn-outline-primary btn-sm compare-size-tab';
        allBtn.dataset.size = '__all__';
        allBtn.textContent = this.t('all');
        allBtn.addEventListener('click', () => this.switchCompareSizeTab('__all__'));
        container.appendChild(allBtn);

        sizes.forEach(size => {
            const btn = document.createElement('button');
            btn.className = 'btn btn-outline-primary btn-sm compare-size-tab';
            btn.dataset.size = size;
            btn.textContent = this.localizeSizeLabel(size);
            btn.addEventListener('click', () => this.switchCompareSizeTab(size));
            container.appendChild(btn);
        });
    },

    switchCompareSizeTab(size, idxA = null, idxB = null) {
        document.querySelectorAll('.compare-size-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.size === size);
        });

        this.compareSelectedSize = size;

        if (!this.compareData) return;

        const runAIndex = idxA ?? this.allRuns.indexOf(this.compareRunA);
        const runBIndex = idxB ?? this.allRuns.indexOf(this.compareRunB);
        const entries = this.getFilteredComparisonEntries(this.compareData, size);

        this.createCompareChart('compare-serialize-chart', this.t('chartSerialize'),
            entries, runAIndex, runBIndex, r => r.serializeTimeMs.mean, false, null, size);
        this.createCompareChart('compare-deserialize-chart', this.t('chartDeserialize'),
            entries, runAIndex, runBIndex, r => r.deserializeTimeMs.mean, false, null, size);
        this.createCompareChart('compare-roundtrip-chart', this.t('chartRoundTrip'),
            entries, runAIndex, runBIndex, r => r.roundTripTimeMs.mean, false, null, size);
        this.createCompareChart('compare-throughput-chart', this.t('chartThroughputMsg'),
            entries, runAIndex, runBIndex, r => r.throughput?.serializeMsgPerSec, false, 'msg/sec', size);
        this.createCompareChart('compare-payload-size-chart', this.t('chartPayloadSize'),
            entries, runAIndex, runBIndex, r => r.serializedSizeBytes, true, null, size);
        this.createCompareChart('compare-memory-chart', this.t('chartMemoryPeak'),
            entries, runAIndex, runBIndex, r => r.memoryUsage?.totalPeakBytes, true, null, size);
        this.createCompareChart('compare-gzip-bytes-chart', this.t('chartGzipBytes'),
            entries, runAIndex, runBIndex, r => r.compression?.gzipBytes, true, null, size);
        this.createCompareChart('compare-gzip-ratio-chart', this.t('chartGzipRatio'),
            entries, runAIndex, runBIndex,
            r => Number.isFinite(r.compression?.gzipRatio) ? r.compression.gzipRatio * 100 : null,
            false, '%', size);
        this.createCompareChart('compare-throughput-deser-chart', this.t('chartThroughputDeserMsg'),
            entries, runAIndex, runBIndex, r => r.throughput?.deserializeMsgPerSec, false, 'msg/sec', size);
        this.createCompareChart('compare-throughput-mb-chart', this.t('chartThroughputMb'),
            entries, runAIndex, runBIndex, r => r.throughput?.serializeMbPerSec, false, 'MB/sec', size);
        this.createCompareChart('compare-throughput-deser-mb-chart', this.t('chartThroughputDeserMb'),
            entries, runAIndex, runBIndex, r => r.throughput?.deserializeMbPerSec, false, 'MB/sec', size);

        this.updateCompareZstdCharts(entries, runAIndex, runBIndex, size);

        this.createCompareTable(entries);
    },

    updateCompareZstdCharts(entries, idxA, idxB, selectedSize) {
        const zstdBytesCard = document.getElementById('compare-zstd-bytes-card');
        const zstdRatioCard = document.getElementById('compare-zstd-ratio-card');
        const hasZstd = entries.some(item =>
            (item.a?.compression?.zstdBytes ?? 0) > 0 || (item.b?.compression?.zstdBytes ?? 0) > 0);

        if (!hasZstd) {
            zstdBytesCard?.classList.add('d-none');
            zstdRatioCard?.classList.add('d-none');

            ['compare-zstd-bytes-chart', 'compare-zstd-ratio-chart'].forEach(chartId => {
                if (this.charts[chartId]) {
                    this.charts[chartId].destroy();
                    delete this.charts[chartId];
                }
            });
            return;
        }

        zstdBytesCard?.classList.remove('d-none');
        zstdRatioCard?.classList.remove('d-none');

        this.createCompareChart('compare-zstd-bytes-chart', this.t('chartZstdBytes'),
            entries, idxA, idxB, r => r.compression?.zstdBytes, true, null, selectedSize);
        this.createCompareChart('compare-zstd-ratio-chart', this.t('chartZstdRatio'),
            entries, idxA, idxB,
            r => Number.isFinite(r.compression?.zstdRatio) ? r.compression.zstdRatio * 100 : null,
            false, '%', selectedSize);
    },

    getFilteredComparisonEntries(comparison, size) {
        if (size === '__all__') return comparison.entries;
        return comparison.entries.filter(entry => entry.payloadSizeLabel === size);
    },

    getRunLanguage(run) {
        return (run?.systemInfo?.language || 'python').toLowerCase();
    },

    buildComparisonData(runA, runB) {
        const mapKey = r => `${r.format}|${r.payloadSizeLabel}`;
        const mapA = Object.fromEntries(runA.results.map(r => [mapKey(r), r]));
        const mapB = Object.fromEntries(runB.results.map(r => [mapKey(r), r]));

        const sameLanguage = this.getRunLanguage(runA) === this.getRunLanguage(runB);
        const keys = sameLanguage
            ? Object.keys(mapA).filter(key => key in mapB)
            : [...new Set([...Object.keys(mapA), ...Object.keys(mapB)])];

        const entries = keys
            .map(key => {
                const [format, payloadSizeLabel] = key.split('|');
                return {
                    key,
                    format,
                    payloadSizeLabel,
                    a: mapA[key] || null,
                    b: mapB[key] || null,
                };
            })
            .sort((left, right) => {
                if (left.format === right.format) {
                    const order = { small: 0, medium: 1, large: 2 };
                    const leftOrder = order[(left.payloadSizeLabel || '').toLowerCase()] ?? 99;
                    const rightOrder = order[(right.payloadSizeLabel || '').toLowerCase()] ?? 99;
                    return leftOrder - rightOrder;
                }
                return left.format.localeCompare(right.format);
            });

        return { entries, sameLanguage };
    },

    createCompareChart(canvasId, title, entries, idxA, idxB, valueExtractor, isSize = false, unit = null, selectedSize = '__all__') {
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        const labels = entries.map(item =>
            selectedSize === '__all__'
                ? `${item.format} (${this.localizeSizeLabel(item.payloadSizeLabel)})`
                : item.format);
        const dataA = entries.map(item => {
            if (!item.a) return null;
            const value = valueExtractor(item.a);
            return Number.isFinite(value) ? value : null;
        });
        const dataB = entries.map(item => {
            if (!item.b) return null;
            const value = valueExtractor(item.b);
            return Number.isFinite(value) ? value : null;
        });

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
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
                        text: selectedSize === '__all__'
                            ? title
                            : `${title} (${this.localizeSizeLabel(selectedSize)})`,
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

    createCompareTable(entries) {
        const tbody = document.getElementById('compare-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        const valueCell = (value, formatter) => {
            if (value === null || value === undefined || !Number.isFinite(value)) return '—';
            return formatter(value);
        };

        const diffCell = (valueA, valueB) => {
            if (!Number.isFinite(valueA) || !Number.isFinite(valueB) || valueA === 0) return '—';
            const pct = ((valueB - valueA) / valueA * 100);
            const cls = pct < 0 ? 'text-success' : pct > 0 ? 'text-danger' : 'text-muted';
            const sign = pct > 0 ? '+' : '';
            return `<span class="${cls}">${sign}${pct.toFixed(1)}%</span>`;
        };

        const metricRows = (item) => {
            const a = item.a;
            const b = item.b;
            const hasAnyZstd = (a?.compression?.zstdBytes ?? 0) > 0 || (b?.compression?.zstdBytes ?? 0) > 0;

            const rows = [
                {
                    metric: 'Serialize mean (ms)',
                    a: a?.serializeTimeMs?.mean,
                    b: b?.serializeTimeMs?.mean,
                    fmt: (v) => v.toFixed(4),
                },
                {
                    metric: 'Deserialize mean (ms)',
                    a: a?.deserializeTimeMs?.mean,
                    b: b?.deserializeTimeMs?.mean,
                    fmt: (v) => v.toFixed(4),
                },
                {
                    metric: 'Round-Trip mean (ms)',
                    a: a?.roundTripTimeMs?.mean,
                    b: b?.roundTripTimeMs?.mean,
                    fmt: (v) => v.toFixed(4),
                },
                {
                    metric: 'Payload size (bytes)',
                    a: a?.serializedSizeBytes,
                    b: b?.serializedSizeBytes,
                    fmt: (v) => v.toLocaleString(),
                },
                {
                    metric: 'Memory peak (bytes)',
                    a: a?.memoryUsage?.totalPeakBytes,
                    b: b?.memoryUsage?.totalPeakBytes,
                    fmt: (v) => v.toLocaleString(),
                },
                {
                    metric: 'Compression Gzip (bytes)',
                    a: a?.compression?.gzipBytes,
                    b: b?.compression?.gzipBytes,
                    fmt: (v) => v.toLocaleString(),
                },
                {
                    metric: 'Compression Gzip ratio (%)',
                    a: Number.isFinite(a?.compression?.gzipRatio) ? a.compression.gzipRatio * 100 : null,
                    b: Number.isFinite(b?.compression?.gzipRatio) ? b.compression.gzipRatio * 100 : null,
                    fmt: (v) => `${v.toFixed(1)}%`,
                },
                {
                    metric: 'Throughput serialize (msg/s)',
                    a: a?.throughput?.serializeMsgPerSec,
                    b: b?.throughput?.serializeMsgPerSec,
                    fmt: (v) => v.toLocaleString(undefined, { maximumFractionDigits: 0 }),
                },
                {
                    metric: 'Throughput deserialize (msg/s)',
                    a: a?.throughput?.deserializeMsgPerSec,
                    b: b?.throughput?.deserializeMsgPerSec,
                    fmt: (v) => v.toLocaleString(undefined, { maximumFractionDigits: 0 }),
                },
                {
                    metric: 'Throughput serialize (MB/s)',
                    a: a?.throughput?.serializeMbPerSec,
                    b: b?.throughput?.serializeMbPerSec,
                    fmt: (v) => v.toLocaleString(undefined, { maximumFractionDigits: 2 }),
                },
                {
                    metric: 'Throughput deserialize (MB/s)',
                    a: a?.throughput?.deserializeMbPerSec,
                    b: b?.throughput?.deserializeMbPerSec,
                    fmt: (v) => v.toLocaleString(undefined, { maximumFractionDigits: 2 }),
                },
            ];

            if (hasAnyZstd) {
                rows.push(
                    {
                        metric: 'Compression Zstd (bytes)',
                        a: a?.compression?.zstdBytes,
                        b: b?.compression?.zstdBytes,
                        fmt: (v) => v.toLocaleString(),
                    },
                    {
                        metric: 'Compression Zstd ratio (%)',
                        a: Number.isFinite(a?.compression?.zstdRatio) ? a.compression.zstdRatio * 100 : null,
                        b: Number.isFinite(b?.compression?.zstdRatio) ? b.compression.zstdRatio * 100 : null,
                        fmt: (v) => `${v.toFixed(1)}%`,
                    }
                );
            }

            return rows;
        };

        entries.forEach(item => {
            const a = item.a;
            const color = this.formatColors[item.format] || { bg: 'rgba(128,128,128,0.7)' };

            metricRows(item).forEach(metric => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><span class="format-badge" style="background:${color.bg}">${item.format}</span></td>
                    <td>${this.localizeSizeLabel(item.payloadSizeLabel)}</td>
                    <td>${metric.metric}</td>
                    <td>${valueCell(metric.a, metric.fmt)}</td>
                    <td>${valueCell(metric.b, metric.fmt)}</td>
                    <td>${diffCell(metric.a, metric.b)}</td>
                `;
                tbody.appendChild(row);
            });
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
        this.compareData = null;
        this.compareSelectedSize = '__all__';
    },
};
