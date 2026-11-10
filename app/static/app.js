const $ = (id) => document.getElementById(id);
const fmt = (n) => (n ?? 0).toLocaleString("en-IN");
const TEAL = "#14A39A", GREYS = ["#7D8B9C", "#A7B1BE", "#C5CCD6", "#5B6B7F", "#D5DAE1", "#8E9AAA"];
const STORE = "odometrics.profile";

let profile = load() || {};
let meta = null;
const charts = {};

function load() { try { return JSON.parse(localStorage.getItem(STORE)); } catch { return null; } }
function save() { try { localStorage.setItem(STORE, JSON.stringify(profile)); } catch {} }
async function api(path, params = {}) {
  const q = new URLSearchParams(params).toString();
  const r = await fetch(`/api/${path}?${q}`);
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
  return r.json();
}
function delta(v, unit = "%", suffix = "") {
  if (v === null || v === undefined) return `<span class="muted">no comparison</span>`;
  const cls = v > 0 ? "up" : v < 0 ? "down" : "muted";
  const arrow = v > 0 ? "▲" : v < 0 ? "▼" : "";
  return `<span class="${cls}">${arrow} ${Math.abs(v)}${unit}</span>${suffix}`;
}

/* ---------------- onboarding ---------------- */
const STEPS = [
  {
    title: "Which segment do you sell?", help: "One brand per account.",
    render: () => choices([["2W", "Two-wheelers", "Bikes and scooters"], ["4W", "Four-wheelers", "Cars, SUVs, taxis"]], "segment"),
    valid: () => (profile.segment) ? "" : "Choose a segment",
  },
  {
    title: "Which brand do you represent?", help: "Brands registered in Kerala, by volume.",
    before: async () => { meta = await api("meta", { segment: profile.segment }); },
    render: () => listPick(meta.brands.map((b) => ({ value: b.brand, label: b.brand, meta: fmt(b.volume) + " regs" })), "brand", false),
    valid: () => (profile.brand) ? "" : "Choose your brand",
  },
  {
    title: "Are you a pure EV brand?", help: "Pure EV dealers are compared on EV registrations only.",
    before: () => { if (profile.ev_only === undefined) profile.ev_only = !!brandProfile()?.ev_only; },
    render: () => choices([[true, "Pure EV", "Only electric models"], [false, "Mixed", "Petrol, diesel, CNG, hybrid and EV"]], "ev_only"),
    valid: () => (profile.ev_only !== undefined) ? "" : "Choose one",
  },
  {
    title: "Where is your brand positioned?", help: "Used to suggest your real competitors.",
    before: () => {
      const b = brandProfile();
      if (!profile.positioning && b?.positioning) profile.positioning = b.positioning;
      if (!profile.ticket && b?.ticket) profile.ticket = Math.round(((b.ticket[0] + b.ticket[1]) / 2) * 10) / 10;
    },
    render: () => {
      const el = choices([["mass", "Mass", ""], ["mid", "Mid", ""], ["premium", "Premium", ""], ["luxury", "Luxury", ""]], "positioning");
      const wrap = document.createElement("div");
      wrap.innerHTML = `<p style="margin-top:18px">Average ticket size (lakh ₹)</p>
        <input type="number" step="0.1" min="0" id="ticket" value="${profile.ticket ?? ""}" style="width:140px">`;
      wrap.querySelector("input").oninput = (e) => { profile.ticket = parseFloat(e.target.value) || 0; $("w-error").textContent = ""; };
      el.append(wrap);
      return el;
    },
    valid: () => ((profile.positioning && profile.ticket > 0)) ? "" : "Choose positioning and enter a ticket size",
  },
  {
    title: "Which RTOs are in your territory?", help: "Pick every RTO your showrooms sell into.",
    render: () => listPick(meta.rtos.map((r) => ({ value: r.code, label: `${r.code} · ${r.name}`, meta: fmt(r.volume) + " regs" })), "rtos", true),
    valid: () => ((profile.rtos && profile.rtos.length)) ? "" : "Pick at least one RTO",
  },
  {
    title: "Who are your competitors?", help: "Suggested from your segment, positioning and ticket size. Change as you like.",
    before: async () => {
      if (!profile.competitors?.length) {
        const s = await api("suggest", { segment: profile.segment, brand: profile.brand, ev_only: profile.ev_only,
          positioning: profile.positioning, ticket: profile.ticket });
        profile.competitors = s.competitors;
      }
    },
    render: () => {
      const opts = meta.brands.filter((b) => b.brand !== profile.brand)
        .map((b) => ({ value: b.brand, label: b.brand, meta: [b.positioning, b.ev_only ? "EV" : ""].filter(Boolean).join(" · ") }));
      opts.sort((a, b) => profile.competitors.includes(b.value) - profile.competitors.includes(a.value));
      return listPick(opts, "competitors", true);
    },
    valid: () => ((profile.competitors?.length)) ? "" : "Pick at least one competitor",
  },
];
let step = 0;

function brandProfile() { return meta?.brands.find((b) => b.brand === profile.brand); }

