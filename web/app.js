/* ─────────────────────────────────────────────────────────────────────────────
   Channel4  app.js  —  Chat-style UI
   API_BASE auto-detects local vs Railway production.
───────────────────────────────────────────────────────────────────────────── */

const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? "http://localhost:8000"
  : "https://web-production-1a439.up.railway.app";

// ── State ──────────────────────────────────────────────────────────────────────
let basketItems      = [];
let personaId        = "default_user";
let currentDepth     = "standard";
let msgIdCounter     = 0;
const decisions      = {};   // msgId → full decision data
let lastSearchIntent = null; // last resolved intent in this chat session

// ── API ────────────────────────────────────────────────────────────────────────
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

// ── Helpers ────────────────────────────────────────────────────────────────────
function esc(str = "") {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
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

function sortLabel(sort) {
  return { default: "Best Match", "price-asc": "Price ↑", "price-desc": "Price ↓", rating: "Rating", value: "Best Value" }[sort] || sort;
}

function sortProducts(products, sort) {
  const arr = [...products];
  if (sort === "price-asc")  return arr.sort((a, b) => (a.price ?? 9999) - (b.price ?? 9999));
  if (sort === "price-desc") return arr.sort((a, b) => (b.price ?? 0) - (a.price ?? 0));
  if (sort === "rating")     return arr.sort((a, b) => (b.review_score  || 0) - (a.review_score  || 0));
  if (sort === "value")      return arr.sort((a, b) => (b.overall_score || 0) - (a.overall_score || 0));
  return arr;
}

// ── Chat DOM refs ──────────────────────────────────────────────────────────────
const chatMessages = document.getElementById("chatMessages");

function scrollToBottom() {
  chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: "smooth" });
}

// ── Append user message ────────────────────────────────────────────────────────
function appendUserMsg(text) {
  document.getElementById("emptyState")?.remove();
  const row = document.createElement("div");
  row.className = "msg-row user";
  row.innerHTML = `<div class="user-bubble">${esc(text)}</div>`;
  chatMessages.appendChild(row);
  scrollToBottom();
}

