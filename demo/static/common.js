// Shared by every PrivacyLens page: header/nav, helpers, API calls.
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (x) => `${(x * 100).toFixed(1)}%`;
const num = (x) => (x == null ? "—" : x);
const ms = (x) => (x == null ? "" : `${x < 0.1 ? x.toFixed(3) : x.toFixed(2)} ms`);
const kv = (rows) => `<dl class="kv">${rows.filter((r) => r[1] != null && r[1] !== "").map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`;

const LOCAL = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
const WHERE = LOCAL ? "Local" : "Hosted demo";

const SAMPLES = {
  "Checkout form": "Name: Priya Sharma\nCard number: 4532 0151 1283 0366\nExpiry: 09/28\nPhone: +91 98765 43210\nEmail: priya.sharma@example.com",
  "Bank SMS": "Your OTP is 482913 for txn of Rs 2,499 at AMAZON. Do not share. If not you, call 1800-123-4567 or visit https://bank.example.com/report",
  "KYC upload": "PAN: ABCDE1234F\nRegistered mobile 9876543210\nLogin from IP 203.0.113.42 at 10:42",
  "Support chat": "hey, my card 4111-1111-1111-1111 got declined. reach me at test@example.com or 9123456789. verification code 0042",
};

const PAGES = [
  ["/", "Live demo"],
  ["/pipeline", "Pipeline"],
  ["/training", "Model training"],
  ["/evaluation", "Evaluation"],
];

function renderChrome() {
  const here = location.pathname.replace(/\/$/, "") || "/";
  $("top").innerHTML = `
    <header>
      <a class="brand" href="/" style="text-decoration:none;color:inherit">
        <div class="logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/><path d="M8.5 11h5"/></svg>
        </div>
        <div><h1>PrivacyLens</h1><p class="tag">Detect and redact sensitive data before it leaves the device.</p></div>
      </a>
      <div id="status" class="pill"><span class="dot"></span><span id="statusText">Connecting…</span></div>
    </header>
    <nav class="tabs" aria-label="Pages">
      ${PAGES.map(([href, name], i) => `<a href="${href}"${href === here ? ' aria-current="page"' : ""}><span>0${i + 1}</span>${name}</a>`).join("")}
    </nav>`;
  const i = PAGES.findIndex(([href]) => href === here);
  const nx = $("next");
  if (nx && i >= 0) {
    const prev = PAGES[i - 1], next = PAGES[i + 1];
    nx.innerHTML = (prev ? `<a href="${prev[0]}"><small>← Previous</small>${prev[1]}</a>` : "<span></span>") +
                   (next ? `<a class="fwd" href="${next[0]}"><small>Next →</small>${next[1]}</a>` : "");
  }
  const f = $("foot");
  if (f) f.innerHTML = `
    <span>Detection runs on ${LOCAL ? "the local Python backend" : "this demo's server (in real use it runs on-device)"}.</span>
    <span>Types: CARD · PHONE · PAN · EMAIL · IP · URL · OTP</span>
    <span>API: <code>POST /api/sanitize</code> · <code>GET /api/pipeline</code></span>`;
  fetch("/api/health").then((r) => r.ok && setStatus(true, `${WHERE} · 0 leaks`)).catch(() => setStatus(false, "Backend offline"));
}

function setStatus(ok, text) {
  $("status").classList.toggle("bad", !ok);
  $("statusText").textContent = text;
}

function renderOutput(s) {
  if (!s) return '<span class="empty">Safe-to-share text appears here.</span>';
  return esc(s).replace(/\[REDACTED:([A-Z]+)\]/g, '<span class="ph">[REDACTED:$1]</span>');
}

function addSamples(el, onPick) {
  for (const [name, text] of Object.entries(SAMPLES)) {
    const b = document.createElement("button");
    b.className = "sample"; b.textContent = name;
    b.onclick = () => onPick(text);
    el.appendChild(b);
  }
}

// The last text typed on any page, so Pipeline can replay the demo's input.
const lastInput = {
  get() { try { return sessionStorage.getItem("pl:last"); } catch { return null; } },
  set(v) { try { sessionStorage.setItem("pl:last", v); } catch {} },
};

// Debounced, race-safe POST /api/sanitize driver for a textarea.
function liveSanitize(textarea, { onResult, onError }) {
  let last = null, timer = null, seq = 0;
  const go = async () => {
    const text = textarea.value;
    if (text === last) return;
    last = text;
    lastInput.set(text);
    const id = ++seq;
    try {
      const r = await fetch("/api/sanitize", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }),
      });
      const body = await r.json();
      if (id !== seq) return;
      if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Request rejected");
      onResult(body);
      setStatus(body.leaked === 0, body.leaked === 0 ? `${WHERE} · 0 leaks` : `${body.leaked} leaked`);
    } catch (e) {
      if (id !== seq) return;
      last = null;
      onError(e);
      setStatus(false, "Blocked");
    }
  };
  const run = (now) => { clearTimeout(timer); now ? go() : (timer = setTimeout(go, 180)); };
  textarea.addEventListener("input", () => run(false));
  return run;
}

let _pipeline = null;
const getPipeline = () => (_pipeline ??= fetch("/api/pipeline").then((r) => {
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}));

renderChrome();
