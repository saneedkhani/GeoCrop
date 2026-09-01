(function () {
    const stateSelect = document.getElementById('filter-state');
    const regionSelect = document.getElementById('filter-region');
    const cropSelect = document.getElementById('filter-crop');
    const clearBtn = document.getElementById('clear-filters');
    const breakdownBody = document.getElementById('breakdown-body');

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