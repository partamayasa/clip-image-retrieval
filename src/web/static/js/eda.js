/**
 * Multimodal Information Retrieval - Exploratory Data Analysis (EDA) Module
 */

let edaDataCache = null;
let edaTabulator = null;
let chartArticleType = null;
let chartBaseColour = null;
let chartGender = null;
let chartUsage = null;

async function initOrRedrawEdaTable() {
  if (edaTabulator) {
    setTimeout(() => {
      edaTabulator.redraw(true);
      window.dispatchEvent(new Event("resize"));
    }, 50);
    return;
  }

  try {
    if (!edaDataCache) {
      const resp = await fetch("/api/eda-stats");
      edaDataCache = await resp.json();
    }
    const data = edaDataCache;
    const total = data.total_records || 1500;

    // 2. Interactive Charts (ApexCharts - AdminLTE apexcharts.html Pattern)
    // Chart 1: Top 10 Article Type Horizontal Bar Chart
    if (!chartArticleType && data.distribution_articleType) {
      const topArticle = Object.entries(data.distribution_articleType).slice(0, 10);
      const articleCats = topArticle.map(([k, v]) => k);
      const articleCounts = topArticle.map(([k, v]) => v);

      const options1 = {
        series: [{ name: "Products", data: articleCounts }],
        chart: {
          id: "chart-eda-article-type",
          type: "bar",
          height: 330,
          toolbar: { show: false }
        },
        plotOptions: {
          bar: {
            horizontal: true,
            borderRadius: 4,
            barHeight: "65%"
          }
        },
        colors: ["#0d6efd"],
        dataLabels: {
          enabled: true,
          style: { fontSize: "11px", fontWeight: "bold" }
        },
        xaxis: {
          categories: articleCats,
          title: { text: "Number of Products" }
        },
        yaxis: {
          title: { text: "Article Type" }
        },
        tooltip: {
          theme: document.documentElement.getAttribute("data-bs-theme") || "light"
        }
      };
      chartArticleType = new ApexCharts(document.querySelector("#chart-eda-article-type"), options1);
      chartArticleType.render();
    }

    // Chart 2: Top 10 Base Colours Vertical Column Chart
    if (!chartBaseColour && data.distribution_baseColour_top10) {
      const topColours = Object.entries(data.distribution_baseColour_top10).slice(0, 10);
      const colourNames = topColours.map(([k, v]) => k);
      const colourCounts = topColours.map(([k, v]) => v);

      const options2 = {
        series: [{ name: "Products", data: colourCounts }],
        chart: {
          id: "chart-eda-base-colour",
          type: "bar",
          height: 330,
          toolbar: { show: false }
        },
        plotOptions: {
          bar: {
            horizontal: false,
            columnWidth: "55%",
            borderRadius: 4
          }
        },
        colors: ["#475569"],
        dataLabels: {
          enabled: true,
          style: { fontSize: "11px", fontWeight: "bold" }
        },
        xaxis: {
          categories: colourNames,
          labels: { rotate: -45 },
          title: { text: "Base Colour" }
        },
        yaxis: {
          title: { text: "Number of Products" }
        },
        tooltip: {
          theme: document.documentElement.getAttribute("data-bs-theme") || "light"
        }
      };
      chartBaseColour = new ApexCharts(document.querySelector("#chart-eda-base-colour"), options2);
      chartBaseColour.render();
    }

    // Chart 3: Target User Segmentation (Gender) Donut Chart
    if (!chartGender && data.distribution_gender) {
      const genderLabels = Object.keys(data.distribution_gender);
      const genderCounts = Object.values(data.distribution_gender);

      const options3 = {
        series: genderCounts,
        chart: {
          id: "chart-eda-gender",
          type: "donut",
          height: 330
        },
        labels: genderLabels,
        colors: ["#0d6efd", "#d63384", "#6c757d", "#20c997", "#fd7e14"],
        dataLabels: {
          enabled: true,
          formatter: (val) => `${val.toFixed(1)}%`
        },
        plotOptions: {
          pie: {
            donut: {
              size: "65%"
            }
          }
        },
        legend: {
          position: "bottom"
        },
        tooltip: {
          theme: document.documentElement.getAttribute("data-bs-theme") || "light",
          y: {
            formatter: (val) => `${val} Products`
          }
        }
      };
      chartGender = new ApexCharts(document.querySelector("#chart-eda-gender"), options3);
      chartGender.render();
    }

    // Chart 4: Usage Context Horizontal Bar Chart
    if (!chartUsage && data.distribution_usage) {
      const usageLabels = Object.keys(data.distribution_usage);
      const usageCounts = Object.values(data.distribution_usage);

      const options4 = {
        series: [{ name: "Products", data: usageCounts }],
        chart: {
          id: "chart-eda-usage",
          type: "bar",
          height: 330,
          toolbar: { show: false }
        },
        plotOptions: {
          bar: {
            horizontal: true,
            borderRadius: 4,
            barHeight: "65%",
            distributed: true
          }
        },
        colors: ["#6f42c1", "#fd7e14", "#0dcaf0", "#198754", "#ffc107", "#20c997"],
        dataLabels: {
          enabled: true,
          style: { fontSize: "11px", fontWeight: "bold" }
        },
        xaxis: {
          categories: usageLabels,
          title: { text: "Number of Products" }
        },
        yaxis: {
          title: { text: "Usage Context" }
        },
        legend: { show: false },
        tooltip: {
          theme: document.documentElement.getAttribute("data-bs-theme") || "light"
        }
      };
      chartUsage = new ApexCharts(document.querySelector("#chart-eda-usage"), options4);
      chartUsage.render();
    }

    // 3. ArticleType Breakdown Table
    const articleTbody = document.getElementById("edaArticleTableBody");
    if (articleTbody && data.distribution_articleType) {
      articleTbody.innerHTML = Object.entries(data.distribution_articleType)
        .map(([cat, count]) => {
          const pct = ((count / total) * 100).toFixed(1);
          return `
            <tr>
              <td class="text-start ps-3 align-middle text-body">${cat}</td>
              <td class="text-center align-middle text-body">${count}</td>
              <td class="text-center align-middle text-body">${pct}%</td>
            </tr>
          `;
        }).join("");
    }

    // 4. Top 10 Colors Breakdown Table
    const colorTbody = document.getElementById("edaColorTableBody");
    if (colorTbody && data.distribution_baseColour_top10) {
      colorTbody.innerHTML = Object.entries(data.distribution_baseColour_top10)
        .map(([col, count]) => {
          const pct = ((count / total) * 100).toFixed(1);
          return `
            <tr>
              <td class="text-start ps-3 align-middle text-body">${col}</td>
              <td class="text-center align-middle text-body">${count}</td>
              <td class="text-center align-middle text-body">${pct}%</td>
            </tr>
          `;
        }).join("");
    }

    // 5. Tabulator Dataset Sample Table (AdminLTE tables/data.html pattern)
    const samples = data.visual_verification_20_pairs || [];
    edaTabulator = new Tabulator("#eda-tabulator-table", {
      data: samples,
      layout: "fitColumns",
      pagination: true,
      paginationSize: 10,
      paginationSizeSelector: [10, 20],
      movableColumns: true,
      columns: [
        {
          title: "No",
          field: "no",
          width: 55,
          minWidth: 50,
          hozAlign: "center",
          headerHozAlign: "center",
          headerSort: true,
          formatter: (cell) => `<span>${cell.getValue() || cell.getRow().getPosition(true)}</span>`,
        },
        {
          title: "Product ID",
          field: "id",
          width: 105,
          minWidth: 95,
          hozAlign: "center",
          headerHozAlign: "center",
          headerSort: true,
          formatter: (cell) => {
            const row = cell.getRow().getData();
            const nameEscaped = (row.productDisplayName || "").replace(/'/g, "\\'");
            const imgFile = row.image_filename || `${row.id}.jpg`;
            return `
              <div class="py-1 text-center">
                <div class="font-monospace mb-1" style="font-size: 0.95rem;">${row.id}</div>
                <img src="/api/images/${imgFile}" alt="${nameEscaped}" 
                     style="width: 52px; height: 68px; object-fit: contain; background: #ffffff; border-radius: 4px; cursor: pointer; border: 1px solid var(--bs-border-color);" 
                     onclick="openImagePreview('/api/images/${imgFile}', '${nameEscaped}')" />
              </div>
            `;
          },
        },
        {
          title: "Product Display Name",
          field: "productDisplayName",
          minWidth: 190,
          hozAlign: "left",
          headerHozAlign: "left",
          formatter: (cell) => {
            const row = cell.getRow().getData();
            const name = cell.getValue() || "-";
            const nameEscaped = name.replace(/'/g, "\\'");
            return `
              <div class="text-body mb-2" style="font-size: 0.95rem; line-height: 1.45; white-space: normal;">${name}</div>
              <button class="btn btn-sm btn-outline-primary py-1 px-2 rounded" style="font-size: 0.8rem;" title="Evaluate this product in Retrieval Lab" onclick="switchToLabAndSearch('${nameEscaped}')">
                <i class="bi bi-search me-1"></i>Search
              </button>
            `;
          },
        },
        {
          title: "Product Validation Details",
          field: "detail_validasi",
          minWidth: 260,
          hozAlign: "left",
          headerHozAlign: "left",
          formatter: (cell) => {
            const row = cell.getRow().getData();
            const masterCat = row.masterCategory || "Apparel";
            const artType = row.articleType || "-";
            const gender = row.gender || "-";
            const colour = row.baseColour || "-";
            const usage = row.usage || "-";
            const rawStatus = row.validation_status || row.status_validasi || "Consistent";

            let badgeClass = "text-bg-success";
            let displayStatus = "Konsisten";
            if (rawStatus === "Sebagian Sesuai" || rawStatus === "Partially Consistent" || rawStatus === "Sebagian Konsisten") {
              badgeClass = "text-bg-warning";
              displayStatus = "Sebagian Konsisten";
            } else if (rawStatus === "Bermasalah" || rawStatus === "Inconsistent / Issue Found" || rawStatus === "Tidak Konsisten" || rawStatus === "Tidak Konsisten / Masalah Ditemukan") {
              badgeClass = "text-bg-danger";
              displayStatus = "Tidak Konsisten / Masalah Ditemukan";
            } else if (rawStatus === "Sesuai" || rawStatus === "Consistent" || rawStatus === "Konsisten") {
              badgeClass = "text-bg-success";
              displayStatus = "Konsisten";
            }

            return `
              <div style="font-size: 0.93rem; line-height: 1.6; white-space: normal;">
                <div class="mb-1"><span class="text-secondary fw-semibold">Kategori / Tipe:</span> <span class="text-body">${masterCat} / ${artType}</span></div>
                <div class="mb-1"><span class="text-secondary fw-semibold">Ringkasan Atribut:</span> <span class="text-body">${gender}, ${colour}, ${usage}</span></div>
                <div><span class="text-secondary fw-semibold">Status Validasi:</span> <span class="badge ${badgeClass} fw-normal" style="font-size: 0.82rem; padding: 0.35em 0.65em;">${displayStatus}</span></div>
              </div>
            `;
          },
        },
        {
          title: "Audit Findings & Rationale",
          field: "finding_rationale",
          minWidth: 320,
          hozAlign: "left",
          headerHozAlign: "left",
          formatter: (cell) => {
            const row = cell.getRow().getData();
            const text = row.finding_rationale || row.alasan_temuan || "-";
            return `<div class="text-body" style="font-size: 0.93rem; line-height: 1.6; white-space: normal; word-break: normal; overflow-wrap: break-word;">${text}</div>`;
          },
        },
      ],
    });

    // 6. Connect Export and Print Buttons
    const edaCsv = document.getElementById("eda-export-csv");
    if (edaCsv && !edaCsv.dataset.bound) {
      edaCsv.dataset.bound = "true";
      edaCsv.addEventListener("click", () => edaTabulator.download("csv", "dataset_eda_records.csv"));
    }
    const edaJson = document.getElementById("eda-export-json");
    if (edaJson && !edaJson.dataset.bound) {
      edaJson.dataset.bound = "true";
      edaJson.addEventListener("click", () => edaTabulator.download("json", "dataset_eda_records.json"));
    }
    const edaPrint = document.getElementById("eda-print-table");
    if (edaPrint && !edaPrint.dataset.bound) {
      edaPrint.dataset.bound = "true";
      edaPrint.addEventListener("click", () => edaTabulator.print(false, true));
    }

    // 7. Populate 5 Key Retrieval Insights
    const insightsContainer = document.getElementById("edaInsightsContainer");
    if (insightsContainer && data.insights) {
      insightsContainer.innerHTML = data.insights.map((ins, i) => `
        <div class="card card-outline card-secondary mb-3 shadow-none border">
          <div class="card-header py-2 bg-body-tertiary">
            <h6 class="fw-bold mb-0 text-body">Insight ${i + 1}: ${ins.topic}</h6>
          </div>
          <div class="card-body p-3">
            <p class="small mb-2 text-body"><strong>Empirical Observation:</strong> ${ins.observation}</p>
            <div class="small p-2 rounded bg-body-secondary text-body mb-2">
              <strong>Multimodal Retrieval Implication:</strong> ${ins.retrieval_implication}
            </div>
            ${ins.action_solution ? `
            <div class="small p-2 rounded bg-light border text-body">
              <strong>Mitigation Strategy &amp; Solution:</strong> ${ins.action_solution}
            </div>` : ''}
          </div>
        </div>
      `).join("");
    }

  } catch (err) {
    console.error("Error loading EDA data:", err);
  }
}
