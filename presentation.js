/**
 * Claim intake — 5-slide live-demo deck.
 * Palette and helpers adapted from healthcare_tb_testing_clinical_training.
 * Run: node presentation.js
 */
const pptxgen = require("pptxgenjs");

const BG = "0F172A";
const TEXT = "F1F5F9";
const MUTED = "94A3B8";
const SUBTLE = "CBD5E1";
const AMBER = "F59E0B";
const CARD = "1E293B";
const OPEN = "34D399";
const HOLD = "FBBF24";
const REFUSE = "F87171";

const FONT_HEAD = "Georgia";
const FONT_BODY = "Helvetica";
const FONT_MONO = "Menlo";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3" × 7.5"
pres.title = "Claim intake · Module 4.3";
pres.author = "Grok Enablement Workshop";
pres.subject = "Live demo — FNOL desk";

function addBg(slide) {
  slide.background = { color: BG };
}

function addFooter(slide, pageNum) {
  slide.addText("Claim intake · Module 4.3 · never a payout", {
    x: 0.6, y: 7.1, w: 10.0, h: 0.28,
    fontFace: FONT_BODY, fontSize: 11, color: MUTED, margin: 0,
  });
  slide.addText(String(pageNum) + " / 5", {
    x: 11.5, y: 7.1, w: 1.2, h: 0.28,
    fontFace: FONT_MONO, fontSize: 11, color: MUTED, align: "right", margin: 0,
  });
}

function card(slide, x, y, w, h) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: CARD },
    line: { color: CARD, width: 0 },
  });
}

// ----- 1 Title -----
{
  const s = pres.addSlide();
  addBg(s);
  s.addText("MODULE 4.3  ·  LIVE DEMO", {
    x: 0.7, y: 1.7, w: 12, h: 0.35,
    fontFace: FONT_MONO, fontSize: 13, color: AMBER, charSpacing: 3, margin: 0,
  });
  s.addText("Claim intake", {
    x: 0.7, y: 2.15, w: 12, h: 1.05,
    fontFace: FONT_HEAD, fontSize: 54, bold: true, color: TEXT, margin: 0,
  });
  s.addText("Open, hold, or refuse against the policy excerpt.\nNever state a payout.", {
    x: 0.7, y: 3.35, w: 11, h: 1.0,
    fontFace: FONT_BODY, fontSize: 22, color: SUBTLE, margin: 0,
  });
  s.addText("The product is the laptop. These slides only name the track.", {
    x: 0.7, y: 5.6, w: 11, h: 0.35,
    fontFace: FONT_BODY, fontSize: 14, italic: true, color: MUTED, margin: 0,
  });
  addFooter(s, 1);
}

// ----- 2 Two cases -----
{
  const s = pres.addSlide();
  addBg(s);
  s.addText("Two cases. Both live.", {
    x: 0.6, y: 0.35, w: 12, h: 0.5,
    fontFace: FONT_HEAD, fontSize: 28, bold: true, color: TEXT, margin: 0,
  });

  const cases = [
    { id: "CL-03", peril: "Glass", result: "open", color: OPEN, rule: "PX-GLASS", note: "Photos on file. Accept for intake. Do not promise a payout." },
    { id: "CL-04", peril: "Flood", result: "refuse", color: REFUSE, rule: "PX-FLOOD", note: "Flood is excluded. Quote this rule. Log, do not send." },
    { id: "CL-08", peril: "Collision", result: "hold", color: HOLD, rule: "PX-COLLISION", note: "Photos missing → hold. Attach a photo → open, then confirm." },
  ];
  cases.forEach((c, i) => {
    const x = 0.6 + i * 4.15;
    card(s, x, 1.2, 3.95, 4.55);
    s.addText(c.id, {
      x: x + 0.25, y: 1.45, w: 3.45, h: 0.3,
      fontFace: FONT_MONO, fontSize: 14, color: AMBER, margin: 0,
    });
    s.addText(c.peril, {
      x: x + 0.25, y: 1.85, w: 3.45, h: 0.5,
      fontFace: FONT_HEAD, fontSize: 28, bold: true, color: TEXT, margin: 0,
    });
    s.addText(c.result, {
      x: x + 0.25, y: 2.45, w: 3.45, h: 0.5,
      fontFace: FONT_HEAD, fontSize: 26, bold: true, color: c.color, margin: 0,
    });
    s.addText(c.rule, {
      x: x + 0.25, y: 3.05, w: 3.45, h: 0.28,
      fontFace: FONT_MONO, fontSize: 13, color: MUTED, margin: 0,
    });
    s.addText(c.note, {
      x: x + 0.25, y: 3.55, w: 3.45, h: 1.9,
      fontFace: FONT_BODY, fontSize: 16, color: SUBTLE, margin: 0,
    });
  });
  addFooter(s, 2);
}

