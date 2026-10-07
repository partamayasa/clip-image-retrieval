/**
 * Multimodal Information Retrieval - Core Application Controller
 */

function switchView(viewName) {
  const viewRetrieval = document.getElementById("view-retrieval");
  const viewBenchmark = document.getElementById("view-benchmark");
  const viewEda = document.getElementById("view-eda");
  const viewDataprep = document.getElementById("view-dataprep");
  const viewGroundtruth = document.getElementById("view-groundtruth");
  const navRetrieval = document.getElementById("nav-retrieval");
  const navBenchmark = document.getElementById("nav-benchmark");
  const navEda = document.getElementById("nav-eda");
  const navDataprep = document.getElementById("nav-dataprep");
  const navGroundtruth = document.getElementById("nav-groundtruth");
  const pageTitle = document.getElementById("headerPageTitle");
  const pageSubtitle = document.getElementById("headerPageSubtitle");
  const breadcrumbs = document.getElementById("headerBreadcrumbs");

  // Helper to hide all views and un-highlight all navs
  const hideAll = () => {
    [viewRetrieval, viewBenchmark, viewEda, viewDataprep, viewGroundtruth].forEach(v => v && v.classList.add("d-none"));
    [navRetrieval, navBenchmark, navEda, navDataprep, navGroundtruth].forEach(n => n && n.classList.remove("active"));
  };

  if (viewName === "groundtruth") {
    hideAll();
    if (viewGroundtruth) viewGroundtruth.classList.remove("d-none");
    if (navGroundtruth) navGroundtruth.classList.add("active");

    if (pageTitle) pageTitle.innerText = "Ground Truth & Relevance Mapping";
    if (pageSubtitle) pageSubtitle.innerText = "Deterministic Product-to-Query Relevance Relations & Multi-Attribute Alignment (2,014 Pairs)";
    if (breadcrumbs) {
      breadcrumbs.innerHTML = `
        <li class="breadcrumb-item"><a href="javascript:void(0)" onclick="switchView('retrieval')">Home</a></li>
        <li class="breadcrumb-item">Research</li>
        <li class="breadcrumb-item active">Ground Truth</li>
      `;
    }
    if (typeof initOrRedrawGroundTruthTable === "function") {
      initOrRedrawGroundTruthTable();
    }
  } else if (viewName === "benchmark") {
    hideAll();
    if (viewBenchmark) viewBenchmark.classList.remove("d-none");
    if (navBenchmark) navBenchmark.classList.add("active");

    if (pageTitle) pageTitle.innerText = "Research Queries & Quantitative Evaluation";
    if (pageSubtitle) pageSubtitle.innerText = "Quantitative Performance Evaluation Table Based on 30 Standardized Benchmark Queries";
    if (breadcrumbs) {
      breadcrumbs.innerHTML = `
        <li class="breadcrumb-item"><a href="javascript:void(0)" onclick="switchView('retrieval')">Home</a></li>
        <li class="breadcrumb-item">Evaluation</li>
        <li class="breadcrumb-item active">Research Queries &amp; Quantitative Evaluation</li>
      `;
    }
    initOrRedrawBenchmarkTable();
  } else if (viewName === "eda") {
    hideAll();
    if (viewEda) viewEda.classList.remove("d-none");
    if (navEda) navEda.classList.add("active");

    if (pageTitle) pageTitle.innerText = "Exploratory Data Analysis & Retrieval Insights";
    if (pageSubtitle) pageSubtitle.innerText = "Dataset Distributions, Metadata Completeness & Multimodal Retrieval Implications";
    if (breadcrumbs) {
      breadcrumbs.innerHTML = `
        <li class="breadcrumb-item"><a href="javascript:void(0)" onclick="switchView('retrieval')">Home</a></li>
        <li class="breadcrumb-item">Dataset &amp; Insights</li>
        <li class="breadcrumb-item active">Exploratory Data Analysis &amp; Retrieval Insights</li>
      `;
    }
    initOrRedrawEdaTable();
  } else if (viewName === "dataprep") {
    hideAll();
    if (viewDataprep) viewDataprep.classList.remove("d-none");
    if (navDataprep) navDataprep.classList.add("active");

    if (pageTitle) pageTitle.innerText = "Data Preparation & Research Pipeline Transparency";
    if (pageSubtitle) pageSubtitle.innerText = "End-to-End Pipeline Auditability, Stratified Sampling Rationale, and Ground-Truth Determinism";
    if (breadcrumbs) {
      breadcrumbs.innerHTML = `
        <li class="breadcrumb-item"><a href="javascript:void(0)" onclick="switchView('retrieval')">Home</a></li>
        <li class="breadcrumb-item">Data Engineering</li>
        <li class="breadcrumb-item active">Data Preparation &amp; Transparency</li>
      `;
    }
    loadDataPreparationView();
  } else {
    hideAll();
    if (viewRetrieval) viewRetrieval.classList.remove("d-none");
    if (navRetrieval) navRetrieval.classList.add("active");

    if (pageTitle) pageTitle.innerText = "Fashion Product Image Retrieval";
    if (pageSubtitle) pageSubtitle.innerText = "Project 1: Attribute-Based Text-to-Image Ranking using CLIP Shared Latent Space";
    if (breadcrumbs) {
      breadcrumbs.innerHTML = `
        <li class="breadcrumb-item"><a href="javascript:void(0)" onclick="switchView('retrieval')">Home</a></li>
        <li class="breadcrumb-item">Project 1</li>
        <li class="breadcrumb-item active">Retrieval Lab</li>
      `;
    }
  }
}

