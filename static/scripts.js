document.addEventListener("DOMContentLoaded", async function () {
    fetchComponent("navbar-placeholder", "/navbar");
    fetchComponent("footer-placeholder", "/footer");

    const path = window.location.pathname;
    console.log(`Current path: ${path}`);

    if (path.includes("data")) {
        console.log("Loading Data Page...");
        loadCategories();
        initializeChart();
        setTimeout(() => {
            loadMetrics("btc");
            setTimeout(() => loadChartData("btc", "Close"), 300);
        }, 300);
    } else if (path.includes("home")) {
        console.log("Loading Prediction Page...");
        await fetchPredictionData();
    } else {
        console.log("Home Page - No Prediction Loaded.");
    }
});

function fetchComponent(elementId, url) {
    fetch(url)
        .then(res => res.text())
        .then(html => document.getElementById(elementId).innerHTML = html)
        .catch(err => console.error(`Napaka pri nalaganju komponente ${elementId}:`, err));
}

// ======================
// === DATA SECTION ====
// ======================

let chart;
function initializeChart() {
    const ctx = document.getElementById("dataChart").getContext("2d");
    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                data: [],
                borderColor: "#f7931a",
                borderWidth: 1,
                pointRadius: 0,
                fill: true,
                backgroundColor: "rgba(247,147,26,0.2)"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: "rgba(200,200,200,0.3)", drawBorder: false } }
            },
            plugins: {
                legend: { display: false },
                tooltip: { enabled: true }
            },
            elements: { line: { tension: 0.3 } }
        }
    });
}

function loadCategories() {
    const categories = ["indicators", "btc", "bea", "fred", "btc-etf"];
    document.getElementById("categories").innerHTML = categories.map(cat => `
        <button class="btn btn-outline-dark mx-2" onclick="loadMetrics('${cat}')">${cat.toUpperCase()}</button>
    `).join("");
}

function loadMetrics(category) {
    fetch(`/get_metrics/${category}`)
        .then(res => res.json())
        .then(data => {
            const metricsList = document.getElementById("metrics-list");
            metricsList.innerHTML = data.metrics.map(metric => `
                <button class="list-group-item list-group-item-action" onclick="loadChartData('${category}', '${metric}')">${metric}</button>
            `).join("");
        })
        .catch(() => {
            document.getElementById("metrics-list").innerHTML = `<p class="text-danger">Napaka pri nalaganju metrik.</p>`;
        });
}

function loadChartData(category, metric) {
    showLoading();
    fetch(`/get_chart_data?category=${category}&metric=${metric}`)
        .then(res => res.json())
        .then(data => {
            hideLoading();
            if (data.dates && data.values) {
                chart.data.labels = data.dates;
                chart.data.datasets[0].data = data.values;
                chart.update();
                updateTable(data);
                document.getElementById("chart-title").innerText = `Graf - ${category.toUpperCase()} - ${metric}`;
                updateDataSource(category);
            }
        })
        .catch(() => showError());
}

function updateTable(data) {
    const tbody = document.querySelector("#data-table tbody");
    tbody.innerHTML = data.dates.map((date, i) => `<tr><td>${date}</td><td>${data.values[i]}</td></tr>`).join("");
}

function showLoading() {
    document.getElementById("loading").style.display = "block";
    document.getElementById("error-message").style.display = "none";
}

function hideLoading() {
    document.getElementById("loading").style.display = "none";
}

function showError() {
    document.getElementById("error-message").innerText = "Napaka pri nalaganju podatkov.";
    document.getElementById("error-message").style.display = "block";
}

function updateDataSource(category) {
    const sources = {
        "btc": "Vir: <a href='https://blockchain.com' target='_blank'>Blockchain.com</a>",
        "btc-etf": "Vir: <a href='https://www.bloomberg.com' target='_blank'>Bloomberg, BTC ETF podatki</a>",
        "bea": "Vir: <a href='https://www.bea.gov' target='_blank'>Bureau of Economic Analysis (BEA)</a>",
        "fred": "Vir: <a href='https://fred.stlouisfed.org' target='_blank'>FRED</a>",
        "indicators": "Vir: Lastni indikatorji"
    };
    document.getElementById("data-source").innerHTML = sources[category] || "";
}

// ==============================
// === TFT PREDICTION SECTION ===
// ==============================

