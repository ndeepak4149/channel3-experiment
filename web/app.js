/* ─────────────────────────────────────────────────────────────────────────────
   Channel4  app.js
   Calls the Railway API (set API_BASE below after deploying).
   For local dev: set API_BASE = "http://localhost:8000"
───────────────────────────────────────────────────────────────────────────── */

const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : "https://web-production-1a439.up.railway.app";

// ── State ─────────────────────────────────────────────────────────────────────
let basketItems  = [];       // array of query strings
let personaId    = "default_user";
let currentDepth = "standard";

// ── Helpers ───────────────────────────────────────────────────────────────────
async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

function esc(str = "") {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmt(price) {
  if (price == null) return "N/A";
  return "$" + Number(price).toFixed(2);
}

function tierClass(tier = "") { return tier.toLowerCase().replace(/[^a-z]/g, ""); }

function dealIcon(rec = "") {
  return { buy_now: "🟢 BUY NOW", good_deal: "✅ GOOD DEAL", wait: "⏳ WAIT", overpriced: "🔴 OVERPRICED" }[rec] || rec;
}

function confBar(conf = 0) {
  const pct = Math.round(conf * 100);
  return `<div class="conf-bar"><div class="conf-fill" style="width:${pct}%"></div></div>`;
}

function setLoading(btn, loading, loaderText = "...") {
  const text   = btn.querySelector(".btn-text");
  const loader = btn.querySelector(".btn-loader");
  btn.disabled = loading;
  text?.classList.toggle("hidden", loading);
  loader?.classList.toggle("hidden", !loading);
  if (loading && loader) loader.textContent = loaderText;
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(s => s.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("tab-" + tab.dataset.tab).classList.add("active");
  });
});

document.getElementById("depthSelect").addEventListener("change", e => {
  currentDepth = e.target.value;
});

// ── SEARCH TAB ────────────────────────────────────────────────────────────────
const searchInput   = document.getElementById("searchInput");
const searchBtn     = document.getElementById("searchBtn");
const searchResults = document.getElementById("searchResults");

searchBtn.addEventListener("click", runSearch);
searchInput.addEventListener("keydown", e => { if (e.key === "Enter") runSearch(); });

document.querySelectorAll(".chip").forEach(chip => {
  chip.addEventListener("click", () => {
    searchInput.value = chip.dataset.query;
    runSearch();
  });
});

function renderSkeletons() {
  return `
    <div class="skeleton skeleton-card"></div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px">
      <div class="skeleton" style="height:200px;border-radius:10px"></div>
      <div class="skeleton" style="height:200px;border-radius:10px"></div>
      <div class="skeleton" style="height:200px;border-radius:10px"></div>
    </div>`;
}

// Store full decision data for interactive product selection
let _lastDecision = null;

