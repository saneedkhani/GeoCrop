(function () {
    const stateSelect = document.getElementById('filter-state');
    const regionSelect = document.getElementById('filter-region');
    const cropSelect = document.getElementById('filter-crop');
    const clearBtn = document.getElementById('clear-filters');
    const breakdownBody = document.getElementById('breakdown-body');
    const cropChart = document.getElementById('crop-chart');

    function buildQuery() {
        const params = new URLSearchParams();
        if (stateSelect.value) params.set('state', stateSelect.value);
        if (regionSelect.value) params.set('region', regionSelect.value);
        if (cropSelect.value) params.set('crop_type', cropSelect.value);
        return params.toString();
    }

    function renderBreakdown(rows) {
        breakdownBody.innerHTML = '';

        if (rows.length === 0) {
            breakdownBody.innerHTML =
                '<tr class="no-data-row"><td colspan="4">No fields match the selected filters.</td></tr>';
            return;
        }

        rows.forEach(function (row) {
            const color = CROP_COLORS[row.crop_type] || '#999999';
            const tr = document.createElement('tr');
            tr.innerHTML =
                '<td><span class="crop-swatch" style="background:' + color + '"></span>' + row.crop_type + '</td>' +
                '<td>' + row.area.toLocaleString() + '</td>' +
                '<td>' + row.avg_yield.toLocaleString() + '</td>' +
                '<td>' + row.pct_of_total_area + '%</td>';
            breakdownBody.appendChild(tr);
        });
    }

    function renderChart(rows) {
        if (!cropChart) return;
        cropChart.innerHTML = '';

        if (rows.length === 0) {
            cropChart.innerHTML = '<div class="chart-empty">No fields match the selected filters.</div>';
            return;
        }

        // Largest share first so the chart reads top-to-bottom by importance.
        const sorted = rows.slice().sort(function (a, b) { return b.pct_of_total_area - a.pct_of_total_area; });

        sorted.forEach(function (row) {
            const color = CROP_COLORS[row.crop_type] || '#999999';
            const pct = Math.max(row.pct_of_total_area, 0);

            const line = document.createElement('div');
            line.className = 'chart-row';
            line.innerHTML =
                '<span class="chart-row-label"><span class="crop-swatch" style="background:' + color + '"></span>' + row.crop_type + '</span>' +
                '<span class="chart-row-track"><span class="chart-row-fill" style="width:' + pct + '%; background:' + color + '"></span></span>' +
                '<span class="chart-row-value">' + pct + '%</span>';
            cropChart.appendChild(line);
        });
    }

    function loadStats() {
        const query = buildQuery();
        const url = DASHBOARD_STATS_URL + (query ? '?' + query : '');

        fetch(url)
            .then(function (res) { return res.json(); })
            .then(function (stats) {
                document.getElementById('stat-crop-types').textContent = stats.total_crop_types;
                document.getElementById('stat-area').textContent = stats.total_area.toLocaleString();
                document.getElementById('stat-yield').textContent = stats.avg_yield.toLocaleString();
                renderBreakdown(stats.crop_breakdown);
                renderChart(stats.crop_breakdown);
            })
            .catch(function (err) {
                console.error('Failed to load dashboard stats:', err);
            });
    }

    stateSelect.addEventListener('change', loadStats);
    regionSelect.addEventListener('change', loadStats);
    cropSelect.addEventListener('change', loadStats);

    clearBtn.addEventListener('click', function () {
        stateSelect.value = '';
        regionSelect.value = '';
        cropSelect.value = '';
        loadStats();
    });

    loadStats();
})();
