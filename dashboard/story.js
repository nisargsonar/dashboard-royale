// Story intro for the Gilded Ace dashboard.
// Explains the problem in 7 short scenes, then asks the viewer how they like their numbers
// (Simple for management, Analyst for data people). Every number comes from window.DATA via window.GA.
(function () {
  "use strict";
  const GA = window.GA;
  if (!GA) return;
  const D = GA.D, F = GA.MONTHS[0], L = GA.MONTHS[GA.MONTHS.length - 1];
  const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------------------------------------------------------------- facts from the data
  const ref = GA.floorTpa(F, L), nDays = GA.periodDays(F, L);
  const all = GA.machineAgg(false, F, L);
  const b10 = all.filter(a => GA.BOTTOM.includes(a.m));
  const count = k => b10.filter(a => GA.verdict(a, ref, nDays)[2] === k).length;
  const nInspect = count("inspect"), nLocation = count("location"), nNew = count("new");
  const inB40 = b10.filter(a => a.zone === "Z-B40").length;
  const closure = GA.WALK.find(w => w.s);
  const rate = pred => { const r = GA.ZD.filter(x => x.z === "Z-B40" && pred(x.d)); return GA.sum(r, x => x.ent) / GA.sum(r, x => x.cov); };
  const pre = rate(d => d < closure.s), during = rate(d => d >= closure.s && d < closure.e), after = rate(d => d >= closure.e);
  const drop = Math.round((1 - during / pre) * 100), back = Math.round(after / pre * 100);
  const m58 = all.find(a => a.m === "M-1158");
  const A = Object.fromEntries(GA.rows(D.actions).map(a => [a.id, a]));
  const cost = { inspect: 5 * A["A-INSPECT"].unit_cost, signs: A["A-WAYFINDING"].unit_cost, pilot: A["A-COMP-PILOT"].unit_cost };
  const spent = cost.inspect + cost.signs + cost.pilot, keep = 100000 - spent;
  const nMachines = D.machines.m.length;
  const usd = v => "$" + Math.round(v).toLocaleString("en-US");

  // bank shading (expected earnings per working hour, full period)
  const bst = {};
  GA.BD.forEach(r => { const a = bst[r.b] || (bst[r.b] = { t: 0, av: 0 }); a.t += r.theo; a.av += r.av; });
  const vals = GA.BANKS.map(b => (bst[b.bank] && bst[b.bank].av ? bst[b.bank].t / bst[b.bank].av : 0));
  const sorted = vals.slice().sort((a, b) => a - b);
  const qs = [0.2, 0.4, 0.6, 0.8].map(p => sorted[Math.floor(p * (sorted.length - 1))]);
  const SEQ = ["#f1dcdf", "#dca6ae", "#c06c7a", "#9b2335", "#5c0a14"];
  const shade = v => SEQ[qs.filter(q => v > q).length];
  const bankById = Object.fromEntries(GA.BANKS.map(b => [b.bank, b]));
  const ZC = Object.fromEntries(GA.ZONES.map(z => [z.zone, z]));
  const b10Banks = [...new Set(b10.map(a => a.b))];

  // ---------------------------------------------------------------- drawing helpers (SVG strings)
  const delay = s => `style="animation-delay:${s}s"`;
  function slot(x, y, s, d, ring) {
    return `<g transform="translate(${x} ${y}) scale(${s})"><g class="pop" ${delay(d)}>
      <rect x="4" y="-8" width="32" height="10" rx="3" fill="#b0862a"/>
      <rect x="0" y="0" width="40" height="56" rx="6" fill="#9b2335"/>
      <rect x="5" y="9" width="30" height="17" rx="3" fill="#fff"/>
      <text x="10.5" y="21.5" font-size="10" font-weight="700" fill="#9b2335" text-anchor="middle">7</text>
      <text x="20" y="21.5" font-size="10" font-weight="700" fill="#b0862a" text-anchor="middle">★</text>
      <text x="29.5" y="21.5" font-size="10" font-weight="700" fill="#9b2335" text-anchor="middle">7</text>
      <rect x="9" y="33" width="22" height="5" rx="2" fill="#6b0f1a"/>
      <rect x="2" y="46" width="36" height="6" rx="2" fill="#7a1a2a"/>
      <line x1="41" y1="16" x2="47" y2="6" stroke="#77726c" stroke-width="2.5" stroke-linecap="round"/><circle cx="47.5" cy="5" r="3.6" fill="#d03b3b"/>
      ${ring ? `<rect x="-5" y="-13" width="50" height="72" rx="9" fill="none" stroke="#d03b3b" stroke-width="3" class="blink"/>` : ""}
    </g></g>`;
  }
  function person(x, y, s, kind) {
    const mgr = kind === "manager";
    const suit = mgr ? "#3e3e3e" : "#2b73c2", skin = mgr ? "#e8b98f" : "#c98f68", hair = mgr ? "#5a4636" : "#1f1a17";
    const extra = mgr
      ? `<path d="M32 46 L28 58 L32 74 L36 58Z" fill="#9b2335"/>
         <g transform="translate(42 54) rotate(10)"><rect width="20" height="26" rx="2" fill="#b0862a"/><rect x="3" y="4" width="14" height="19" fill="#fff"/>
         <line x1="5" y1="9" x2="15" y2="9" stroke="#c4bcb0"/><line x1="5" y1="13" x2="15" y2="13" stroke="#c4bcb0"/><line x1="5" y1="17" x2="12" y2="17" stroke="#c4bcb0"/></g>`
      : `<line x1="52" y1="64" x2="62" y2="78" stroke="#5a4636" stroke-width="3.5" stroke-linecap="round"/>
         <circle cx="48" cy="57" r="10" fill="rgba(255,255,255,.65)" stroke="#5a4636" stroke-width="3.5"/>`;
    return `<g transform="translate(${x} ${y}) scale(${s})"><g class="slideL">
      <path d="M10 96 Q10 46 32 44 Q54 46 54 96Z" fill="${suit}"/>
      <rect x="27" y="34" width="10" height="12" fill="${skin}"/>
      <circle cx="32" cy="22" r="16" fill="${skin}"/>
      <path d="M16 20 Q18 4 32 5 Q47 4 48 20 Q44 11 32 11 Q21 11 16 20Z" fill="${hair}"/>
      <circle cx="26" cy="23" r="1.9" fill="#1c1a19"/><circle cx="38" cy="23" r="1.9" fill="#1c1a19"/>
      <path d="M26 30 Q32 34 38 30" stroke="#1c1a19" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      ${extra}</g></g>`;
  }
  function bubble(x, y, w, h, lines, tx, ty, d) {
    const txt = lines.map((l, i) => `<text x="${x + w / 2}" y="${y + 25 + i * 19}" text-anchor="middle" font-size="14.5" font-weight="${i === lines.length - 1 ? 700 : 400}" fill="#1c1a19">${l}</text>`).join("");
    return `<g class="pop" ${delay(d)}>
      <path d="M${x + 18} ${y + h - 2} L${tx} ${ty} L${x + 42} ${y + h - 2}Z" fill="#fff" stroke="#d9cdbb"/>
      <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14" fill="#fff" stroke="#d9cdbb"/>
      <rect x="${x + 19}" y="${y + h - 3}" width="22" height="5" fill="#fff"/>${txt}</g>`;
  }
  const svg = (inner, label) => `<svg viewBox="0 0 400 280" role="img" aria-label="${label}"><rect width="400" height="280" fill="#f7f1e8"/>${inner}</svg>`;

  function mapSVG(mode) {
    let g = `<svg viewBox="-10 -22 150 142" role="img" aria-label="Casino floor map"><rect x="-10" y="-22" width="150" height="142" fill="#f7f1e8"/>`;
    GA.WALK.forEach(w => {
      const a = ZC[w.zone_a], b = ZC[w.zone_b], closed = mode === "hall" && w.s;
      g += `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${closed ? "#d03b3b" : "#ddd3c5"}" stroke-width="${closed ? 1.8 : 3.2}" stroke-linecap="round" ${closed ? 'class="dash"' : ""}/>`;
    });
    GA.BANKS.forEach((b, i) => {
      const dim = mode === "hall" && b.zone === "Z-B40";
      g += `<circle cx="${b.x}" cy="${b.y}" r="3.1" fill="${shade(vals[i])}" stroke="#fff" stroke-width=".6" ${dim ? 'class="dim"' : `class="pop" ${delay((i * 0.012).toFixed(3))}`}/>`;
    });
    if (mode === "clue") b10Banks.forEach((bk, i) => { const b = bankById[bk]; if (b) g += `<circle cx="${b.x}" cy="${b.y}" r="5.6" fill="none" stroke="#1c1a19" stroke-width=".9" class="pulse" ${delay(0.8 + i * 0.12)}/>`; });
    if (mode === "leak") {
      b10Banks.forEach(bk => { const b = bankById[bk]; if (b && bk !== m58.b) g += `<circle cx="${b.x}" cy="${b.y}" r="5.4" fill="none" stroke="#a8a29a" stroke-width=".7"/>`; });
      const b = bankById[m58.b];
      g += `<circle cx="${b.x}" cy="${b.y}" r="6.6" fill="none" stroke="#d03b3b" stroke-width="1.5" class="blink"/>
            <text x="${b.x + 9}" y="${b.y + 2}" font-size="5.5" font-weight="700" fill="#d03b3b" paint-order="stroke" stroke="#f7f1e8" stroke-width="1.6">M-1158</text>`;
    }
    const off = { "Z-HTL": -13, "Z-HL": -11, "Z-B40": 16, "Z-GAR": 16, "Z-BAR": 15, "Z-ENT": -10, "Z-PIT": -11 };
    GA.ZONES.forEach(z => {
      const strong = (mode !== "floor" && z.zone === "Z-B40");
      g += `<text x="${z.x}" y="${z.y + (off[z.zone] || -10)}" text-anchor="middle" font-size="${strong ? 5.6 : 4.6}" font-weight="700" fill="${strong ? "#9b2335" : "#1c1a19"}" paint-order="stroke" stroke="#f7f1e8" stroke-width="1.6">${z.name}</text>`;
    });
    return g + "</svg>";
  }

  // ---------------------------------------------------------------- scenes
  const ICON_BRIEF = `<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="6" y="16" width="36" height="24" rx="4" fill="#9b2335"/><rect x="18" y="9" width="12" height="9" rx="2" fill="none" stroke="#9b2335" stroke-width="3"/><rect x="6" y="25" width="36" height="3" fill="#6b0f1a"/></svg>`;
  const ICON_CHART = `<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="8" y="26" width="7" height="14" rx="1.5" fill="#2b73c2"/><rect x="20" y="18" width="7" height="22" rx="1.5" fill="#2b73c2"/><rect x="32" y="10" width="7" height="30" rx="1.5" fill="#2b73c2"/><path d="M6 34 Q20 8 42 12" stroke="#9b2335" stroke-width="2.5" fill="none"/></svg>`;

  const scenes = [
    {
      title: "Meet The Gilded Ace",
      body: `<p>A Las Vegas casino with about <span class="hl">${nMachines - 10} slot machines</span> on its floor. It's made up for this challenge, but its data behaves like a real casino's.</p>
             <p>We studied <span class="hl">six months</span> of it: January to June 2025.</p>
             <div class="st-chips"><span>${nMachines} machines over time</span><span>181 days</span><span>Fictional casino</span></div>`,
      art: () => {
        let bulbs = "";
        for (let i = 0; i < 12; i++) { bulbs += `<circle cx="${128 + i * 13}" cy="25" r="2.6" fill="#ffd38a" class="blink" ${delay((i % 2) * 0.55)}/><circle cx="${128 + i * 13}" cy="59" r="2.6" fill="#ffd38a" class="blink" ${delay(((i + 1) % 2) * 0.55)}/>`; }
        return svg(`<rect y="228" width="400" height="52" fill="#e9dfcf"/>
          <g class="rise"><rect x="68" y="72" width="264" height="158" fill="#fffaf2" stroke="#e2d6c4"/><rect x="58" y="60" width="284" height="16" rx="4" fill="#500000"/>
          <rect x="178" y="158" width="44" height="72" fill="#6b0f1a"/><line x1="200" y1="158" x2="200" y2="230" stroke="#3a0a10" stroke-width="2"/></g>
          <g class="pop" ${delay(0.3)}><rect x="118" y="18" width="164" height="48" rx="9" fill="#9b2335"/><text x="200" y="49" text-anchor="middle" font-family="Oswald, sans-serif" font-size="19" font-weight="600" fill="#fff" letter-spacing="1">THE GILDED ACE</text></g>
          ${bulbs}
          ${slot(82, 170, 0.9, 0.6)}${slot(126, 170, 0.9, 0.75)}${slot(232, 170, 0.9, 0.9)}${slot(276, 170, 0.9, 1.05)}`, "Cartoon of The Gilded Ace casino with slot machines");
      }
    },
    {
      title: "The manager has a plan",
      body: `<p>Ten machines earned the least money. The manager wants to <span class="hl">replace all ten</span>, and has <span class="hl">$100,000</span> to spend in July.</p>
             <p>But a new machine only helps if the old machine was the real problem. So before spending anything, we checked.</p>`,
      art: () => {
        let row = "";
        for (let i = 0; i < 10; i++) row += slot(150 + (i % 5) * 46, 150 + Math.floor(i / 5) * 62, 0.62, 0.5 + i * 0.08, true);
        return svg(`<rect y="236" width="400" height="44" fill="#e9dfcf"/>${person(18, 108, 1.32, "manager")}
          ${bubble(110, 22, 196, 64, ["These 10 earned the least.", "Let's replace them!"], 70, 128, 0.6)}
          <g class="pop" ${delay(1.4)}><rect x="300" y="92" width="94" height="30" rx="15" fill="#b0862a"/><text x="347" y="112" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">$100k · July</text></g>
          ${row}`, "Cartoon of a manager pointing at ten slot machines");
      }
    },
    {
      title: "Wait. Why did they earn so little?",
      body: `<p>A machine can earn little for three very different reasons:</p>
             <ul class="st-list">
               <li><span class="ic" style="background:#b0862a">1</span><span><b>Luck.</b> It just had a bad run, like a coin landing tails six times in a row.</span></li>
               <li><span class="ic" style="background:#9b2335">2</span><span><b>Location.</b> It sits in a corner where few people walk by.</span></li>
               <li><span class="ic" style="background:#2b73c2">3</span><span><b>Leak.</b> Something is off and it pays out more than it should.</span></li>
             </ul><p>Each one needs a different fix. We tested all three.</p>`,
      art: () => {
        const card = (x, d, icon, label) => `<g transform="translate(${x} 100)"><g class="pop" ${delay(d)}><rect width="82" height="116" rx="12" fill="#fff" stroke="#e2d6c4"/>${icon}<text x="41" y="96" text-anchor="middle" font-family="Oswald, sans-serif" font-size="17" font-weight="600" fill="#1c1a19">${label}</text></g></g>`;
        const coin = `<circle cx="41" cy="46" r="20" fill="#b0862a" stroke="#8a6510" stroke-width="2.5"/><text x="41" y="53" text-anchor="middle" font-size="21" font-weight="700" fill="#fff">$</text>`;
        const pin = `<path transform="translate(41 46)" d="M0 -24 C13 -24 20 -14 20 -4 C20 10 0 26 0 26 C0 26 -20 10 -20 -4 C-20 -14 -13 -24 0 -24Z" fill="#9b2335"/><circle cx="41" cy="43" r="7.5" fill="#fff"/>`;
        const leak = `<rect x="22" y="22" width="30" height="9" rx="3" fill="#77726c"/><rect x="44" y="22" width="9" height="20" rx="3" fill="#77726c"/><g transform="translate(48 52)"><path class="drip" d="M0 -8 C4 -2 6 2 6 5 A6 6 0 0 1 -6 5 C-6 2 -4 -2 0 -8Z" fill="#2b73c2"/></g>`;
        return svg(`<rect y="236" width="400" height="44" fill="#e9dfcf"/>${person(14, 112, 1.26, "analyst")}
          ${bubble(104, 18, 214, 64, ["A machine can earn little", "for three reasons."], 66, 128, 0.5)}
          ${card(118, 0.9, coin, "Luck")}${card(212, 1.2, pin, "Location")}${card(306, 1.5, leak, "Leak")}`, "Cartoon of an analyst with three suspects: luck, location, leak");
      }
    },
    {
      title: "Clue 1: they're almost all in one corner",
      body: `<p>This is the <span class="hl">real casino floor</span>, drawn from the data. Darker dots earn more per hour. The rings show where the manager's 10 machines sit.</p>
             <p><span class="hl">${inB40} of the 10</span> are in <b>Back Forty</b>, the quietest corner. The same games earn <span class="hl">30–45% more</span> anywhere else on the floor.</p>`,
      art: () => mapSVG("clue") + `<div class="st-box st-legend rise" ${delay(0.6)}><span><i style="background:#5c0a14"></i>earns more</span><span><i style="background:#f1dcdf"></i>earns less</span><span><i style="background:transparent;border:1.5px solid #1c1a19"></i>manager's 10</span></div>`
    },
    {
      title: "Clue 2: the hallway closed",
      body: `<p>In March, the hallway from the main entrance to Back Forty <span class="hl">closed for five weeks</span> for renovation.</p>
             <p>Foot traffic in Back Forty fell <span class="hl">${drop}%</span>. When the hallway reopened, only <span class="hl">${back}%</span> of the old traffic came back.</p>
             <p>Fewer people walking by means less play. The machines there aren't broken; they're just hard to find.</p>`,
      art: () => mapSVG("hall") + `<div class="st-box st-meter rise" ${delay(0.4)}>Back Forty foot traffic<div class="n" data-count="${-drop}" data-suffix="%">0%</div>while the hallway was closed</div>`
    },
    {
      title: "Clue 3: one machine acts strangely",
      body: `<p>Machine <span class="hl">M-1158</span> pays out a win on <span class="hl">${(m58.hit * 100).toFixed(1)}%</span> of spins. Its game design says <span class="hl">${(m58.hitp * 100).toFixed(1)}%</span>, and it was like this every month.</p>
             <p>Over hundreds of thousands of spins, that gap is not luck. It's like a coin landing heads 700 times out of 1,000. Every other machine's results look like normal luck.</p>
             <p class="note">This is a reason to check the machine, not proof that anything is wrong.</p>`,
      art: () => mapSVG("leak") + `<div class="st-box st-bars rise" ${delay(0.4)}><b>How often M-1158 pays a win</b>
          <div class="r"><span>Design</span><div class="tr"><div class="grow" style="width:${(m58.hitp / 0.5 * 100).toFixed(1)}%;background:#a8a29a;animation-delay:.7s"></div></div><b>${(m58.hitp * 100).toFixed(1)}%</b></div>
          <div class="r"><span>M-1158</span><div class="tr"><div class="grow" style="width:${(m58.hit / 0.5 * 100).toFixed(1)}%;background:#d03b3b;animation-delay:1s"></div></div><b>${(m58.hit * 100).toFixed(1)}%</b></div></div>`
    },
    {
      title: "Our advice",
      body: `<p><span class="hl">Don't replace all 10.</span> ${nLocation} are in a quiet spot, ${nNew} are too new to judge, and ${nInspect} needs a check.</p>
             <p>Spend <span class="hl">${usd(spent)}</span> on three small fixes and <span class="hl">keep ${usd(keep)}</span>. Bad luck doesn't need fixing.</p>
             <p>Next, the full dashboard shows the proof behind every claim.</p>`,
      nextLabel: "Choose your view ›",
      art: () => {
        const tot = 100000;
        return `<div class="st-plan">
          <div class="st-cards">
            <div class="st-card pop" ${delay(0.2)}><div class="what"><span class="tag" style="background:#9b2335"></span>Inspect M-1158</div><div class="why">plus 4 more, to be sure</div><div class="cost">${usd(cost.inspect)}</div></div>
            <div class="st-card pop" ${delay(0.4)}><div class="what"><span class="tag" style="background:#2b73c2"></span>Signs to Back Forty</div><div class="why">help guests find it</div><div class="cost">${usd(cost.signs)}</div></div>
            <div class="st-card pop" ${delay(0.6)}><div class="what"><span class="tag" style="background:#a8781a"></span>Test the comp rule</div><div class="why">on half the guests</div><div class="cost">${usd(cost.pilot)}</div></div>
          </div>
          <div class="st-bar">
            <div class="grow" style="flex:${cost.inspect / tot};background:#9b2335;animation-delay:.9s"></div>
            <div class="grow" style="flex:${cost.signs / tot};background:#2b73c2;animation-delay:1.05s"></div>
            <div class="grow" style="flex:${cost.pilot / tot};background:#a8781a;animation-delay:1.2s"></div>
            <div class="grow keep" style="flex:${keep / tot};animation-delay:1.35s">Keep ${usd(keep)}</div>
          </div>
          <div class="cap rise" ${delay(1.6)}>$100,000 budget for July 1–30</div></div>`;
      }
    }
  ];
  const TOTAL = scenes.length; // chooser is scene TOTAL + 1

  // ---------------------------------------------------------------- overlay
  let root = null, idx = 0, raf = 0;
  function build() {
    root = document.createElement("div");
    root.className = "story";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", "Story: the problem explained");
    root.innerHTML = `
      <div class="st-top"><div class="st-brand">LUCK OR LEAK · THE CASE</div><div class="st-dots" aria-hidden="true"></div><button class="st-skip" type="button">Skip intro ›</button></div>
      <div class="st-stage"><div class="st-art"></div><div class="st-copy" aria-live="polite"></div></div>
      <div class="st-nav"><button class="st-back" type="button">‹ Back</button><button class="st-next" type="button">Next ›</button></div>
      <div class="st-hint">Use ← → keys · Esc to skip</div>`;
    document.body.append(root);
    root.querySelector(".st-skip").addEventListener("click", () => go(TOTAL));
    root.querySelector(".st-back").addEventListener("click", () => go(idx - 1));
    root.querySelector(".st-next").addEventListener("click", () => go(idx + 1));
    document.addEventListener("keydown", onKey);
  }
  function onKey(e) {
    if (!root || root.hidden) return;
    if (e.key === "ArrowRight" && idx < TOTAL) go(idx + 1);
    else if (e.key === "ArrowLeft" && idx > 0) go(idx - 1);
    else if (e.key === "Escape") go(TOTAL);
  }
  function countUp(el) {
    const to = +el.dataset.count, suf = el.dataset.suffix || "";
    const fmt = v => (v < 0 ? "−" : "") + Math.abs(Math.round(v)) + suf;
    if (reduce) { el.textContent = fmt(to); return; }
    const t0 = performance.now() + 500, dur = 1300;
    cancelAnimationFrame(raf);
    const step = t => { const k = Math.max(0, Math.min(1, (t - t0) / dur)); el.textContent = fmt(to * (1 - Math.pow(1 - k, 3))); if (k < 1) raf = requestAnimationFrame(step); };
    raf = requestAnimationFrame(step);
  }
  function go(i) {
    idx = Math.max(0, Math.min(TOTAL, i));
    const stage = root.querySelector(".st-stage"), art = root.querySelector(".st-art"), copy = root.querySelector(".st-copy");
    const dots = root.querySelector(".st-dots");
    dots.innerHTML = Array.from({ length: TOTAL + 1 }, (_, k) => `<i class="${k === idx ? "on" : k < idx ? "done" : ""}"></i>`).join("");
    const chooser = idx === TOTAL;
    stage.classList.toggle("choose", chooser);
    root.querySelector(".st-nav").style.visibility = chooser ? "hidden" : "visible";
    root.querySelector(".st-skip").style.visibility = chooser ? "hidden" : "visible";
    if (chooser) {
      art.innerHTML = "";
      copy.innerHTML = `<div class="st-kick">Before we start</div><h2 class="st-title">How do you like your numbers?</h2>
        <div class="st-body"><p>Pick the version that fits you. You can switch at any time from the top bar.</p></div>
        <div class="st-choices">
          <button class="st-choice" type="button" data-view="simple">${ICON_BRIEF}<h3>I run the business</h3><p>Keep it simple: plain words, real-life examples, the key numbers.</p><div class="ex">Best for managers and non-technical readers</div></button>
          <button class="st-choice" type="button" data-view="analyst">${ICON_CHART}<h3>I work with data</h3><p>Show me the math: z-scores, formulas, model errors and full tables.</p><div class="ex">Best for analysts, data scientists and judges checking the method</div></button>
        </div>
        <button class="st-notsure" type="button" data-view="simple">Not sure? Start simple.</button>`;
      copy.querySelectorAll("[data-view]").forEach(b => b.addEventListener("click", () => finish(b.dataset.view)));
      const first = copy.querySelector(".st-choice"); if (first) first.focus();
      return;
    }
    const sc = scenes[idx];
    art.innerHTML = sc.art();
    copy.innerHTML = `<div class="st-kick">Scene ${idx + 1} of ${TOTAL}</div><h2 class="st-title">${sc.title}</h2><div class="st-body">${sc.body}</div>`;
    root.querySelector(".st-back").disabled = idx === 0;
    root.querySelector(".st-next").textContent = sc.nextLabel || "Next ›";
    art.querySelectorAll("[data-count]").forEach(countUp);
  }
  function open(scene) {
    if (!root) build();
    root.hidden = false;
    document.documentElement.style.overflow = "hidden";
    go((scene || 1) - 1);
    const nb = root.querySelector(".st-next"); if (nb && idx < TOTAL) nb.focus();
  }
  function finish(view) {
    cancelAnimationFrame(raf);
    root.hidden = true;
    document.documentElement.style.overflow = "";
    GA.setView(view);
    GA.goTab("overview");
  }

  window.GAStory = { open };
  if (GA.shouldShowStory()) open(Math.min(GA.startScene(), TOTAL + 1));
})();
