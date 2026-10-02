/**
 * Multimodal Information Retrieval - Retrieval Lab Module
 */

let benchmarkQueries = [];
let currentBenchmarkSpec = null;
let currentQueryText = "";
let currentResults = [];
let currentPage = 1;
const itemsPerPage = 9; // 3x3 format = 9 items per page

async function initQueryPills() {
  const container = document.getElementById("queryPillsContainer");
  if (!container) return;

  try {
    const resp = await fetch("/api/benchmark-queries");
    const data = await resp.json();
    benchmarkQueries = data.queries || [];
  } catch (e) {
    console.error("Could not fetch queries from API", e);
  }

  container.innerHTML = "";
  benchmarkQueries.forEach((q, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    let btnClass = "btn-outline-success";
    if (q.level === "Menengah") btnClass = "btn-outline-warning";
    else if (q.level === "Spesifik") btnClass = "btn-outline-danger";

    btn.className = `btn btn-sm ${btnClass} pill-btn`;
    if (q.id === "Q01" || q.id === "Q1" || idx === 0) {
      btn.classList.add("active");
      document.getElementById("searchInput").value = q.text;
    }
    btn.innerHTML = `<span class="badge text-bg-secondary me-1">${q.id}</span> ${q.text}`;
    btn.title = `${q.target_description || ""} (${q.relevance_criteria || ""})`;
    btn.onclick = () => {
      document.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("searchInput").value = q.text;
      executeSearch();
    };
    container.appendChild(btn);
  });
}

