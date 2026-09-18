/* UI only. Queue, quotes, confirm, undo, and ask come from python/serve_desk.py
   which calls python/decide.py against md/policy-excerpt.md and data/fnol.json. */

function tone(label) {
  if (label === "open") return { bg: "#dce8d8", fg: "#1e3a29", ring: "#3d6b4f" };
  if (label === "refuse") return { bg: "#f3dcd8", fg: "#6b221c", ring: "#a33b32" };
  if (label === "hold" || label === "hold for photos") {
    return { bg: "#f3e6c8", fg: "#5c4310", ring: "#c4922a" };
  }
  return { bg: "#e4e0d8", fg: "#2a2620", ring: "#8a8478" };
}

const state = { id: null, cases: [], ask: null, notice: null, log: [] };

function current() {
  return state.cases.find((c) => c.id === state.id) || state.cases[0];
}

function shown(c) {
  return (c && (c.label || c.decision)) || "";
}

function renderQueue() {
  const ul = document.getElementById("queue");
  ul.innerHTML = state.cases
    .map((c) => {
      const t = tone(shown(c));
      const active = c.id === state.id;
      const pillBg = active ? t.ring : t.bg;
      const pillFg = active ? "#fbf8f2" : t.fg;
      const photos = c.photos ? "photos on file" : "photos missing";
      return `<li>
      <button type="button" class="qbtn ${active ? "active" : ""}" data-id="${c.id}">
        <div class="row">
          <span class="mono">${c.id}</span>
          <span class="pill" style="background:${pillBg};color:${pillFg}">${shown(c)}</span>
        </div>
        <p class="who">${c.peril || ""}</p>
        <p class="proc">${c.cover || ""} · ${photos}</p>
        <p class="when">${c.send_state || "draft"}${c.claim_number ? " · " + c.claim_number : ""}</p>
      </button>
    </li>`;
    })
    .join("");
  ul.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.id = btn.dataset.id;
      state.ask = null;
      state.notice = null;
      render();
    });
  });
  const count = document.getElementById("queue-count");
  count.textContent = `Queue ${state.cases.length}`;
}

function renderDetail() {
  const c = current();
  if (!c) return;
  const t = tone(shown(c));
  document.getElementById("report-id").textContent = c.id;
  document.getElementById("peril-title").textContent = c.peril || c.id;
  document.getElementById("subtitle").textContent = [c.cover, c.send_state, c.claim_number]
    .filter(Boolean)
    .join(" · ");
  const box = document.getElementById("verdict");
  box.style.background = t.bg;
  box.style.color = t.fg;
  document.getElementById("decision-label").textContent = shown(c);
  document.getElementById("decision-rule").textContent = c.rule_id || "";
  document.getElementById("peril").textContent = c.peril || "";
  document.getElementById("photos").textContent = c.photos ? "on file" : "missing";
  document.getElementById("cover").textContent = c.cover || "";
  document.getElementById("quote-body").textContent = c.quoted || "";
  const sendBits = [c.send_state];
  if (c.claim_number) sendBits.push(c.claim_number);
  if (c.decision === "refuse") sendBits.push("logged, not sent");
  document.getElementById("send-state").textContent = sendBits.filter(Boolean).join(" · ");

  const confirmBtn = document.getElementById("confirm-btn");
  const undoBtn = document.getElementById("undo-btn");
  confirmBtn.disabled = !c.can_confirm;
  undoBtn.disabled = !c.can_undo;
  confirmBtn.textContent = c.decision === "hold" ? "Confirm hold" : "Confirm";

  const notice = document.getElementById("notice");
  if (state.notice) {
    notice.hidden = false;
    notice.textContent = state.notice;
  } else {
    notice.hidden = true;
    notice.textContent = "";
  }

  const reply = document.getElementById("reply");
  if (!state.ask) {
    reply.hidden = true;
    reply.innerHTML = "";
  } else {
    const at = tone(state.ask.label);
    reply.hidden = false;
    reply.style.background = at.bg;
    reply.style.color = at.fg;
    const rule = state.ask.rule_id ? ` · ${state.ask.rule_id}` : "";
    reply.innerHTML = `<p class="title">${state.ask.label}${rule}</p>
      <p class="body">${state.ask.detail || state.ask.quoted || ""}</p>`;
  }

  const log = document.getElementById("log");
  if (!state.log.length) {
    log.innerHTML = "<li>No log lines yet.</li>";
    return;
  }
  log.innerHTML = state.log
    .slice()
    .reverse()
    .map((row) => {
      const bits = [row.ts, row.id, row.event || row.decision, row.claim_number].filter(Boolean);
      return `<li>${bits.join(" · ")}</li>`;
    })
    .join("");
}

function render() {
  renderQueue();
  renderDetail();
}

async function loadQueue() {
  const res = await fetch("/api/queue");
  if (!res.ok) {
    throw new Error("Queue API failed. Start the desk with bin/desk.sh (not a static file open).");
  }
  state.cases = await res.json();
  if (!state.cases.some((c) => c.id === state.id) && state.cases[0]) {
    state.id = state.cases[0].id;
  }
  render();
}

async function loadLog() {
  const res = await fetch("/api/log");
  if (!res.ok) return;
  state.log = await res.json();
  renderDetail();
}

async function postAction(path) {
  const c = current();
  if (!c) return;
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: c.id }),
  });
  const data = await res.json();
  state.notice = res.ok ? null : data.error || "request failed";
  await loadQueue();
  await loadLog();
}

document.getElementById("confirm-btn").addEventListener("click", () => {
  postAction("/api/confirm");
});
document.getElementById("undo-btn").addEventListener("click", () => {
  postAction("/api/undo");
});

document.getElementById("ask-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = document.getElementById("ask-input").value.trim();
  if (!text) return;
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: text }),
  });
  state.ask = await res.json();
  renderDetail();
});

loadQueue()
  .then(loadLog)
  .catch((err) => {
    document.getElementById("queue").innerHTML =
      `<li style="padding:1rem;color:#7a1c1a">${err.message}</li>`;
  });
