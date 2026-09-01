(function () {
    const map = L.map('map', { zoomControl: true }).setView([39.5, -98.35], 4);

    // Layer 1: OpenStreetMap street base layer
    const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });

    // Layer 2: Esri World Imagery satellite base layer
    const satelliteLayer = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
            maxZoom: 18,
            attribution: 'Tiles &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics'
        }
    );

    streetLayer.addTo(map);

    // collapsed: true -> shows just the layers icon; expands on hover/click
    L.control.layers(
        { 'Street Map': streetLayer, 'Satellite': satelliteLayer },
        {},
        { position: 'topright', collapsed: true }
    ).addTo(map);

    let geoLayer = null;
    let boundaryLayer = null;

    const countrySelect = document.getElementById('filter-country');
    const stateSelect = document.getElementById('filter-state');
    const cropSelect = document.getElementById('filter-crop');
    const clearBtn = document.getElementById('clear-filters');
    const noResultsEl = document.getElementById('no-results');
    const legendEl = document.getElementById('map-legend');

    // Public US states boundary GeoJSON, used to highlight the selected
    // country/state on the map (separate from the field polygons layer).
    const US_STATES_URL =
        'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json';

    function boundaryStyle(feature) {
        const country = countrySelect.value;
        const state = stateSelect.value;
        const stateName = feature.properties.name;

        if (state) {
            if (stateName === state) {
                return { color: '#f2b134', weight: 3, fillColor: '#f2b134', fillOpacity: 0.28 };
            }
            return { color: 'transparent', weight: 0, fillOpacity: 0 };
        }

        if (country) {
            // No specific state chosen -> highlight the whole country (all states).
            return { color: '#2f6f9e', weight: 1.3, fillColor: '#2f6f9e', fillOpacity: 0.12 };
        }

        return { color: 'transparent', weight: 0, fillOpacity: 0 };
    }

    function refreshBoundaryStyle() {
        if (!boundaryLayer) return;
        boundaryLayer.setStyle(boundaryStyle);

        // If a specific state is highlighted, zoom to it.
        const state = stateSelect.value;
        if (state) {
            let matched = null;
            boundaryLayer.eachLayer(function (layer) {
                if (layer.feature.properties.name === state) matched = layer;
            });
            if (matched) {
                map.fitBounds(matched.getBounds(), { maxZoom: 7, padding: [20, 20] });
            }
        } else if (countrySelect.value) {
            map.fitBounds(boundaryLayer.getBounds(), { maxZoom: 5, padding: [10, 10] });
        }
    }

    fetch(US_STATES_URL)
        .then(function (res) { return res.json(); })
        .then(function (statesGeoJson) {
            boundaryLayer = L.geoJSON(statesGeoJson, { style: boundaryStyle }).addTo(map);
            boundaryLayer.bringToBack();
            refreshBoundaryStyle();
        })
        .catch(function (err) {
            console.error('Failed to load state boundaries:', err);
        });

    function buildQuery() {
        const params = new URLSearchParams();
        if (countrySelect.value) params.set('country', countrySelect.value);
        if (stateSelect.value) params.set('state', stateSelect.value);
        if (cropSelect.value) params.set('crop_type', cropSelect.value);
        return params.toString();
    }

    function popupHtml(props) {
        return (
            '<div class="field-popup">' +
            '<h4>' + props.name + '</h4>' +
            '<table>' +
            '<tr><td class="label">Crop type</td><td>' + props.crop_type + '</td></tr>' +
            '<tr><td class="label">State</td><td>' + props.state + '</td></tr>' +
            '<tr><td class="label">Area</td><td>' + props.area + ' acres</td></tr>' +
            '<tr><td class="label">Yield</td><td>' + props.yield + '</td></tr>' +
            '<tr><td class="label">Confidence</td><td>' + Math.round(props.confidence * 100) + '%</td></tr>' +
            '</table>' +
            '</div>'
        );
    }

    function renderLegend(fields) {
        const seen = new Set();
        legendEl.innerHTML = '<div class="legend-title">Crop Types</div>';
        fields.forEach(function (f) {
            if (seen.has(f.properties.crop_type)) return;
            seen.add(f.properties.crop_type);
            const item = document.createElement('div');
            item.className = 'legend-item';
            item.innerHTML =
                '<span class="legend-swatch" style="background:' + f.properties.color + '"></span>' +
                f.properties.crop_type;
            legendEl.appendChild(item);
        });
        if (seen.size === 0) {
            const empty = document.createElement('div');
            empty.className = 'legend-item';
            empty.textContent = 'No fields shown';
            legendEl.appendChild(empty);
        }
    }

    function updateStats(stats) {
        document.getElementById('stat-fields').textContent = stats.total_fields;
        document.getElementById('stat-crop-types').textContent = stats.total_crop_types;
        document.getElementById('stat-area').textContent = stats.total_area.toLocaleString();
        document.getElementById('stat-yield').textContent = stats.avg_yield.toLocaleString();
    }

    function loadFields() {
        const query = buildQuery();
        const url = FIELD_DATA_URL + (query ? '?' + query : '');

        refreshBoundaryStyle();

        fetch(url)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (geoLayer) {
                    map.removeLayer(geoLayer);
                    geoLayer = null;
                }

                const features = data.geojson.features;
                noResultsEl.style.display = features.length === 0 ? 'block' : 'none';

                if (features.length > 0) {
                    geoLayer = L.geoJSON(data.geojson, {
                        style: function (feature) {
                            return {
                                color: feature.properties.color,
                                weight: 2,
                                fillColor: feature.properties.color,
                                fillOpacity: 0.55
                            };
                        },
                        onEachFeature: function (feature, layer) {
                            layer.bindPopup(popupHtml(feature.properties));
                            layer.on('mouseover', function () {
                                layer.setStyle({ weight: 4, fillOpacity: 0.8 });
                            });
                            layer.on('mouseout', function () {
                                geoLayer.resetStyle(layer);
                            });
                        }
                    }).addTo(map);

                    // Only auto-fit to the fields themselves when no country/state
                    // boundary highlight is driving the view.
                    if (!countrySelect.value && !stateSelect.value) {
                        map.fitBounds(geoLayer.getBounds(), { maxZoom: 6, padding: [20, 20] });
                    }
                }

                renderLegend(features);
                updateStats(data.stats);
            })
            .catch(function (err) {
                console.error('Failed to load field data:', err);
            });
    }

    countrySelect.addEventListener('change', loadFields);
    stateSelect.addEventListener('change', loadFields);
    cropSelect.addEventListener('change', loadFields);

    clearBtn.addEventListener('click', function () {
        countrySelect.value = '';
        stateSelect.value = '';
        cropSelect.value = '';
        loadFields();
    });

    loadFields();
})();