async function executeSearch() {
  const searchInput = document.getElementById("searchInput");
  if (!searchInput) return;
  const query = searchInput.value.trim();
  if (!query) return;

  // Sync active pill button
  document.querySelectorAll(".pill-btn").forEach(b => {
    const badge = b.querySelector(".badge");
    const badgeText = badge ? badge.innerText : "";
    const btnText = b.innerText.replace(badgeText, "").trim().toLowerCase();
    if (btnText === query.toLowerCase() || badgeText.toLowerCase() === query.toLowerCase()) {
      b.classList.add("active");
    } else {
      b.classList.remove("active");
    }
  });

  const loader = document.getElementById("loadingIndicator");
  const grid = document.getElementById("productsGrid");
  const pagContainer = document.getElementById("paginationContainer");
  if (loader) loader.classList.remove("d-none");
  if (grid) grid.classList.add("d-none");
  if (pagContainer) pagContainer.classList.add("d-none");

  try {
    const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    const data = await resp.json();

    if (data.metrics) {
      // Show & update benchmark evaluation banner (Hidden per requirement)
      const banner = document.getElementById("benchmarkEvalBanner");
      if (banner && data.benchmark_spec) {
        // banner.classList.remove("d-none");
        const benchQueryEl = document.getElementById("benchBannerQuery");
        if (benchQueryEl) benchQueryEl.innerText = `${data.benchmark_spec.id}: "${data.query}"`;
        
        const benchCriteria = document.getElementById("benchBannerCriteria");
        if (benchCriteria) {
          benchCriteria.innerHTML = `
            <strong>Kriteria Relevansi:</strong> <code>${data.benchmark_spec.relevance_criteria || "-"}</code> &bull; 
            <strong>Target:</strong> ${data.benchmark_spec.target_description || "-"}
          `;
        }
        
        const benchPool = document.getElementById("benchBannerPool");
        if (benchPool) benchPool.innerText = `Ground Truth: ${data.metrics.total_corpus_relevant} items`;

        const r5 = (data.metrics.recall_at_5 * 100).toFixed(1);
        const r10 = (data.metrics.recall_at_10 * 100).toFixed(1);
        const r20 = (data.metrics.recall_at_20 * 100).toFixed(1);
        const p5 = (data.metrics.precision_at_5 * 100).toFixed(1);
        const p10 = (data.metrics.precision_at_10 * 100).toFixed(1);
        const p20 = (data.metrics.precision_at_20 * 100).toFixed(1);

        const bannerMetrics = document.getElementById("benchBannerMetrics");
        if (bannerMetrics) {
          bannerMetrics.innerHTML = `
            <div class="col-6 col-md-2">
              <div class="p-2 border rounded bg-body-tertiary">
                <div class="text-secondary small fw-bold">Recall@5</div>
                <div class="fs-5 fw-bold text-body">${r5}%</div>
                <div class="text-muted" style="font-size: 0.72rem;">${data.metrics.relevant_count_top5} / ${data.metrics.total_corpus_relevant}</div>
              </div>
            </div>
            <div class="col-6 col-md-2">
              <div class="p-2 border rounded bg-body-tertiary">
                <div class="text-secondary small fw-bold">Recall@10</div>
                <div class="fs-5 fw-bold text-body">${r10}%</div>
                <div class="text-muted" style="font-size: 0.72rem;">${data.metrics.relevant_count_top10} / ${data.metrics.total_corpus_relevant}</div>
              </div>
            </div>
            <div class="col-6 col-md-2">
              <div class="p-2 border rounded bg-body-tertiary">
                <div class="text-secondary small fw-bold">Recall@20</div>
                <div class="fs-5 fw-bold text-body">${r20}%</div>
                <div class="text-muted" style="font-size: 0.72rem;">${data.metrics.relevant_count_top20} / ${data.metrics.total_corpus_relevant}</div>
              </div>
            </div>
            <div class="col-6 col-md-2">
              <div class="p-2 border rounded bg-body-tertiary">
                <div class="text-secondary small fw-bold">Precision@5</div>
                <div class="fs-5 fw-bold text-body">${p5}%</div>
                <div class="text-muted" style="font-size: 0.72rem;">${data.metrics.relevant_count_top5} / 5</div>
              </div>
            </div>
            <div class="col-6 col-md-2">
              <div class="p-2 border rounded bg-body-tertiary">
                <div class="text-secondary small fw-bold">Precision@10</div>
                <div class="fs-5 fw-bold text-body">${p10}%</div>
                <div class="text-muted" style="font-size: 0.72rem;">${data.metrics.relevant_count_top10} / 10</div>
              </div>
            </div>
            <div class="col-6 col-md-2">
              <div class="p-2 border rounded bg-body-tertiary">
                <div class="text-secondary small fw-bold">Precision@20</div>
                <div class="fs-5 fw-bold text-body">${p20}%</div>
                <div class="text-muted" style="font-size: 0.72rem;">${data.metrics.relevant_count_top20} / 20</div>
              </div>
            </div>
          `;
        }
      }
    } else {
      const banner = document.getElementById("benchmarkEvalBanner");
      if (banner) banner.classList.add("d-none");
    }

    // 2. Setup Results and Pagination
    currentResults = data.results || [];
    currentBenchmarkSpec = data.benchmark_spec || null;
    currentQueryText = data.query || query;
    currentPage = 1;
    renderCurrentPage();

    const gTitle = document.getElementById("galleryTitle");
    if (gTitle) {
      gTitle.innerHTML = `<i class="bi bi-grid-3x3-gap-fill me-1"></i> Top Retrieved Candidates`;
    }

  } catch (err) {
    console.error("Search error:", err);
  } finally {
    if (loader) loader.classList.add("d-none");
    if (grid) grid.classList.remove("d-none");
  }
}

