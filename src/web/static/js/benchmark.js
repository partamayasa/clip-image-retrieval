/**
 * Multimodal Information Retrieval - Benchmark & Quantitative Evaluation Module
 */

let benchmarkDataCache = null;
let evalTabulator = null;

async function initOrRedrawBenchmarkTable() {
  if (evalTabulator) {
    setTimeout(() => {
      evalTabulator.redraw(true);
      window.dispatchEvent(new Event("resize"));
    }, 50);
    return;
  }

  try {
    if (!benchmarkDataCache) {
      const resp = await fetch("/api/benchmark-report");
      benchmarkDataCache = await resp.json();
    }
    const report = benchmarkDataCache;
    const om = report.overall_metrics;
    const byLevel = report.metrics_by_level;
    const queries = report.query_details || [];

    // 2. Populate Ambiguity Level Breakdown Table
    const levelTableBody = document.getElementById("bmLevelTableBody");
    if (levelTableBody && byLevel) {
      levelTableBody.innerHTML = `
        ${Object.entries(byLevel).map(([lvl, m]) => {
          let badgeClass = "text-bg-success";
          let displayLvl = lvl;
          if (lvl === "Medium" || lvl === "Menengah") { badgeClass = "text-bg-warning"; displayLvl = "Medium"; }
          else if (lvl === "Specific" || lvl === "Spesifik") { badgeClass = "text-bg-danger"; displayLvl = "Specific"; }
          else if (lvl === "General" || lvl === "Umum") { badgeClass = "text-bg-success"; displayLvl = "General"; }

          return `
            <tr>
              <td class="text-center align-middle"><span class="badge ${badgeClass}">${displayLvl}</span></td>
              <td class="text-center align-middle">${(m['precision@5'] * 100).toFixed(1)}%</td>
              <td class="text-center align-middle">${(m['precision@10'] * 100).toFixed(1)}%</td>
              <td class="text-center align-middle">${(m['precision@20'] * 100).toFixed(1)}%</td>
              <td class="text-center align-middle">${(m['recall@5'] * 100).toFixed(1)}%</td>
              <td class="text-center align-middle">${(m['recall@10'] * 100).toFixed(1)}%</td>
              <td class="text-center align-middle">${(m['recall@20'] * 100).toFixed(1)}%</td>
            </tr>
          `;
        }).join("")}
        <tr class="fw-bold border-top border-2 text-center align-middle">
          <td class="text-center align-middle">Overall Mean</td>
          <td class="text-center align-middle">${(om['precision@5'] * 100).toFixed(1)}%</td>
          <td class="text-center align-middle">${(om['precision@10'] * 100).toFixed(1)}%</td>
          <td class="text-center align-middle">${(om['precision@20'] * 100).toFixed(1)}%</td>
          <td class="text-center align-middle">${(om['recall@5'] * 100).toFixed(1)}%</td>
          <td class="text-center align-middle">${(om['recall@10'] * 100).toFixed(1)}%</td>
          <td class="text-center align-middle">${(om['recall@20'] * 100).toFixed(1)}%</td>
        </tr>
      `;
    }

    // 3. Status Badge and Cell Formatters for Tabulator
    const levelBadgeFormatter = (cell) => {
      const val = cell.getValue();
      let color = "secondary";
      let label = val;
      if (val === "General" || val === "Umum") { color = "success"; label = "General"; }
      else if (val === "Medium" || val === "Menengah") { color = "warning"; label = "Medium"; }
      else if (val === "Specific" || val === "Spesifik") { color = "danger"; label = "Specific"; }
      return `<span class="badge text-bg-${color}">${label}</span>`;
    };

    const percentFormatter = (cell) => {
      const val = cell.getValue();
      if (val === undefined || val === null) return "-";
      return `${(val * 100).toFixed(0)}%`;
    };

    const recallFormatter = (cell) => {
      const val = cell.getValue();
      if (val === undefined || val === null) return "-";
      return `${(val * 100).toFixed(1)}%`;
    };

    // 4. Initialize Tabulator DataTable (AdminLTE tables/data.html pattern)
    evalTabulator = new Tabulator("#benchmark-tabulator-table", {
      data: queries,
      layout: "fitColumns",
      pagination: true,
      paginationSize: 10,
      paginationSizeSelector: [10, 25, 30, 50],
      movableColumns: true,
      columns: [
        { title: "#", field: "id", width: 50, minWidth: 50, hozAlign: "center", headerHozAlign: "center", headerSort: true },
        {
          title: "Level",
          field: "level",
          formatter: levelBadgeFormatter,
          width: 95,
          minWidth: 95,
          hozAlign: "center",
          headerHozAlign: "center",
          headerTooltip: "Query Ambiguity Level (General, Moderate, Specific)",
        },
        {
          title: "Query Text",
          field: "query",
          minWidth: 260,
          hozAlign: "left",
          headerHozAlign: "left",
          headerTooltip: "Text query evaluated against multimodal index",
        },
        {
          title: "GT Pool",
          field: "ground_truth_pool",
          width: 95,
          minWidth: 95,
          hozAlign: "center",
          headerHozAlign: "center",
          sorter: "number",
          headerTooltip: "Ground Truth Pool (Total verified matching items in corpus)",
        },
        { title: "P@5", field: "precision@5", width: 75, minWidth: 75, hozAlign: "center", headerHozAlign: "center", sorter: "number", formatter: percentFormatter, headerTooltip: "Precision @ Top 5 Results" },
        { title: "P@10", field: "precision@10", width: 80, minWidth: 80, hozAlign: "center", headerHozAlign: "center", sorter: "number", formatter: percentFormatter, headerTooltip: "Precision @ Top 10 Results" },
        { title: "P@20", field: "precision@20", width: 80, minWidth: 80, hozAlign: "center", headerHozAlign: "center", sorter: "number", formatter: percentFormatter, headerTooltip: "Precision @ Top 20 Results" },
        { title: "Rec@5", field: "recall@5", width: 85, minWidth: 85, hozAlign: "center", headerHozAlign: "center", sorter: "number", formatter: recallFormatter, headerTooltip: "Recall @ Top 5 Results" },
        { title: "Rec@10", field: "recall@10", width: 90, minWidth: 90, hozAlign: "center", headerHozAlign: "center", sorter: "number", formatter: recallFormatter, headerTooltip: "Recall @ Top 10 Results" },
        { title: "Rec@20", field: "recall@20", width: 90, minWidth: 90, hozAlign: "center", headerHozAlign: "center", sorter: "number", formatter: recallFormatter, headerTooltip: "Recall @ Top 20 Results" },
        {
          title: "Action",
          width: 80,
          minWidth: 80,
          hozAlign: "center",
          headerHozAlign: "center",
          headerSort: false,
          formatter: () => `<button class="btn btn-sm btn-outline-primary py-0 px-2 rounded small" title="Evaluate this query in Retrieval Lab"><i class="bi bi-play-fill me-1"></i>Test</button>`,
          cellClick: (e, cell) => {
            const rowData = cell.getRow().getData();
            switchToLabAndSearch(rowData.query);
          },
        },
      ],
    });

    // 5. Connect Export and Print Buttons (tables/data.html pattern)
    const btnCsv = document.getElementById("eval-export-csv");
    if (btnCsv && !btnCsv.dataset.bound) {
      btnCsv.dataset.bound = "true";
      btnCsv.addEventListener("click", () => evalTabulator.download("csv", "benchmark_evaluasi_kuantitatif.csv"));
    }
    const btnJson = document.getElementById("eval-export-json");
    if (btnJson && !btnJson.dataset.bound) {
      btnJson.dataset.bound = "true";
      btnJson.addEventListener("click", () => evalTabulator.download("json", "benchmark_evaluasi_kuantitatif.json"));
    }
    const btnPrint = document.getElementById("eval-print-table");
    if (btnPrint && !btnPrint.dataset.bound) {
      btnPrint.dataset.bound = "true";
      btnPrint.addEventListener("click", () => evalTabulator.print(false, true));
    }

  } catch (err) {
    console.error("Error loading benchmark table:", err);
  }
}