function renderDecision(d) {
  _lastDecision = d;
  const tp    = d.top_pick || {};
  const conf  = d.purchase_confidence || 0;
  const alts  = d.alternatives || [];
  const vs    = d.value_scores || {};
  const revs  = d.reviews || {};
  const deals = d.deals || {};
  const comp  = d.comparison;
  const fuqs  = d.follow_up_questions || [];

  let html = `
    <div class="top-pick-card">
      <div class="top-pick-label">🎯 Top Pick</div>
      <div class="top-pick-title">${esc(tp.title)}</div>
      <div class="top-pick-meta">
        <span class="price">${fmt(tp.price)}</span>
        <span class="retailer">@ ${esc(tp.retailer || "")}</span>
      </div>
      <div class="confidence-row">
        ${confBar(conf)}
        <span>${Math.round(conf * 100)}% confidence</span>
      </div>
      <div class="reasoning">${esc(tp.reasoning || "")}</div>
      ${tp.url ? `<a class="buy-btn" href="${esc(tp.url)}" target="_blank" rel="noopener">Buy now →</a>` : ""}
    </div>`;

  // Clickable product grid — all products
  const offers   = d.product_offers || {};
  const allProds = [tp, ...alts];
  const scored   = allProds.map(p => {
    const v    = vs[p.id] || {};
    const deal = deals[p.id] || {};
    const off  = offers[p.id] || {};
    return {
      ...p, ...v,
      price:    p.price    ?? off.price    ?? deal.current_price,
      retailer: p.retailer ?? off.retailer,
      url:      p.url      ?? off.url,
    };
  }).filter(p => p.title);

  if (scored.length) {
    html += `<div class="section-title">All Products — click any to see details</div><div class="product-grid" id="productGrid">`;
    for (const p of scored) {
      const tc    = tierClass(p.value_tier);
      const isTop = p.id === tp.id;
      html += `
        <div class="product-card${isTop ? " selected" : ""}" data-pid="${esc(p.id)}" style="cursor:pointer">
          <div class="product-title">${esc(p.title)}</div>
          ${p.overall_score != null ? `<div class="value-badge ${tc}">#${p.rank || "?"} · ${Math.round(p.overall_score)}/100</div>` : ""}
          ${p.price    ? `<div class="product-price" style="margin-top:6px">${fmt(p.price)}</div>` : ""}
          ${p.retailer ? `<div class="product-retailer">@ ${esc(p.retailer)}</div>` : ""}
          ${p.one_liner ? `<div style="font-size:12px;color:var(--muted);margin-top:4px">${esc(p.one_liner)}</div>` : ""}
          ${p.url ? `<a class="buy-btn" href="${esc(p.url)}" target="_blank" rel="noopener" style="display:inline-block;margin-top:10px;font-size:12px;padding:6px 14px">Buy →</a>` : ""}
          ${isTop ? `<div style="font-size:11px;color:var(--accent);margin-top:6px;font-weight:600">✓ Top Pick</div>` : ""}
        </div>`;
    }
    html += `</div>`;
  }

  // Detail panel — shown for whichever product is selected
  html += `<div id="productDetail"></div>`;

  // Comparison (full depth)
  if (comp) {
    const winnerTitle = (comp.product_titles || {})[comp.overall_winner] || "?";
    html += `
      <div class="compare-winner-card" style="margin-bottom:20px">
        <div class="compare-winner-label">🆚 Comparison</div>
        <div class="compare-winner-name">${esc(winnerTitle)}</div>
        <div class="compare-summary">${esc(comp.summary || "")}</div>
      </div>
      <div class="compare-axes-table" style="margin-bottom:20px">
        <div class="panel-title">Breakdown by axis</div>`;
    for (const ax of (comp.axes || []).slice(0, 6)) {
      const w = (comp.product_titles || {})[ax.winner] || "?";
      html += `
        <div class="compare-axis-row">
          <span class="compare-axis-name">${esc(ax.axis)}</span>
          <span class="compare-axis-winner">${esc(w)}</span>
        </div>`;
    }
    html += `</div>`;
  }

  // Follow-up questions
  if (fuqs.length) {
    html += `<div class="section-title">Questions to ask yourself</div>
      <ul class="followup-list">${fuqs.slice(0, 4).map(q => `<li>${esc(q)}</li>`).join("")}</ul>`;
  }

  return html;
}

function renderProductDetail(pid) {
  const d     = _lastDecision;
  const tp    = d.top_pick || {};
  const revs  = d.reviews || {};
  const deals = d.deals   || {};
  const alts  = d.alternatives || [];

  const allProds = [tp, ...alts.map(a => ({ id: a.id, title: a.title }))];
  const prod  = allProds.find(p => p.id === pid) || {};
  const rev   = revs[pid]  || {};
  const deal  = deals[pid] || {};
  const isTop = pid === tp.id;

  const hasReview = rev.aggregate_score != null;
  const hasDeal   = !!deal.recommendation;

  if (!hasReview && !hasDeal) return "";

  let html = `<div class="panels-row" style="margin-top:4px">`;

  if (hasReview) {
    html += `
      <div class="panel">
        <div class="panel-title">⭐ Reviews — ${esc(prod.title || "").substring(0, 40)}</div>
        <div class="score-bar-row">
          <div class="score-bar"><div class="score-fill" style="width:${rev.aggregate_score}%"></div></div>
          <span class="score-val">${rev.aggregate_score}/100</span>
        </div>
        <p style="font-size:12.5px;color:var(--muted);margin-bottom:10px">${esc(rev.consensus_summary || "")}</p>
        <div class="pros-cons">
          <ul class="pros-list"><strong>Pros</strong>${(rev.pros || []).slice(0,3).map(p => `<li>${esc(p)}</li>`).join("")}</ul>
          <ul class="cons-list"><strong>Cons</strong>${(rev.cons || []).slice(0,3).map(c => `<li>${esc(c)}</li>`).join("")}</ul>
        </div>
        ${(rev.red_flags || []).length ? `<p style="font-size:12px;color:var(--red);margin-top:8px">⚠ ${esc(rev.red_flags[0])}</p>` : ""}
      </div>`;
  }

  if (hasDeal) {
    html += `
      <div class="panel">
        <div class="panel-title">💰 Deal Intel — ${esc(prod.title || "").substring(0, 40)}</div>
        <div class="deal-rec ${deal.recommendation}">${dealIcon(deal.recommendation)}</div>
        <p class="deal-reasoning">${esc(deal.reasoning || "")}</p>
        ${deal.current_price ? `<p style="font-size:13px;margin-top:6px">Price: <strong>${fmt(deal.current_price)}</strong></p>` : ""}
        ${deal.discount_pct  ? `<p style="font-size:12.5px">Discount: <strong>${Math.round(deal.discount_pct)}% off</strong></p>` : ""}
        ${deal.next_likely_sale ? `<p style="font-size:12.5px;color:var(--muted)">Next sale: ${esc(deal.next_likely_sale)} (~${deal.days_to_sale} days)</p>` : ""}
        ${isTop && tp.url ? `<a class="buy-btn" href="${esc(tp.url)}" target="_blank" rel="noopener" style="display:inline-block;margin-top:10px">Buy now →</a>` : ""}
      </div>`;
  }

  html += `</div>`;
  return html;
}

// Wire up product card clicks (delegated from searchResults)
searchResults.addEventListener("click", e => {
  const card = e.target.closest(".product-card[data-pid]");
  if (!card) return;
  const pid = card.dataset.pid;

  // Highlight selected card
  document.querySelectorAll(".product-card[data-pid]").forEach(c => c.classList.remove("selected"));
  card.classList.add("selected");

  // Render detail panel
  const detail = document.getElementById("productDetail");
  if (detail) detail.innerHTML = renderProductDetail(pid);
});

// ── Render detail for top pick on load (after HTML is injected)
async function runSearch() {
  const intent = searchInput.value.trim();
  if (!intent) return;

  setLoading(searchBtn, true, "Searching...");
  searchResults.classList.remove("hidden");
  searchResults.innerHTML = renderSkeletons();

  try {
    const data = await api("/api/decide", {
      method: "POST",
      body: JSON.stringify({ intent, depth: currentDepth, persona_id: personaId }),
    });
    searchResults.innerHTML = renderDecision(data);
    // Auto-show top pick detail
    const detail = document.getElementById("productDetail");
    if (detail && data.top_pick) detail.innerHTML = renderProductDetail(data.top_pick.id);
  } catch (err) {
    searchResults.innerHTML = `<div class="notice error">Error: ${esc(err.message)}</div>`;
  } finally {
    setLoading(searchBtn, false);
  }
}

// ── BASKET TAB ────────────────────────────────────────────────────────────────
const basketInput       = document.getElementById("basketInput");
const basketAddBtn      = document.getElementById("basketAddBtn");
const basketListEl      = document.getElementById("basketList");
const basketEmpty       = document.getElementById("basketEmpty");
const basketOptimizeBtn = document.getElementById("basketOptimizeBtn");
const basketResults     = document.getElementById("basketResults");

basketAddBtn.addEventListener("click", addToBasket);
basketInput.addEventListener("keydown", e => { if (e.key === "Enter") addToBasket(); });

function addToBasket() {
  const q = basketInput.value.trim();
  if (!q) return;
  basketItems.push(q);
  basketInput.value = "";
  renderBasketList();
}

function renderBasketList() {
  const empty = basketItems.length === 0;
  basketEmpty.classList.toggle("hidden", !empty);
  basketOptimizeBtn.classList.toggle("hidden", empty);

  basketListEl.innerHTML = basketItems.map((item, i) => `
    <div class="basket-item">
      <span class="basket-item-name">${esc(item)}</span>
      <button class="basket-item-remove" data-idx="${i}">×</button>
    </div>`).join("");

  basketListEl.querySelectorAll(".basket-item-remove").forEach(btn => {
    btn.addEventListener("click", () => {
      basketItems.splice(Number(btn.dataset.idx), 1);
      renderBasketList();
    });
  });
}

basketOptimizeBtn.addEventListener("click", async () => {
  if (!basketItems.length) return;
  setLoading(basketOptimizeBtn, true, "Optimizing...");
  basketResults.classList.add("hidden");
  try {
    const data = await api("/api/basket/optimize", {
      method: "POST",
      body: JSON.stringify({ queries: basketItems }),
    });
    basketResults.innerHTML = renderBasket(data);
    basketResults.classList.remove("hidden");
  } catch (err) {
    basketResults.innerHTML = `<div class="notice error">Error: ${esc(err.message)}</div>`;
    basketResults.classList.remove("hidden");
  } finally {
    setLoading(basketOptimizeBtn, false);
  }
});

function renderBasket(d) {
  const breakdown = d.retailer_breakdown || {};
  let html = "";

  for (const [domain, s] of Object.entries(breakdown)) {
    html += `
      <div class="retailer-block">
        <div class="retailer-name">🏪 ${esc(domain)}</div>
        <ul class="retailer-items">`;
    for (const item of (d.items || []).filter(it => it.recommended_retailer === domain)) {
      html += `<li>${esc(item.product_title)} — ${fmt(item.price)}
        ${item.product_url ? `<a href="${esc(item.product_url)}" target="_blank" rel="noopener">→ buy</a>` : ""}</li>`;
    }
    html += `</ul>
        <div class="retailer-totals">
          <span>Items: ${fmt(s.subtotal)}</span>
          <span>Shipping: ${s.shipping === 0 ? "Free" : fmt(s.shipping)}</span>
          <span><strong>Order total: ${fmt(s.order_total)}</strong></span>
        </div>
        ${s.note ? `<p style="font-size:12px;color:var(--muted);margin-top:6px">${esc(s.note)}</p>` : ""}
      </div>`;
  }

  html += `
    <div class="basket-summary">
      <span>Subtotal: ${fmt(d.subtotal)}</span>
      <span>Shipping: ${fmt(d.total_shipping)}</span>
      <span><strong>Total: ${fmt(d.total_cost)}</strong></span>
      ${d.savings_vs_single > 0 ? `<span style="color:var(--green)">Saved vs single retailer: ${fmt(d.savings_vs_single)}</span>` : ""}
    </div>`;

  if ((d.notes || []).length) {
    html += `<div style="margin-top:12px;font-size:12.5px;color:var(--muted)">${d.notes.map(n => `💡 ${esc(n)}`).join("<br>")}</div>`;
  }

  return html;
}

// ── COMPARE TAB ───────────────────────────────────────────────────────────────
const compareBtn     = document.getElementById("compareBtn");
const compareResults = document.getElementById("compareResults");

compareBtn.addEventListener("click", async () => {
  const inputs  = [...document.querySelectorAll(".compare-input")];
  const queries = inputs.map(i => i.value.trim()).filter(Boolean);

  if (queries.length < 2) {
    compareResults.innerHTML = `<div class="notice error">Enter at least 2 products to compare.</div>`;
    compareResults.classList.remove("hidden");
    return;
  }

  compareBtn.disabled = true;
  compareBtn.textContent = "Comparing...";
  compareResults.classList.add("hidden");

  try {
    const data = await api("/api/compare", {
      method: "POST",
      body: JSON.stringify({ queries }),
    });
    compareResults.innerHTML = renderComparison(data);
    compareResults.classList.remove("hidden");
  } catch (err) {
    compareResults.innerHTML = `<div class="notice error">Error: ${esc(err.message)}</div>`;
    compareResults.classList.remove("hidden");
  } finally {
    compareBtn.disabled    = false;
    compareBtn.textContent = "Compare";
  }
});

function renderComparison(c) {
  const titles  = c.product_titles || {};
  const winner  = titles[c.overall_winner] || "?";
  const runnerup= titles[c.runner_up]      || "";

  let html = `
    <div class="compare-winner-card">
      <div class="compare-winner-label">Overall Winner</div>
      <div class="compare-winner-name">${esc(winner)}</div>
      ${runnerup ? `<div style="font-size:12.5px;color:var(--muted);margin-bottom:8px">Runner-up: ${esc(runnerup)}</div>` : ""}
      <div class="compare-summary">${esc(c.summary || "")}</div>
    </div>`;

  if ((c.axes || []).length) {
    html += `<div class="compare-axes-table">
      <div class="panel-title">Comparison Axes</div>`;
    for (const ax of c.axes) {
      const w = titles[ax.winner] || "?";
      html += `
        <div class="compare-axis-row">
          <span class="compare-axis-name">${esc(ax.axis)}</span>
          <span class="compare-axis-winner">${esc(w)}</span>
        </div>`;
    }
    html += `</div>`;
  }

  if (c.best_for && Object.keys(c.best_for).length) {
    html += `<div class="compare-best-for">
      <div class="panel-title">Best for...</div>`;
    for (const [persona, pid] of Object.entries(c.best_for).slice(0, 4)) {
      const label = persona.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
      html += `
        <div class="compare-axis-row">
          <span class="compare-axis-name">${esc(label)}</span>
          <span class="compare-axis-winner">${esc(titles[pid] || "?")}</span>
        </div>`;
    }
    html += `</div>`;
  }

  return html;
}

// ── PERSONA TAB ───────────────────────────────────────────────────────────────
const personaIdInput = document.getElementById("personaIdInput");
const loadPersonaBtn = document.getElementById("loadPersonaBtn");
const personaCard    = document.getElementById("personaCard");
const declareMsg     = document.getElementById("declareMsg");

loadPersonaBtn.addEventListener("click", loadPersona);
personaIdInput.addEventListener("keydown", e => { if (e.key === "Enter") loadPersona(); });

async function loadPersona() {
  const id = personaIdInput.value.trim() || "default_user";
  personaId = id;
  loadPersonaBtn.disabled = true;
  try {
    const p = await api(`/api/persona/${encodeURIComponent(id)}`);
    personaCard.innerHTML = renderPersona(p);
    personaCard.classList.remove("hidden");
  } catch (err) {
    personaCard.innerHTML = `<div class="notice error">Error: ${esc(err.message)}</div>`;
    personaCard.classList.remove("hidden");
  } finally {
    loadPersonaBtn.disabled = false;
  }
}

function renderPersona(p) {
  const rows = [
    ["Persona ID",   p.persona_id],
    ["Price tier",   (p.price_tier || "").toUpperCase()],
    ["Priorities",   (p.value_priorities || []).join(" > ")],
    ["Deal sensitivity", `${Math.round((p.deal_sensitivity || 0) * 100)}%`],
    ["Preferred brands", (p.preferred_brands || []).join(", ") || "—"],
    ["Avoided brands",   (p.avoided_brands   || []).join(", ") || "—"],
    ["Sizes",            Object.entries(p.declared_sizes || {}).map(([k,v]) => `${k}: ${v}`).join(", ") || "—"],
    ["Interactions", p.interaction_count || 0],
  ];
  return rows.map(([k, v]) =>
    `<div class="persona-row"><span class="persona-key">${esc(k)}</span><span class="persona-val">${esc(String(v))}</span></div>`
  ).join("");
}

// Declare buttons
document.querySelectorAll("[data-declare]").forEach(btn => {
  btn.addEventListener("click", async () => {
    const type   = btn.dataset.declare;
    const srcId  = btn.dataset.source;
    const key    = btn.dataset.key || "";
    const src    = document.getElementById(srcId);
    const value  = src?.value?.trim() || "";
    if (!value) return;

    const id = personaIdInput.value.trim() || "default_user";
    personaId = id;

    try {
      const res = await api(`/api/persona/${encodeURIComponent(id)}/declare`, {
        method: "POST",
        body: JSON.stringify({ declaration_type: type, value, extra: key }),
      });
      showDeclareMsg(res.message || "Saved.");
      if (src) src.value = "";
    } catch (err) {
      showDeclareMsg("Error: " + err.message, true);
    }
  });
});

function showDeclareMsg(msg, isError = false) {
  declareMsg.textContent = msg;
  declareMsg.classList.remove("hidden");
  if (isError) {
    declareMsg.style.background = "rgba(239,68,68,.12)";
    declareMsg.style.color      = "var(--red)";
  } else {
    declareMsg.style.background = "rgba(99,102,241,.12)";
    declareMsg.style.color      = "var(--accent-h)";
  }
  setTimeout(() => declareMsg.classList.add("hidden"), 4000);
}
