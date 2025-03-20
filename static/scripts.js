document.addEventListener("DOMContentLoaded", function () {
    fetchComponent("navbar-placeholder", "/navbar");
    fetchComponent("footer-placeholder", "/footer");

    if (window.location.pathname.includes("data")) {
        loadCategories();
        initializeChart();
        setTimeout(() => {
            loadMetrics("btc");
            setTimeout(() => loadChartData("btc", "Close"), 300);
        }, 300);
    }
});

function fetchComponent(elementId, url) {
    fetch(url)
        .then(res => res.text())
        .then(html => document.getElementById(elementId).innerHTML = html)
        .catch(err => console.error(`Error loading ${elementId}:`, err));
}

let chart;
function initializeChart() {
    const ctx = document.getElementById("dataChart").getContext("2d");
    chart = new Chart(ctx, {
        type: "line",
        data: { labels: [], datasets: [{ data: [], borderColor: "#f7931a", borderWidth: 1, pointRadius: 0, fill: true, backgroundColor: "rgba(247,147,26,0.2)" }] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: "rgba(200,200,200,0.3)", drawBorder: false } }
            },
            plugins: { legend: { display: false }, tooltip: { enabled: true } },
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