/**
 * Multimodal Information Retrieval - Data Preparation Pipeline Module
 */

let dataPrepCache = null;
let chartDpAttrition = null;
let chartDpDist = null;

async function loadDataPreparationView() {
  try {
    if (!dataPrepCache) {
      const res = await fetch("/api/data-preparation");
      if (!res.ok) throw new Error("Failed to load data preparation info");
      dataPrepCache = await res.json();
    }
    const data = dataPrepCache;
    const theme = document.documentElement.getAttribute("data-bs-theme") || "light";


    // 2. Pipeline Stages Cards
    const stagesContainer = document.getElementById("dpPipelineStagesContainer");
    if (stagesContainer && stagesContainer.children.length === 0 && data.pipeline_stages) {
      const stage2LineTitles = {
        1: "Data Ingestion & Integrity<br>Validation",
        2: "Target Category<br>Filtering",
        3: "Reproducible Stratified<br>Sampling",
        4: "Deterministic Ground Truth<br>Synchronization",
        5: "Offline Multimodal Vector<br>Indexing",
        6: "SQLite Relational Data<br>Persistence"
      };

      stagesContainer.innerHTML = data.pipeline_stages.map(st => `
        <div class="col-12 col-md-6 col-xxl-4">
          <div class="card h-100 border shadow-sm">
            <div class="card-header py-2 d-flex align-items-center bg-body-tertiary" style="min-height: 60px;">
              <div class="d-flex align-items-center gap-2">
                <span class="badge text-bg-primary rounded-pill px-2 py-1 fs-6 flex-shrink-0">Stage ${st.stage}</span>
                <strong class="text-body lh-sm" style="line-height: 1.25;">${stage2LineTitles[st.stage] || st.name}</strong>
              </div>
            </div>
            <div class="card-body p-3 d-flex flex-column justify-content-between">
              <p class="card-text small text-body mb-2">${st.description}</p>
              <div class="bg-body-secondary p-2 rounded small mt-auto">
                <div class="text-truncate mb-1"><span class="text-secondary fw-semibold">Input:</span> <span class="text-body">${st.input}</span></div>
                <div class="text-truncate mb-1"><span class="text-secondary fw-semibold">Output:</span> <code class="text-primary">${st.output}</code></div>
                <div class="text-truncate"><span class="text-secondary fw-semibold">Script:</span> <code class="text-dark bg-light px-1 rounded">${st.script}</code></div>
              </div>
            </div>
          </div>
        </div>
      `).join("");
    }

    // 3. Attrition Chart (Waterfall Analysis)
    if (!chartDpAttrition && data.attrition_waterfall) {
      const cats = data.attrition_waterfall.map(i => i.step);
      const vals = data.attrition_waterfall.map(i => i.count);
      const optionsAttr = {
        series: [{ name: "Jumlah Gambar", data: vals }],
        chart: {
          id: "chart-dataprep-attrition",
          type: "bar",
          height: 360,
          toolbar: { show: false }
        },
        plotOptions: {
          bar: {
            horizontal: true,
            borderRadius: 4,
            barHeight: "55%",
            distributed: true
          }
        },
        colors: ["#6c757d", "#198754", "#0dcaf0", "#0d6efd", "#ffc107"],
        dataLabels: {
          enabled: true,
          formatter: function (val) { return val.toLocaleString() + " gambar"; },
          style: { fontSize: "11px", fontWeight: "normal" }
        },
        xaxis: {
          categories: cats,
          labels: { formatter: function (v) { return v >= 1000 ? (v / 1000).toFixed(0) + "k" : v; } }
        },
        legend: { show: false },
        tooltip: { theme: theme }
      };
      chartDpAttrition = new ApexCharts(document.querySelector("#chart-dataprep-attrition"), optionsAttr);
      chartDpAttrition.render();
    }

    // 4. Category Distribution Chart
    const catDist = data.corpus_composition ? (data.corpus_composition.article_type_dist || {}) : {};
    const catEntries = Object.entries(catDist);

    if (!chartDpDist && catEntries.length > 0) {
      const cats = catEntries.map(e => e[0]);
      const counts = catEntries.map(e => e[1]);
      const optionsDist = {
        series: [{ name: "Gambar dalam Korpus", data: counts }],
        chart: {
          id: "chart-dataprep-dist",
          type: "bar",
          height: 360,
          toolbar: { show: false }
        },
        plotOptions: {
          bar: {
            horizontal: false,
            columnWidth: "60%",
            borderRadius: 3
          }
        },
        colors: ["#0d6efd"],
        dataLabels: { enabled: false },
        xaxis: {
          categories: cats,
          labels: { rotate: -45, style: { fontSize: "10px" } }
        },
        yaxis: { title: { text: "Jumlah Gambar" } },
        tooltip: { theme: theme }
      };
      chartDpDist = new ApexCharts(document.querySelector("#chart-dataprep-dist"), optionsDist);
      chartDpDist.render();
    }

  } catch (err) {
    console.error("Error loading data preparation info:", err);
  }
}

function copyDataPrepScript() {
  const codeText = `# End-to-End Data Pipeline Execution Commands
# 1. Physical validation & removal of corrupted files (~44,095 clean images)
python -m src.data.validator

# 2. Filter target article types & stratified 1,500-corpus sampling
python -m src.data.sampler

# 3. Exploratory Data Analysis & visual verification
python -m src.data.eda

# 4. Synchronize 30 benchmark queries with deterministic boolean ground-truth
python -m src.data.sync_ground_truth

# 5. Offline CLIP ViT-B/32 visual feature extraction (512-d)
python -m src.models.indexer --subset 1500

# 6. Run automated quantitative IR evaluation (Precision, Recall)
python -m src.evaluation.benchmark

# 7. Run unit test suite for metric verification & database connection
python -m pytest tests/ -v`;

  navigator.clipboard.writeText(codeText).then(() => {
    alert("Pipeline replication commands copied to clipboard!");
  }).catch(() => {
    prompt("Copy the commands below:", codeText);
  });
}