function choices(items, key) {
  const box = document.createElement("div");
  box.className = "choices";
  for (const [value, title, sub] of items) {
    const b = document.createElement("button");
    b.className = "choice" + (profile[key] === value ? " on" : "");
    b.innerHTML = `<b>${title}</b>${sub ? `<small>${sub}</small>` : ""}`;
    b.onclick = () => {
      if (profile[key] !== value && key === "segment") { profile = { segment: value }; }
      profile[key] = value;
      if (key === "ev_only" || key === "positioning") profile.competitors = [];
      box.querySelectorAll(".choice").forEach((c) => c.classList.remove("on"));
      b.classList.add("on");
      $("w-error").textContent = "";
    };
    box.append(b);
  }
  return box;
}

function listPick(items, key, multi) {
  const wrap = document.createElement("div");
  const search = Object.assign(document.createElement("input"), { type: "text", placeholder: "Search", className: "search" });
  const list = document.createElement("div");
  list.className = "list";
  const selected = () => (multi ? (profile[key] ||= []) : profile[key]);
  const draw = () => {
    const q = search.value.toLowerCase();
    list.innerHTML = "";
    for (const it of items.filter((i) => i.label.toLowerCase().includes(q))) {
      const row = document.createElement("label");
      const checked = multi ? selected().includes(it.value) : selected() === it.value;
      row.innerHTML = `<span><input type="${multi ? "checkbox" : "radio"}" name="${key}" ${checked ? "checked" : ""}> ${it.label}</span><span class="meta">${it.meta || ""}</span>`;
      row.querySelector("input").onchange = (e) => {
        if (multi) {
          const s = selected();
          e.target.checked ? s.push(it.value) : s.splice(s.indexOf(it.value), 1);
        } else {
          if (key === "brand" && profile.brand !== it.value) {
            delete profile.ev_only; delete profile.positioning; delete profile.ticket; profile.competitors = [];
          }
          profile[key] = it.value;
        }
        $("w-error").textContent = "";
      };
      list.append(row);
    }
  };
  search.oninput = draw;
  draw();
  if (multi) {
    const all = document.createElement("button");
    all.className = "ghost"; all.textContent = "Select all shown"; all.style.marginTop = "10px";
    all.onclick = () => {
      const q = search.value.toLowerCase();
      const s = selected();
      items.filter((i) => i.label.toLowerCase().includes(q)).forEach((i) => s.includes(i.value) || s.push(i.value));
      draw();
    };
    wrap.append(search, list, all);
  } else wrap.append(search, list);
  return wrap;
}

async function showStep() {
  const s = STEPS[step];
  $("steps").innerHTML = STEPS.map((_, i) => `<div class="${i <= step ? "done" : ""}"></div>`).join("");
  $("w-title").textContent = s.title;
  $("w-help").textContent = s.help;
  $("w-error").textContent = "";
  $("w-body").innerHTML = "<p class='muted'>Loading…</p>";
  if (s.before) await s.before();
  $("w-body").innerHTML = "";
  $("w-body").append(s.render());
  $("w-back").style.visibility = step ? "visible" : "hidden";
  $("w-next").textContent = step === STEPS.length - 1 ? "Show my dashboard" : "Next";
}

$("w-next").onclick = async () => {
  const err = STEPS[step].valid();
  if (err) { $("w-error").textContent = err; return; }
  save();
  if (step < STEPS.length - 1) { step++; await showStep(); }
  else { profile.done = true; save(); startDashboard(); }
};
$("w-back").onclick = async () => { if (step) { step--; await showStep(); } };
$("edit-profile").onclick = async () => {
  step = 0; $("dashboard").classList.add("hidden"); $("onboarding").classList.remove("hidden");
  $("edit-profile").classList.add("hidden");
  meta = await api("meta", { segment: profile.segment || "4W" });
  showStep();
};

/* ---------------- dashboard ---------------- */
async function startDashboard() {
  $("onboarding").classList.add("hidden");
  $("dashboard").classList.remove("hidden");
  $("edit-profile").classList.remove("hidden");
  meta = await api("meta", { segment: profile.segment });
  $("asof").textContent = `Data as of ${new Date(meta.as_of).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}`;
  $("f-period").innerHTML = [...meta.periods].reverse().map((p) => `<option value="${p.value}">${p.label}</option>`).join("");
  $("f-fuel").innerHTML = `<option value="">All fuels</option>` + meta.fuels.map((f) => `<option value="${f.value}">${f.label}</option>`).join("");
  $("f-fuel").value = profile.ev_only ? "EV" : "";
  $("f-period").onchange = $("f-fuel").onchange = refresh;
  refresh();
}

