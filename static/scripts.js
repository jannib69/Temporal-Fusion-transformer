document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM fully loaded.");

    // Load navbar and footer if placeholders exist
    fetchComponent("navbar-placeholder", "/navbar");
    fetchComponent("footer-placeholder", "/footer");

    if (window.location.pathname.includes("data")) {
        console.log("Data page detected. Loading categories...");
        loadCategories();
        setTimeout(() => loadMetrics("btc"), 300);
    }

    initializeChart();
});

// **Function to Fetch Navbar/Footer**
function fetchComponent(elementId, url) {
    const placeholder = document.getElementById(elementId);
    if (!placeholder) return;

    fetch(url)
        .then(response => response.text())
        .then(data => {
            placeholder.innerHTML = data;
            console.log(`${elementId} loaded.`);
        })
        .catch(error => console.error(`Error loading ${elementId}:`, error));
}

// **Initialize Empty Chart**
let chart = null;
function initializeChart() {
    console.log("Initializing empty chart...");
    const ctx = document.getElementById("dataChart").getContext("2d");

    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Ni podatkov",
                data: [],
                borderColor: "#f7931a",
                borderWidth: 1, // **Thin line**
                pointRadius: 0, // **Removes points on the line**
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true },
                tooltip: { enabled: true }
            },
            elements: {
                line: { tension: 0.2 }, // **Smoother line**
            }
        }
    });
}

// **Load Categories**
function loadCategories() {
    console.log("Loading categories...");

    const categoriesDiv = document.getElementById("categories");

    if (!categoriesDiv) {
        console.error("Categories container not found.");
        return;
    }

    const categories = ["btc", "bea", "fred", "btc-etf"];

    categoriesDiv.innerHTML = categories.map(category => `
        <button class="btn btn-outline-dark mx-2" onclick="loadMetrics('${category}')">${category.toUpperCase()}</button>
    `).join("");

    console.log("Categories loaded.");
}

// **Load Metrics**
function loadMetrics(category) {
    console.log(`Fetching metrics for category: ${category}`);

    const metricsList = document.getElementById("metrics-list");

    if (!metricsList) {
        console.error("Metrics list container not found.");
        return;
    }

    metricsList.innerHTML = `<p class="text-center text-secondary">Loading metrics...</p>`;

    fetch(`/get_metrics/${category}`)
        .then(response => response.json())
        .then(data => {
            console.log(`Metrics received for ${category}:`, data);

            if (data.error || !Array.isArray(data.metrics)) {
                throw new Error(data.error || "Invalid metrics format.");
            }

            // **Check if all metrics are displayed**
            console.log(`Total metrics received: ${data.metrics.length}`);

            metricsList.innerHTML = data.metrics.map(metric => `
                <button class="list-group-item list-group-item-action"
                        onclick="loadChartData('${category}', '${metric}')">${metric}</button>
            `).join("");

            console.log(`Metrics loaded for ${category}`);
        })
        .catch(error => {
            console.error(`Error fetching metrics for ${category}:`, error);
            metricsList.innerHTML = `<p class="text-danger">Error loading metrics.</p>`;
        });
}

// **Load Chart Data**
function loadChartData(category, metric) {
    console.log(`Fetching chart data for ${category} - ${metric}`);

    const loadingDiv = document.getElementById("loading");
    const errorMessage = document.getElementById("error-message");

    // Show loading spinner
    loadingDiv.style.display = "block";
    errorMessage.style.display = "none";

    fetch(`/get_chart_data?category=${category}&metric=${metric}`)
        .then(response => response.json())
        .then(data => {
            console.log(`Chart data received for ${metric}:`, data);

            if (!data.dates || !data.values || data.values.length === 0) {
                throw new Error("No data available for this metric.");
            }

            loadingDiv.style.display = "none";

            // **Update Chart Dynamically**
            chart.data.labels = data.dates;
            chart.data.datasets[0].label = metric;
            chart.data.datasets[0].data = data.values;
            chart.update();

            updateTable(data);
        })
        .catch(error => {
            console.error(`Error loading chart data for ${metric}:`, error);

            loadingDiv.style.display = "none";

            errorMessage.innerText = "Napaka pri nalaganju podatkov.";
            errorMessage.style.display = "block";
        });
}

// **Update Data Table**
function updateTable(data) {
    console.log("Updating data table...");

    const tbody = document.querySelector("#data-table tbody");

    if (!tbody) {
        console.error("Data table not found.");
        return;
    }

    tbody.innerHTML = data.dates.map((date, i) => `
        <tr><td>${date}</td><td>${data.values[i]}</td></tr>
    `).join("");

    console.log("Data table updated.");
}

document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM fully loaded.");

    // Load Navbar and Footer
    fetchComponent("navbar-placeholder", "/navbar");
    fetchComponent("footer-placeholder", "/footer");

    // Show loading spinner
    const loadingDiv = document.getElementById("loading");
    const dashboardContent = document.getElementById("dashboard-content");

    // Fetch data immediately when page loads
    console.log("Requesting data load...");
    fetch("/load_data")
        .then(response => response.json())
        .then(data => {
            console.log("Data loaded:", data.status);

            // Hide spinner and show dashboard content
            loadingDiv.style.display = "none";
            dashboardContent.style.display = "block";

            // Load categories and default metrics
            loadCategories();
            setTimeout(() => loadMetrics("btc"), 300);
        })
        .catch(error => {
            console.error("Error loading data:", error);
            loadingDiv.innerHTML = "<p class='text-danger'>Napaka pri nalaganju podatkov.</p>";
        });
});