function renderCurrentPage() {
  const grid = document.getElementById("productsGrid");
  const pagContainer = document.getElementById("paginationContainer");
  const pagList = document.getElementById("paginationList");
  const pagInfo = document.getElementById("paginationInfo");

  if (!grid) return;
  grid.innerHTML = "";

  const totalItems = currentResults.length;
  if (totalItems === 0) {
    grid.innerHTML = `<div class="col-12 text-center text-muted py-4">Tidak ada produk yang cocok dengan query.</div>`;
    if (pagContainer) pagContainer.classList.add("d-none");
    return;
  }

  const totalPages = Math.ceil(totalItems / itemsPerPage);
  if (currentPage > totalPages) currentPage = totalPages;
  if (currentPage < 1) currentPage = 1;

  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = Math.min(startIndex + itemsPerPage, totalItems);
  const pageItems = currentResults.slice(startIndex, endIndex);

  // Render 3x3 format with 50/50 split (Image on Left, Metadata on Right)
  pageItems.forEach(item => {
    const col = document.createElement("div");
    col.className = "col";

    const artType = item.articleType || "-";
    const baseCol = item.baseColour || "-";

    let outlineClass = "card-primary";
    let badgeFooter = `<div class="text-secondary small fw-medium" style="font-size: 0.78rem;"><i class="bi bi-tag me-1"></i> Retrieved Result <span class="fw-normal">(${artType}, ${baseCol})</span></div>`;
    
    if (item.is_relevant === true) {
      outlineClass = "card-success";
      let matchDetail = "";
      let matchTooltip = "";
      if (currentBenchmarkSpec) {
        const checks = evaluateProductAttributes(item, currentBenchmarkSpec.relevance_criteria);
        if (checks) {
          const matched = Object.values(checks).filter(c => c.required && c.matched);
          if (matched.length > 0) {
            matchDetail = matched.map(c => c.actual).join(", ");
            matchTooltip = matched.map(c => `${c.name}: ${c.actual}`).join(", ");
          }
        }
      }
      const matchText = matchDetail || `${artType}, ${baseCol}`;
      const titleAttr = matchTooltip ? ` title="Ground Truth Match: ${matchTooltip}"` : "";
      badgeFooter = `<div class="text-success small fw-bold"${titleAttr} style="font-size: 0.78rem;"><i class="bi bi-check-circle-fill me-1"></i> Ground Truth Match <span class="fw-normal">(${matchText})</span></div>`;
    } else if (item.is_relevant === false) {
      outlineClass = "card-danger";
      let mismatchInfo = "";
      let tooltipInfo = "";
      if (currentBenchmarkSpec) {
        const checks = evaluateProductAttributes(item, currentBenchmarkSpec.relevance_criteria);
        if (checks) {
          const failed = Object.values(checks).filter(c => c.required && !c.matched);
          if (failed.length > 0) {
            mismatchInfo = failed.map(c => `${c.name}: ${c.actual}`).join(", ");
            tooltipInfo = failed.map(c => `${c.name} adalah '${c.actual}' (seharusnya: ${c.targetText})`).join("; ");
          }
        }
      }
      const mismatchDetail = mismatchInfo || `${artType}, ${baseCol}`;
      const titleAttr = tooltipInfo ? ` title="Attribute Mismatch: ${tooltipInfo}"` : "";
      badgeFooter = `<div class="text-danger small fw-bold"${titleAttr} style="font-size: 0.78rem;"><i class="bi bi-x-circle-fill me-1"></i> Attribute Mismatch <span class="fw-normal">(${mismatchDetail})</span></div>`;
    }

    const simVal = Number(item.score) || 0;
    const simScore = simVal.toFixed(4);
    const simPct = (simVal * 100).toFixed(2);

    col.innerHTML = `
      <div class="card card-outline ${outlineClass} h-100 shadow-sm overflow-hidden">
        <div class="row g-0 h-100 align-items-stretch">
          <!-- 50% Gambar Produk -->
          <div class="col-6 bg-white d-flex align-items-center justify-content-center p-1 border-end">
            <div class="product-img-box" onclick="openImagePreview('/api/images/${item.image_filename}', '${item.productDisplayName.replace(/'/g, "\\'")}')" title="Klik untuk melihat perbesaran gambar">
              <img src="/api/images/${item.image_filename}" alt="${item.productDisplayName}" loading="lazy" />
            </div>
          </div>
          <!-- 50% Informasi Metadata di Sebelah Gambar -->
          <div class="col-6 d-flex flex-column p-3">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <span class="badge text-bg-light border">#${item.rank}</span>
              <span class="badge text-bg-light border font-monospace" style="font-size: 0.75rem;">${simPct}%</span>
            </div>
            <h6 class="product-card-title text-body mb-1" title="${item.productDisplayName}">
              ${item.productDisplayName}
            </h6>
            <div class="text-secondary small font-monospace mb-2" style="font-size: 0.75rem;">ID: ${item.id}</div>
            <div class="d-flex flex-wrap gap-1 mb-2">
              <span class="badge text-bg-light border badge-subtle">${item.gender}</span>
              <span class="badge text-bg-light border badge-subtle">${item.baseColour}</span>
              <span class="badge text-bg-light border badge-subtle">${item.articleType}</span>
              <span class="badge text-bg-light border badge-subtle">${item.usage}</span>
            </div>
            <div class="mt-auto pt-2 border-top d-flex align-items-center">
              ${badgeFooter}
            </div>
          </div>
        </div>
      </div>
    `;
    grid.appendChild(col);
  });

  // 3. Render Pagination & Update Page 1 of {b} indicators
  if (pagContainer && pagList && pagInfo) {
    pagContainer.classList.remove("d-none");
    pagInfo.innerText = `Page ${currentPage} of ${totalPages} (Menampilkan urutan ${startIndex + 1} - ${endIndex} dari total ${totalItems} hasil pencarian)`;

    let pagHtml = "";
    
    // Previous Button
    pagHtml += `
      <li class="page-item ${currentPage <= 1 ? 'disabled' : ''}">
        <a class="page-link" href="javascript:void(0)" onclick="goToPage(${currentPage - 1})">
          &laquo; Prev
        </a>
      </li>
    `;

    // Smart Windowed Page Number Buttons
    const windowSize = 2; // shows currentPage +/- 2
    let startPage = Math.max(1, currentPage - windowSize);
    let endPage = Math.min(totalPages, currentPage + windowSize);

    if (startPage > 1) {
      pagHtml += `
        <li class="page-item ${currentPage === 1 ? 'active fw-bold' : ''}">
          <a class="page-link" href="javascript:void(0)" onclick="goToPage(1)">1</a>
        </li>
      `;
      if (startPage > 2) {
        pagHtml += `<li class="page-item disabled"><span class="page-link border-0">...</span></li>`;
      }
    }

    for (let p = startPage; p <= endPage; p++) {
      pagHtml += `
        <li class="page-item ${p === currentPage ? 'active fw-bold' : ''}">
          <a class="page-link" href="javascript:void(0)" onclick="goToPage(${p})">${p}</a>
        </li>
      `;
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        pagHtml += `<li class="page-item disabled"><span class="page-link border-0">...</span></li>`;
      }
      pagHtml += `
        <li class="page-item ${currentPage === totalPages ? 'active fw-bold' : ''}">
          <a class="page-link" href="javascript:void(0)" onclick="goToPage(${totalPages})">${totalPages}</a>
        </li>
      `;
    }

    // Next Button
    pagHtml += `
      <li class="page-item ${currentPage >= totalPages ? 'disabled' : ''}">
        <a class="page-link" href="javascript:void(0)" onclick="goToPage(${currentPage + 1})">
          Next &raquo;
        </a>
      </li>
    `;

    pagList.innerHTML = pagHtml;
  }
}

