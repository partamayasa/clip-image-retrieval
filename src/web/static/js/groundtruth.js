/**
 * Multimodal Information Retrieval - Ground Truth Module
 */

let groundTruthDataCache = null;
let gtTabulator = null;
let currentGtViewMode = "table"; // "table" or "cards"

async function initOrRedrawGroundTruthTable() {
  if (gtTabulator && currentGtViewMode === "table") {
    setTimeout(() => {
      gtTabulator.redraw(true);
      const queryVal = document.getElementById("gtFilterQuery")?.value || "";
      if (!queryVal) {
        gtTabulator.setSort("query_text", "asc");
      }
      window.dispatchEvent(new Event("resize"));
    }, 50);
    return;
  }

  try {
    if (!groundTruthDataCache) {
      const resp = await fetch("/api/ground-truth");
      groundTruthDataCache = await resp.json();
    }

    const data = groundTruthDataCache;
    const summary = data.summary || {};
    const relations = data.relations || [];


    // 2. Populate Filter Dropdowns (once)
    populateGtFilterDropdowns(summary);

    // 3. Initialize Tabulator or Cards based on current mode
    if (currentGtViewMode === "table") {
      initGtTabulator(relations);
    } else {
      renderGtQueryCards(relations);
    }

    // 4. Bind Action Buttons (Export, Search, Filter)
    bindGtEventListeners();

  } catch (err) {
    console.error("Error loading Ground Truth data:", err);
  }
}

function populateGtFilterDropdowns(summary) {
  const querySelect = document.getElementById("gtFilterQuery");
  const catSelect = document.getElementById("gtFilterCategory");

  if (querySelect && querySelect.options.length <= 1 && summary.queries) {
    summary.queries.forEach(q => {
      const opt = document.createElement("option");
      opt.value = q.id;
      opt.textContent = `[${q.id}] ${q.query_text} (${q.total_relevant} items - ${q.level})`;
      querySelect.appendChild(opt);
    });
  }

  if (catSelect && catSelect.options.length <= 1 && summary.category_breakdown) {
    summary.category_breakdown.forEach(cat => {
      if (cat.article_type) {
        const opt = document.createElement("option");
        opt.value = cat.article_type;
        opt.textContent = `${cat.article_type} (${cat.pair_count} pairs)`;
        catSelect.appendChild(opt);
      }
    });
  }
}

