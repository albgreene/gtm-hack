/* =========================================================
   KugelAudio GmbH — Sign-up page
   Name + phone only.
   ========================================================= */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  $("#year").textContent = new Date().getFullYear();

  /* ---------- Mobile nav ---------- */
  const nav = $("#nav");
  const burger = $("#burger");
  burger.addEventListener("click", () => {
    const open = nav.classList.toggle("menu-open");
    burger.setAttribute("aria-expanded", open);
  });

  /* =========================================================
     Proof carousel
     ========================================================= */
  const track = $("#proofTrack");
  const items = $$(".proof__item", track);
  const dots = $("#proofDots");
  let idx = 0, timer;

  items.forEach((_, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.setAttribute("role", "tab");
    b.setAttribute("aria-label", `Highlight ${i + 1} of ${items.length}`);
    b.addEventListener("click", () => { go(i); restart(); });
    dots.appendChild(b);
  });

  function go(i) {
    idx = (i + items.length) % items.length;
    const gap = parseFloat(getComputedStyle(track).columnGap) || 48;
    const w = items[0].getBoundingClientRect().width + gap;
    track.style.transform = `translateX(${-idx * w}px)`;
    items.forEach((it, k) => it.classList.toggle("is-active", k === idx));
    $$("button", dots).forEach((d, k) => {
      d.classList.toggle("is-active", k === idx);
      d.setAttribute("aria-selected", k === idx);
    });
  }
  function restart() {
    clearInterval(timer);
    if (!reduceMotion) timer = setInterval(() => go(idx + 1), 6000);
  }
  go(0);
  restart();
  window.addEventListener("resize", () => go(idx));

  /* =========================================================
     Country calling codes
     ISO|Name|dial — NANP territories carry their area code.
     ========================================================= */
  const RAW = "AF|Afghanistan|93,AX|Åland Islands|358,AL|Albania|355,DZ|Algeria|213,AS|American Samoa|1 684,AD|Andorra|376,AO|Angola|244,AI|Anguilla|1 264,AG|Antigua and Barbuda|1 268,AR|Argentina|54,AM|Armenia|374,AW|Aruba|297,AU|Australia|61,AT|Austria|43,AZ|Azerbaijan|994,BS|Bahamas|1 242,BH|Bahrain|973,BD|Bangladesh|880,BB|Barbados|1 246,BY|Belarus|375,BE|Belgium|32,BZ|Belize|501,BJ|Benin|229,BM|Bermuda|1 441,BT|Bhutan|975,BO|Bolivia|591,BA|Bosnia and Herzegovina|387,BW|Botswana|267,BR|Brazil|55,IO|British Indian Ocean Territory|246,VG|British Virgin Islands|1 284,BN|Brunei|673,BG|Bulgaria|359,BF|Burkina Faso|226,BI|Burundi|257,KH|Cambodia|855,CM|Cameroon|237,CA|Canada|1,CV|Cape Verde|238,BQ|Caribbean Netherlands|599,KY|Cayman Islands|1 345,CF|Central African Republic|236,TD|Chad|235,CL|Chile|56,CN|China|86,CO|Colombia|57,KM|Comoros|269,CG|Congo|242,CD|Congo (DRC)|243,CK|Cook Islands|682,CR|Costa Rica|506,CI|Côte d’Ivoire|225,HR|Croatia|385,CU|Cuba|53,CW|Curaçao|599,CY|Cyprus|357,CZ|Czechia|420,DK|Denmark|45,DJ|Djibouti|253,DM|Dominica|1 767,DO|Dominican Republic|1 809,EC|Ecuador|593,EG|Egypt|20,SV|El Salvador|503,GQ|Equatorial Guinea|240,ER|Eritrea|291,EE|Estonia|372,SZ|Eswatini|268,ET|Ethiopia|251,FK|Falkland Islands|500,FO|Faroe Islands|298,FJ|Fiji|679,FI|Finland|358,FR|France|33,GF|French Guiana|594,PF|French Polynesia|689,GA|Gabon|241,GM|Gambia|220,GE|Georgia|995,DE|Germany|49,GH|Ghana|233,GI|Gibraltar|350,GR|Greece|30,GL|Greenland|299,GD|Grenada|1 473,GP|Guadeloupe|590,GU|Guam|1 671,GT|Guatemala|502,GG|Guernsey|44,GN|Guinea|224,GW|Guinea-Bissau|245,GY|Guyana|592,HT|Haiti|509,HN|Honduras|504,HK|Hong Kong|852,HU|Hungary|36,IS|Iceland|354,IN|India|91,ID|Indonesia|62,IR|Iran|98,IQ|Iraq|964,IE|Ireland|353,IM|Isle of Man|44,IL|Israel|972,IT|Italy|39,JM|Jamaica|1 876,JP|Japan|81,JE|Jersey|44,JO|Jordan|962,KZ|Kazakhstan|7,KE|Kenya|254,KI|Kiribati|686,XK|Kosovo|383,KW|Kuwait|965,KG|Kyrgyzstan|996,LA|Laos|856,LV|Latvia|371,LB|Lebanon|961,LS|Lesotho|266,LR|Liberia|231,LY|Libya|218,LI|Liechtenstein|423,LT|Lithuania|370,LU|Luxembourg|352,MO|Macau|853,MG|Madagascar|261,MW|Malawi|265,MY|Malaysia|60,MV|Maldives|960,ML|Mali|223,MT|Malta|356,MH|Marshall Islands|692,MQ|Martinique|596,MR|Mauritania|222,MU|Mauritius|230,YT|Mayotte|262,MX|Mexico|52,FM|Micronesia|691,MD|Moldova|373,MC|Monaco|377,MN|Mongolia|976,ME|Montenegro|382,MS|Montserrat|1 664,MA|Morocco|212,MZ|Mozambique|258,MM|Myanmar|95,NA|Namibia|264,NR|Nauru|674,NP|Nepal|977,NL|Netherlands|31,NC|New Caledonia|687,NZ|New Zealand|64,NI|Nicaragua|505,NE|Niger|227,NG|Nigeria|234,NU|Niue|683,KP|North Korea|850,MK|North Macedonia|389,MP|Northern Mariana Islands|1 670,NO|Norway|47,OM|Oman|968,PK|Pakistan|92,PW|Palau|680,PS|Palestine|970,PA|Panama|507,PG|Papua New Guinea|675,PY|Paraguay|595,PE|Peru|51,PH|Philippines|63,PL|Poland|48,PT|Portugal|351,PR|Puerto Rico|1 787,QA|Qatar|974,RE|Réunion|262,RO|Romania|40,RU|Russia|7,RW|Rwanda|250,BL|Saint Barthélemy|590,SH|Saint Helena|290,KN|Saint Kitts and Nevis|1 869,LC|Saint Lucia|1 758,MF|Saint Martin|590,PM|Saint Pierre and Miquelon|508,VC|Saint Vincent and the Grenadines|1 784,WS|Samoa|685,SM|San Marino|378,ST|São Tomé and Príncipe|239,SA|Saudi Arabia|966,SN|Senegal|221,RS|Serbia|381,SC|Seychelles|248,SL|Sierra Leone|232,SG|Singapore|65,SX|Sint Maarten|1 721,SK|Slovakia|421,SI|Slovenia|386,SB|Solomon Islands|677,SO|Somalia|252,ZA|South Africa|27,KR|South Korea|82,SS|South Sudan|211,ES|Spain|34,LK|Sri Lanka|94,SD|Sudan|249,SR|Suriname|597,SE|Sweden|46,CH|Switzerland|41,SY|Syria|963,TW|Taiwan|886,TJ|Tajikistan|992,TZ|Tanzania|255,TH|Thailand|66,TL|Timor-Leste|670,TG|Togo|228,TK|Tokelau|690,TO|Tonga|676,TT|Trinidad and Tobago|1 868,TN|Tunisia|216,TR|Türkiye|90,TM|Turkmenistan|993,TC|Turks and Caicos Islands|1 649,TV|Tuvalu|688,VI|U.S. Virgin Islands|1 340,UG|Uganda|256,UA|Ukraine|380,AE|United Arab Emirates|971,GB|United Kingdom|44,US|United States|1,UY|Uruguay|598,UZ|Uzbekistan|998,VU|Vanuatu|678,VA|Vatican City|39,VE|Venezuela|58,VN|Vietnam|84,WF|Wallis and Futuna|681,EH|Western Sahara|212,YE|Yemen|967,ZM|Zambia|260,ZW|Zimbabwe|263";
  const COUNTRIES = RAW.split(",").map((row) => {
    const [iso, name, dial] = row.split("|");
    return { iso, name, dial, digits: dial.replace(/\D/g, "") };
  });
  const BY_ISO = Object.fromEntries(COUNTRIES.map((c) => [c.iso, c]));
  const SUGGESTED = ["DE", "AT", "CH"];
  // Dial codes shared by several countries resolve to the most common one when a number is pasted.
  const PRIMARY = { "1": "US", "44": "GB", "7": "RU", "39": "IT", "358": "FI", "590": "GP", "262": "RE", "599": "CW", "212": "MA" };

  const flag = (iso) => String.fromCodePoint(...[...iso].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65));
  const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  const cc = $("#cc");
  const ccBtn = $("#ccBtn");
  const ccPop = $("#ccPop");
  const ccSearch = $("#ccSearch");
  const ccList = $("#ccList");
  const phone = $("#phone");
  let current = null;
  let active = -1;
  let shown = [];

  function setCountry(iso) {
    const c = BY_ISO[iso] || BY_ISO.DE;
    current = c;
    $("#ccFlag").textContent = flag(c.iso);
    $("#ccDial").textContent = "+" + c.dial;
    $("#countryIso").value = c.iso;
    $("#dialCode").value = "+" + c.digits;
    ccBtn.setAttribute("aria-label", `Country code: ${c.name} +${c.dial}. Change country`);
  }

  // Timezone is a better location hint than language: plenty of German browsers run en-US.
  const TZ = {
    "Europe/Berlin": "DE", "Europe/Busingen": "DE", "Europe/Vienna": "AT", "Europe/Zurich": "CH", "Europe/Vaduz": "LI",
    "Europe/London": "GB", "Europe/Dublin": "IE", "Europe/Paris": "FR", "Europe/Amsterdam": "NL", "Europe/Brussels": "BE",
    "Europe/Luxembourg": "LU", "Europe/Madrid": "ES", "Europe/Rome": "IT", "Europe/Lisbon": "PT", "Europe/Copenhagen": "DK",
    "Europe/Stockholm": "SE", "Europe/Oslo": "NO", "Europe/Helsinki": "FI", "Europe/Warsaw": "PL", "Europe/Prague": "CZ",
  };
  function guessCountry() {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
    if (TZ[tz]) return TZ[tz];
    const tag = (navigator.languages && navigator.languages[0]) || navigator.language || "";
    const region = (tag.split("-")[1] || "").toUpperCase();
    if (BY_ISO[region] && !(region === "US" && !tz.startsWith("America/"))) return region;
    return "DE";
  }

  function optionHTML(c, key) {
    const sel = current && c.iso === current.iso;
    return `<li role="option" id="cc-${key}-${c.iso}" data-iso="${c.iso}" aria-selected="${sel}" class="cc__opt${sel ? " is-selected" : ""}">` +
      `<span class="cc__flag" aria-hidden="true">${flag(c.iso)}</span><span class="cc__name">${c.name}</span><span class="cc__code">+${c.dial}</span></li>`;
  }

  function renderList(query = "") {
    const q = norm(query.trim()).replace(/^\+/, "");
    const qDigits = /^[\d\s]+$/.test(q) ? q.replace(/\s/g, "") : "";
    let html = "";
    if (!q) {
      html += `<li class="cc__group" role="presentation">Suggested</li>` + SUGGESTED.map((i) => optionHTML(BY_ISO[i], "s")).join("");
      html += `<li class="cc__group" role="presentation">All countries</li>` + COUNTRIES.map((c) => optionHTML(c, "a")).join("");
    } else {
      const hits = COUNTRIES.filter((c) =>
        qDigits ? c.digits.startsWith(qDigits) : norm(c.name).includes(q) || c.iso.toLowerCase() === q
      ).sort((a, b) => {
        if (qDigits) {
          const rank = (c) => (c.digits === qDigits ? 0 : 2) + (PRIMARY[c.digits] === c.iso ? 0 : 1);
          return rank(a) - rank(b) || a.digits.length - b.digits.length || a.name.localeCompare(b.name);
        }
        const an = norm(a.name).startsWith(q) ? 0 : 1, bn = norm(b.name).startsWith(q) ? 0 : 1;
        return an - bn || a.name.localeCompare(b.name);
      });
      html = hits.length ? hits.map((c) => optionHTML(c, "a")).join("") : `<li class="cc__empty" role="presentation">No country found</li>`;
    }
    ccList.innerHTML = html;
    shown = $$(".cc__opt", ccList);
    const selIdx = shown.findIndex((o) => o.dataset.iso === current.iso);
    setActive(q ? 0 : selIdx, !q);
  }

  function setActive(i, center = false) {
    shown.forEach((o) => o.classList.remove("is-active"));
    active = shown.length ? Math.max(0, Math.min(shown.length - 1, i)) : -1;
    if (active < 0) { ccSearch.removeAttribute("aria-activedescendant"); return; }
    const o = shown[active];
    o.classList.add("is-active");
    ccSearch.setAttribute("aria-activedescendant", o.id);
    if (center) ccList.scrollTop = o.offsetTop - ccList.clientHeight / 2 + o.offsetHeight / 2;
    else o.scrollIntoView({ block: "nearest" });
  }

  function openList() {
    ccPop.hidden = false;
    cc.classList.add("is-open");
    ccBtn.setAttribute("aria-expanded", "true");
    ccSearch.value = "";
    renderList();
    ccSearch.focus();
  }
  function closeList({ restoreFocus = false } = {}) {
    if (ccPop.hidden) return;
    ccPop.hidden = true;
    cc.classList.remove("is-open");
    ccBtn.setAttribute("aria-expanded", "false");
    if (restoreFocus) ccBtn.focus();
  }
  function choose(iso) {
    setCountry(iso);
    closeList();
    phone.focus();
    if (phoneField().classList.contains("has-error")) validatePhone();
  }

  ccBtn.addEventListener("click", () => (ccPop.hidden ? openList() : closeList({ restoreFocus: true })));
  ccBtn.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); openList(); }
  });
  ccSearch.addEventListener("input", () => renderList(ccSearch.value));
  ccSearch.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(active + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(active - 1); }
    else if (e.key === "Enter") { e.preventDefault(); if (active >= 0) choose(shown[active].dataset.iso); }
    else if (e.key === "Escape") { e.preventDefault(); closeList({ restoreFocus: true }); }
    else if (e.key === "Tab") closeList();
  });
  ccList.addEventListener("mousedown", (e) => e.preventDefault()); // keep focus in the search box
  ccList.addEventListener("click", (e) => {
    const o = e.target.closest(".cc__opt");
    if (o) choose(o.dataset.iso);
  });
  ccList.addEventListener("mousemove", (e) => {
    const o = e.target.closest(".cc__opt");
    if (o && shown[active] !== o) setActive(shown.indexOf(o));
  });
  document.addEventListener("pointerdown", (e) => { if (!cc.contains(e.target)) closeList(); });

  setCountry(guessCountry());

  /* ---------- Phone number: accepts +44…, 0044… or national format ---------- */
  function absorbInternational() {
    const m = phone.value.trim().match(/^(?:\+|00)\s*([\d\s().-]+)$/);
    if (!m) return;
    const digits = m[1].replace(/\D/g, "");
    let best = null; // longest dial-code prefix wins
    for (const c of COUNTRIES) {
      if (digits.startsWith(c.digits) && (!best || c.digits.length > best.digits.length)) best = c;
    }
    if (!best) return;
    const primary = PRIMARY[best.digits];
    const iso = current.digits === best.digits ? current.iso : primary || best.iso;
    setCountry(iso);
    phone.value = digits.slice(best.digits.length);
  }
  phone.addEventListener("blur", absorbInternational);
  phone.addEventListener("paste", () => setTimeout(absorbInternational, 0));

  // National significant number: drop the trunk "0" (Italy, San Marino and the Vatican keep it),
  // and the area code a NANP territory already carries in its dial code.
  function nationalDigits() {
    let d = phone.value.replace(/\D/g, "");
    if (!["IT", "SM", "VA"].includes(current.iso)) d = d.replace(/^0+/, "");
    const area = current.digits.slice(1);
    if (current.digits.length === 4 && d.length === 10 && d.startsWith(area)) d = d.slice(3);
    return d;
  }
  const e164 = () => "+" + current.digits + nationalDigits();
  const pretty = () => `+${current.dial} ${nationalDigits().replace(/^(\d{3})(?=\d{4})/, "$1 ")}`;

  /* =========================================================
     Validation + submit
     ========================================================= */
  const form = $("#signupForm");
  const phoneField = () => phone.closest(".field");
  const consent = $("#consent");

  function setError(input, msg) {
    const field = input.closest(".field");
    field.classList.toggle("has-error", !!msg);
    $(".field__err", field).textContent = msg;
    input.setAttribute("aria-invalid", !!msg);
    return !msg;
  }
  function validateName(input) {
    const label = input.name === "firstName" ? "first name" : "last name";
    const v = input.value.trim();
    return setError(input, !v ? `Please enter your ${label}.` : !/\p{L}/u.test(v) ? `Please enter a valid ${label}.` : "");
  }
  function validatePhone() {
    const raw = phone.value.trim();
    let msg = "";
    if (!raw) msg = "Please enter your phone number.";
    else if (/[^\d\s()+./-]/.test(raw)) msg = "Use digits only, e.g. 151 2345678.";
    else {
      const total = current.digits.length + nationalDigits().length;
      if (nationalDigits().length < 4 || total < 8 || total > 15) msg = "Please enter a valid phone number.";
    }
    return setError(phone, msg);
  }
  function validateConsent() {
    const ok = consent.checked;
    consent.closest(".check").classList.toggle("has-error", !ok);
    consent.setAttribute("aria-invalid", !ok);
    $("#consentErr").textContent = ok ? "" : "Please accept the Terms of Service to continue.";
    return ok;
  }

  ["firstName", "lastName"].forEach((name) => {
    const input = form.elements[name];
    input.addEventListener("blur", () => { if (input.value) validateName(input); });
    input.addEventListener("input", () => { if (input.closest(".field").classList.contains("has-error")) validateName(input); });
  });
  phone.addEventListener("blur", () => { if (phone.value) validatePhone(); });
  phone.addEventListener("input", () => { if (phoneField().classList.contains("has-error")) validatePhone(); });
  consent.addEventListener("change", () => { if ($("#consentErr").textContent) validateConsent(); });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    absorbInternational();
    const first = form.elements.firstName, last = form.elements.lastName;
    const checks = [[first, validateName(first)], [last, validateName(last)], [phone, validatePhone()], [consent, validateConsent()]];
    const bad = checks.find(([, ok]) => !ok);
    if (bad) { bad[0].focus(); return; }

    // Hand-off point for the backend:
    // { firstName, lastName, phone: e164(), country: current.iso, consent: true }
    form.dataset.phoneE164 = e164();

    const btn = $("#submitBtn");
    btn.classList.add("is-loading");
    btn.textContent = "Signing you up";
    setTimeout(() => {
      btn.classList.remove("is-loading");
      btn.textContent = "Get started";
      $("#doneTitle").textContent = `You're in, ${first.value.trim()}.`;
      $("#donePhone").textContent = pretty();
      $("#formView").hidden = true;
      const done = $("#doneView");
      done.hidden = false;
      done.focus({ preventScroll: true });
    }, reduceMotion ? 0 : 1000);
  });

  $("#editBtn").addEventListener("click", () => {
    $("#doneView").hidden = true;
    $("#formView").hidden = false;
    phone.focus();
    phone.select();
  });
})();