function goToPage(page) {
  const totalPages = Math.max(1, Math.ceil(currentResults.length / itemsPerPage));
  if (page < 1 || page > totalPages) return;
  currentPage = page;
  renderCurrentPage();
  const target = document.getElementById("galleryTitle");
  if (target) {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function openImagePreview(src, title) {
  const img = document.getElementById("zoomModalImg");
  const caption = document.getElementById("zoomModalCaption");
  if (img) img.src = src;
  if (caption) caption.innerText = title;
  const modalEl = document.getElementById("imageZoomModal");
  if (modalEl) {
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
  }
}

function evaluateProductAttributes(item, criteriaStr) {
  if (!criteriaStr) return null;
  const cleanCrit = criteriaStr.replace(/\s*\([^)]*\)/g, "").trim();
  const parts = cleanCrit.split("&").map(s => s.trim());
  
  const checks = {
    articleType: { name: "Article Type", required: false, matched: true, targetText: "", actual: item.articleType || "-" },
    baseColour: { name: "Base Colour", required: false, matched: true, targetText: "", actual: item.baseColour || "-" },
    gender: { name: "Gender", required: false, matched: true, targetText: "", actual: item.gender || "-" },
    usage: { name: "Usage", required: false, matched: true, targetText: "", actual: item.usage || "-" }
  };

  parts.forEach(part => {
    if (part.includes("articleType")) {
      checks.articleType.required = true;
      if (part.includes("in [")) {
        const listMatch = part.match(/in\s*\[(.*?)\]/);
        if (listMatch) {
          const allowed = listMatch[1].split(",").map(s => s.replace(/['"]/g, "").trim().toLowerCase());
          checks.articleType.targetText = listMatch[1].replace(/['"]/g, "").trim();
          checks.articleType.matched = allowed.includes(checks.articleType.actual.toLowerCase());
        }
      } else if (part.includes("contains")) {
        const match = part.match(/contains\s+['"]([^'"]+)['"]/);
        const val = match ? match[1] : "Shoes";
        checks.articleType.targetText = `Contains '${val}'`;
        checks.articleType.matched = checks.articleType.actual.toLowerCase().includes(val.toLowerCase());
      } else if (part.includes("==")) {
        const match = part.match(/==\s*['"]([^'"]+)['"]/);
        const val = match ? match[1] : "";
        checks.articleType.targetText = val;
        checks.articleType.matched = (checks.articleType.actual.toLowerCase() === val.toLowerCase());
      }
    } else if (part.includes("baseColour")) {
      checks.baseColour.required = true;
      if (part.includes("in [")) {
        const listMatch = part.match(/in\s*\[(.*?)\]/);
        if (listMatch) {
          const allowed = listMatch[1].split(",").map(s => s.replace(/['"]/g, "").trim().toLowerCase());
          checks.baseColour.targetText = listMatch[1].replace(/['"]/g, "").trim();
          checks.baseColour.matched = allowed.includes(checks.baseColour.actual.toLowerCase());
        }
      } else if (part.includes("==")) {
        const match = part.match(/==\s*['"]([^'"]+)['"]/);
        const val = match ? match[1] : "";
        checks.baseColour.targetText = val;
        checks.baseColour.matched = (checks.baseColour.actual.toLowerCase() === val.toLowerCase());
      }
    } else if (part.includes("gender")) {
      checks.gender.required = true;
      if (part.includes("in [")) {
        const listMatch = part.match(/in\s*\[(.*?)\]/);
        if (listMatch) {
          const allowed = listMatch[1].split(",").map(s => s.replace(/['"]/g, "").trim().toLowerCase());
          checks.gender.targetText = listMatch[1].replace(/['"]/g, "").trim();
          checks.gender.matched = allowed.includes(checks.gender.actual.toLowerCase());
        }
      } else if (part.includes("==")) {
        const match = part.match(/==\s*['"]([^'"]+)['"]/);
        const val = match ? match[1] : "";
        checks.gender.targetText = val;
        checks.gender.matched = (checks.gender.actual.toLowerCase() === val.toLowerCase());
      }
    } else if (part.includes("usage")) {
      checks.usage.required = true;
      if (part.includes("in [")) {
        const listMatch = part.match(/in\s*\[(.*?)\]/);
        if (listMatch) {
          const allowed = listMatch[1].split(",").map(s => s.replace(/['"]/g, "").trim().toLowerCase());
          checks.usage.targetText = listMatch[1].replace(/['"]/g, "").trim();
          checks.usage.matched = allowed.includes(checks.usage.actual.toLowerCase());
        }
      } else if (part.includes("==")) {
        const match = part.match(/==\s*['"]([^'"]+)['"]/);
        const val = match ? match[1] : "";
        checks.usage.targetText = val;
        checks.usage.matched = (checks.usage.actual.toLowerCase() === val.toLowerCase());
      }
    }
  });

  return checks;
}

function openProductDetailModal(productId) {
  const item = currentResults.find(x => Number(x.id) === Number(productId));
  if (!item) return;

  const modalBody = document.getElementById("productDetailModalBody");
  if (!modalBody) return;

  const checks = currentBenchmarkSpec ? evaluateProductAttributes(item, currentBenchmarkSpec.relevance_criteria) : null;
  
  const failedAttributes = [];
  if (checks) {
    Object.keys(checks).forEach(k => {
      const c = checks[k];
      if (c.required && !c.matched) {
        failedAttributes.push(c);
      }
    });
  }

  function renderAttrStatus(c) {
    if (!c || !c.required) {
      return `<span class="badge text-bg-secondary"><i class="bi bi-dash me-1"></i>Bebas (Tidak Ditentukan Kueri)</span>`;
    }
    if (c.matched) {
      return `<span class="badge text-bg-success"><i class="bi bi-check-circle-fill me-1"></i>Sesuai Kueri (${c.targetText})</span>`;
    }
    return `<span class="badge text-bg-danger"><i class="bi bi-x-circle-fill me-1"></i>Tidak Sesuai (Harus ${c.targetText})</span>`;
  }

  let evalBannerHtml = "";
  if (item.is_relevant === true) {
    evalBannerHtml = `
      <div class="alert alert-success d-flex align-items-center mb-3 py-2">
        <i class="bi bi-check-circle-fill fs-4 me-3"></i>
        <div>
          <strong class="d-block">Status: Ground Truth Relevan</strong>
          <span class="small">Produk ini memenuhi seluruh kriteria kueri benchmark: <code>${currentBenchmarkSpec.relevance_criteria}</code></span>
        </div>
      </div>
    `;
  } else if (item.is_relevant === false) {
    const reasons = failedAttributes.map(a => `${a.name} berbeda (ekspektasi: <strong>${a.targetText}</strong>, aktual: <em>${a.actual}</em>)`).join("; ");
    evalBannerHtml = `
      <div class="alert alert-danger d-flex align-items-center mb-3 py-2">
        <i class="bi bi-exclamation-triangle-fill fs-4 me-3"></i>
        <div>
          <strong class="d-block">Status: False Positive / Diskrepansi Atribut</strong>
          <span class="small">Produk terambil oleh CLIP karena kemiripan visual, namun tidak relevan menurut Ground Truth: ${reasons || "Atribut tidak cocok"}.</span>
        </div>
      </div>
    `;
  } else {
    evalBannerHtml = `
      <div class="alert alert-secondary d-flex align-items-center mb-3 py-2">
        <i class="bi bi-info-circle-fill fs-4 me-3"></i>
        <div>
          <strong class="d-block">Kueri Eksploratif Bebas</strong>
          <span class="small">Kueri ini bukan merupakan kueri standar benchmark sehingga evaluasi Ground Truth tidak diaktifkan.</span>
        </div>
      </div>
    `;
  }

  const simVal = Number(item.score) || 0;
  const simScore = simVal.toFixed(4);
  const simPct = (simVal * 100).toFixed(2);

  modalBody.innerHTML = `
    ${evalBannerHtml}

    <div class="row g-3">
      <!-- Gambar Produk -->
      <div class="col-md-5 text-center">
        <div class="p-2 border rounded bg-white shadow-sm mb-2">
          <img src="/api/images/${item.image_filename}" alt="${item.productDisplayName}" 
               style="max-height: 280px; max-width: 100%; object-fit: contain; cursor: pointer;"
               onclick="openImagePreview('/api/images/${item.image_filename}', '${item.productDisplayName.replace(/'/g, "\\'")}')"
               title="Klik untuk memperbesar gambar" />
        </div>
        <div class="font-monospace text-secondary small">ID: ${item.id} &bull; File: ${item.image_filename}</div>
      </div>

      <!-- Detail Atribut Produk -->
      <div class="col-md-7">
        <h6 class="fw-bold text-body mb-2">${item.productDisplayName}</h6>
        <div class="d-flex align-items-center gap-2 mb-3">
          <span class="badge text-bg-primary">Rank #${item.rank}</span>
          <span class="badge text-bg-light border font-monospace">Cosine Similarity: ${simScore} (${simPct}%)</span>
        </div>

        <div class="table-responsive">
          <table class="table table-sm table-bordered align-middle mb-0" style="font-size: 0.85rem;">
            <thead class="table-light">
              <tr>
                <th style="width: 32%;">Atribut</th>
                <th style="width: 33%;">Nilai Aktual</th>
                <th style="width: 35%;">Status Kueri</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="fw-semibold">Article Type</td>
                <td><span class="badge text-bg-light border">${item.articleType}</span></td>
                <td>${checks ? renderAttrStatus(checks.articleType) : '<span class="text-muted">-</span>'}</td>
              </tr>
              <tr>
                <td class="fw-semibold">Base Colour</td>
                <td><span class="badge text-bg-light border">${item.baseColour}</span></td>
                <td>${checks ? renderAttrStatus(checks.baseColour) : '<span class="text-muted">-</span>'}</td>
              </tr>
              <tr>
                <td class="fw-semibold">Gender</td>
                <td><span class="badge text-bg-light border">${item.gender}</span></td>
                <td>${checks ? renderAttrStatus(checks.gender) : '<span class="text-muted">-</span>'}</td>
              </tr>
              <tr>
                <td class="fw-semibold">Usage Context</td>
                <td><span class="badge text-bg-light border">${item.usage}</span></td>
                <td>${checks ? renderAttrStatus(checks.usage) : '<span class="text-muted">-</span>'}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  const detailModal = new bootstrap.Modal(document.getElementById("productDetailModal"));
  detailModal.show();
}

function switchToLabAndSearch(query) {
  switchView("retrieval");
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.value = query;
  }
  document.querySelectorAll(".pill-btn").forEach(b => {
    if (b.innerText.toLowerCase().includes(query.toLowerCase())) {
      b.classList.add("active");
    } else {
      b.classList.remove("active");
    }
  });
  executeSearch();
}
