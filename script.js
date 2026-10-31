/* =========================================================
   KugelAudio GmbH — Landing page interactions
   ========================================================= */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fmt = (n, d = 0) => n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

  $("#year").textContent = new Date().getFullYear();

  /* ---------- Nav ---------- */
  const nav = $("#nav");
  const hero = $(".hero");
  const onScroll = () => {
    const threshold = hero.offsetHeight - 72;
    nav.classList.toggle("is-scrolled", window.scrollY > threshold);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  const burger = $("#burger");
  burger.addEventListener("click", () => {
    const open = nav.classList.toggle("menu-open");
    burger.setAttribute("aria-expanded", open);
  });
  $$("#mobileMenu a").forEach((a) => a.addEventListener("click", () => {
    nav.classList.remove("menu-open");
    burger.setAttribute("aria-expanded", "false");
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

  $$(".reveal").forEach((el) => {
    // stagger siblings
    const sibs = [...el.parentElement.children].filter((c) => c.classList.contains("reveal"));
    el.style.transitionDelay = `${Math.min(sibs.indexOf(el), 5) * 90}ms`;
    io.observe(el);
  });

  /* =========================================================
     Hero conversation — Kugel Ear 1 flags an unsure name,
     the agent asks once instead of guessing
     ========================================================= */
  const stack = $("#chatStack");
  const done = $("#chatDone");
  const convo = [
    { who: "user", label: "Caller", text: "Hi, this is Viktor Brandt." },
    { who: "ear", label: "Kugel Ear 1 · unsure", alts: [["Viktor", 55], ["Victor", 31], ["Wiktor", 14]] },
    { who: "ai", label: "Your agent · Kugel 3.5", text: "Thanks! Is that Viktor with a K?" },
    { who: "user", label: "Caller", text: "Yes, with a K." },
  ];
  let chatToken = 0;
  const sleep = (ms, token) => new Promise((res, rej) => setTimeout(() => (token === chatToken ? res() : rej("cancel")), ms));

  function bubble(line) {
    const el = document.createElement("div");
    el.className = `bubble bubble--${line.who}`;
    el.innerHTML = line.who === "ear"
      ? `<small>${line.label}</small><div class="bubble__alts">${line.alts.map(([w, p], i) => `<span class="${i ? "" : "is-top"}">${w}<em>${p}%</em></span>`).join("")}</div>`
      : `<small>${line.label}</small><span></span>`;
    stack.appendChild(el);
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add("is-in")));
    return el;
  }

  async function runChat() {
    const token = ++chatToken;
    stack.innerHTML = "";
    done.classList.remove("is-in");
    if (reduceMotion) {
      convo.forEach((line) => { const b = bubble(line); if (line.text) $("span", b).textContent = line.text; b.classList.add("is-in"); });
      done.classList.add("is-in");
      return;
    }
    try {
      await sleep(900, token);
      for (const line of convo) {
        const b = bubble(line);
        if (line.text) {
          const span = $("span", b);
          const caret = document.createElement("i");
          caret.className = "caret";
          b.appendChild(caret);
          await sleep(350, token);
          const words = line.text.split(" ");
          for (let i = 0; i < words.length; i++) {
            span.textContent += (i ? " " : "") + words[i];
            await sleep(line.who === "ai" ? 85 : 110, token);
          }
          caret.remove();
        }
        await sleep(line.who === "ear" ? 1300 : 800, token);
      }
      done.classList.add("is-in");
      await sleep(5200, token);
      $$(".bubble", stack).forEach((b, i) => setTimeout(() => b.classList.add("is-out"), i * 90));
      done.classList.remove("is-in");
      await sleep(800, token);
      runChat();
    } catch (_) { /* restarted */ }
  }
  runChat();

  /* =========================================================
     Benchmarks — figures as published on kugelaudio.com
     ========================================================= */
  const BENCH = {
    stt: {
      title: "kugel-ear-1 · speech to text",
      note: "Speech-to-text results of 16 October 2026. Every model got the same audio and the same judges.",
      models: ["Kugel Ear 1", "ElevenLabs Scribe v2", "OpenAI gpt-transcribe", "Speechmatics Enhanced", "Deepgram Nova-3"],
      tests: [
        { name: "Support calls", d: 1, sub: "words right · higher is better", unit: "%", dir: "up", vals: [93.4, 92.1, 90.3, 90.6, 89.9] },
        { name: "Through a phone line", d: 1, sub: "words right · higher is better", unit: "%", dir: "up", vals: [88.5, 86.7, 86.2, 85.0, 81.2] },
        { name: "Names and addresses", d: 1, sub: "written exactly right · higher is better", unit: "%", dir: "up", vals: [69.0, 49.5, 57.3, 64.7, 59.7] },
        { name: "Time to final transcript", sub: "median · lower is better", unit: " ms", dir: "down", vals: [72, null, 587, 273, 94] },
      ],
    },
    tts: {
      title: "kugel-3.5 · text to speech",
      note: "KugelBench: Kugel 3.5 on 08.10.2026, the other models between 29.09.2026 and 06.10.2026. Every model spoke the same texts and was scored by the same automatic judges.",
      models: ["Kugel 3.5", "ElevenLabs v4 Turbo", "Cartesia Sonic 3.6", "Deepgram Aura-2"],
      tests: [
        { name: "Words in the wrong accent", sub: "given the reference voice · lower is better", unit: "%", dir: "down", vals: [0, 4.3, 0.5, 12.8] },
        { name: "Short words said wrong", sub: "lower is better", unit: "%", dir: "down", vals: [3, 7.7, 6.1, 20.6] },
        { name: "Numbers and codes read in their groups", sub: "higher is better", unit: "%", dir: "up", vals: [90.8, 71.9, 82.6, 0.9] },
        { name: "Numbers read exactly", sub: "higher is better", unit: "%", dir: "up", vals: [97.1, 95.4, 94, 36.1] },
      ],
    },
    lat: {
      title: "streaming text to speech · time to first audio",
      note: "Median time to first audio across the leading streaming voice models, measured over WebSocket streaming. Network round-trip included, connection setup excluded.",
      models: ["Kugel 3", "Cartesia Sonic 3.5", "ElevenLabs Flash v2.5", "Cartesia Sonic Turbo", "Deepgram Aura-1", "ElevenLabs Turbo v2.5", "Deepgram Aura-2", "ElevenLabs Multilingual v2"],
      tests: [
        { name: "Time to first audio", sub: "median · lower is better", unit: " ms", dir: "down", vals: [91, 111, 126, 127, 157, 178, 207, 431], wide: true },
      ],
    },
  };

  const benchGrid = $("#benchGrid");
  const benchTip = $("#benchTip");
  const fmtVal = (v, t) => (v === null ? "not measured" : fmt(v, t.d ?? (t.unit === "%" && v % 1 ? 1 : 0)) + t.unit);

  function renderBench(key) {
    const b = BENCH[key];
    $("#benchTitle").textContent = b.title;
    $("#benchNote").textContent = b.note;
    benchGrid.innerHTML = b.tests.map((t) => {
      const real = t.vals.filter((v) => v !== null);
      const max = Math.max(...real);
      const best = t.dir === "up" ? Math.max(...real) : Math.min(...real);
      const rows = b.models.map((m, i) => {
        const v = t.vals[i];
        const w = v === null ? 0 : (v / max) * 100;
        const ours = i === 0;
        return `<li class="bar${ours ? " is-ours" : ""}${v === null ? " is-na" : ""}" data-tip="${m} · ${t.name}: ${fmtVal(v, t)}">` +
          `<span class="bar__name">${m}</span>` +
          `<span class="bar__track"><i data-w="${w.toFixed(2)}"></i></span>` +
          `<span class="bar__val">${fmtVal(v, t)}${v === best ? '<em>best</em>' : ""}</span></li>`;
      }).join("");
      return `<figure class="bench__card${t.wide ? " bench__card--wide" : ""}"><figcaption><b>${t.name}</b><span>${t.sub}</span></figcaption><ul class="bars">${rows}</ul></figure>`;
    }).join("");
    requestAnimationFrame(() => requestAnimationFrame(() => {
      $$(".bar__track i", benchGrid).forEach((i) => (i.style.width = i.dataset.w + "%"));
    }));
  }

  benchGrid.addEventListener("pointermove", (e) => {
    const row = e.target.closest(".bar");
    if (!row) { benchTip.style.opacity = 0; return; }
    const box = $("#bench").getBoundingClientRect();
    benchTip.textContent = row.dataset.tip;
    benchTip.style.left = e.clientX - box.left + "px";
    benchTip.style.top = e.clientY - box.top + "px";
    benchTip.style.opacity = 1;
  });
  benchGrid.addEventListener("pointerleave", () => (benchTip.style.opacity = 0));

  $$("#bench .seg button").forEach((btn) => btn.addEventListener("click", () => {
    $$("#bench .seg button").forEach((x) => {
      x.classList.toggle("is-active", x === btn);
      x.setAttribute("aria-selected", x === btn);
    });
    renderBench(btn.dataset.bench);
  }));

  const benchIO = new IntersectionObserver(([en]) => {
    if (en.isIntersecting) { renderBench("stt"); benchIO.disconnect(); }
  }, { threshold: 0.2 });
  benchIO.observe($("#bench"));

  /* =========================================================
     Use-case carousel
     ========================================================= */
  const track = $("#cases");
  const prev = $("#casePrev");
  const next = $("#caseNext");
  const step = () => {
    const card = $(".case", track);
    return card ? card.getBoundingClientRect().width + 20 : 300;
  };
  function syncArrows() {
    prev.disabled = track.scrollLeft < 4;
    next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
  }
  prev.addEventListener("click", () => track.scrollBy({ left: -step(), behavior: reduceMotion ? "auto" : "smooth" }));
  next.addEventListener("click", () => track.scrollBy({ left: step(), behavior: reduceMotion ? "auto" : "smooth" }));
  track.addEventListener("scroll", syncArrows, { passive: true });
  window.addEventListener("resize", syncArrows);
  syncArrows();

  /* =========================================================
     Cost calculator — list prices per audio minute, excl. VAT
     ========================================================= */
  const STT_RATE = 0.008;      // kugel-ear-1, per minute of input audio
  const CLARITY_RATE = 0.0015; // clarity-1, per minute of input audio
  const calc = { calls: $("#r-calls"), tts: $("#r-tts"), stt: $("#r-stt"), clarity: $("#r-clarity") };
  const eur = (n, d = 2) => "€" + fmt(n, d);
  let model = { id: "kugel-3.5", rate: 0.0525 };

  function paintRange(inp) {
    const p = ((inp.value - inp.min) / (inp.max - inp.min)) * 100;
    inp.style.setProperty("--p", p + "%");
  }
  const mins = (v) => `${fmt(v, v % 1 ? 1 : 0)} min`;

  function calcCost() {
    const calls = +calc.calls.value, tts = +calc.tts.value, stt = +calc.stt.value, clarity = calc.clarity.checked;
    $("#o-calls").textContent = fmt(calls);
    $("#o-tts").textContent = mins(tts);
    $("#o-stt").textContent = mins(stt);
    [calc.calls, calc.tts, calc.stt].forEach(paintRange);

    const ttsMin = calls * tts, sttMin = calls * stt;
    const lines = [
      ["Text to Speech · " + model.id, ttsMin, model.rate],
      ["Speech to Text · kugel-ear-1", sttMin, STT_RATE],
    ];
    if (clarity) lines.push(["Clarity · clarity-1", sttMin, CLARITY_RATE]);
    const total = lines.reduce((a, [, m, r]) => a + m * r, 0);
    countUp($("#calcOut"), total, { dur: 450, format: (v) => eur(v) });
    $("#calcLines").innerHTML = lines.map(([label, m, r]) =>
      `<div><dt>${label}<small>${fmt(m)} min × €${r}</small></dt><dd>${eur(m * r)}</dd></div>`
    ).join("");
  }

  $$(".seg--calc button").forEach((btn) => btn.addEventListener("click", () => {
    $$(".seg--calc button").forEach((x) => {
      x.classList.toggle("is-active", x === btn);
      x.setAttribute("aria-checked", x === btn);
    });
    model = { id: btn.dataset.model, rate: +btn.dataset.rate };
    calcCost();
  }));
  [calc.calls, calc.tts, calc.stt].forEach((inp) => inp.addEventListener("input", calcCost));
  calc.clarity.addEventListener("change", calcCost);
  calcCost();

  /* ---------- FAQ: one open at a time ---------- */
  $$(".faq__list details").forEach((d) => d.addEventListener("toggle", () => {
    if (d.open) $$(".faq__list details").forEach((o) => o !== d && (o.open = false));
  }));

  /* ---------- Newsletter ---------- */
  $("#newsForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const note = $("#newsNote");
    const email = $("input[type=email]", e.target);
    const consent = $(".news .check input");
    note.classList.remove("ok", "err");
    if (!email.checkValidity() || !email.value) { note.textContent = "Please enter a valid business e-mail."; note.classList.add("err"); email.focus(); return; }
    if (!consent.checked) { note.textContent = "Please confirm you'd like to receive our updates."; note.classList.add("err"); return; }
    note.textContent = "✓ Thanks — you're subscribed.";
    note.classList.add("ok");
    e.target.reset();
    consent.checked = false;
  });
})();
