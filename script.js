/* =========================================================
   KugelAudio GmbH — Landing page interactions
   ========================================================= */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fmt = (n, d = 0) => n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  const eur = (n) => "€" + fmt(Math.round(n));

  $("#year").textContent = new Date().getFullYear();

  /* ---------- Nav ---------- */
  const nav = $("#nav");
  const hero = $(".hero");
  const onScroll = () => {
    const threshold = hero.offsetHeight - 80;
    nav.classList.toggle("is-scrolled", window.scrollY > threshold || nav.classList.contains("menu-open"));
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  const burger = $("#burger");
  burger.addEventListener("click", () => {
    const open = nav.classList.toggle("menu-open");
    burger.setAttribute("aria-expanded", open);
    onScroll();
  });
  $$("#mobileMenu a").forEach((a) => a.addEventListener("click", () => {
    nav.classList.remove("menu-open");
    burger.setAttribute("aria-expanded", "false");
    onScroll();
  }));

  /* ---------- Count-up ---------- */
  function countUp(el, to, { dur = 1600, decimals = 0, prefix = "", suffix = "", format } = {}) {
    if (reduceMotion) { el.textContent = format ? format(to) : prefix + fmt(to, decimals) + suffix; return; }
    const from = parseFloat(el.dataset.current || 0);
    const t0 = performance.now();
    const tick = (t) => {
      const p = Math.max(0, Math.min(1, (t - t0) / dur));
      const e = 1 - Math.pow(1 - p, 4);
      const v = from + (to - from) * e;
      el.textContent = format ? format(v) : prefix + fmt(v, decimals) + suffix;
      if (p < 1) requestAnimationFrame(tick);
      else el.dataset.current = to;
    };
    requestAnimationFrame(tick);
  }

  /* ---------- Reveal on scroll ---------- */
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (!en.isIntersecting) return;
      const el = en.target;
      el.classList.add("is-in");
      $$("[data-count]", el).concat(el.matches("[data-count]") ? [el] : []).forEach((c) => {
        if (c.dataset.done) return;
        c.dataset.done = 1;
        countUp(c, parseFloat(c.dataset.count), {
          decimals: +(c.dataset.decimals || 0),
          prefix: c.dataset.prefix ? c.dataset.prefix.replace("&lt;", "<") : "",
          suffix: c.dataset.suffix || "",
        });
      });
      io.unobserve(el);
    });
  }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });

  $$(".reveal").forEach((el, i) => {
    // stagger siblings
    const sibs = [...el.parentElement.children].filter((c) => c.classList.contains("reveal"));
    el.style.transitionDelay = `${Math.min(sibs.indexOf(el), 5) * 80}ms`;
    io.observe(el);
  });

  /* ---------- Steps line ---------- */
  const stepsIO = new IntersectionObserver(([en]) => {
    if (en.isIntersecting) { $("#stepsFill").style.width = "100%"; stepsIO.disconnect(); }
  }, { threshold: 0.4 });
  stepsIO.observe($("#steps"));

  /* =========================================================
     Brand waves (canvas) — echo of the KugelAudio sine mark
     ========================================================= */
  function waveCanvas(canvas, opts) {
    const ctx = canvas.getContext("2d");
    let w, h, dpr, t = 0, mouse = 0.5, visible = true, raf;
    const lines = opts.lines;

    function size() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function draw() {
      ctx.clearRect(0, 0, w, h);
      const mid = h * opts.y;
      const wl = Math.max(w * opts.wavelength, 520);
      lines.forEach((ln, i) => {
        ctx.beginPath();
        const amp = h * ln.amp * (0.85 + 0.15 * Math.sin(t * 0.6 + i)) * (0.9 + mouse * 0.2);
        for (let x = -10; x <= w + 10; x += 6) {
          const env = Math.sin(Math.PI * Math.min(1, Math.max(0, x / w))) ** 0.6; // soft fade at edges
          const y = mid + Math.sin((x / wl) * Math.PI * 2 + t + ln.phase) * amp * (0.35 + 0.65 * env);
          x === -10 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = ln.color;
        ctx.lineWidth = ln.width;
        ctx.shadowColor = ln.glow || "transparent";
        ctx.shadowBlur = ln.glow ? 18 : 0;
        ctx.stroke();
      });
    }
    function loop() {
      t += opts.speed;
      draw();
      if (visible) raf = requestAnimationFrame(loop);
    }
    size(); draw();
    window.addEventListener("resize", () => { size(); draw(); });
    if (reduceMotion) return;
    canvas.parentElement.addEventListener("pointermove", (e) => {
      const r = canvas.getBoundingClientRect();
      mouse = (e.clientY - r.top) / r.height;
    });
    new IntersectionObserver(([en]) => {
      visible = en.isIntersecting;
      cancelAnimationFrame(raf);
      if (visible) loop();
    }).observe(canvas);
  }

  const brandLines = (scale = 1) => [
    { amp: 0.30 * scale, width: 3,   color: "rgba(255,255,255,.55)", phase: 0 },
    { amp: 0.24 * scale, width: 2.5, color: "rgba(255,207,0,.85)",   phase: 0.05, glow: "rgba(255,207,0,.6)" },
    { amp: 0.18 * scale, width: 2,   color: "rgba(227,6,19,.85)",    phase: 0.1,  glow: "rgba(227,6,19,.6)" },
    { amp: 0.12 * scale, width: 1.2, color: "rgba(255,255,255,.35)", phase: 0.15 },
    ...Array.from({ length: 10 }, (_, i) => ({
      amp: (0.05 + i * 0.03) * scale, width: 0.6, color: `rgba(255,255,255,${0.03 + i * 0.004})`, phase: -0.3 - i * 0.12,
    })),
  ];
  waveCanvas($("#heroWaves"), { y: 0.62, wavelength: 0.9, speed: 0.008, lines: brandLines(1) });
  waveCanvas($("#ctaWaves"), { y: 0.5, wavelength: 1.1, speed: 0.006, lines: brandLines(0.9) });

  /* =========================================================
     Live call simulation
     ========================================================= */
  const transcript = $("#transcript");
  const waveEl = $("#callWave");
  const scoreBar = $("#scoreBar");
  const scoreVal = $("#scoreVal");
  const toast = $("#toast");
  const timerEl = $("#callTimer");
  const BARS = 54;
  const bars = Array.from({ length: BARS }, () => {
    const i = document.createElement("i");
    waveEl.appendChild(i);
    return i;
  });

  const script = [
    { who: "ai", text: "Good morning, Nordlicht Solar — this is Lena. How can I help you today?" },
    { who: "user", text: "Hi, we'd like solar panels on our warehouse roof. Around 2,000 square metres.", set: { project: "PV · 2,000 m² roof" }, score: 34 },
    { who: "ai", text: "Great project! May I have your name and the company you're calling for?" },
    { who: "user", text: "Markus Weber, from Weber Logistik in Hamburg. I run operations.", set: { name: "Markus Weber", company: "Weber Logistik" }, score: 58 },
    { who: "ai", text: "Thanks, Markus. Do you have a budget range and a timeline in mind?" },
    { who: "user", text: "Roughly 150k, and ideally we'd start in Q1.", set: { budget: "~ €150,000", timeline: "Q1 2027" }, score: 87 },
    { who: "ai", text: "Perfect. I've booked a site visit for Tuesday at 10:00 — confirmation is on its way." , done: true },
  ];

  const SCORE_LEN = 2 * Math.PI * 34;
  let simToken = 0, speaking = null, timerStart = 0;

  function setScore(v) {
    scoreBar.style.strokeDashoffset = SCORE_LEN * (1 - v / 100);
    scoreBar.style.stroke = v >= 75 ? "#ffcf00" : v >= 45 ? "#ff9a3c" : "#e30613";
    countUp(scoreVal, v, { dur: 900 });
  }

  function resetCall() {
    transcript.innerHTML = "";
    $$("#fields > div").forEach((d) => { d.classList.remove("is-set"); $("dd", d).textContent = "—"; });
    scoreVal.dataset.current = 0; scoreVal.textContent = "0";
    scoreBar.style.strokeDashoffset = SCORE_LEN;
    toast.classList.remove("is-on");
  }

  const wait = (ms, token) => new Promise((res, rej) => setTimeout(() => (token === simToken ? res() : rej("cancel")), ms));

  async function typeMsg(line, token) {
    const el = document.createElement("div");
    el.className = `msg msg--${line.who}`;
    el.innerHTML = `<small>${line.who === "ai" ? "Lena · AI" : "Caller"}</small><span></span><i class="caret"></i>`;
    transcript.appendChild(el);
    const span = $("span", el);
    speaking = line.who;
    waveEl.className = "callcard__wave " + line.who;
    const words = line.text.split(" ");
    for (let i = 0; i < words.length; i++) {
      span.textContent += (i ? " " : "") + words[i];
      await wait(line.who === "ai" ? 85 : 110, token);
    }
    $(".caret", el).remove();
    speaking = null;
    waveEl.className = "callcard__wave";
  }

  async function runCall() {
    const token = ++simToken;
    resetCall();
    timerStart = performance.now();
    try {
      await wait(700, token);
      for (const line of script) {
        await typeMsg(line, token);
        if (line.set) {
          await wait(250, token);
          for (const [k, v] of Object.entries(line.set)) {
            const row = $(`#fields [data-k="${k}"]`);
            $("dd", row).textContent = v;
            row.classList.add("is-set");
            await wait(220, token);
          }
          setScore(line.score);
        }
        if (line.done) { await wait(500, token); toast.classList.add("is-on"); }
        await wait(650, token);
      }
      await wait(4200, token);
      runCall();
    } catch (_) { /* restarted */ }
  }

  // waveform + timer animation
  (function animateWave() {
    const t = performance.now() / 1000;
    bars.forEach((b, i) => {
      const center = 1 - Math.abs(i - BARS / 2) / (BARS / 2);
      let h;
      if (speaking) {
        const n = Math.sin(t * 13 + i * 0.7) * 0.5 + Math.sin(t * 7.3 + i * 1.9) * 0.35 + Math.random() * 0.4;
        h = 6 + Math.abs(n) * 44 * (0.35 + center * 0.75);
      } else {
        h = 4 + Math.abs(Math.sin(t * 2 + i * 0.4)) * 4 * center;
      }
      b.style.height = h.toFixed(1) + "px";
    });
    const s = Math.floor((performance.now() - timerStart) / 1000);
    timerEl.textContent = String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
    if (!reduceMotion) requestAnimationFrame(animateWave);
  })();

  // start when visible
  const callIO = new IntersectionObserver(([en]) => {
    if (en.isIntersecting) { runCall(); callIO.disconnect(); }
  }, { threshold: 0.3 });
  callIO.observe($("#callcard"));

  $("#listenBtn").addEventListener("click", () => {
    $("#callcard").scrollIntoView({ behavior: "smooth", block: "center" });
    runCall();
  });

  /* =========================================================
     Analytics dashboard
     ========================================================= */
  function rng(seed) { // mulberry32
    return () => {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function makeData(days) {
    const r = rng(days * 7919);
    const calls = [], leads = [];
    for (let i = 0; i < days; i++) {
      const trend = 1 + (i / days) * 0.35;
      const weekday = [0.55, 1, 1.08, 1.05, 1.1, 0.95, 0.6][i % 7];
      const c = Math.round((62 + r() * 18) * trend * weekday);
      calls.push(c);
      leads.push(Math.round(c * (0.22 + r() * 0.08 + (i / days) * 0.06)));
    }
    const sum = (a) => a.reduce((x, y) => x + y, 0);
    const totalCalls = sum(calls), totalLeads = sum(leads);
    const meetings = Math.round(totalLeads * 0.41);
    return {
      calls, leads, totalCalls, totalLeads, meetings,
      conv: (totalLeads / totalCalls) * 100,
      pipe: meetings * 4200,
      deltas: { calls: 18 + r() * 14, leads: 26 + r() * 20, conv: 2 + r() * 3, pipe: 31 + r() * 22 },
      intents: [
        ["New business inquiry", 34 + r() * 6],
        ["Appointment booking", 24 + r() * 5],
        ["Pricing & quotes", 18 + r() * 4],
        ["Support / existing order", 12 + r() * 4],
        ["Other", 6 + r() * 3],
      ],
      aht: 150 + Math.round(r() * 30),
      sent: 88 + Math.round(r() * 6),
      res: 80 + Math.round(r() * 8),
    };
  }

  const svgNS = "http://www.w3.org/2000/svg";
  const chartSvg = $("#chartSvg");
  const chartBox = $("#chart");
  const tip = $("#chartTip");
  let current = null;

  function el(tag, attrs, parent) {
    const n = document.createElementNS(svgNS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    parent && parent.appendChild(n);
    return n;
  }

  function smoothPath(pts) {
    let d = `M${pts[0][0]},${pts[0][1]}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const [x0, y0] = pts[i - 1] || pts[i], [x1, y1] = pts[i], [x2, y2] = pts[i + 1], [x3, y3] = pts[i + 2] || pts[i + 1];
      const c1x = x1 + (x2 - x0) / 6, c1y = y1 + (y2 - y0) / 6, c2x = x2 - (x3 - x1) / 6, c2y = y2 - (y3 - y1) / 6;
      d += ` C${c1x},${c1y} ${c2x},${c2y} ${x2},${y2}`;
    }
    return d;
  }

  function drawChart(data, animate = true) {
    const W = chartBox.clientWidth, H = chartBox.clientHeight;
    const pad = { l: 34, r: 8, t: 10, b: 24 };
    chartSvg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    chartSvg.innerHTML = "";
    const defs = el("defs", {}, chartSvg);
    const g = el("linearGradient", { id: "gLeads", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    el("stop", { offset: "0%", "stop-color": "#ffcf00", "stop-opacity": ".35" }, g);
    el("stop", { offset: "100%", "stop-color": "#ffcf00", "stop-opacity": "0" }, g);

    const max = Math.ceil(Math.max(...data.calls) / 20) * 20;
    const n = data.calls.length;
    const x = (i) => pad.l + (i / (n - 1)) * (W - pad.l - pad.r);
    const y = (v) => pad.t + (1 - v / max) * (H - pad.t - pad.b);

    const grid = el("g", { class: "grid" }, chartSvg);
    const axis = el("g", { class: "axis" }, chartSvg);
    for (let k = 0; k <= 4; k++) {
      const v = (max / 4) * k;
      el("line", { x1: pad.l, x2: W - pad.r, y1: y(v), y2: y(v) }, grid);
      el("text", { x: 0, y: y(v) + 3 }, axis).textContent = Math.round(v);
    }
    const labelEvery = Math.ceil(n / 6);
    for (let i = 0; i < n; i += labelEvery) {
      el("text", { x: x(i), y: H - 6, "text-anchor": "middle" }, axis).textContent = `D${i + 1}`;
    }

    const pc = data.calls.map((v, i) => [x(i), y(v)]);
    const pl = data.leads.map((v, i) => [x(i), y(v)]);
    const area = el("path", { class: "a-leads", d: smoothPath(pl) + ` L${x(n - 1)},${y(0)} L${x(0)},${y(0)} Z`, opacity: 0 }, chartSvg);
    const lc = el("path", { class: "l-calls", d: smoothPath(pc) }, chartSvg);
    const ll = el("path", { class: "l-leads", d: smoothPath(pl) }, chartSvg);
    if (animate && !reduceMotion) {
      [lc, ll].forEach((p) => { const len = p.getTotalLength(); p.style.setProperty("--len", len); p.classList.add("draw"); });
      area.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 900, delay: 600, fill: "forwards", easing: "ease-out" });
    } else area.setAttribute("opacity", 1);

    const hl = el("line", { class: "hover-line", y1: pad.t, y2: H - pad.b, opacity: 0 }, chartSvg);
    const hd = el("circle", { class: "hover-dot", r: 5, opacity: 0 }, chartSvg);

    chartBox.onpointermove = (e) => {
      const r = chartBox.getBoundingClientRect();
      const i = Math.max(0, Math.min(n - 1, Math.round(((e.clientX - r.left - pad.l) / (W - pad.l - pad.r)) * (n - 1))));
      hl.setAttribute("x1", x(i)); hl.setAttribute("x2", x(i)); hl.setAttribute("opacity", 1);
      hd.setAttribute("cx", x(i)); hd.setAttribute("cy", y(data.leads[i])); hd.setAttribute("opacity", 1);
      tip.style.left = x(i) + "px"; tip.style.top = y(data.calls[i]) + "px"; tip.style.opacity = 1;
      tip.innerHTML = `Day ${i + 1} · <b>${data.calls[i]}</b> calls · <b>${data.leads[i]}</b> qualified`;
    };
    chartBox.onpointerleave = () => { hl.setAttribute("opacity", 0); hd.setAttribute("opacity", 0); tip.style.opacity = 0; };
  }

  function renderDash(days, animate = true) {
    const d = makeData(days);
    current = d;
    countUp($("#k-calls"), d.totalCalls);
    countUp($("#k-leads"), d.totalLeads);
    countUp($("#k-conv"), d.conv, { decimals: 1, suffix: "%" });
    countUp($("#k-pipe"), d.pipe, { format: (v) => v >= 1e6 ? "€" + (v / 1e6).toFixed(2) + "M" : "€" + fmt(Math.round(v / 1000)) + "k" });
    $("#d-calls").textContent = `▲ ${d.deltas.calls.toFixed(0)}%`;
    $("#d-leads").textContent = `▲ ${d.deltas.leads.toFixed(0)}%`;
    $("#d-conv").textContent = `▲ ${d.deltas.conv.toFixed(1)} pp`;
    $("#d-pipe").textContent = `▲ ${d.deltas.pipe.toFixed(0)}%`;

    const steps = [
      ["Calls answered", d.totalCalls],
      ["Real conversations", Math.round(d.totalCalls * 0.82)],
      ["Qualified leads", d.totalLeads],
      ["Meetings booked", d.meetings],
    ];
    $("#funnel").innerHTML = steps.map(([k, v]) =>
      `<div class="funnel__row"><div>${k}<b>${fmt(v)}</b></div><span class="funnel__bar"><span data-w="${(v / d.totalCalls) * 100}"></span></span></div>`
    ).join("");
    const totalI = d.intents.reduce((a, [, v]) => a + v, 0);
    $("#intents").innerHTML = d.intents.map(([k, v]) =>
      `<div class="intent">${k}<b>${Math.round((v / totalI) * 100)}%</b><i data-w="${(v / d.intents[0][1]) * 100}"></i></div>`
    ).join("");
    requestAnimationFrame(() => requestAnimationFrame(() => {
      $$("#funnel [data-w]").forEach((s) => (s.style.width = s.dataset.w + "%"));
      $$("#intents [data-w]").forEach((s) => s.style.setProperty("--w", s.dataset.w + "%"));
    }));
    $("#q-aht").textContent = `${Math.floor(d.aht / 60)}:${String(d.aht % 60).padStart(2, "0")}`;
    $("#q-sent").textContent = d.sent + "%";
    $("#q-res").textContent = d.res + "%";
    drawChart(d, animate);
  }

  $$(".seg button").forEach((b) => b.addEventListener("click", () => {
    $$(".seg button").forEach((x) => x.classList.toggle("is-active", x === b));
    renderDash(+b.dataset.range);
  }));

  const dashIO = new IntersectionObserver(([en]) => {
    if (en.isIntersecting) { renderDash(30); dashIO.disconnect(); }
  }, { threshold: 0.25 });
  dashIO.observe($("#dash"));

  let rT;
  window.addEventListener("resize", () => {
    clearTimeout(rT);
    rT = setTimeout(() => current && drawChart(current, false), 150);
  });

  /* =========================================================
     Use cases
     ========================================================= */
  const cases = [
    {
      title: "Turn every listing inquiry into a viewing.",
      text: "Agents are out showing properties — Lena isn't. She answers questions about listings, qualifies buyers on budget and financing and books viewings straight into your calendar.",
      list: ["Pre-qualifies on budget, financing & move-in date", "Books viewings in real time", "Sends exposé via SMS or email"],
      stat: "+62%", label: "more viewings booked per month",
    },
    {
      title: "Fill the service bay and the showroom.",
      text: "From test-drive requests to service appointments and recall campaigns — handle peak Monday mornings without a single caller on hold.",
      list: ["Service & test-drive scheduling", "Trade-in pre-qualification", "Outbound recall & follow-up campaigns"],
      stat: "0 s", label: "average hold time, even on Mondays",
    },
    {
      title: "Give your front desk its time back.",
      text: "Appointment booking, rescheduling and prescription reminders handled empathetically and in compliance with German data protection standards.",
      list: ["Booking & rescheduling 24/7", "Insurance and patient-type triage", "GDPR-compliant, EU-hosted"],
      stat: "−70%", label: "front-desk phone workload",
    },
    {
      title: "An SDR that never sleeps.",
      text: "Qualify inbound demo requests within seconds, call back trial sign-ups and route enterprise prospects to the right AE with a full brief.",
      list: ["Speed-to-lead under 60 seconds", "BANT / MEDDIC qualification", "Auto-routing to the right account exec"],
      stat: "3.4×", label: "more qualified pipeline",
    },
  ];
  const casePanel = $("#casePanel");
  function showCase(i) {
    const c = cases[i];
    $("#caseTitle").textContent = c.title;
    $("#caseText").textContent = c.text;
    $("#caseList").innerHTML = c.list.map((l) => `<li>${l}</li>`).join("");
    $("#caseStat").textContent = c.stat;
    $("#caseStatLabel").textContent = c.label;
    casePanel.classList.remove("swap"); void casePanel.offsetWidth; casePanel.classList.add("swap");
  }
  $$(".cases__tabs button").forEach((b) => b.addEventListener("click", () => {
    $$(".cases__tabs button").forEach((x) => x.classList.toggle("is-active", x === b));
    showCase(+b.dataset.case);
  }));
  showCase(0);

  /* =========================================================
     ROI calculator
     ========================================================= */
  const r = { calls: $("#r-calls"), miss: $("#r-miss"), deal: $("#r-deal"), close: $("#r-close") };
  const roiOut = $("#roiOut");
  function paintRange(inp) {
    const p = ((inp.value - inp.min) / (inp.max - inp.min)) * 100;
    inp.style.setProperty("--p", p + "%");
  }
  function calcROI() {
    const calls = +r.calls.value, miss = +r.miss.value / 100, deal = +r.deal.value, close = +r.close.value / 100;
    $("#o-calls").textContent = fmt(calls);
    $("#o-miss").textContent = Math.round(miss * 100) + "%";
    $("#o-deal").textContent = eur(deal);
    $("#o-close").textContent = Math.round(close * 100) + "%";
    Object.values(r).forEach(paintRange);
    const recoveredCalls = calls * miss * 0.85;           // missed callers who never call back
    const deals = recoveredCalls * close * 12;
    const revenue = deals * deal;
    countUp(roiOut, revenue, { dur: 500, format: eur });
    $("#roiSub").textContent = `≈ ${fmt(Math.round(recoveredCalls))} recovered calls / month → ${fmt(Math.round(deals))} extra deals / year`;
  }
  Object.values(r).forEach((inp) => inp.addEventListener("input", calcROI));
  calcROI();

  /* =========================================================
     Pricing toggle
     ========================================================= */
  $$(".billing button").forEach((b) => b.addEventListener("click", () => {
    $$(".billing button").forEach((x) => x.classList.toggle("is-active", x === b));
    const mode = b.dataset.bill;
    $$(".plan__price b[data-m]").forEach((p) => countUp(p, +p.dataset[mode], { dur: 500 }));
  }));

  /* ---------- FAQ: one open at a time ---------- */
  $$(".faq__list details").forEach((d) => d.addEventListener("toggle", () => {
    if (d.open) $$(".faq__list details").forEach((o) => o !== d && (o.open = false));
  }));

  /* ---------- Demo form ---------- */
  $("#demoForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const note = $("#formNote");
    note.textContent = "✓ Thanks! Our team will reach out within one business day.";
    note.classList.add("ok");
    e.target.reset();
  });
})();