// ----- 3 Demo order -----
{
  const s = pres.addSlide();
  addBg(s);
  s.addText("Demo order. Then stop.", {
    x: 0.6, y: 0.35, w: 12, h: 0.5,
    fontFace: FONT_HEAD, fontSize: 28, bold: true, color: TEXT, margin: 0,
  });
  const steps = [
    { n: "01", t: "Name the track", d: "Claim intake. Open, hold, or refuse. Never a payout." },
    { n: "02", t: "Pass — live", d: "CL-03 glass → open. Read the PX-GLASS line from the file." },
    { n: "03", t: "Refuse — live", d: "CL-04 flood → refuse. Read the PX-FLOOD line. Confirm is blocked." },
    { n: "04", t: "Point at the laptop", d: "AGENTS.md, skill, hook, MCP lookup_rule, Intake Clerk bot." },
    { n: "05", t: "Stop", d: "Questions from judges only. If asked what we pay: the desk does not state a payout." },
  ];
  steps.forEach((st, i) => {
    const y = 1.05 + i * 1.1;
    card(s, 0.6, y, 12.1, 0.98);
    s.addText(st.n, {
      x: 0.85, y: y + 0.22, w: 0.9, h: 0.54,
      fontFace: FONT_MONO, fontSize: 20, bold: true, color: AMBER, margin: 0, valign: "middle",
    });
    s.addText(st.t, {
      x: 1.9, y: y + 0.12, w: 10.4, h: 0.38,
      fontFace: FONT_HEAD, fontSize: 18, bold: true, color: TEXT, margin: 0,
    });
    s.addText(st.d, {
      x: 1.9, y: y + 0.5, w: 10.4, h: 0.36,
      fontFace: FONT_BODY, fontSize: 14, color: SUBTLE, margin: 0,
    });
  });
  addFooter(s, 3);
}

// ----- 4 Must-show -----
{
  const s = pres.addSlide();
  addBg(s);
  s.addText("What is on the laptop", {
    x: 0.6, y: 0.35, w: 12, h: 0.5,
    fontFace: FONT_HEAD, fontSize: 28, bold: true, color: TEXT, margin: 0,
  });
  const items = [
    { k: "inspect", v: "Kit in data/ and md/ before any engine files" },
    { k: "AGENTS.md", v: "Only md/policy-excerpt.md. Call lookup_rule." },
    { k: "skill", v: "/review-fnol — same order as python/decide.py" },
    { k: "hook", v: "Blocks edits to the policy excerpt" },
    { k: "MCP", v: "lookup_rule flood → PX-FLOOD" },
    { k: "script + test", v: "bin/run.sh · bin/demo.sh · CL-04 stays refused" },
    { k: "website", v: "bin/desk.sh · 127.0.0.1:8788 · confirm before send" },
    { k: "Grok Bot", v: "Intake Clerk. Waits for a yes. Never mints. Never pays." },
  ];
  items.forEach((it, i) => {
    const col = i < 4 ? 0 : 1;
    const row = i % 4;
    const x = 0.6 + col * 6.35;
    const y = 1.1 + row * 1.35;
    card(s, x, y, 6.1, 1.2);
    s.addText(it.k, {
      x: x + 0.25, y: y + 0.18, w: 5.6, h: 0.35,
      fontFace: FONT_MONO, fontSize: 14, color: AMBER, margin: 0,
    });
    s.addText(it.v, {
      x: x + 0.25, y: y + 0.55, w: 5.6, h: 0.48,
      fontFace: FONT_BODY, fontSize: 15, color: SUBTLE, margin: 0,
    });
  });
  addFooter(s, 4);
}

// ----- 5 If this went live -----
{
  const s = pres.addSlide();
  addBg(s);
  s.addText("If this went live", {
    x: 0.6, y: 0.35, w: 12, h: 0.5,
    fontFace: FONT_HEAD, fontSize: 28, bold: true, color: TEXT, margin: 0,
  });
  const live = [
    { t: "Who clicks", d: "The intake clerk. Open and hold stay draft until Confirm. Refuse is logged, not sent." },
    { t: "How you undo", d: "Undo restores draft and clears the claim number. History is appended, not deleted." },
    { t: "What the log holds", d: "Report id, decision, quoted policy line, timestamp as YYYY-MM-DD HH:MM:SS. No amount." },
    { t: "Photos", d: "CL-08: attach an image to move hold → open. Remove photo to return to hold. Kit file is never rewritten." },
  ];
  live.forEach((it, i) => {
    const y = 1.1 + i * 1.35;
    card(s, 0.6, y, 12.1, 1.22);
    s.addText(it.t, {
      x: 0.9, y: y + 0.18, w: 11.5, h: 0.35,
      fontFace: FONT_HEAD, fontSize: 18, bold: true, color: AMBER, margin: 0,
    });
    s.addText(it.d, {
      x: 0.9, y: y + 0.58, w: 11.5, h: 0.48,
      fontFace: FONT_BODY, fontSize: 16, color: SUBTLE, margin: 0,
    });
  });
  addFooter(s, 5);
}

pres.writeFile({
  fileName: "/Users/tek/work/xAI/project/Hackathon/GrokHackathon-ram/Claim-intake-demo.pptx",
}).then(() => console.log("wrote Claim-intake-demo.pptx"));
