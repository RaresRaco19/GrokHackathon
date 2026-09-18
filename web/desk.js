(function () {
  "use strict";

  const STATE_KEY = "intake.desk.v1";
  const RANGE_KEY = "intake.timeRange";
  const FILTER_KEY = "intake.filters.queue";
  const TOAST_MS = 4000;

  const ARROW = `<svg class="arrow" viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" r="8.25" fill="none" stroke="currentColor" stroke-width="1.25"/><path d="M6.5 11.5 L11.5 6.5 M7.5 6.5 H11.5 V10.5" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  const PAYOUT_RE = /payout|settlement|how much|we will pay|payment|\bpays?\b|\$|\bdollars\b|\busd\b|indemnif|reserve/i;
  const OFFDESK_RE = /prescribe|dose|medicine|liable|legal advice|medical/i;

  function params() {
    return new URLSearchParams(location.search);
  }

  function demoState() {
    return params().get("state");
  }

  function loadOverlay() {
    try {
      return JSON.parse(localStorage.getItem(STATE_KEY) || "{}");
    } catch {
      return {};
    }
  }

  function saveOverlay(data) {
    localStorage.setItem(STATE_KEY, JSON.stringify(data));
  }

  function getRange() {
    return localStorage.getItem(RANGE_KEY) || "7d";
  }

  function setRange(v) {
    localStorage.setItem(RANGE_KEY, v);
  }

  function relative(iso) {
    const t = new Date(iso).getTime();
    const s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60) return "just now";
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
  }

  function absolute(iso) {
    const d = new Date(iso);
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}, ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
  }

  function mintNumber(id) {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const stamp = `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}T${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}Z`;
    return `FNOL-${id}-${stamp}`;
  }

  function applyOverlay(report) {
    const o = loadOverlay()[report.id];
    if (!o) return report;
    const next = Object.assign({}, report, o);
    if (o.send_state === "numbered") {
      next.can_confirm = false;
      next.can_undo = true;
    } else if (o.send_state === "draft" && report.decision === "open") {
      next.can_confirm = true;
      next.can_undo = false;
      next.claim_number = null;
    }
    return next;
  }

  function inRange(iso, range) {
    if (demoState() === "empty") return false;
    const t = new Date(iso).getTime();
    const now = Date.now();
    if (range === "shift") {
      const d = new Date();
      d.setHours(6, 0, 0, 0);
      return t >= d.getTime();
    }
    const days = range === "30d" ? 30 : range === "90d" ? 90 : 7;
    return t >= now - days * 86400000;
  }

  async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error("http");
    return res.json();
  }

  async function loadFixture() {
    try {
      const api = await fetchJson("/api/queue");
      if (Array.isArray(api) || (api && api.reports)) {
        return api.reports ? api : { reports: api, policy: [], log: [], kpis: {}, updated_at: new Date().toISOString() };
      }
    } catch {
      /* fixture */
    }
    return fetchJson("desk.json");
  }

  let cache = null;

  async function loadData() {
    const state = demoState();
    if (state === "error") throw new Error("demo-error");
    if (state === "loading") {
      await new Promise((r) => setTimeout(r, 800));
    }
    if (!cache) cache = await loadFixture();
    const range = getRange();
    const reports = cache.reports.map(applyOverlay).filter((r) => inRange(r.received_at, range));
    const log = (cache.log || []).filter((e) => inRange(e.ts, range));
    const overlay = loadOverlay();
    Object.keys(overlay).forEach((id) => {
      if (overlay[id].log_event && !log.some((e) => e.event === overlay[id].log_event.event && e.id === id && e.ts === overlay[id].log_event.ts)) {
        if (inRange(overlay[id].log_event.ts, range)) log.push(overlay[id].log_event);
      }
    });
    log.sort((a, b) => new Date(b.ts) - new Date(a.ts));
    const kpis = {
      reports_in_queue: reports.length,
      rules_in_force: (cache.policy || []).length || 4,
      photos_on_file: reports.filter((r) => r.photos).length,
    };
    return {
      reports,
      policy: cache.policy || [],
      log,
      kpis,
      updated_at: cache.updated_at,
      all: cache.reports.map(applyOverlay),
    };
  }

  function toast(message, kind) {
    let region = document.querySelector(".toast-region");
    if (!region) {
      region = document.createElement("div");
      region.className = "toast-region";
      region.setAttribute("aria-live", "polite");
      document.body.appendChild(region);
    }
    const el = document.createElement("div");
    el.className = "toast" + (kind === "error" ? " toast-err" : "");
    el.setAttribute("role", kind === "error" ? "alert" : "status");
    el.textContent = message;
    region.appendChild(el);
    const t = setTimeout(() => el.remove(), TOAST_MS);
    el.addEventListener("mouseenter", () => clearTimeout(t));
  }

  function decisionPhrase(decision) {
    if (decision === "open") return "Open";
    if (decision === "hold") return "Hold for photos";
    if (decision === "refuse") return "Refuse";
    return "Off-desk";
  }

  function badge(decision) {
    const label = decision === "open" ? "Open" : decision === "hold" ? "Hold" : decision === "refuse" ? "Refuse" : "Off-desk";
    const cls = decision === "open" ? "open" : decision === "hold" ? "hold" : decision === "refuse" ? "refuse" : "off-desk";
    return `<span class="badge badge-${cls}">${label}</span>`;
  }

  function photosLabel(v) {
    return v ? "On file" : "Missing";
  }

  function mountShell(opts) {
    const current = opts.current;
    const cta = opts.cta || { href: "clerk.html", label: "Open desk", disabled: false, title: "" };
    const hideRange = !!opts.hideRange;
    const range = getRange();
    const header = document.createElement("header");
    header.className = "topbar";
    header.innerHTML = `
      <a class="skip" href="#main">Skip to main content</a>
      <div class="topbar-inner">
        <button class="menu-btn icon-btn" type="button" aria-label="Menu" data-menu>☰</button>
        <nav class="nav-links" aria-label="Desk">
          <a href="clerk.html" ${current === "clerk" ? 'aria-current="page"' : ""}>Desk</a>
          <a href="policy.html" ${current === "policy" ? 'aria-current="page"' : ""}>Policy</a>
          <a href="log.html" ${current === "log" ? 'aria-current="page"' : ""}>Log</a>
          <button class="linkish" type="button" data-ask>Ask</button>
        </nav>
        <a class="wordmark" href="index.html" ${current === "overview" ? 'aria-current="page"' : ""}>INTAKE</a>
        <div class="nav-right">
          ${
            hideRange
              ? ""
              : `<label class="sr-only" for="time-range">Time range</label>
          <select id="time-range" class="time-range" aria-label="Time range">
            <option value="7d"${range === "7d" ? " selected" : ""}>Last 7 days</option>
            <option value="30d"${range === "30d" ? " selected" : ""}>Last 30 days</option>
            <option value="90d"${range === "90d" ? " selected" : ""}>Last 90 days</option>
            <option value="shift"${range === "shift" ? " selected" : ""}>This shift</option>
          </select>`
          }
          <span class="clerk">This laptop</span>
          <a class="btn btn-primary" href="${cta.href || "#"}" ${cta.disabled ? 'aria-disabled="true" tabindex="-1"' : ""} title="${cta.title || ""}" data-cta>
            ${cta.label} ${ARROW}
          </a>
        </div>
      </div>
    `;
    document.body.prepend(header);

    const drawer = document.createElement("div");
    drawer.className = "drawer";
    drawer.innerHTML = `
      <div class="drawer-backdrop" data-close-drawer></div>
      <div class="drawer-panel" role="dialog" aria-label="Menu">
        <button class="icon-btn" type="button" aria-label="Close menu" data-close-drawer>✕</button>
        <a href="clerk.html">Desk</a>
        <a href="queue.html">Queue</a>
        <a href="policy.html">Policy</a>
        <a href="log.html">Log</a>
        <button class="linkish" type="button" data-ask>Ask</button>
        <a href="index.html">Intake home</a>
      </div>
    `;
    document.body.appendChild(drawer);

    const dialog = document.createElement("dialog");
    dialog.className = "dialog";
    dialog.innerHTML = `
      <form class="dialog-card" method="dialog" data-ask-form>
        <h2 id="ask-title">Ask the desk</h2>
        <p class="helper" style="color:var(--color-text-muted);font-size:0.875rem;margin:0">Payout and medical-legal questions are refused. The desk quotes the policy line.</p>
        <label for="ask-q">Question</label>
        <textarea id="ask-q" name="q" required></textarea>
        <p class="inline-error" data-ask-err hidden></p>
        <div class="ask-result" data-ask-out hidden></div>
        <div class="dialog-actions">
          <button class="btn btn-ghost" value="cancel" type="button" data-ask-close>Close</button>
          <button class="btn btn-primary" type="submit">Check question</button>
        </div>
      </form>
    `;
    document.body.appendChild(dialog);

    document.querySelectorAll("[data-menu]").forEach((b) =>
      b.addEventListener("click", () => drawer.classList.add("open"))
    );
    document.querySelectorAll("[data-close-drawer]").forEach((b) =>
      b.addEventListener("click", () => drawer.classList.remove("open"))
    );
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        drawer.classList.remove("open");
        if (dialog.open) dialog.close();
      }
    });
    const rangeEl = document.getElementById("time-range");
    if (rangeEl) {
      rangeEl.addEventListener("change", (e) => {
        setRange(e.target.value);
        location.reload();
      });
    }
    if (!window.__intakeAskBound) {
      window.__intakeAskBound = true;
      document.addEventListener("click", (e) => {
        if (!e.target.closest("[data-ask]")) return;
        e.preventDefault();
        document.querySelector(".drawer")?.classList.remove("open");
        const d = document.querySelector("dialog.dialog");
        if (!d) return;
        d.showModal();
        d.querySelector("textarea")?.focus();
      });
    }
    dialog.querySelector("[data-ask-close]").addEventListener("click", () => dialog.close());
    dialog.querySelector("[data-ask-form]").addEventListener("submit", (e) => {
      e.preventDefault();
      const q = dialog.querySelector("textarea").value.trim();
      const err = dialog.querySelector("[data-ask-err]");
      const out = dialog.querySelector("[data-ask-out]");
      if (!q) {
        err.hidden = false;
        err.textContent = "Write a question first.";
        return;
      }
      err.hidden = true;
      let html = "";
      if (PAYOUT_RE.test(q)) {
        html = `<p>${badge("refuse")} <strong>PX-NO-PAY</strong></p><p>PX-NO-PAY. Never write “we will pay” or name a settlement amount.</p>`;
      } else if (OFFDESK_RE.test(q)) {
        html = `<p>${badge("refuse")} Off-desk</p><p>No rule line matched.</p>`;
      } else {
        html = `<p>On-desk. Open the matching report in Queue. The engine quotes policy-excerpt.md; this website does not decide.</p>`;
      }
      out.hidden = false;
      out.innerHTML = html;
    });

    if (!document.querySelector(".toast-region")) {
      const t = document.createElement("div");
      t.className = "toast-region";
      t.setAttribute("aria-live", "polite");
      document.body.appendChild(t);
    }
  }

  function emptyState(title, body, actionLabel, actionHref) {
    return `<div class="empty" role="status"><h2>${title}</h2><p>${body}</p>${
      actionLabel ? `<p><a class="btn btn-primary" href="${actionHref}">${actionLabel}</a></p>` : ""
    }</div>`;
  }

  function scoreCard(report) {
    const items = report.score_items || [];
    const highs = items.filter((i) => i.importance === "high");
    const passedHigh = highs.filter((i) => i.passed).length;
    const pct = highs.length ? Math.round((passedHigh / highs.length) * 100) : 0;
    const word = report.decision === "open" ? "Open" : report.decision === "hold" ? "Hold" : "Refuse";
    const rows = items
      .map((i) => {
        const mark = i.passed ? `<span class="mark pass" aria-label="Pass">✓</span>` : `<span class="mark miss" aria-label="Miss">✕</span>`;
        return `<div class="check-row">${mark}<span>${i.text}</span><span class="pill pill-${i.importance}">${i.importance[0].toUpperCase() + i.importance.slice(1)}</span></div>`;
      })
      .join("");
    return `<article class="score-card" aria-labelledby="score-${report.id}">
      <div class="score-head">
        <div>
          <div class="score-meta" id="score-${report.id}">${report.id} · ${report.peril}</div>
          <div class="score-meta">High checks ${passedHigh} / ${highs.length}</div>
        </div>
        <div class="score-word numeric">${word}</div>
      </div>
      <div class="bar" aria-hidden="true"><span style="width:${pct}%"></span></div>
      ${rows}
      <p class="score-note">${
        report.decision === "open"
          ? "High-importance checks passed. Confirm is the clerk click that mints a number."
          : report.decision === "refuse"
            ? "Flood is excluded. Refuse is logged on this laptop and is not sent."
            : "A high-importance item missed: photos are missing. Hold until they arrive."
      }</p>
    </article>`;
  }

  function renderBarChart(el, reports) {
    const perils = ["glass", "flood", "collision"];
    const series = ["open", "hold", "refuse"];
    const colors = { open: "#1b365d", hold: "#c4a35a", refuse: "#6b2d2d" };
    const counts = {};
    perils.forEach((p) => {
      counts[p] = { open: 0, hold: 0, refuse: 0 };
    });
    reports.forEach((r) => {
      if (counts[r.peril]) counts[r.peril][r.decision] += 1;
    });
    const w = 720;
    const h = 260;
    const pad = { t: 16, r: 8, b: 48, l: 36 };
    const cw = w - pad.l - pad.r;
    const ch = h - pad.t - pad.b;
    const groupW = cw / perils.length;
    const barW = 16;
    const max = Math.max(1, ...perils.flatMap((p) => series.map((s) => counts[p][s])));
    let bars = "";
    perils.forEach((p, gi) => {
      series.forEach((s, si) => {
        const v = counts[p][s];
        const bh = (v / max) * ch;
        const x = pad.l + gi * groupW + groupW / 2 - (series.length * (barW + 4)) / 2 + si * (barW + 4);
        const y = pad.t + ch - bh;
        bars += `<rect x="${x}" y="${y}" width="${barW}" height="${bh}" fill="${colors[s]}"><title>${p} ${s}: ${v}</title></rect>`;
      });
      const lx = pad.l + gi * groupW + groupW / 2;
      bars += `<text x="${lx}" y="${h - 16}" text-anchor="middle" fill="#5c5c5c" font-size="12">${p}</text>`;
    });
    const avgY = pad.t + ch * (1 - 1 / 3);
    el.innerHTML = `<svg class="chart-svg" viewBox="0 0 ${w} ${h}" role="img" aria-labelledby="chart-bar-title">
      <title id="chart-bar-title">Decisions by peril</title>
      <line x1="${pad.l}" y1="${pad.t + ch}" x2="${w - pad.r}" y2="${pad.t + ch}" stroke="#e1ded6"/>
      <line x1="${pad.l}" y1="${avgY}" x2="${w - pad.r}" y2="${avgY}" stroke="#141414" stroke-dasharray="3 3"/>
      ${bars}
    </svg>
    <table class="data sr-chart-data"><caption>Decisions by peril</caption><thead><tr><th>Peril</th><th>Open</th><th>Hold</th><th>Refuse</th></tr></thead><tbody>${perils
      .map((p) => `<tr><td>${p}</td><td class="numeric">${counts[p].open}</td><td class="numeric">${counts[p].hold}</td><td class="numeric">${counts[p].refuse}</td></tr>`)
      .join("")}</tbody></table>`;
  }

  function renderScatter(el, reports) {
    const w = 720;
    const h = 280;
    const pad = { t: 24, r: 24, b: 40, l: 48 };
    const weight = { refuse: 0, hold: 0.5, open: 1 };
    const points = reports
      .map((r) => {
        const x = pad.l + (r.photos ? 0.75 : 0.25) * (w - pad.l - pad.r);
        const y = pad.t + (1 - weight[r.decision]) * (h - pad.t - pad.b);
        const fill = r.decision === "open" ? "#1b365d" : r.decision === "hold" ? "#c4a35a" : "#6b2d2d";
        return `<circle cx="${x}" cy="${y}" r="7" fill="${fill}"><title>${r.id}</title></circle>
          <text x="${x + 10}" y="${y + 4}" font-size="11" fill="#141414">${r.id}</text>`;
      })
      .join("");
    el.innerHTML = `<svg class="chart-svg" viewBox="0 0 ${w} ${h}" role="img" aria-labelledby="chart-sc-title">
      <title id="chart-sc-title">Photos on file vs decision</title>
      <line x1="${pad.l}" y1="${h - pad.b}" x2="${w - pad.r}" y2="${h - pad.b}" stroke="#e1ded6"/>
      <line x1="${pad.l}" y1="${pad.t}" x2="${pad.l}" y2="${h - pad.b}" stroke="#e1ded6"/>
      <text x="${w / 2}" y="${h - 8}" text-anchor="middle" font-size="11" fill="#5c5c5c">Photos (left missing · right on file)</text>
      <text x="8" y="${pad.t + 8}" font-size="11" fill="#5c5c5c">open</text>
      <text x="8" y="${h - pad.b}" font-size="11" fill="#5c5c5c">refuse</text>
      ${points}
    </svg>
    <table class="data sr-chart-data"><caption>Photos vs decision</caption><thead><tr><th>Report</th><th>Photos</th><th>Decision</th></tr></thead><tbody>${reports
      .map((r) => `<tr><td>${r.id}</td><td>${photosLabel(r.photos)}</td><td>${r.decision}</td></tr>`)
      .join("")}</tbody></table>`;
  }

  function confirmReport(id) {
    return loadData().then((data) => {
      const r = data.all.find((x) => x.id === id);
      if (!r) throw new Error("missing");
      if (r.decision === "refuse") {
        toast("Refuse is not sent.", "error");
        return r;
      }
      if (r.decision === "hold") {
        toast("Hold waits for photos.", "error");
        return r;
      }
      const overlay = loadOverlay();
      const ts = new Date().toISOString();
      const number = mintNumber(id);
      overlay[id] = {
        send_state: "numbered",
        claim_number: number,
        log_event: { ts, id, event: "confirmed", detail: r.cover },
      };
      saveOverlay(overlay);
      toast(`Claim number ${number} minted.`);
      return applyOverlay(Object.assign({}, r, overlay[id]));
    });
  }

  function undoReport(id) {
    const overlay = loadOverlay();
    const ts = new Date().toISOString();
    overlay[id] = {
      send_state: "draft",
      claim_number: null,
      log_event: { ts, id, event: "undone", detail: id },
    };
    saveOverlay(overlay);
    toast("Returned to draft.");
    return loadData();
  }

  function getQueueFilters() {
    try {
      return Object.assign({ decision: "all", photos: "all", send_state: "all" }, JSON.parse(localStorage.getItem(FILTER_KEY) || "{}"));
    } catch {
      return { decision: "all", photos: "all", send_state: "all" };
    }
  }

  function setQueueFilters(f) {
    localStorage.setItem(FILTER_KEY, JSON.stringify(f));
  }

  window.Intake = {
    loadData,
    mountShell,
    toast,
    badge,
    decisionPhrase,
    photosLabel,
    relative,
    absolute,
    scoreCard,
    renderBarChart,
    renderScatter,
    emptyState,
    confirmReport,
    undoReport,
    demoState,
    getQueueFilters,
    setQueueFilters,
    params,
  };
})();
