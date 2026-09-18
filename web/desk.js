(function () {
  "use strict";

  const STATE_KEY = "intake.desk.v1";
  const RANGE_KEY = "intake.timeRange";
  const FILTER_KEY = "intake.filters.queue";
  const TOAST_MS = 4000;

  const ARROW = `<svg class="arrow" viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" r="8.25" fill="none" stroke="currentColor" stroke-width="1.25"/><path d="M6.5 11.5 L11.5 6.5 M7.5 6.5 H11.5 V10.5" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  const PHOTO = {
    glass: ["assets/glass.jpg", "Spiderweb crack across a car windshield, viewed from the passenger seat."],
    flood: ["assets/flood.jpg", "Silver sedan in knee-deep floodwater on a residential street."],
    collision: ["assets/collision.jpg", "Silver hatchback with a crumpled rear bumper in an empty parking lot."],
  };

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

  function applyOverlay(report) {
    return report;
  }

  function normalizeReport(r) {
    const next = Object.assign({}, r);
    if (next.ui_send_state) next.send_state = next.ui_send_state;
    else if (next.send_state === "sent") next.send_state = "numbered";
    const pair = PHOTO[next.peril];
    if (pair) {
      if (!next.photo) next.photo = pair[0];
      if (!next.photo_alt) next.photo_alt = pair[1];
    }
    if (!next.received_at) next.received_at = new Date().toISOString();
    return next;
  }

  function normalizeLog(e) {
    return {
      ts: e.ts,
      id: e.id,
      event: e.event,
      detail: e.detail || e.rule_id || e.claim_number || e.decision || "",
    };
  }

  async function api(method, path, body) {
    const res = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.error || "http " + res.status);
      err.status = res.status;
      err.payload = data;
      throw err;
    }
    return data;
  }

  function inRange(iso, range) {
    if (demoState() === "empty") return false;
    if (!iso) return true;
    const t = new Date(iso).getTime();
    if (Number.isNaN(t)) return true;
    const now = Date.now();
    if (range === "shift") {
      const d = new Date();
      d.setHours(6, 0, 0, 0);
      return t >= d.getTime();
    }
    const days = range === "30d" ? 30 : range === "90d" ? 90 : 7;
    return t >= now - days * 86400000;
  }

  let cache = null;

  async function loadLive() {
    const payload = await api("GET", "/api/queue");
    const rows = (payload.reports || payload.items || []).map(normalizeReport);
    const log = (payload.log || payload.events || []).map(normalizeLog);
    return {
      reports: rows,
      policy: payload.policy || [],
      log,
      updated_at: payload.updated_at || new Date().toISOString(),
    };
  }

  async function loadData(opts) {
    const state = demoState();
    if (state === "error") throw new Error("demo-error");
    if (state === "loading") {
      await new Promise((r) => setTimeout(r, 800));
    }
    if (!cache || (opts && opts.force)) cache = await loadLive();
    const range = getRange();
    const reports = cache.reports.filter((r) => inRange(r.received_at, range));
    const log = (cache.log || []).filter((e) => e.ts && inRange(e.ts, range));
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
      all: cache.reports.slice(),
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
    if (!decision) return "Pending assessment";
    return "Off-desk";
  }

  function badge(decision) {
    if (!decision) return `<span class="badge">Pending</span>`;
    const label = decision === "open" ? "Open" : decision === "hold" ? "Hold" : decision === "refuse" ? "Refuse" : "Off-desk";
    const cls = decision === "open" ? "open" : decision === "hold" ? "hold" : decision === "refuse" ? "refuse" : "off-desk";
    return `<span class="badge badge-${cls}">${label}</span>`;
  }

  function photosLabel(v) {
    return v ? "On file" : "Missing";
  }

  function perilIcon(peril) {
    const stroke = `fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"`;
    const paths = {
      glass: `<rect x="4.5" y="5" width="15" height="14" rx="1.5"/><path d="M12 5v14"/><path d="M12 12L8 8M12 12l4-3M12 12l-3 4M12 12l3.5 4"/>`,
      flood: `<path d="M4 8.5h16"/><path d="M4 13c1.8 0 1.8-2.4 3.6-2.4S9.4 13 11.2 13s1.8-2.4 3.6-2.4 1.8 2.4 3.6 2.4 1.8-2.4 3.6-2.4"/><path d="M4 18c1.8 0 1.8-2.4 3.6-2.4S9.4 18 11.2 18s1.8-2.4 3.6-2.4 1.8 2.4 3.6 2.4 1.8-2.4 3.6-2.4"/>`,
      collision: `<path d="M4.5 15.2h14l-.7-4.1c-.2-1-.9-1.7-1.9-2L12.5 8H9.2L4.5 15.2z"/><circle cx="8" cy="16.6" r="1.35"/><circle cx="16" cy="16.6" r="1.35"/><path d="M19.2 12.4l2 .3M18.8 14.2l2.2.6M19.4 15.8l1.4.9"/>`,
    };
    const inner = paths[peril] || `<circle cx="12" cy="12" r="7"/><path d="M12 9v3l2 2"/>`;
    return `<span class="peril-icon" data-peril="${peril || "other"}" aria-hidden="true"><svg viewBox="0 0 24 24" ${stroke}>${inner}</svg></span>`;
  }

  const LOG_LABEL = {
    refuse_logged: "Refuse logged",
    confirmed: "Confirmed",
    undone: "Undone",
    ask_refused: "Ask refused",
    assess: "Assessed",
    upload: "File added",
  };

  function logMarkup(events, opts) {
    const selected = (opts && opts.selectedId) || "";
    const rows = events || [];
    const body = rows.length
      ? rows
          .map((e) => {
            const claimId = /^CL-\d+/i.test(e.id || "") ? e.id : "";
            const current = claimId && claimId === selected ? ' aria-current="true"' : "";
            const pick = claimId ? ` data-log-id="${claimId}"` : "";
            const tag = claimId ? "button" : "div";
            const type = claimId ? ' type="button"' : "";
            return `<${tag} class="desk-log-row"${type}${pick}${current}>
              <span class="desk-log-when"><time datetime="${e.ts || ""}" title="${e.ts ? absolute(e.ts) : ""}">${e.ts ? relative(e.ts) : "—"}</time></span>
              <span class="desk-log-id numeric">${claimId || "—"}</span>
              <span class="desk-log-event">${LOG_LABEL[e.event] || e.event || ""}</span>
              <span class="desk-log-detail numeric">${e.detail || ""}</span>
            </${tag}>`;
          })
          .join("")
      : `<p class="desk-log-empty">No events on this laptop yet.</p>`;
    return `<aside class="desk-log" id="log" aria-label="Live-ops log">
      <div class="tray-head">This laptop <span class="numeric">${rows.length}</span></div>
      <div class="desk-log-body">${body}</div>
    </aside>`;
  }

  function groupByPeril(rows) {
    const order = ["glass", "flood", "collision"];
    const map = {};
    rows.forEach((r) => {
      const key = r.peril || "other";
      if (!map[key]) map[key] = [];
      map[key].push(r);
    });
    return order
      .filter((k) => map[k] && map[k].length)
      .concat(Object.keys(map).filter((k) => order.indexOf(k) < 0))
      .map((peril) => ({ peril, rows: map[peril] }));
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
          <a href="clerk.html#log" ${current === "log" ? 'aria-current="page"' : ""}>Log</a>
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
        <a href="clerk.html#log">Log</a>
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
      const submit = dialog.querySelector("[type=submit]");
      if (!q) {
        err.hidden = false;
        err.textContent = "Write a question first.";
        return;
      }
      err.hidden = true;
      out.hidden = false;
      out.textContent = "Checking the policy excerpt…";
      if (submit) submit.disabled = true;
      api("POST", "/api/assess", { question: q })
        .then((d) => {
          out.innerHTML = `<p>${badge(d.decision)} <strong>${d.rule_id || ""}</strong></p><blockquote class="quote">${d.quote || ""}</blockquote>`;
          cache = null;
        })
        .catch((ex) => {
          err.hidden = false;
          err.textContent = ex.message || "Could not check the question.";
          out.hidden = true;
        })
        .finally(() => {
          if (submit) submit.disabled = false;
        });
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
    const word = decisionPhrase(report.decision);
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
    cache = null;
    return api("POST", "/api/confirm", { id })
      .then((r) => {
        const row = normalizeReport(r);
        if (row.claim_number) toast("Claim number " + row.claim_number + " minted.");
        return row;
      })
      .catch((ex) => {
        const msg = (ex.payload && ex.payload.error) || ex.message || "";
        if (msg.indexOf("refuse") !== -1) toast("Refuse is not sent.", "error");
        else if (msg.indexOf("hold") !== -1) toast("Hold waits for photos.", "error");
        else toast(msg || "Could not confirm.", "error");
        throw ex;
      });
  }

  function undoReport(id) {
    cache = null;
    return api("POST", "/api/undo", { id }).then((r) => {
      toast("Returned to draft.");
      return loadData({ force: true });
    });
  }

  function assessReport(id) {
    cache = null;
    return api("POST", "/api/assess", { id }).then(normalizeReport);
  }

  function formatSize(bytes) {
    const n = Number(bytes) || 0;
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return Math.round(n / 102.4) / 10 + " KB";
    return Math.round(n / 104857.6) / 10 + " MB";
  }

  function fileBox(r) {
    const files = r.files || [];
    const items = files.length
      ? `<ul class="file-list">${files
          .map(
            (f) => `<li>
              <a href="${f.url}" target="_blank" rel="noopener">${f.name || "file"}</a>
              <span class="numeric">${formatSize(f.size)}</span>
            </li>`
          )
          .join("")}</ul>`
      : `<p class="file-empty">No files on this report yet.</p>`;
    return `<section class="file-box">
      <div class="file-head">
        <h3>Files</h3>
        <label class="btn btn-ghost file-add">Add file
          <input type="file" accept="image/*,.pdf,application/pdf" data-upload="${r.id}" />
        </label>
      </div>
      ${items}
    </section>`;
  }

  function uploadFile(id, file) {
    cache = null;
    const body = new FormData();
    body.append("id", id);
    body.append("file", file, file.name);
    return fetch("/api/upload", { method: "POST", body })
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          const err = new Error(data.error || "upload failed");
          err.payload = data;
          throw err;
        }
        toast("File added to " + id + ".");
        return normalizeReport(data);
      });
  }

  function bindUploads(root, onDone) {
    if (!root) return;
    root.querySelectorAll("[data-upload]").forEach((input) => {
      input.addEventListener("change", () => {
        const id = input.getAttribute("data-upload");
        const file = input.files && input.files[0];
        if (!id || !file) return;
        uploadFile(id, file)
          .then((row) => {
            if (row.decision === "hold" && row.photos) return assessReport(id);
          })
          .then(() => onDone && onDone())
          .catch((ex) => {
            toast((ex.payload && ex.payload.error) || ex.message || "Could not add file.", "error");
          });
      });
    });
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
    perilIcon,
    groupByPeril,
    logMarkup,
    relative,
    absolute,
    scoreCard,
    renderBarChart,
    renderScatter,
    emptyState,
    confirmReport,
    undoReport,
    assessReport,
    fileBox,
    uploadFile,
    bindUploads,
    demoState,
    getQueueFilters,
    setQueueFilters,
    params,
  };
})();
