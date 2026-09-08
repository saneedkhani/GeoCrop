document.addEventListener("DOMContentLoaded", function () {
    
    // ---------- 1. Color Palette Dictionary ----------
    const CROP_COLORS = {
        "Wheat": "#ef4444",
        "Maize": "#f59e0b",
        "Soybeans": "#0284c7",
        "Cotton": "#facc15",
        "Grass": "#10b981",
        "Barley": "#8b5cf6",
        "Other": "#94a3b8"
    };

    // ---------- 2. Leaflet Map Engine Setup ----------
    // Centered around Multan, Pakistan agricultural zone
    const map = L.map('gisMap', {
        center: [30.1978, 71.4697],
        zoom: 13,
        zoomControl: false
    });

    L.control.zoom({ position: 'bottomleft' }).addTo(map);

    // Free Satellite Imagery (Esri World Imagery)
    const esriSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 18
    }).addTo(map);

    // Dark Boundaries / Labels overlay
    const cartoLabels = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
        maxZoom: 18
    }).addTo(map);

    // ---------- 3. Mock GeoJSON Dataset ----------
    // Ready to be replaced by Django REST API: fetch('/api/v1/fields/')
    const mockFieldData = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": "F-101",
                    "name": "Field A1",
                    "crop": "Wheat",
                    "area_ha": 6.4,
                    "confidence": "96%",
                    "yield_est": "58 bu/ac",
                    "rotation": {"2024": "Corn", "2025": "Soybean", "2026": "Wheat"}
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[71.450, 30.200], [71.465, 30.205], [71.460, 30.190], [71.448, 30.192], [71.450, 30.200]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": "F-102",
                    "name": "Field B2",
                    "crop": "Maize",
                    "area_ha": 4.2,
                    "confidence": "92%",
                    "yield_est": "172 bu/ac",
                    "rotation": {"2024": "Wheat", "2025": "Wheat", "2026": "Maize"}
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[71.468, 30.206], [71.482, 30.210], [71.480, 30.195], [71.466, 30.194], [71.468, 30.206]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": "F-103",
                    "name": "Field C3",
                    "crop": "Cotton",
                    "area_ha": 8.1,
                    "confidence": "89%",
                    "yield_est": "840 lbs/ac",
                    "rotation": {"2024": "Cotton", "2025": "Wheat", "2026": "Cotton"}
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[71.452, 30.188], [71.464, 30.189], [71.462, 30.175], [71.450, 30.176], [71.452, 30.188]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "id": "F-104",
                    "name": "Field D4",
                    "crop": "Soybeans",
                    "area_ha": 7.7,
                    "confidence": "94%",
                    "yield_est": "52 bu/ac",
                    "rotation": {"2024": "Wheat", "2025": "Corn", "2026": "Soybeans"}
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[71.467, 30.192], [71.485, 30.193], [71.482, 30.180], [71.465, 30.181], [71.467, 30.192]]]
                }
            }
        ]
    };

    let geoJsonLayer = null;
    let activeFilterCrop = "all";
    let ndviChartInstance = null;

    // Layer Style Function
    function getFeatureStyle(feature) {
        const crop = feature.properties.crop;
        const color = CROP_COLORS[crop] || "#94a3b8";
        
        return {
            fillColor: color,
            weight: 2,
            opacity: 0.9,
            color: '#ffffff',
            fillOpacity: 0.55
        };
    }

    // ---------- 4. Sidebar Ranking Renderer ----------
    function updateCropRankingSidebar() {
        const rankingContainer = document.getElementById("cropRankingList");
        rankingContainer.innerHTML = "";

        const cropTotals = {};
        mockFieldData.features.forEach(f => {
            const crop = f.properties.crop;
            const area = f.properties.area_ha;
            if (activeFilterCrop === "all" || activeFilterCrop === crop) {
                cropTotals[crop] = (cropTotals[crop] || 0) + area;
            }
        });

        Object.entries(cropTotals).forEach(([crop, area]) => {
            const color = CROP_COLORS[crop] || "#94a3b8";
            const row = document.createElement("div");
            row.className = "ranking-row";
            row.innerHTML = `
                <div class="ranking-left">
                    <span class="crop-color-indicator" style="background: ${color}"></span>
                    <span>${crop}</span>
                </div>
                <strong>${area.toFixed(1)} ha</strong>
            `;
            rankingContainer.appendChild(row);
        });
    }

    // ---------- 5. Field Inspector & Open-Meteo Integration ----------
    function inspectField(feature, latlng) {
        const props = feature.properties;
        const card = document.getElementById("fieldInspectorCard");
        card.classList.remove("hidden");

        document.getElementById("inspectorFieldBadge").textContent = props.name;
        document.getElementById("inspectorCropTitle").textContent = props.crop;
        document.getElementById("inspectorArea").textContent = `${props.area_ha} ha`;
        document.getElementById("inspectorConfidence").textContent = props.confidence;
        document.getElementById("inspectorYield").textContent = props.yield_est;

        // Render Crop Rotation Log
        const rotContainer = document.getElementById("rotationTimeline");
        rotContainer.innerHTML = "";
        Object.entries(props.rotation).forEach(([yr, crp]) => {
            const pill = document.createElement("div");
            pill.className = "timeline-pill";
            pill.innerHTML = `<span>${yr}</span><strong>${crp}</strong>`;
            rotContainer.appendChild(pill);
        });

        // Open-Meteo API Fetch for Live Weather
        fetch(`https://api.open-meteo.com/v1/forecast?latitude=${latlng.lat}&longitude=${latlng.lng}&current_weather=true&hourly=soil_temperature_0cm`)
            .then(res => res.json())
            .then(data => {
                if (data.current_weather) {
                    document.getElementById("wmTemp").textContent = data.current_weather.temperature;
                    document.getElementById("wmRain").textContent = data.current_weather.weathercode === 0 ? "0.0" : "0.4";
                    document.getElementById("inspectorMoisture").textContent = "38%";
                }
            })
            .catch(() => {
                document.getElementById("wmTemp").textContent = "31.2";
                document.getElementById("wmRain").textContent = "0.0";
                document.getElementById("inspectorMoisture").textContent = "34%";
            });

        // Render Chart.js NDVI Graph
        renderNdviChart();
    }

    function renderNdviChart() {
        const ctx = document.getElementById('ndviChart').getContext('2d');
        if (ndviChartInstance) ndviChartInstance.destroy();

        ndviChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'],
                datasets: [{
                    label: 'NDVI Index',
                    data: [0.25, 0.45, 0.78, 0.84, 0.62, 0.30],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#94a3b8', font: { size: 10 } } },
                    y: { min: 0, max: 1, ticks: { color: '#94a3b8', font: { size: 10 } } }
                }
            }
        });
    }

    document.getElementById("closeInspectorBtn").addEventListener("click", () => {
        document.getElementById("fieldInspectorCard").classList.add("hidden");
    });

    // ---------- 6. Dropdowns & Lock Feature Modals ----------
    function setupDropdownToggle(btnId, menuId) {
        const btn = document.getElementById(btnId);
        const menu = document.getElementById(menuId);

        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            document.querySelectorAll(".dropdown-menu").forEach(m => {
                if (m !== menu) m.classList.remove("show");
            });
            menu.classList.toggle("show");
        });
    }

    setupDropdownToggle("layerDropdownBtn", "layerMenu");
    setupDropdownToggle("cropDropdownBtn", "cropMenu");
    setupDropdownToggle("yearDropdownBtn", "yearMenu");
    setupDropdownToggle("seasonDropdownBtn", "seasonMenu");

    document.addEventListener("click", () => {
        document.querySelectorAll(".dropdown-menu").forEach(m => m.classList.remove("show"));
    });

    // Crop Selection Filter Click
    document.querySelectorAll(".crop-pill").forEach(pill => {
        pill.addEventListener("click", function () {
            document.querySelectorAll(".crop-pill").forEach(p => p.classList.remove("active"));
            this.classList.add("active");
            activeFilterCrop = this.dataset.crop;
            document.getElementById("selectedCropText").textContent = activeFilterCrop === "all" ? "All crops" : activeFilterCrop;
            renderVectorPolygons();
        });
    });

    // Modal Trigger for Locked Premium Features
    document.querySelectorAll(".menu-option.locked").forEach(opt => {
        opt.addEventListener("click", function () {
            const featureName = this.dataset.lockedFeature;
            document.getElementById("lockedFeatureTitle").textContent = `Unlock ${featureName}`;
            document.getElementById("lockedModal").classList.remove("hidden");
        });
    });

    document.getElementById("getProBtn").addEventListener("click", function () {
        document.getElementById("lockedFeatureTitle").textContent = "Export Custom GIS Report";
        document.getElementById("lockedModal").classList.remove("hidden");
    });

    document.getElementById("closeModalBtn").addEventListener("click", () => {
        document.getElementById("lockedModal").classList.add("hidden");
    });

    // Initial Map Render
    renderVectorPolygons();
});



// Fetch real fields from Django API instead of hardcoded data
function renderVectorPolygons() {
    if (geoJsonLayer) {
        map.removeLayer(geoJsonLayer);
    }

    const year = document.getElementById("selectedYearText").textContent.trim();
    const season = document.getElementById("selectedSeasonText").textContent.replace("Season ", "").trim();

    fetch(`/api/v1/fields/?crop=${activeFilterCrop}&year=${year}&season=${season}`)
        .then(response => response.json())
        .then(data => {
            geoJsonLayer = L.geoJSON(data, {
                style: getFeatureStyle,
                onEachFeature: function (feature, layer) {
                    layer.bindTooltip(`
                        <div style="font-family: sans-serif; padding: 2px 4px;">
                            <strong>${feature.properties.name}</strong><br/>
                            Crop: ${feature.properties.crop}<br/>
                            Size: ${feature.properties.area_ha} ha
                        </div>
                    `, { sticky: true });

                    layer.on('click', function (e) {
                        inspectField(feature, e.latlng);
                    });
                }
            }).addTo(map);

            updateCropRankingSidebar(data);
        })
        .catch(err => console.error("Error loading GIS fields from Django API:", err));
}