function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute("data-bs-theme") || "light";
  const next = current === "dark" ? "light" : "dark";
  html.setAttribute("data-bs-theme", next);

  const sidebar = document.querySelector(".app-sidebar");
  if (sidebar) sidebar.setAttribute("data-bs-theme", "dark");
  
  const icon = document.getElementById("themeIcon");
  if (icon) {
    icon.className = next === "dark" ? "bi bi-sun-fill" : "bi bi-moon-fill";
  }

  if (typeof evalTabulator !== "undefined" && evalTabulator) {
    setTimeout(() => evalTabulator.redraw(true), 50);
  }
  if (typeof edaTabulator !== "undefined" && edaTabulator) {
    setTimeout(() => edaTabulator.redraw(true), 50);
  }
  if (typeof gtTabulator !== "undefined" && gtTabulator) {
    setTimeout(() => gtTabulator.redraw(true), 50);
  }
}

// Global Initialization
document.addEventListener("DOMContentLoaded", async () => {
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") executeSearch();
    });
  }

  const pillsCollapse = document.getElementById("queryPillsCollapse");
  if (pillsCollapse) {
    pillsCollapse.addEventListener("show.bs.collapse", () => {
      const toggleText = document.getElementById("queryPillsToggleText");
      const icon = document.getElementById("queryPillsIcon");
      if (toggleText) toggleText.innerText = "Hide";
      if (icon) icon.className = "bi bi-eye-slash me-1";
    });
    pillsCollapse.addEventListener("hide.bs.collapse", () => {
      const toggleText = document.getElementById("queryPillsToggleText");
      const icon = document.getElementById("queryPillsIcon");
      if (toggleText) toggleText.innerText = "Show";
      if (icon) icon.className = "bi bi-eye me-1";
    });
  }

  window.addEventListener("hashchange", () => {
    const hash = window.location.hash;
    if (hash === "#groundtruth" || hash === "#ground-truth") {
      switchView("groundtruth");
    } else if (hash === "#benchmark" || hash === "#evaluasi") {
      switchView("benchmark");
    } else if (hash === "#dataprep" || hash === "#data-preparation") {
      switchView("dataprep");
    } else if (hash === "#eda") {
      switchView("eda");
    } else if (hash === "#retrieval") {
      switchView("retrieval");
    }
  });

  // Initial Startup (Load pills first so Q01 is selected, then execute search)
  await initQueryPills();
  await executeSearch();

  const initialHash = window.location.hash;
  if (initialHash === "#groundtruth" || initialHash === "#ground-truth") {
    switchView("groundtruth");
  } else if (initialHash === "#benchmark" || initialHash === "#evaluasi") {
    switchView("benchmark");
  } else if (initialHash === "#dataprep" || initialHash === "#data-preparation") {
    switchView("dataprep");
  } else if (initialHash === "#eda") {
    switchView("eda");
  }
});