// ── Typing indicator ───────────────────────────────────────────────────────────
function appendTyping() {
  const row = document.createElement("div");
  row.className = "msg-row ai";
  row.id = "typingRow";
  row.innerHTML = `
    <div class="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  chatMessages.appendChild(row);
  scrollToBottom();
}

function removeTyping() {
  document.getElementById("typingRow")?.remove();
}

// ── Append AI response ─────────────────────────────────────────────────────────
function appendAiMsg(decision, query) {
  const id = ++msgIdCounter;
  decisions[id] = decision;

  const row = document.createElement("div");
  row.className = "msg-row ai";
  row.dataset.msgId = id;
  row.innerHTML = buildAiRow(id, decision, query, "default");
  chatMessages.appendChild(row);
  scrollToBottom();

  wireFilters(row, id, query);
  wireProductClicks(row, id);

  if (decision.top_pick) {
    showProductDetail(row, id, decision.top_pick.id);
  }
}

// ── Build full AI response HTML ────────────────────────────────────────────────
function buildAiRow(id, d, query, sort) {
  const tp     = d.top_pick || {};
  const conf   = d.purchase_confidence || 0;
  const alts   = d.alternatives || [];
  const vs     = d.value_scores || {};
  const revs   = d.reviews || {};
  const deals  = d.deals || {};
  const comp   = d.comparison;
  const fuqs   = d.follow_up_questions || [];
  const offers = d.product_offers || {};

  // Build merged product list
  const allProds = [tp, ...alts];
  let scored = allProds.map(p => {
    const v    = vs[p.id]    || {};
    const deal = deals[p.id] || {};
    const off  = offers[p.id] || {};
    return {
      ...p, ...v,
      price:        p.price    ?? off.price    ?? deal.current_price,
      retailer:     p.retailer ?? off.retailer,
      url:          p.url      ?? off.url,
      review_score: (revs[p.id] || {}).aggregate_score,
    };
  }).filter(p => p.title);

  scored = sortProducts(scored, sort);

  const count = scored.length;
  const intro = tp.title
    ? `Found <strong>${count} option${count !== 1 ? "s" : ""}</strong> for <strong>"${esc(query)}"</strong> — sorted by ${sortLabel(sort).toLowerCase()}.`
    : `Here are the results for <strong>"${esc(query)}"</strong>.`;

  // Filter bar chips
  const filters = ["default", "price-asc", "price-desc", "rating", "value"];
  const filterChips = filters.map(s =>
    `<button class="filter-chip${sort === s ? " active" : ""}" data-sort="${s}">${sortLabel(s)}</button>`
  ).join("");

  let html = `
    <div class="ai-response">
      <div class="ai-intro">
        <div class="ai-intro-icon">◈</div>
        <span>${intro}</span>
      </div>
      <div class="filter-bar">
        <span class="filter-label">Sort</span>
        ${filterChips}
      </div>
      <div class="ai-results-body">`;

  // Top pick card
  if (tp.title) {
    html += `
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
        <div class="reasoning">${esc(tp.reasoning || d.reasoning || "")}</div>
        ${tp.url ? `<a class="buy-btn" href="${esc(tp.url)}" target="_blank" rel="noopener">Buy now →</a>` : ""}
      </div>`;
  }

  // Product grid
  if (scored.length) {
    html += `<div class="section-title">All Options — click any to see review &amp; deal details</div>
      <div class="product-grid" id="productGrid-${id}">`;

    for (const p of scored) {
      const tc    = tierClass(p.value_tier);
      const isTop = p.id === tp.id;
      html += `
        <div class="product-card${isTop ? " selected" : ""}" data-pid="${esc(p.id)}">
          <div class="product-title">${esc(p.title)}</div>
          ${p.overall_score != null ? `<div class="value-badge ${tc}">#${p.rank || "?"} · ${Math.round(p.overall_score)}/100</div>` : ""}
          ${p.price    ? `<div class="product-price">${fmt(p.price)}</div>` : ""}
          ${p.retailer ? `<div class="product-retailer">@ ${esc(p.retailer)}</div>` : ""}
          ${p.one_liner ? `<div style="font-size:11.5px;color:var(--muted);margin-top:3px;line-height:1.4">${esc(p.one_liner)}</div>` : ""}
          ${p.url ? `<a class="buy-btn" href="${esc(p.url)}" target="_blank" rel="noopener" style="margin-top:10px;font-size:12px;padding:6px 12px">Buy →</a>` : ""}
          ${isTop ? `<div style="font-size:10.5px;color:var(--accent);margin-top:6px;font-weight:700">✓ Top Pick</div>` : ""}
        </div>`;
    }

    html += `</div>`;
  }

  // Detail slot
  html += `<div id="detail-${id}"></div>`;

  // Comparison block
  if (comp) {
    const winnerTitle = (comp.product_titles || {})[comp.overall_winner] || "?";
    html += `
      <div class="compare-winner-card">
        <div class="compare-winner-label">🆚 Comparison</div>
        <div class="compare-winner-name">${esc(winnerTitle)}</div>
        <div class="compare-summary">${esc(comp.summary || "")}</div>
      </div>
      <div class="compare-axes-table">
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
    html += `<div class="section-title">Refine your search</div>
      <ul class="followup-list">${fuqs.slice(0, 4).map(q => `<li>${esc(q)}</li>`).join("")}</ul>`;
  }

  html += `</div></div>`;
  return html;
}

// ── Wire filter chips ──────────────────────────────────────────────────────────
function wireFilters(row, id, query) {
  row.querySelectorAll(".filter-chip[data-sort]").forEach(chip => {
    chip.addEventListener("click", () => {
      const sort = chip.dataset.sort;
      row.innerHTML = buildAiRow(id, decisions[id], query, sort);
      wireFilters(row, id, query);
      wireProductClicks(row, id);
      if (decisions[id].top_pick) showProductDetail(row, id, decisions[id].top_pick.id);
    });
  });
}