async function fetchPredictionData() {
    const maxEncoderLength = 120;
    const maxPredictionLength = 31;

    try {
        const response = await fetch(`/predict_and_plot?max_encoder_length=${maxEncoderLength}&max_prediction_length=${maxPredictionLength}`);
        const data = await response.json();

        if (!data.historical || !data.predicted) {
            console.error("Napaka: Neveljavni podatki prejeti.");
            return;
        }
        const mainContent = document.getElementById("main-content");
        if (mainContent) {
            document.getElementById("loading").style.display = "none";
            mainContent.style.display = "block";
        }

        document.getElementById("loading").style.display = "none";
        document.getElementById("main-content").style.display = "block";

        renderChart(data.historical, data.predicted);

    } catch (error) {
        console.error("Napaka pri pridobivanju napovedi:", error);
        document.getElementById("loading").style.display = "none";
        showError();
    }
}

function renderChart(historicalData, predictedData) {
    const ctx = document.getElementById("predictionChart").getContext("2d");

    // Filter and process historical data
    const filteredHistoricalData = historicalData.filter(d => d.Close !== null);
    const historicalDates = filteredHistoricalData.map(d => new Date(d.Date));
    const historicalPrices = filteredHistoricalData.map(d => d.Close);

    // Filter and process predicted data
    const filteredPredictedData = predictedData.filter(d => d.Predicted_Median !== null);
    const predictedDates = filteredPredictedData.map(d => new Date(d.Date));
    const predictedMedian = filteredPredictedData.map(d => d.Predicted_Median);
    const lowerBound = filteredPredictedData.map(d => d.Lower_Bound);
    const upperBound = filteredPredictedData.map(d => d.Upper_Bound);

    // Ensure the dates are sorted correctly
    const allDates = [...new Set([...historicalDates, ...predictedDates])].sort((a, b) => a - b);

    // Calculate min/max for y-axis scaling
    const allPrices = [...historicalPrices, ...predictedMedian, ...lowerBound, ...upperBound].filter(v => v != null);
    const minY = Math.min(...allPrices) * 0.98;
    const maxY = Math.max(...allPrices) * 1.02;

    // Destroy old chart instance if exists
    if (window.predictionChartInstance) {
        window.predictionChartInstance.destroy();
    }

    // Initialize new chart
    window.predictionChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels: allDates, // Ensure correct x-axis reference
            datasets: [
                {
                    label: "Pretekle cene",
                    data: historicalDates.map((date, i) => ({ x: date, y: historicalPrices[i] })),
                    borderColor: "black",
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: "Napoved (Median)",
                    data: predictedDates.map((date, i) => ({ x: date, y: predictedMedian[i] })),
                    borderColor: "#f7931a",  // BTC Orange
                    borderWidth: 2.5,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: "Zgornja meja",
                    data: predictedDates.map((date, i) => ({ x: date, y: upperBound[i] })),
                    borderColor: "#f7931a",
                    borderDash: [5, 5],  // Dashed line
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: "Spodnja meja",
                    data: predictedDates.map((date, i) => ({ x: date, y: lowerBound[i] })),
                    borderColor: "#f7931a",
                    borderDash: [5, 5],  // Dashed line
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: { top: 20, bottom: 20 }
            },
            scales: {
                x: {
                    type: "time",
                    time: {
                        unit: "day",
                        tooltipFormat: "yyyy-MM-dd",
                        displayFormats: { day: "yyyy-MM-dd" }
                    },
                    title: { display: true, text: "Datum", font: { size: 14, weight: "bold" } },
                    ticks: { autoSkip: true, maxTicksLimit: 10, maxRotation: 30, minRotation: 30 }
                },
                y: {
                    min: minY,
                    max: maxY,
                    title: { display: true, text: "Cena ($)", font: { size: 14, weight: "bold" } },
                    grid: { drawBorder: false }
                }
            },
            plugins: {
                legend: {
                    position: "top",
                    labels: {
                        usePointStyle: true,
                        pointStyle: "line",
                        font: { size: 13 }
                    }
                },
                tooltip: {
                    mode: "nearest",
                    intersect: false,
                    callbacks: {
                        title: (context) => {
                            const date = context[0].parsed.x;
                            return new Date(date).toLocaleDateString("sl-SI", { year: 'numeric', month: 'long', day: 'numeric' });
                        },
                        label: (context) => {
                            let label = context.dataset.label || "";
                            if (context.raw.y !== null) {
                                label += `: ${context.raw.y.toFixed(2)}`;
                            }
                            return label;
                        }
                    }
                },
                zoom: {
                    pan: {
                        enabled: true,
                        mode: "x",
                        scaleMode: "x",
                        speed: 0.5
                    },
                    zoom: {
                        enabled: true,
                        mode: "x",
                        scaleMode: "x",
                        speed: 0.1
                    }
                }
            }
        }
    });
}