function initGtTabulator(relations) {
  const tableContainer = document.getElementById("gt-tabulator-table");
  if (!tableContainer) return;

  const levelBadgeFormatter = (cell) => {
    const val = cell.getValue();
    let color = "secondary";
    if (val === "General" || val === "Umum") color = "success";
    else if (val === "Medium" || val === "Menengah") color = "warning";
    else if (val === "Specific" || val === "Spesifik") color = "danger";
    return `<span class="badge text-bg-${color}">${val}</span>`;
  };

  const imageFormatter = (cell) => {
    const row = cell.getRow().getData();
    const prodId = row.product_id;
    const name = (row.product_name || `Product #${prodId}`).replace(/'/g, "\\'");
    const imgUrl = `/api/images/${prodId}.jpg`;
    return `
      <div class="d-flex align-items-center justify-content-center position-relative" style="width: 44px; height: 44px; margin: 0 auto;">
        <img src="${imgUrl}" alt="${prodId}" class="rounded border shadow-xs" 
             style="width: 42px; height: 42px; object-fit: cover; cursor: pointer;"
             loading="lazy"
             onerror="this.onerror=null; this.src='/static/adminlte/assets/img/default-150x150.png';"
             onclick="showImageZoomModal('${imgUrl}', '${name} (ID: ${prodId})')"
             title="Click to view full image" />
      </div>
    `;
  };

  const queryBadgeFormatter = (cell) => {
    const row = cell.getRow().getData();
    return `
      <div class="d-flex flex-wrap align-items-center gap-1" style="white-space: normal; line-height: 1.3;">
        <span class="badge text-bg-secondary fw-bold">${row.query_id}</span>
        <span class="fw-semibold text-wrap text-break">${row.query_text}</span>
      </div>
    `;
  };

  const criteriaFormatter = (cell) => {
    const val = cell.getValue() || "-";
    return `<code class="small d-inline-block text-break" style="font-size: 0.76rem; background: rgba(0,0,0,0.05); padding: 4px 6px; border-radius: 4px; white-space: normal; word-break: break-word; line-height: 1.35;" title="${val}">${val}</code>`;
  };

  const parseQueryNumber = (qid) => parseInt(String(qid || "").replace(/\D/g, ""), 10) || 0;

  const querySorter = (a, b, aRow, bRow) => {
    const qA = aRow && typeof aRow.getData === "function" ? (aRow.getData()?.query_id || "") : "";
    const qB = bRow && typeof bRow.getData === "function" ? (bRow.getData()?.query_id || "") : "";
    const numA = parseQueryNumber(qA);
    const numB = parseQueryNumber(qB);
    if (numA !== numB) return numA - numB;
    const pA = aRow && typeof aRow.getData === "function" ? (aRow.getData()?.product_id || 0) : 0;
    const pB = bRow && typeof bRow.getData === "function" ? (bRow.getData()?.product_id || 0) : 0;
    return pA - pB;
  };

  // Pre-sort relations by query Q01 -> Q30 then product_id
  if (Array.isArray(relations)) {
    relations.sort((a, b) => {
      const qDiff = parseQueryNumber(a.query_id) - parseQueryNumber(b.query_id);
      if (qDiff !== 0) return qDiff;
      return (a.product_id || 0) - (b.product_id || 0);
    });
  }

  gtTabulator = new Tabulator("#gt-tabulator-table", {
    data: relations,
    layout: "fitDataFill",
    responsiveLayout: false,
    pagination: true,
    paginationSize: 15,
    paginationSizeSelector: [15, 25, 50, 100],
    paginationCounter: "rows",
    placeholder: "No Ground Truth matching criteria found",
    initialSort: [
      { column: "query_text", dir: "asc" }
    ],
    columns: [
      {
        title: "Query",
        field: "query_text",
        width: 170,
        minWidth: 140,
        variableHeight: true,
        formatter: queryBadgeFormatter,
        sorter: querySorter,
      },
      {
        title: "Level",
        field: "query_level",
        width: 95,
        minWidth: 85,
        hozAlign: "center",
        headerHozAlign: "center",
        formatter: levelBadgeFormatter,
      },
      {
        title: "Relevance Logic Criteria",
        field: "relevance_criteria",
        width: 250,
        minWidth: 180,
        variableHeight: true,
        formatter: criteriaFormatter,
      },
      {
        title: "Image",
        field: "image_url",
        width: 65,
        minWidth: 65,
        hozAlign: "center",
        headerHozAlign: "center",
        headerSort: false,
        formatter: imageFormatter,
      },
      {
        title: "Product ID",
        field: "product_id",
        width: 105,
        minWidth: 95,
        hozAlign: "center",
        headerHozAlign: "center",
        sorter: "number",
        formatter: (cell) => `<span class="badge bg-body-secondary text-body border fw-mono">#${cell.getValue()}</span>`,
      },
      {
        title: "Product Name",
        field: "product_name",
        minWidth: 160,
        variableHeight: true,
        formatter: (cell) => {
          const val = cell.getValue() || "-";
          return `<span class="fw-medium text-wrap text-break d-inline-block" style="white-space: normal; line-height: 1.3;" title="${val}">${val}</span>`;
        },
      },
      {
        title: "Article Type",
        field: "article_type",
        width: 120,
        minWidth: 110,
        hozAlign: "center",
        headerHozAlign: "center",
      },
      {
        title: "Colour",
        field: "base_colour",
        width: 95,
        minWidth: 90,
        hozAlign: "center",
        headerHozAlign: "center",
        formatter: (cell) => `<span class="badge text-bg-light border text-dark">${cell.getValue() || "-"}</span>`,
      },
      {
        title: "Gender",
        field: "gender",
        width: 85,
        minWidth: 80,
        hozAlign: "center",
        headerHozAlign: "center",
      },
      {
        title: "Usage",
        field: "usage",
        width: 95,
        minWidth: 85,
        hozAlign: "center",
        headerHozAlign: "center",
        formatter: (cell) => `<span class="badge text-bg-secondary">${cell.getValue() || "-"}</span>`,
      },
      {
        title: "Action",
        width: 95,
        minWidth: 90,
        hozAlign: "center",
        headerHozAlign: "center",
        headerSort: false,
        formatter: () => `
          <button class="btn btn-sm btn-outline-primary py-0 px-2 rounded small" title="Test this query in Retrieval Lab">
            <i class="bi bi-play-fill me-1"></i>Test
          </button>
        `,
        cellClick: (e, cell) => {
          const rowData = cell.getRow().getData();
          switchToLabAndSearch(rowData.query_text);
        },
      },
    ],
  });

  gtTabulator.on("tableBuilt", () => {
    const queryVal = document.getElementById("gtFilterQuery")?.value || "";
    if (!queryVal) {
      gtTabulator.setSort("query_text", "asc");
    }
  });
}

function applyGtFilters() {
  if (!groundTruthDataCache) return;

  const queryVal = document.getElementById("gtFilterQuery")?.value || "";
  const levelVal = document.getElementById("gtFilterLevel")?.value || "";
  const catVal = document.getElementById("gtFilterCategory")?.value || "";
  const searchVal = (document.getElementById("gtSearchInput")?.value || "").toLowerCase().trim();

  let filtered = groundTruthDataCache.relations || [];

  if (queryVal) {
    filtered = filtered.filter(r => r.query_id === queryVal);
  }
  if (levelVal) {
    filtered = filtered.filter(r => r.query_level === levelVal);
  }
  if (catVal) {
    filtered = filtered.filter(r => r.article_type === catVal);
  }
  if (searchVal) {
    filtered = filtered.filter(r => {
      const pName = (r.product_name || "").toLowerCase();
      const pId = String(r.product_id);
      const qText = (r.query_text || "").toLowerCase();
      const col = (r.base_colour || "").toLowerCase();
      const cat = (r.article_type || "").toLowerCase();
      return pName.includes(searchVal) || pId.includes(searchVal) || qText.includes(searchVal) || col.includes(searchVal) || cat.includes(searchVal);
    });
  }

  const parseQNum = (qid) => parseInt(String(qid || "").replace(/\D/g, ""), 10) || 0;
  filtered.sort((a, b) => {
    const qDiff = parseQNum(a.query_id) - parseQNum(b.query_id);
    if (qDiff !== 0) return qDiff;
    return (a.product_id || 0) - (b.product_id || 0);
  });

  // Update counter
  const counterEl = document.getElementById("gtFilteredCount");
  if (counterEl) {
    counterEl.innerText = `${filtered.length.toLocaleString()} relations found`;
  }

  if (currentGtViewMode === "table" && gtTabulator) {
    gtTabulator.setData(filtered).then(() => {
      if (!queryVal) {
        gtTabulator.setSort("query_text", "asc");
      }
    });
  } else if (currentGtViewMode === "cards") {
    renderGtQueryCards(filtered);
  }
}

function resetGtFilters() {
  const querySelect = document.getElementById("gtFilterQuery");
  const levelSelect = document.getElementById("gtFilterLevel");
  const catSelect = document.getElementById("gtFilterCategory");
  const searchInput = document.getElementById("gtSearchInput");

  if (querySelect) querySelect.value = "";
  if (levelSelect) levelSelect.value = "";
  if (catSelect) catSelect.value = "";
  if (searchInput) searchInput.value = "";

  applyGtFilters();
}

function setGtViewMode(mode) {
  currentGtViewMode = mode;
  const btnTable = document.getElementById("gtModeTableBtn");
  const btnCards = document.getElementById("gtModeCardsBtn");
  const containerTable = document.getElementById("gtTableContainer");
  const containerCards = document.getElementById("gtCardsContainer");

  if (mode === "table") {
    btnTable?.classList.add("active");
    btnCards?.classList.remove("active");
    containerTable?.classList.remove("d-none");
    containerCards?.classList.add("d-none");
    if (!gtTabulator && groundTruthDataCache) {
      initGtTabulator(groundTruthDataCache.relations || []);
    } else if (gtTabulator) {
      setTimeout(() => gtTabulator.redraw(true), 50);
    }
  } else {
    btnCards?.classList.add("active");
    btnTable?.classList.remove("active");
    containerCards?.classList.remove("d-none");
    containerTable?.classList.add("d-none");
    applyGtFilters();
  }
}

function renderGtQueryCards(relations) {
  const container = document.getElementById("gtCardsAccordion");
  if (!container) return;

  if (relations.length === 0) {
    container.innerHTML = `
      <div class="alert alert-info text-center py-4 my-3">
        <i class="bi bi-info-circle fs-3 d-block mb-2"></i>
        <strong>No Ground Truth relations found matching the current filters.</strong>
        <p class="mb-0 text-secondary small">Try resetting filters or adjusting search terms.</p>
      </div>
    `;
    return;
  }

  // Group relations by query_id
  const groups = {};
  relations.forEach(r => {
    if (!groups[r.query_id]) {
      groups[r.query_id] = {
        query_id: r.query_id,
        query_text: r.query_text,
        query_level: r.query_level,
        target_description: r.target_description,
        relevance_criteria: r.relevance_criteria,
        items: []
      };
    }
    groups[r.query_id].items.push(r);
  });

  const queryList = Object.values(groups).sort((a, b) => a.query_id.localeCompare(b.query_id));

  container.innerHTML = queryList.map((g, idx) => {
    let levelBadge = "text-bg-success";
    if (g.query_level === "Medium" || g.query_level === "Menengah") levelBadge = "text-bg-warning";
    else if (g.query_level === "Specific" || g.query_level === "Spesifik") levelBadge = "text-bg-danger";

    const isFirst = idx === 0;

    const cardsHtml = g.items.map(p => {
      const imgUrl = `/api/images/${p.product_id}.jpg`;
      const pName = (p.product_name || `Product #${p.product_id}`).replace(/'/g, "\\'");
      return `
        <div class="col-6 col-sm-4 col-md-3 col-xl-2">
          <div class="card h-100 shadow-xs border hover-shadow" style="font-size: 0.8rem;">
            <div class="position-relative bg-light text-center p-1 rounded-top" style="height: 120px; overflow: hidden;">
              <img src="${imgUrl}" alt="${p.product_id}" 
                   class="img-fluid h-100" style="object-fit: contain; cursor: pointer;"
                   loading="lazy"
                   onerror="this.onerror=null; this.src='/static/adminlte/assets/img/default-150x150.png';"
                   onclick="showImageZoomModal('${imgUrl}', '${pName} (#${p.product_id})')"
                   title="Click to zoom image" />
              <span class="position-absolute top-0 start-0 m-1 badge bg-dark opacity-75 small">#${p.product_id}</span>
            </div>
            <div class="card-body p-2 d-flex flex-column justify-content-between">
              <div>
                <div class="fw-semibold text-truncate mb-1" title="${p.product_name || ''}">${p.product_name || `Product #${p.product_id}`}</div>
                <div class="text-secondary small d-flex flex-wrap gap-1 mb-1">
                  <span class="badge text-bg-light border">${p.article_type || ''}</span>
                  <span class="badge text-bg-light border">${p.base_colour || ''}</span>
                  <span class="badge text-bg-light border">${p.gender || ''}</span>
                </div>
              </div>
              <div class="mt-2 pt-1 border-top d-flex justify-content-between align-items-center">
                <span class="badge text-bg-secondary" style="font-size: 0.7rem;">${p.usage || 'Casual'}</span>
                <button class="btn btn-outline-primary btn-xs py-0 px-1" style="font-size: 0.72rem;" onclick="switchToLabAndSearch('${g.query_text}')" title="Test query in retrieval lab">
                  <i class="bi bi-play-fill"></i>Test
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join("");

    return `
      <div class="accordion-item mb-3 border rounded shadow-sm overflow-hidden">
        <h2 class="accordion-header" id="heading-${g.query_id}">
          <button class="accordion-button ${isFirst ? '' : 'collapsed'} py-2 px-3 bg-body-tertiary" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-${g.query_id}" aria-expanded="${isFirst ? 'true' : 'false'}">
            <div class="d-flex flex-wrap align-items-center justify-content-between w-100 pe-3 gap-2">
              <div class="d-flex align-items-center gap-2">
                <span class="badge bg-secondary fs-6">${g.query_id}</span>
                <span class="fw-bold fs-6">"${g.query_text}"</span>
                <span class="badge ${levelBadge}">${g.query_level}</span>
                <span class="badge rounded-pill bg-primary">${g.items.length} relevant items</span>
              </div>
              <div class="d-none d-md-flex align-items-center gap-2">
                <code class="small text-secondary" style="font-size: 0.75rem;">${g.relevance_criteria || ''}</code>
              </div>
            </div>
          </button>
        </h2>
        <div id="collapse-${g.query_id}" class="accordion-collapse collapse ${isFirst ? 'show' : ''}" data-bs-parent="#gtCardsAccordion">
          <div class="accordion-body p-3 bg-body">
            <div class="d-flex flex-wrap justify-content-between align-items-center mb-3 pb-2 border-bottom">
              <div>
                <p class="mb-1 text-secondary small"><strong>Target Description:</strong> ${g.target_description || '-'}</p>
                <p class="mb-0 text-secondary small"><strong>Deterministic Criteria:</strong> <code>${g.relevance_criteria || '-'}</code></p>
              </div>
              <div>
                <button class="btn btn-sm btn-primary d-flex align-items-center gap-1" onclick="switchToLabAndSearch('${g.query_text}')">
                  <i class="bi bi-play-circle-fill"></i>
                  <span>Test in Retrieval Lab</span>
                </button>
              </div>
            </div>
            <div class="row g-2">
              ${cardsHtml}
            </div>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function bindGtEventListeners() {
  const btnCsv = document.getElementById("eval-gt-export-csv");
  if (btnCsv && !btnCsv.dataset.bound) {
    btnCsv.dataset.bound = "true";
    btnCsv.addEventListener("click", () => {
      if (gtTabulator) {
        gtTabulator.download("csv", "ground_truth_relations_fashion.csv");
      }
    });
  }

  const btnJson = document.getElementById("eval-gt-export-json");
  if (btnJson && !btnJson.dataset.bound) {
    btnJson.dataset.bound = "true";
    btnJson.addEventListener("click", () => {
      if (gtTabulator) {
        gtTabulator.download("json", "ground_truth_relations_fashion.json");
      }
    });
  }

  const btnPrint = document.getElementById("eval-gt-print-table");
  if (btnPrint && !btnPrint.dataset.bound) {
    btnPrint.dataset.bound = "true";
    btnPrint.addEventListener("click", () => {
      if (gtTabulator) {
        gtTabulator.print(false, true);
      }
    });
  }

  const searchInput = document.getElementById("gtSearchInput");
  if (searchInput && !searchInput.dataset.bound) {
    searchInput.dataset.bound = "true";
    searchInput.addEventListener("input", () => {
      clearTimeout(searchInput._timer);
      searchInput._timer = setTimeout(applyGtFilters, 250);
    });
  }
}