// ── Wire product card clicks ───────────────────────────────────────────────────
function wireProductClicks(row, id) {
  row.querySelectorAll(".product-card[data-pid]").forEach(card => {
    card.addEventListener("click", e => {
      if (e.target.closest(".buy-btn")) return;
      const pid = card.dataset.pid;
      row.querySelectorAll(".product-card[data-pid]").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      showProductDetail(row, id, pid);
    });
  });
}

// ── Show review + deal detail panel ───────────────────────────────────────────
function showProductDetail(row, id, pid) {
  const d     = decisions[id];
  const tp    = d.top_pick || {};
  const revs  = d.reviews  || {};
  const deals = d.deals    || {};
  const alts  = d.alternatives || [];
  const allProds = [tp, ...alts.map(a => ({ id: a.id, title: a.title }))];
  const prod  = allProds.find(p => p.id === pid) || {};
  const rev   = revs[pid]  || {};
  const deal  = deals[pid] || {};
  const isTop = pid === tp.id;

  const hasReview = rev.aggregate_score != null;
  const hasDeal   = !!deal.recommendation;

  const slot = row.querySelector(`#detail-${id}`);
  if (!slot) return;
  if (!hasReview && !hasDeal) { slot.innerHTML = ""; return; }

  let html = `<div class="panels-row">`;

  if (hasReview) {
    html += `
      <div class="panel">
        <div class="panel-title">⭐ Reviews — ${esc((prod.title || "").substring(0, 38))}</div>
        <div class="score-bar-row">
          <div class="score-bar"><div class="score-fill" style="width:${rev.aggregate_score}%"></div></div>
          <span class="score-val">${rev.aggregate_score}/100</span>
        </div>
        <p style="font-size:12px;color:var(--muted);margin-bottom:10px;line-height:1.5">${esc(rev.consensus_summary || "")}</p>
        <div class="pros-cons">
          <ul class="pros-list"><strong>Pros</strong>${(rev.pros || []).slice(0,3).map(p => `<li>${esc(p)}</li>`).join("")}</ul>
          <ul class="cons-list"><strong>Cons</strong>${(rev.cons || []).slice(0,3).map(c => `<li>${esc(c)}</li>`).join("")}</ul>
        </div>
        ${(rev.red_flags || []).length ? `<p style="font-size:11.5px;color:var(--red);margin-top:8px">⚠ ${esc(rev.red_flags[0])}</p>` : ""}
      </div>`;
  }

  if (hasDeal) {
    html += `
      <div class="panel">
        <div class="panel-title">💰 Deal Intel — ${esc((prod.title || "").substring(0, 38))}</div>
        <div class="deal-rec ${deal.recommendation}">${dealIcon(deal.recommendation)}</div>
        <p class="deal-reasoning">${esc(deal.reasoning || "")}</p>
        ${deal.current_price ? `<p style="font-size:13px;margin-top:7px">Price: <strong>${fmt(deal.current_price)}</strong></p>` : ""}
        ${deal.discount_pct  ? `<p style="font-size:12px">Discount: <strong>${Math.round(deal.discount_pct)}% off</strong></p>` : ""}
        ${deal.next_likely_sale ? `<p style="font-size:12px;color:var(--muted)">Next sale: ${esc(deal.next_likely_sale)} (~${deal.days_to_sale} days)</p>` : ""}
        ${isTop && tp.url ? `<a class="buy-btn" href="${esc(tp.url)}" target="_blank" rel="noopener" style="margin-top:10px">Buy now →</a>` : ""}
      </div>`;
  }

  html += `</div>`;
  slot.innerHTML = html;
}

// ── Append error message ───────────────────────────────────────────────────────
function appendErrorMsg(message) {
  const row = document.createElement("div");
  row.className = "msg-row ai";
  row.innerHTML = `
    <div class="ai-response">
      <div class="ai-results-body">
        <div class="notice error">${esc(message)}</div>
      </div>
    </div>`;
  chatMessages.appendChild(row);
  scrollToBottom();
}

// ── Send message ───────────────────────────────────────────────────────────────
const chatInput = document.getElementById("chatInput");
const sendBtn   = document.getElementById("sendBtn");