async function refresh() {
  $("rto-detail").classList.add("hidden");
  const params = { segment: profile.segment, brand: profile.brand, competitors: profile.competitors.join(","),
    rtos: profile.rtos.join(","), fuel: $("f-fuel").value, period: $("f-period").value };
  let d;
  try { d = await api("dashboard", params); }
  catch (e) { $("d-note").textContent = e.message; return; }
  const fuelName = $("f-fuel").selectedOptions[0].text;
  $("d-title").textContent = `${profile.brand} · ${profile.segment} · ${profile.rtos.length} RTO${profile.rtos.length > 1 ? "s" : ""}`;
  $("d-note").textContent = d.partial
    ? `${d.period_label} is in progress (${d.days_done} of ${d.days_in} days). Growth compares a full-month projection with ${d.prev_label}; share compares like for like. ${fuelName}.`
    : `${d.period_label} compared with ${d.prev_label}. ${fuelName}.`;

  const k = d.kpis;
  $("k-count").textContent = fmt(k.count);
  $("k-count-sub").innerHTML = delta(k.growth, "%", ` <span class="muted">vs ${d.prev_label}</span>`);
  $("k-share").textContent = `${k.share}%`;
  $("k-share-sub").innerHTML = delta(k.share_change, " pts", ` <span class="muted">vs ${d.prev_label}</span>`);
  $("k-rank").textContent = `#${k.rank} of ${k.rank_of}`;
  $("k-rank-sub").innerHTML = `<span class="muted">#${k.market_rank ?? "–"} in the whole territory</span>`;
  $("k-market").textContent = fmt(k.market);
  $("k-market-sub").innerHTML = delta(k.market_growth, "%", ` <span class="muted">vs ${d.prev_label}</span>`);

  $("t-title").textContent = `Competitors, ${d.period_label}`;
  $("t-comp").querySelector("tbody").innerHTML = d.table.map((r) => `
    <tr class="${r.you ? "you" : r.brand === "Others" ? "others" : ""}">
      <td>${r.brand}${r.you ? " (you)" : ""}</td><td class="num">${fmt(r.count)}</td><td class="num">${r.share}%</td>
      <td class="num">${r.share_change === null ? "" : delta(r.share_change, "")}</td></tr>`).join("");

  const brands = Object.keys(d.trend.series);
  drawChart("c-trend", "line", d.trend.labels, brands.map((b, i) => ({
    label: b, data: d.trend.series[b], borderColor: i ? GREYS[(i - 1) % GREYS.length] : TEAL,
    backgroundColor: i ? GREYS[(i - 1) % GREYS.length] : TEAL, borderWidth: i ? 1.5 : 3, pointRadius: i ? 0 : 3, tension: 0.25,
  })), { y: { ticks: { callback: (v) => v + "%" } } });

  const maxShare = Math.max(...d.by_rto.map((r) => r.share), 1);
  $("rto-bars").innerHTML = d.by_rto.map((r) => `
    <div class="bar-row" data-code="${r.code}" title="Leader: ${r.leader} ${r.leader_share}% · market ${fmt(r.market)}">
      <span class="name">${r.code} · ${r.name}</span>
      <div class="bar"><div style="width:${(r.share / maxShare) * 100}%;${r.share_change < 0 ? "background:#C8423B" : ""}"></div></div>
      <span class="num">${r.share}%</span><span class="num">${delta(r.share_change, "")}</span>
    </div>`).join("");
  document.querySelectorAll(".bar-row").forEach((el) => (el.onclick = () => showRto(el.dataset.code)));

  drawChart("c-fuel", "bar", d.fuel_mix.map((f) => f.fuel), [
    { label: profile.brand, data: d.fuel_mix.map((f) => f.you), backgroundColor: TEAL },
    { label: "Market", data: d.fuel_mix.map((f) => f.market), backgroundColor: "#C5CCD6" },
  ], { y: { ticks: { callback: (v) => v + "%" } } });
}

async function showRto(code) {
  const r = await api("rto", { segment: profile.segment, code, brand: profile.brand, fuel: $("f-fuel").value, period: $("f-period").value });
  $("r-title").textContent = `${r.code} · ${r.name}, ${r.period_label} · market ${fmt(r.market)}`;
  $("r-table").querySelector("tbody").innerHTML = r.brands.slice(0, 15).map((b) =>
    `<tr class="${b.you ? "you" : ""}"><td>${b.brand}</td><td class="num">${fmt(b.count)}</td><td class="num">${b.share}%</td></tr>`).join("");
  drawChart("c-rto", "line", r.trend.map((t) => t.label), [
    { label: `${profile.brand} share`, data: r.trend.map((t) => t.share), borderColor: TEAL, backgroundColor: TEAL, borderWidth: 3, tension: 0.25 },
  ], { y: { ticks: { callback: (v) => v + "%" } } });
  $("rto-detail").classList.remove("hidden");
  $("rto-detail").scrollIntoView({ behavior: "smooth", block: "start" });
}
$("r-close").onclick = () => $("rto-detail").classList.add("hidden");

function drawChart(id, type, labels, datasets, scales = {}) {
  charts[id]?.destroy();
  charts[id] = new Chart($(id), {
    type, data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { family: "Inter" } } } },
      scales: { x: { grid: { display: false } }, ...scales },
    },
  });
}

/* ---------------- start ---------------- */
(async () => {
  if (profile.done) startDashboard();
  else { $("onboarding").classList.remove("hidden"); showStep(); }
})();