chatInput.addEventListener("input", () => {
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
});

chatInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

sendBtn.addEventListener("click", sendMessage);

async function sendMessage() {
  const rawMessage = chatInput.value.trim();
  if (!rawMessage || sendBtn.disabled) return;

  chatInput.value = "";
  chatInput.style.height = "auto";
  sendBtn.disabled = true;

  appendUserMsg(rawMessage);
  appendTyping();

  try {
    const body = {
      intent:     rawMessage,
      depth:      currentDepth,
      persona_id: personaId,
    };
    // Pass the previous context so the backend can resolve a combined intent
    if (lastSearchIntent) {
      body.previous_intent = lastSearchIntent;
    }

    const data = await api("/api/decide", {
      method: "POST",
      body: JSON.stringify(body),
    });

    // Track the resolved intent for the next follow-up
    // Use the intent the API actually searched for (previous + current)
    lastSearchIntent = lastSearchIntent
      ? `${lastSearchIntent}, ${rawMessage}`
      : rawMessage;

    removeTyping();
    appendAiMsg(data, rawMessage);
  } catch (err) {
    removeTyping();
    appendErrorMsg("Something went wrong: " + err.message);
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

// ── Example chips (empty state) ────────────────────────────────────────────────
function wireChips() {
  document.querySelectorAll(".chip[data-query]").forEach(chip => {
    chip.addEventListener("click", () => {
      lastSearchIntent = null;  // chips are always fresh topics
      chatInput.value = chip.dataset.query;
      chatInput.style.height = "auto";
      sendMessage();
    });
  });
}
wireChips();

// ── New chat ───────────────────────────────────────────────────────────────────
document.getElementById("newChatBtn").addEventListener("click", () => {
  lastSearchIntent = null;  // clear conversation context
  chatMessages.innerHTML = `
    <div class="empty-state" id="emptyState">
      <div class="empty-logo">◈</div>
      <h1>What are you shopping for?</h1>
      <p>Describe what you need — I'll find, rank, and analyse the best options for you.</p>
      <div class="example-chips">
        <button class="chip" data-query="wireless headphones for the gym under $150">wireless headphones for the gym under $150</button>
        <button class="chip" data-query="best bluetooth speaker under $100">best bluetooth speaker under $100</button>
        <button class="chip" data-query="noise cancelling headphones for travel">noise-cancelling headphones for travel</button>
        <button class="chip" data-query="electric standing desk">electric standing desk</button>
        <button class="chip" data-query="yoga mat for beginners">yoga mat for beginners</button>
      </div>
    </div>`;
  wireChips();
  chatInput.value = "";
  chatInput.style.height = "auto";
  chatInput.focus();
});

// ── Depth picker ───────────────────────────────────────────────────────────────
document.getElementById("depthSelect").addEventListener("change", e => {
  currentDepth = e.target.value;
});

// ── Side panel ─────────────────────────────────────────────────────────────────
const sidePanel      = document.getElementById("sidePanel");
const sidePanelBody  = document.getElementById("sidePanelBody");
const sidePanelTitle = document.getElementById("sidePanelTitle");
const sideOverlay    = document.getElementById("sideOverlay");

let currentPanel = null;

function openPanel(name) {
  if (currentPanel === name) { closePanel(); return; }
  currentPanel = name;
  sidePanel.classList.remove("hidden");
  sideOverlay.classList.remove("hidden");
  if (name === "basket")  renderBasketPanel();
  if (name === "compare") renderComparePanel();
  if (name === "profile") renderProfilePanel();
}

function closePanel() {
  currentPanel = null;
  sidePanel.classList.add("hidden");
  sideOverlay.classList.add("hidden");
}

document.getElementById("sideClose").addEventListener("click", closePanel);
sideOverlay.addEventListener("click", closePanel);
document.getElementById("basketToggle").addEventListener("click",  () => openPanel("basket"));
document.getElementById("compareToggle").addEventListener("click", () => openPanel("compare"));
document.getElementById("profileToggle").addEventListener("click", () => openPanel("profile"));

// ── BASKET PANEL ───────────────────────────────────────────────────────────────
function renderBasketPanel() {
  sidePanelTitle.textContent = "🛒 Basket Optimizer";
  sidePanelBody.innerHTML = `
    <p class="panel-desc">Add items and find the cheapest split across retailers — factoring in shipping.</p>
    <div class="basket-add">
      <input class="side-input" id="basketInput" type="text" placeholder="Add an item..." autocomplete="off" />
      <button class="btn-secondary" id="basketAddBtn">Add</button>
    </div>
    <div class="basket-list" id="basketListEl"></div>
    <div id="basketEmptyMsg"></div>
    <div id="basketOptimizeWrap"></div>
    <div class="basket-results hidden" id="basketResults"></div>`;

  renderBasketItems();

  const basketInput  = document.getElementById("basketInput");
  const basketAddBtn = document.getElementById("basketAddBtn");

  function addToBasket() {
    const q = basketInput.value.trim();
    if (!q) return;
    basketItems.push(q);
    basketInput.value = "";
    renderBasketItems();
  }

  basketAddBtn.addEventListener("click", addToBasket);
  basketInput.addEventListener("keydown", e => { if (e.key === "Enter") addToBasket(); });
}

function renderBasketItems() {
  const listEl   = document.getElementById("basketListEl");
  const emptyMsg = document.getElementById("basketEmptyMsg");
  const optWrap  = document.getElementById("basketOptimizeWrap");
  if (!listEl) return;

  const empty = basketItems.length === 0;

  listEl.innerHTML = basketItems.map((item, i) => `
    <div class="basket-item">
      <span class="basket-item-name">${esc(item)}</span>
      <button class="basket-item-remove" data-idx="${i}">×</button>
    </div>`).join("");

  listEl.querySelectorAll(".basket-item-remove").forEach(btn => {
    btn.addEventListener("click", () => {
      basketItems.splice(Number(btn.dataset.idx), 1);
      renderBasketItems();
    });
  });

  if (emptyMsg) emptyMsg.innerHTML = empty ? `<div class="empty-state-small">Your basket is empty. Add items above.</div>` : "";

  if (optWrap) {
    optWrap.innerHTML = empty ? "" : `
      <button class="btn-primary" id="basketOptimizeBtn">
        <span class="btn-text">Optimize Basket</span>
        <span class="hidden btn-loader">Optimizing…</span>
      </button>`;

    document.getElementById("basketOptimizeBtn")?.addEventListener("click", async () => {
      if (!basketItems.length) return;
      const btn = document.getElementById("basketOptimizeBtn");
      const results = document.getElementById("basketResults");
      btn.disabled = true;
      btn.querySelector(".btn-text").classList.add("hidden");
      btn.querySelector(".btn-loader").classList.remove("hidden");
      results.classList.add("hidden");
      try {
        const data = await api("/api/basket/optimize", {
          method: "POST",
          body: JSON.stringify({ queries: basketItems }),
        });
        results.innerHTML = renderBasketResult(data);
        results.classList.remove("hidden");
      } catch (err) {
        results.innerHTML = `<div class="notice error">Error: ${esc(err.message)}</div>`;
        results.classList.remove("hidden");
      } finally {
        btn.disabled = false;
        btn.querySelector(".btn-text").classList.remove("hidden");
        btn.querySelector(".btn-loader").classList.add("hidden");
      }
    });
  }
}

function renderBasketResult(d) {
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
          <span><strong>Total: ${fmt(s.order_total)}</strong></span>
        </div>
        ${s.note ? `<p style="font-size:11.5px;color:var(--muted);margin-top:6px">${esc(s.note)}</p>` : ""}
      </div>`;
  }
  html += `
    <div class="basket-summary">
      <span>Subtotal: ${fmt(d.subtotal)}</span>
      <span>Shipping: ${fmt(d.total_shipping)}</span>
      <span><strong>Total: ${fmt(d.total_cost)}</strong></span>
      ${d.savings_vs_single > 0 ? `<span style="color:var(--green)">Saved: ${fmt(d.savings_vs_single)}</span>` : ""}
    </div>`;
  if ((d.notes || []).length) {
    html += `<div style="margin-top:10px;font-size:12px;color:var(--muted)">${d.notes.map(n => `💡 ${esc(n)}`).join("<br>")}</div>`;
  }
  return html;
}

// ── COMPARE PANEL ──────────────────────────────────────────────────────────────
function renderComparePanel() {
  sidePanelTitle.textContent = "⚖️ Compare Products";
  sidePanelBody.innerHTML = `
    <p class="panel-desc">Enter 2–4 product searches for a side-by-side intelligence breakdown.</p>
    <div class="compare-inputs">
      <input type="text" class="side-input compare-input" placeholder="Product 1 (e.g. Sony WH-1000XM5)" />
      <input type="text" class="side-input compare-input" placeholder="Product 2 (e.g. Apple AirPods Max)" />
      <input type="text" class="side-input compare-input" placeholder="Product 3 (optional)" />
    </div>
    <button class="btn-primary" id="compareBtn">Compare</button>
    <div class="compare-results hidden" id="compareResults"></div>`;

  document.getElementById("compareBtn").addEventListener("click", async () => {
    const inputs  = [...sidePanelBody.querySelectorAll(".compare-input")];
    const queries = inputs.map(i => i.value.trim()).filter(Boolean);
    const results = document.getElementById("compareResults");
    const btn     = document.getElementById("compareBtn");

    if (queries.length < 2) {
      results.innerHTML = `<div class="notice error">Enter at least 2 products.</div>`;
      results.classList.remove("hidden");
      return;
    }

    btn.disabled    = true;
    btn.textContent = "Comparing…";
    results.classList.add("hidden");

    try {
      const data = await api("/api/compare", {
        method: "POST",
        body: JSON.stringify({ queries }),
      });
      results.innerHTML = renderCompareResult(data);
      results.classList.remove("hidden");
    } catch (err) {
      results.innerHTML = `<div class="notice error">Error: ${esc(err.message)}</div>`;
      results.classList.remove("hidden");
    } finally {
      btn.disabled    = false;
      btn.textContent = "Compare";
    }
  });
}

function renderCompareResult(c) {
  const titles   = c.product_titles || {};
  const winner   = titles[c.overall_winner] || "?";
  const runnerup = titles[c.runner_up]      || "";

  let html = `
    <div class="compare-winner-card">
      <div class="compare-winner-label">Overall Winner</div>
      <div class="compare-winner-name">${esc(winner)}</div>
      ${runnerup ? `<div style="font-size:12.5px;color:var(--muted);margin-bottom:7px">Runner-up: ${esc(runnerup)}</div>` : ""}
      <div class="compare-summary">${esc(c.summary || "")}</div>
    </div>`;

  if ((c.axes || []).length) {
    html += `<div class="compare-axes-table"><div class="panel-title">Comparison axes</div>`;
    for (const ax of c.axes) {
      html += `
        <div class="compare-axis-row">
          <span class="compare-axis-name">${esc(ax.axis)}</span>
          <span class="compare-axis-winner">${esc(titles[ax.winner] || "?")}</span>
        </div>`;
    }
    html += `</div>`;
  }

  if (c.best_for && Object.keys(c.best_for).length) {
    html += `<div class="compare-best-for"><div class="panel-title">Best for…</div>`;
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

// ── PROFILE PANEL ──────────────────────────────────────────────────────────────
function renderProfilePanel() {
  sidePanelTitle.textContent = "👤 Shopping Profile";
  sidePanelBody.innerHTML = `
    <p class="panel-desc">Channel4 learns your preferences over time and personalises results.</p>
    <div class="persona-id-row">
      <input class="side-input" id="personaIdInput" type="text" placeholder="Profile ID (e.g. your name)" value="${esc(personaId)}" />
      <button class="btn-secondary" id="loadPersonaBtn">Load</button>
    </div>
    <div id="personaCard" class="persona-card hidden"></div>
    <div class="declare-section">
      <h3>Declare Preferences</h3>
      <div class="declare-grid">
        <div class="declare-row">
          <label>Favourite brand</label>
          <input type="text" id="declareBrandPrefer" placeholder="e.g. Nike" />
          <button class="btn-ghost" data-declare="brand_prefer" data-source="declareBrandPrefer">Save</button>
        </div>
        <div class="declare-row">
          <label>Avoid brand</label>
          <input type="text" id="declareBrandAvoid" placeholder="e.g. Generic" />
          <button class="btn-ghost" data-declare="brand_avoid" data-source="declareBrandAvoid">Save</button>
        </div>
        <div class="declare-row">
          <label>Shoe size (US)</label>
          <input type="text" id="declareSizeShoes" placeholder="e.g. 10" />
          <button class="btn-ghost" data-declare="size" data-source="declareSizeShoes" data-key="shoes_us">Save</button>
        </div>
        <div class="declare-row">
          <label>Shirt size</label>
          <input type="text" id="declareSizeShirt" placeholder="e.g. M" />
          <button class="btn-ghost" data-declare="size" data-source="declareSizeShirt" data-key="shirt">Save</button>
        </div>
        <div class="declare-row">
          <label>Price tier</label>
          <select id="declareTier">
            <option value="budget">Budget</option>
            <option value="mid" selected>Mid-range</option>
            <option value="premium">Premium</option>
          </select>
          <button class="btn-ghost" data-declare="tier" data-source="declareTier">Save</button>
        </div>
      </div>
      <div id="declareMsg" class="declare-msg hidden"></div>
    </div>`;

  document.getElementById("loadPersonaBtn").addEventListener("click", loadPersona);
  document.getElementById("personaIdInput").addEventListener("keydown", e => { if (e.key === "Enter") loadPersona(); });

  sidePanelBody.querySelectorAll("[data-declare]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const type  = btn.dataset.declare;
      const srcId = btn.dataset.source;
      const key   = btn.dataset.key || "";
      const src   = document.getElementById(srcId);
      const value = src?.value?.trim() || "";
      if (!value) return;

      const id = document.getElementById("personaIdInput").value.trim() || "default_user";
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
}

async function loadPersona() {
  const id  = document.getElementById("personaIdInput").value.trim() || "default_user";
  personaId = id;
  const btn  = document.getElementById("loadPersonaBtn");
  const card = document.getElementById("personaCard");
  btn.disabled = true;
  try {
    const p = await api(`/api/persona/${encodeURIComponent(id)}`);
    card.innerHTML = renderPersonaCard(p);
    card.classList.remove("hidden");
  } catch (err) {
    card.innerHTML = `<div class="notice error">Error: ${esc(err.message)}</div>`;
    card.classList.remove("hidden");
  } finally {
    btn.disabled = false;
  }
}

function renderPersonaCard(p) {
  const rows = [
    ["Persona ID",        p.persona_id],
    ["Price tier",        (p.price_tier || "").toUpperCase()],
    ["Priorities",        (p.value_priorities || []).join(" > ")],
    ["Deal sensitivity",  `${Math.round((p.deal_sensitivity || 0) * 100)}%`],
    ["Preferred brands",  (p.preferred_brands || []).join(", ") || "—"],
    ["Avoided brands",    (p.avoided_brands   || []).join(", ") || "—"],
    ["Sizes",             Object.entries(p.declared_sizes || {}).map(([k,v]) => `${k}: ${v}`).join(", ") || "—"],
    ["Interactions",      p.interaction_count || 0],
  ];
  return rows.map(([k, v]) =>
    `<div class="persona-row"><span class="persona-key">${esc(k)}</span><span class="persona-val">${esc(String(v))}</span></div>`
  ).join("");
}

function showDeclareMsg(msg, isError = false) {
  const el = document.getElementById("declareMsg");
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
  el.style.background = isError ? "rgba(220,38,38,.08)" : "var(--accent-bg)";
  el.style.color      = isError ? "var(--red)"          : "var(--accent)";
  setTimeout(() => el.classList.add("hidden"), 4000);
}
