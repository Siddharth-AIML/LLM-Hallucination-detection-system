
"use strict";

/* ============================================================
   TruthLens V2 — Frontend Controller

   Modes:
   1. Factual Verification
   2. Math Verification
   3. Code Check
   4. Unified Contextual Auditing + Memory Analysis
   5. Standalone Context Memory Analysis

   Mitigation:
   POST /verify/context/mitigate
   ============================================================ */

const API_BASE =
  window.location.protocol === "file:"
    ? "http://127.0.0.1:8000"
    : "";

const EXAMPLES = {
  1: "The Eiffel Tower is located in Paris, France, and was built by Gustave Eiffel in 1889. It stands over 500 meters tall, making it one of the tallest structures in Europe at the time.",
  2: "The Reserve Bank of India kept the repo rate unchanged at its August 2026 policy meeting, marking the fourth consecutive pause. The central bank raised its FY27 GDP growth forecast to 6.7% from 6.6%, citing resilient domestic economic activity. RBI governor Sanjay Malhotra led the decision. The committee also announced a complete removal of all capital gains tax on equity investments.",
  3: "Ola Electric Mobility signed a Memorandum of Understanding with Axis Energy to deploy up to 20 GWh of battery energy storage. The deal marks the company's expansion into utility-scale energy storage beyond its two-wheeler business. Ola Electric shares rallied more than 7% on the BSE following the announcement. The company also confirmed it has acquired Tesla's Indian manufacturing division outright."
};

const VERDICT_LABEL = {
  SUPPORTED: "SUPPORTED",
  CONTRADICTED: "CONTRADICTED",
  PARTIALLY_SUPPORTED: "PARTIALLY SUPPORTED",
  INSUFFICIENT_INFORMATION: "INSUFFICIENT INFO",
  NOT_ASSESSABLE: "NOT ASSESSABLE",
  CONSISTENT: "CONSISTENT",
  INCONSISTENT: "INCONSISTENT",
  CONFLICTED: "CONFLICTED",
  MISALIGNED: "MISALIGNED",
  ALIGNED: "ALIGNED"
};

// Shared elements
const inputEl = document.getElementById("input-text");
const btnEl = document.getElementById("verify-btn");
const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const resultsEl = document.getElementById("results");

// Mode containers
const factualInputEl = document.getElementById("factual-input");
const mathInputEl = document.getElementById("math-input");
const codeInputEl = document.getElementById("code-input");
const contextInputEl = document.getElementById("context-input");
const memoryInputEl = document.getElementById("memory-input");

// Math
const mathQuestionEl = document.getElementById("math-question");
const mathAnswerEl = document.getElementById("math-answer");

// Code
const codeTextEl = document.getElementById("code-text");

// Context audit
const contextQuestionEl = document.getElementById("context-question");
const contextAnswerEl = document.getElementById("context-answer");
const contextSourceEl = document.getElementById("context-source");
const contextHistoryEl = document.getElementById("context-history");
const contextInstructionsEl =
  document.getElementById("context-instructions");

// Standalone memory analysis
const memoryQuestionEl = document.getElementById("memory-question");
const memoryAnswerEl = document.getElementById("memory-answer");
const memoryHistoryEl = document.getElementById("memory-history");
const memoryInstructionsEl =
  document.getElementById("memory-instructions");

let activeMode = "facts";

// ============================================================
// MODE SWITCHING
// ============================================================

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    inputEl.value = EXAMPLES[chip.dataset.example] || "";
    inputEl.focus();
  });
});

document.querySelectorAll(".mode-button").forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});

btnEl.addEventListener("click", () => {
  const actions = {
    facts: verify,
    math: verifyMath,
    code: verifyCode,
    context: verifyContext,
    memory: verifyMemory
  };

  (actions[activeMode] || verify)();
});

function setMode(mode) {
  const modes = ["facts", "math", "code", "context", "memory"];
  activeMode = modes.includes(mode) ? mode : "facts";

  factualInputEl.hidden = activeMode !== "facts";
  mathInputEl.hidden = activeMode !== "math";
  codeInputEl.hidden = activeMode !== "code";
  contextInputEl.hidden = activeMode !== "context";
  memoryInputEl.hidden = activeMode !== "memory";

  btnEl.textContent = {
    facts: "Verify",
    math: "Verify math",
    code: "Check code",
    context: "Run full reliability audit",
    memory: "Analyze memory"
  }[activeMode];

  statusEl.textContent = "";
  summaryEl.replaceChildren();
  summaryEl.hidden = true;
  resultsEl.replaceChildren();

  document.querySelectorAll(".mode-button").forEach((button) => {
    const selected = button.dataset.mode === activeMode;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
}

// ============================================================
// SHARED HELPERS
// ============================================================

async function postJSON(url, payload) {
  const response = await fetch(API_BASE + url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail || data.error || {});

    throw new Error(detail || "API returned " + response.status);
  }

  if (data.error) throw new Error(data.error);

  return data;
}

function startRequest(message) {
  resultsEl.replaceChildren();
  summaryEl.replaceChildren();
  summaryEl.hidden = true;
  btnEl.disabled = true;
  statusEl.textContent = message;
}

function finishRequest() {
  btnEl.disabled = false;
}

function showError(message) {
  statusEl.textContent = "";

  const error = document.createElement("div");
  error.className = "error";
  error.textContent = message;
  resultsEl.replaceChildren(error);
}

function makeHeading(text, level = "h2") {
  const heading = document.createElement(level);
  heading.textContent = text;
  return heading;
}

function showField(container, label, value) {
  const field = document.createElement("div");
  field.className = "math-field";

  const name = document.createElement("div");
  name.className = "math-field-label";
  name.textContent = label.replace(/_/g, " ");

  const content = document.createElement("p");

  if (value === null || value === undefined || value === "") {
    content.textContent = "Not provided";
  } else if (typeof value === "object") {
    content.textContent = JSON.stringify(value, null, 2);
  } else {
    content.textContent = String(value);
  }

  field.append(name, content);
  container.appendChild(field);
}

function showObject(container, object, excluded = []) {
  if (!object || typeof object !== "object" || Array.isArray(object)) {
    showField(container, "Result", object);
    return;
  }

  Object.entries(object).forEach(([key, value]) => {
    if (!excluded.includes(key)) showField(container, key, value);
  });
}

function createCard(title, className = "claim-card") {
  const card = document.createElement("article");
  card.className = className;
  card.appendChild(makeHeading(title, "h2"));
  return card;
}

function verdictLabel(value) {
  return VERDICT_LABEL[value] ||
    String(value || "UNKNOWN").replace(/_/g, " ");
}

// ============================================================
// 1. FACTUAL VERIFICATION — POST /verify
// ============================================================

async function verify() {
  const text = inputEl.value.trim();

  if (!text) {
    showError("Please enter or select some text to verify.");
    return;
  }

  startRequest("Extracting claims and verifying against the Knowledge Base…");

  try {
    const data = await postJSON("/verify", { text });

    if (!data.claims || data.claims.length === 0) {
      showError(data.error || "No factual claims were extracted.");
      return;
    }

    renderFactualResults(data);
    statusEl.textContent = "Factual verification completed.";
  } catch (error) {
    showError("Factual verification failed: " + error.message);
  } finally {
    finishRequest();
  }
}

function renderFactualResults(data) {
  const summary = data.summary || {};
  const counts = summary.verdict_counts || {};

  const summaryHeading = makeHeading(
    "Result summary — " + data.claims.length + " claims"
  );

  const tally = document.createElement("div");
  tally.className = "tally";

  Object.entries(counts).forEach(([verdict, count]) => {
    const item = document.createElement("span");
    item.className = "tally-item b-" + verdict;
    item.textContent = verdictLabel(verdict) + ": " + count;
    tally.appendChild(item);
  });

  summaryEl.replaceChildren(summaryHeading, tally);

  if (summary.note) {
    const note = document.createElement("p");
    note.className = "summary-note";
    note.textContent = summary.note;
    summaryEl.appendChild(note);
  }

  summaryEl.hidden = false;

  const heading = makeHeading(
    data.claims.length + " claims extracted and verified independently"
  );
  heading.className = "results-heading";
  resultsEl.appendChild(heading);

  data.claims.forEach((claim, index) => {
    resultsEl.appendChild(renderClaim(claim, index + 1));
  });
}

function renderClaim(claim, position) {
  const card = document.createElement("article");
  card.className = "claim-card v-" + claim.verdict;

  const head = document.createElement("div");
  head.className = "claim-head";

  const left = document.createElement("div");

  const index = document.createElement("div");
  index.className = "claim-index";
  index.textContent = "CLAIM " + position;

  const text = document.createElement("p");
  text.className = "claim-text";
  text.textContent = claim.claim || "";

  left.append(index, text);

  const badge = document.createElement("span");
  badge.className = "badge b-" + claim.verdict;
  badge.textContent = verdictLabel(claim.verdict);

  head.append(left, badge);
  card.appendChild(head);

  const confidence = document.createElement("div");
  confidence.className = "confidence";

  const label = document.createElement("span");
  label.className = "conf-label";
  label.textContent = "Confidence";

  const bar = document.createElement("div");
  bar.className = "bar";

  const fill = document.createElement("div");
  fill.className = "bar-fill f-" + claim.verdict;
  fill.style.width =
    Math.max(0, Math.min(100, Number(claim.confidence || 0) * 100)) + "%";
  bar.appendChild(fill);

  const value = document.createElement("span");
  value.className = "conf-value";
  value.textContent = Number(claim.confidence || 0).toFixed(2);

  confidence.append(label, bar, value);
  card.appendChild(confidence);

  if (claim.explanation) {
    const explanation = document.createElement("p");
    explanation.className = "explanation";
    explanation.textContent = claim.explanation;
    card.appendChild(explanation);
  }

  card.appendChild(renderEvidence(claim));

  if (claim.retrieved_topics && claim.retrieved_topics.length) {
    const topics = document.createElement("div");
    topics.className = "topics";
    topics.textContent =
      "Retrieved topics: " + claim.retrieved_topics.join(", ");
    card.appendChild(topics);
  }

  return card;
}

function renderEvidence(claim) {
  const supporting = usableEvidence(claim.supporting_evidence);
  const contradicting = usableEvidence(claim.contradicting_evidence);
  const total = supporting.length + contradicting.length;

  const details = document.createElement("details");
  details.className = "evidence";

  const summary = document.createElement("summary");
  summary.textContent =
    total === 0 ? "No evidence retrieved" : "Evidence used (" + total + ")";
  details.appendChild(summary);

  if (total === 0) {
    const empty = document.createElement("p");
    empty.className = "ev-empty";
    empty.textContent =
      "The Knowledge Base returned no evidence passing the retrieval gate.";
    details.appendChild(empty);
    return details;
  }

  appendEvidenceGroup(details, "SUPPORTING", supporting);
  appendEvidenceGroup(details, "CONTRADICTING", contradicting);

  return details;
}

function usableEvidence(items) {
  return (items || []).filter((item) => {
    const text = cleanText(item.text);
    return text.length >= 40 && !/^target=|^oc=\d/.test(text);
  });
}

function appendEvidenceGroup(container, label, items) {
  if (!items.length) return;

  const heading = document.createElement("div");
  heading.className = "ev-group-label";
  heading.textContent = label + " (" + items.length + ")";
  container.appendChild(heading);

  items.forEach((item) => {
    const wrap = document.createElement("div");
    wrap.className = "ev-item";

    const source = document.createElement("div");
    source.className = "ev-source";
    source.textContent = item.source || "Unknown source";

    const text = document.createElement("p");
    text.className = "ev-text";
    text.textContent = truncate(cleanText(item.text), 320);

    wrap.append(source, text);
    container.appendChild(wrap);
  });
}

// ============================================================
// 2. MATH VERIFICATION — POST /verify/math
// ============================================================

async function verifyMath() {
  const question = mathQuestionEl.value.trim();
  const answer = mathAnswerEl.value.trim();

  if (!question || !answer) {
    showError("Enter both the original math question and the LLM answer.");
    return;
  }

  startRequest("Independently checking the calculation…");

  try {
    const result = await postJSON("/verify/math", { question, answer });
    renderMath(result);
    statusEl.textContent = "Math verification completed.";
  } catch (error) {
    showError("Math verification failed: " + error.message);
  } finally {
    finishRequest();
  }
}

function renderMath(result) {
  const card = createCard("Independent Math Verification", "math-card");

  const badge = document.createElement("span");
  badge.className = "badge";
  badge.textContent = verdictLabel(result.verdict);
  card.appendChild(badge);

  showField(card, "Original question", result.original_question);
  showField(card, "LLM answer", result.llm_answer);
  showField(card, "Extracted final answer", result.original_answer);
  showField(card, "Question-derived expression", result.extracted_expression);
  showField(card, "Independently computed result", result.computed_result);
  showField(card, "Conclusive", result.is_conclusive ? "Yes" : "No");
  showField(card, "Explanation", result.explanation);

  resultsEl.appendChild(card);
}

// ============================================================
// 3. UNIFIED CONTEXTUAL RELIABILITY
// POST /verify/context/full
// ============================================================

function getContextPayload() {
  return {
    question: contextQuestionEl.value.trim(),
    answer: contextAnswerEl.value.trim(),
    context: contextSourceEl.value.trim(),
    conversation_history: contextHistoryEl.value.trim(),
    instructions: contextInstructionsEl.value.trim()
  };
}

async function verifyContext() {
  const payload = getContextPayload();

  if (!payload.question || !payload.answer) {
    showError("Enter both the original question and the LLM-generated answer.");
    return;
  }

  startRequest("Running contextual audit and memory analysis…");

  try {
    const data = await postJSON("/verify/context/full", payload);
    renderFullReliability(data, payload);

    statusEl.textContent =
      data.status === "completed"
        ? "Contextual audit and memory analysis completed."
        : "Reliability workflow partially completed. Review the results.";
  } catch (error) {
    showError(
      "Unified reliability audit failed: " + error.message +
      ". Confirm that api.py exposes POST /verify/context/full."
    );
  } finally {
    finishRequest();
  }
}

// ------------------------------------------------------------
// Report rendering helpers. Everything is built with
// createElement + textContent, so model output is never parsed
// as HTML.
// ------------------------------------------------------------

// One place that decides colour. Unknown labels fall back to grey.
const VERDICT_TONE = {
  SUPPORTED: "ok",
  ALIGNED: "ok",
  FOLLOWED: "ok",
  CONSISTENT: "ok",
  CONTRADICTED: "bad",
  MISALIGNED: "bad",
  VIOLATED: "bad",
  CONFLICTED: "bad",
  INCONSISTENT: "bad",
  PARTIALLY_SUPPORTED: "warn",
  PARTIALLY_CONSISTENT: "warn"
};

function verdictTone(verdict) {
  const key = String(verdict || "").trim().toUpperCase().replace(/\s+/g, "_");
  return VERDICT_TONE[key] || "neutral";
}

const AUDIT_DIMENSIONS = [
  ["context_faithfulness", "Context faithfulness"],
  ["conversation_alignment", "Conversation alignment"],
  ["context_memory", "Context memory"],
  ["instruction_consistency", "Instruction consistency"]
];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}

function isBlank(value) {
  if (value === null || value === undefined) return true;
  const text = String(value).trim();
  return text === "" || text.toLowerCase() === "not provided";
}

function cellText(value) {
  if (isBlank(value)) return "—";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function verdictBadge(verdict) {
  return el(
    "span",
    "rr-badge rr-" + verdictTone(verdict),
    verdictLabel(isBlank(verdict) ? "NOT RUN" : verdict)
  );
}

function reportCard(title) {
  const card = el("article", "rr-card");
  card.appendChild(el("h2", "rr-title", title));
  return card;
}

function quoteBox(text) {
  return el("blockquote", "rr-quote", cellText(text));
}

function makeTable(headers, rows) {
  const wrap = el("div", "rr-table-wrap");
  wrap.tabIndex = 0;

  const table = el("table", "rr-table");
  const headRow = el("tr");
  headers.forEach((name) => headRow.appendChild(el("th", "", name)));
  table.appendChild(el("thead")).appendChild(headRow);

  const body = el("tbody");
  rows.forEach((cells) => {
    const row = el("tr");
    cells.forEach((cell) => {
      const td = el("td");
      if (cell instanceof Node) td.appendChild(cell);
      else td.textContent = cellText(cell);
      row.appendChild(td);
    });
    body.appendChild(row);
  });

  table.appendChild(body);
  wrap.appendChild(table);
  return wrap;
}

function summaryBar(entries) {
  const bar = el("div", "rr-summary");

  entries.forEach(({ label, verdict }) => {
    const pill = el("div", "rr-pill");
    pill.appendChild(el("span", "rr-pill-label", label));
    pill.appendChild(verdictBadge(verdict));
    bar.appendChild(pill);
  });

  return bar;
}

function auditSummaryEntries(audit) {
  const source = asObject(audit);

  return AUDIT_DIMENSIONS.map(([key, label]) => ({
    label,
    verdict: asObject(source[key]).verdict
  }));
}

function dimensionRow(label, verdict, reason) {
  const row = el("div", "rr-dim");
  const head = el("div", "rr-dim-head");
  head.append(el("span", "rr-dim-label", label), verdictBadge(verdict));
  row.appendChild(head);

  if (!isBlank(reason)) row.appendChild(el("p", "rr-reason", reason));
  return row;
}

function bulletList(items) {
  const list = el("ul", "rr-list");
  items.forEach((item) => list.appendChild(el("li", "", cellText(item))));
  return list;
}

function renderAuditCard(title, audit) {
  const card = reportCard(title);

  if (!audit || typeof audit !== "object") {
    card.appendChild(el("p", "rr-muted", "Contextual audit did not complete."));
    return card;
  }

  const faithfulness = asObject(audit.context_faithfulness);
  card.appendChild(
    dimensionRow(
      "Context faithfulness",
      faithfulness.verdict,
      faithfulness.reason
    )
  );

  const findings = Array.isArray(faithfulness.findings)
    ? faithfulness.findings.filter((f) => f && typeof f === "object")
    : [];

  if (findings.length) {
    card.appendChild(
      makeTable(
        ["Claim", "Verdict", "Reason", "Evidence"],
        findings.map((f) => [
          f.claim,
          verdictBadge(f.verdict),
          f.reason,
          f.evidence
        ])
      )
    );
  } else {
    card.appendChild(
      el("p", "rr-muted", "No individual claims were assessed.")
    );
  }

  AUDIT_DIMENSIONS.slice(1).forEach(([key, label]) => {
    const section = asObject(audit[key]);
    card.appendChild(dimensionRow(label, section.verdict, section.reason));
  });

  return card;
}

function collectLimitations(...sources) {
  const seen = [];

  sources.forEach((source) => {
    const list = asObject(source).limitations;
    if (!Array.isArray(list)) return;

    list.forEach((item) => {
      if (!isBlank(item) && !seen.includes(item)) seen.push(item);
    });
  });

  return seen;
}

function renderLimitations(container, limitations) {
  if (!limitations.length) return;

  container.appendChild(el("h3", "rr-subtitle", "Limitations"));
  container.appendChild(bulletList(limitations));
}

function renderTechnicalDetails(data, scope) {
  const details = el("details", "rr-tech");
  details.appendChild(el("summary", "", "Technical details"));

  const scopeEntries = Object.entries(asObject(scope));

  if (scopeEntries.length) {
    details.appendChild(el("h3", "rr-subtitle", "Analysis scope"));

    scopeEntries.forEach(([key, value]) => {
      const line = el("p", "rr-reason");
      line.append(
        el("strong", "", key.replace(/_/g, " ") + ": "),
        document.createTextNode(cellText(value))
      );
      details.appendChild(line);
    });
  }

  if (data && !isBlank(data.note)) {
    details.appendChild(el("h3", "rr-subtitle", "Note"));
    details.appendChild(el("p", "rr-reason", data.note));
  }

  details.appendChild(el("h3", "rr-subtitle", "Raw JSON"));
  details.appendChild(el("pre", "rr-json", JSON.stringify(data, null, 2)));
  return details;
}

function renderFullReliability(data, payload) {
  resultsEl.replaceChildren();

  const root = el("div", "rr");

  // 1. Summary bar: one badge per dimension plus memory analysis.
  const overview = reportCard("Unified Reliability Report");

  overview.appendChild(
    summaryBar([
      ...auditSummaryEntries(data.contextual_audit),
      {
        label: "Memory analysis",
        verdict: asObject(asObject(data.memory_analysis).answer_consistency)
          .verdict
      }
    ])
  );

  // Neither verdict is changed; the report only says they disagree.
  const disagreements = Array.isArray(data.disagreements)
    ? data.disagreements.filter((d) => d && typeof d === "object")
    : [];

  if (disagreements.length) overview.appendChild(renderDisagreements(disagreements));

  // 2. Question and the answer being audited.
  overview.appendChild(el("h3", "rr-subtitle", "Question"));
  overview.appendChild(el("p", "rr-question", cellText(data.question)));
  overview.appendChild(el("h3", "rr-subtitle", "Answer being audited"));
  overview.appendChild(quoteBox(data.answer));

  const errors = Object.entries(asObject(data.errors));

  if (errors.length) {
    const callout = el("div", "rr-callout");
    callout.appendChild(el("strong", "", "Some analyses did not complete"));
    errors.forEach(([key, value]) => {
      callout.appendChild(
        el("p", "rr-reason", key.replace(/_/g, " ") + ": " + cellText(value))
      );
    });
    overview.appendChild(callout);
  }

  root.appendChild(overview);

  // 3-4. Contextual audit dimensions.
  root.appendChild(renderAuditCard("Contextual auditing", data.contextual_audit));

  // 5-6. Memory analysis.
  const memoryCard = reportCard("Context memory analysis");

  if (data.memory_analysis == null) {
    memoryCard.appendChild(
      el("p", "rr-muted", "Memory analysis did not complete.")
    );
  } else {
    renderMemoryAnalysis(memoryCard, data.memory_analysis);
  }

  root.appendChild(memoryCard);

  // 7. Limitations (hidden when empty) and technical details.
  const limitations = collectLimitations(
    data.contextual_audit,
    data.memory_analysis
  );

  if (limitations.length) {
    const limitCard = reportCard("Limitations");
    limitCard.appendChild(bulletList(limitations));
    root.appendChild(limitCard);
  }

  // Mitigation uses the same inputs as the audit that produced this report.
  root.appendChild(renderMitigationCard(payload));
  root.appendChild(renderTechnicalDetails(data, data.scope));

  resultsEl.appendChild(root);
}

function renderDisagreements(disagreements) {
  const callout = el("div", "rr-callout rr-amber");
  callout.setAttribute("role", "note");
  callout.appendChild(el("strong", "", "The two analyses disagree"));

  disagreements.forEach((item) => {
    const label =
      (AUDIT_DIMENSIONS.find(([key]) => key === item.dimension) || [])[1] ||
      String(item.dimension || "").replace(/_/g, " ");

    const row = el("div", "rr-disagreement");
    const head = el("div", "rr-dim-head");
    head.append(
      el("span", "rr-dim-label", label + ":"),
      verdictBadge(item.audit_verdict),
      el("span", "", "vs. memory analysis:"),
      verdictBadge(item.memory_verdict)
    );
    row.appendChild(head);

    if (!isBlank(item.audit_reason)) {
      row.appendChild(el("p", "rr-reason", "Audit said: " + item.audit_reason));
    }
    if (!isBlank(item.memory_reason)) {
      row.appendChild(el("p", "rr-reason", "Memory analysis said: " + item.memory_reason));
    }

    callout.appendChild(row);
  });

  callout.appendChild(
    el(
      "p",
      "rr-reason",
      "Both results are shown unchanged. Check the conflict listed under " +
      "context memory analysis against the answer yourself."
    )
  );

  return callout;
}

function renderMitigationCard(payload) {
  const card = reportCard("Targeted mitigation");

  card.appendChild(
    el(
      "p",
      "rr-reason",
      "Ask TruthLens to propose a correction for actionable contextual " +
      "or memory conflicts, then independently re-audit the corrected " +
      "answer. The original answer will not be replaced automatically."
    )
  );

  const button = el("button", "primary", "Suggest Correction & Re-verify");
  button.type = "button";

  const output = el("div", "rr-mitigation-output");
  output.setAttribute("aria-live", "polite");

  button.addEventListener("click", () => {
    runContextMitigation(payload, button, output);
  });

  card.append(button, output);
  return card;
}

// ============================================================
// TARGETED MITIGATION
// POST /verify/context/mitigate
// ============================================================

async function runContextMitigation(payload, clickedButton, output) {
  if (!payload || !payload.question || !payload.answer) {
    output.replaceChildren(
      el("div", "error", "The question and answer are required for mitigation.")
    );
    return;
  }

  // Prevent duplicate mitigation requests.
  if (clickedButton) clickedButton.disabled = true;

  output.replaceChildren(
    el("p", "rr-muted", "Generating a proposed correction and re-verifying it…")
  );
  statusEl.textContent =
    "Generating a proposed correction and re-verifying it…";

  try {
    // Same five fields that were sent to /verify/context/full.
    const data = await postJSON("/verify/context/mitigate", {
      question: payload.question,
      answer: payload.answer,
      context: payload.context,
      conversation_history: payload.conversation_history,
      instructions: payload.instructions
    });

    renderMitigationResult(output, data);
    statusEl.textContent =
      "Mitigation response received. Review the proposed correction and audit.";
  } catch (error) {
    // Shown next to the button so the audit report stays on screen.
    output.replaceChildren(
      el(
        "div",
        "error",
        "Mitigation failed: " + (error && error.message ? error.message : error) +
        ". Check that the API is running and that POST /verify/context/mitigate responds."
      )
    );
    statusEl.textContent = "Mitigation failed.";
  } finally {
    if (clickedButton) clickedButton.disabled = false;
  }
}

function copyButton(label, getText) {
  const button = el("button", "primary rr-small", label);
  button.type = "button";

  button.addEventListener("click", async () => {
    let copied = false;

    try {
      await navigator.clipboard.writeText(getText());
      copied = true;
    } catch (error) {
      copied = false;
    }

    button.textContent = copied ? "Copied!" : "Copy failed — select the text manually";
    setTimeout(() => { button.textContent = label; }, 2000);
  });

  return button;
}

function renderRemainingFailures(failures) {
  const rows = failures.map((failure) => {
    const item = asObject(failure);
    const detail = [item.claim, item.reason].filter((v) => !isBlank(v)).join(" — ");

    return [
      String(item.dimension || "").replace(/[_.]/g, " "),
      verdictBadge(item.verdict),
      detail
    ];
  });

  return makeTable(["Dimension", "Verdict", "Detail"], rows);
}

function renderMitigationResult(container, data) {
  const result = el("div", "rr-mitigation-result");

  result.appendChild(el("h3", "rr-subtitle", "Mitigation result"));
  if (!isBlank(data.message)) result.appendChild(el("p", "rr-reason", data.message));

  const refinedPrompt = typeof data.refined_prompt === "string" ? data.refined_prompt : "";
  const suggestedAnswer = typeof data.suggested_answer === "string" ? data.suggested_answer : "";

  if (!refinedPrompt && !suggestedAnswer) {
    container.replaceChildren(result);
    return;
  }

  // Refined prompt — to give to the original LLM.
  result.appendChild(el("h3", "rr-subtitle", "Refined prompt"));

  const promptBox = el("textarea", "rr-prompt-box");
  promptBox.value = refinedPrompt;
  promptBox.readOnly = true;
  promptBox.rows = 10;
  promptBox.setAttribute("aria-label", "Refined prompt");

  result.append(
    promptBox,
    copyButton("Copy refined prompt", () => promptBox.value),
    el(
      "p",
      "rr-muted",
      "Ready to give to the original LLM. TruthLens has not submitted it."
    )
  );

  // Suggested answer — separate from the prompt.
  result.appendChild(el("h3", "rr-subtitle", "Suggested answer"));
  result.appendChild(quoteBox(suggestedAnswer));

  const answerActions = el("div", "rr-actions");
  answerActions.appendChild(copyButton("Copy suggested answer", () => suggestedAnswer));

  const useButton = el("button", "primary rr-small", "Use as answer for re-audit");
  useButton.type = "button";
  useButton.addEventListener("click", () => {
    contextAnswerEl.value = suggestedAnswer;
    contextAnswerEl.scrollIntoView({ behavior: "smooth", block: "center" });
    contextAnswerEl.focus();
    statusEl.textContent =
      "Suggested answer placed in the input field. Review it before running another audit.";
  });
  answerActions.appendChild(useButton);
  result.appendChild(answerActions);

  if (Array.isArray(data.changes) && data.changes.length) {
    result.appendChild(el("h3", "rr-subtitle", "Changes made"));
    result.appendChild(bulletList(data.changes));
  }

  // Re-audit of the suggested answer.
  result.appendChild(el("h3", "rr-subtitle", "Re-audit of the suggested answer"));

  if (data.re_verification && typeof data.re_verification === "object") {
    const entries = auditSummaryEntries(data.re_verification);

    if (data.re_verification_memory) {
      entries.push({
        label: "Memory analysis",
        verdict: asObject(asObject(data.re_verification_memory).answer_consistency)
          .verdict
      });
    }

    result.appendChild(summaryBar(entries));
  } else {
    result.appendChild(el("p", "rr-muted", "No re-audit was returned."));
  }

  const remaining = Array.isArray(data.remaining_failures) ? data.remaining_failures : [];

  if (remaining.length) {
    const callout = el("div", "rr-callout");
    callout.appendChild(el("strong", "", "Issues remaining after correction"));
    callout.appendChild(renderRemainingFailures(remaining));
    result.appendChild(callout);
  }

  renderLimitations(
    result,
    (Array.isArray(data.correction_limitations) ? data.correction_limitations : [])
      .filter((item) => !isBlank(item))
  );

  const details = el("details", "rr-tech");
  details.appendChild(el("summary", "", "Technical details"));
  details.appendChild(el("pre", "rr-json", JSON.stringify(data, null, 2)));
  result.appendChild(details);

  container.replaceChildren(result);
}

// ============================================================
// CONTEXT MEMORY RESULT RENDERING
// ============================================================

function renderMemoryAnalysis(card, analysis) {
  if (!analysis || typeof analysis !== "object" || Array.isArray(analysis)) {
    card.appendChild(el("p", "rr-muted", cellText(analysis)));
    return;
  }

  // Memory items.
  card.appendChild(el("h3", "rr-subtitle", "Goals, preferences and decisions found"));

  const items = Array.isArray(analysis.memory_items)
    ? analysis.memory_items.filter((item) => item && typeof item === "object")
    : null;

  if (items === null) {
    card.appendChild(el("p", "rr-muted", "No memory_items array was returned."));
  } else if (!items.length) {
    card.appendChild(el("p", "rr-muted", "No explicit memory items extracted."));
  } else {
    const showSupersedes = items.some((item) => !isBlank(item.supersedes));
    const headers = ["Category", "Statement", "Evidence", "Status"];
    if (showSupersedes) headers.push("Supersedes");

    card.appendChild(
      makeTable(
        headers,
        items.map((item) => {
          const row = [item.category, item.statement, item.evidence, item.status];
          if (showSupersedes) row.push(item.supersedes);
          return row;
        })
      )
    );
  }

  // Answer consistency.
  card.appendChild(el("h3", "rr-subtitle", "Answer consistency"));

  const consistency = asObject(analysis.answer_consistency);

  if (isBlank(consistency.verdict) && isBlank(consistency.reason)) {
    card.appendChild(
      el("p", "rr-muted", "No answer-consistency verdict returned.")
    );
    return;
  }

  card.appendChild(
    dimensionRow("Answer vs. earlier instructions", consistency.verdict, consistency.reason)
  );

  const conflicts = Array.isArray(consistency.conflicts)
    ? consistency.conflicts.filter((c) => c && typeof c === "object")
    : [];

  if (conflicts.length) {
    const callout = el("div", "rr-callout");
    callout.appendChild(
      el("strong", "", conflicts.length === 1 ? "Conflict found" : "Conflicts found")
    );

    conflicts.forEach((conflict) => {
      const block = el("div", "rr-conflict");

      [
        ["Rule", conflict.memory_statement],
        ["In the answer", conflict.answer_excerpt],
        ["Why", conflict.reason]
      ].forEach(([label, value]) => {
        const line = el("div", "rr-conflict-line");
        line.append(
          el("span", "rr-conflict-label", label + ":"),
          el("span", "rr-conflict-text", cellText(value))
        );
        block.appendChild(line);
      });

      callout.appendChild(block);
    });

    card.appendChild(callout);
  }
}

// ============================================================
// STANDALONE CONTEXT MEMORY ANALYSIS
// POST /verify/context/memory
// ============================================================

async function verifyMemory() {
  const question = memoryQuestionEl.value.trim();
  const answer = memoryAnswerEl.value.trim();
  const conversation_history = memoryHistoryEl.value.trim();
  const instructions = memoryInstructionsEl.value.trim();

  if (!question || !answer) {
    showError("Enter the current question and the LLM-generated answer.");
    return;
  }

  if (!conversation_history) {
    showError("Enter conversation history for memory analysis.");
    return;
  }

  startRequest("Analyzing user goals, preferences, and decisions…");

  try {
    const data = await postJSON("/verify/context/memory", {
      question,
      answer,
      context: "",
      conversation_history,
      instructions
    });

    const analysis =
      data.memory_analysis || data.analysis || data.result || data;

    resultsEl.replaceChildren();

    const root = el("div", "rr");
    const card = reportCard("Context memory analysis");
    renderMemoryAnalysis(card, analysis);
    renderLimitations(card, collectLimitations(analysis));
    root.appendChild(card);
    resultsEl.appendChild(root);

    statusEl.textContent = "Context memory analysis completed.";
  } catch (error) {
    showError("Context memory analysis failed: " + error.message);
  } finally {
    finishRequest();
  }
}

// ============================================================
// 4. CODE CHECK — SEPARATE SERVER, PORT 8001 OR 8002
// ============================================================

const CODE_API_CANDIDATES = [
  "http://127.0.0.1:8001",
  "http://127.0.0.1:8002"
];

let codeApiBase = null;

async function findCodeApi() {
  if (codeApiBase) return codeApiBase;

  for (const base of CODE_API_CANDIDATES) {
    try {
      const response = await fetch(base + "/health");

      if (response.ok && (await response.json()).status === "ok") {
        codeApiBase = base;
        return base;
      }
    } catch (error) {
      // Try the next port.
    }
  }

  return null;
}

async function verifyCode() {
  const text = codeTextEl.value.trim();

  if (!text) {
    showError("Paste an LLM answer containing code to check.");
    return;
  }

  startRequest("Checking imports and function calls…");

  try {
    const base = await findCodeApi();

    if (!base) {
      throw new Error("Code-check server not found on port 8001 or 8002.");
    }

    const response = await fetch(base + "/check-code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "API returned " + response.status);
    }

    renderCode(data);
    statusEl.textContent = "Code check completed.";
  } catch (error) {
    codeApiBase = null;
    showError("Code check failed: " + error.message);
  } finally {
    finishRequest();
  }
}

function renderCode(data) {
  const counts = data.summary || {};
  const findings = data.findings || [];

  summaryEl.replaceChildren();

  const heading = makeHeading(
    "Code check summary — " + findings.length +
    " findings in " + (data.blocks_found ?? 0) +
    " code block" + (data.blocks_found === 1 ? "" : "s")
  );

  const tally = document.createElement("div");
  tally.className = "tally";

  Object.entries(counts).forEach(([verdict, count]) => {
    const item = document.createElement("span");
    item.className = "tally-item b-" + verdict;
    item.textContent = verdictLabel(verdict) + ": " + count;
    tally.appendChild(item);
  });

  summaryEl.append(heading, tally);
  summaryEl.hidden = false;

  if (!findings.length) {
    const message = document.createElement("p");
    message.textContent = "No Python code findings were returned.";
    resultsEl.appendChild(message);
    return;
  }

  const list = document.createElement("div");
  list.className = "code-findings";

  findings.forEach((finding) => {
    const row = document.createElement("div");
    row.className = "code-row v-" + finding.verdict;

    const item = document.createElement("code");
    item.className = "code-item";
    item.textContent = finding.item || "";

    const kind = document.createElement("span");
    kind.className = "code-kind";
    kind.textContent =
      (finding.kind || "Finding") + " · block " +
      (finding.block ?? "Unknown");

    const badge = document.createElement("span");
    badge.className = "badge b-" + finding.verdict;
    badge.textContent = verdictLabel(finding.verdict);

    const reason = document.createElement("p");
    reason.className = "code-reason";
    reason.textContent = finding.reason || "";

    row.append(item, kind, badge, reason);
    list.appendChild(row);
  });

  resultsEl.appendChild(list);
}

// ============================================================
// GENERAL TEXT HELPERS
// ============================================================

function cleanText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function truncate(value, max) {
  return value.length > max
    ? value.slice(0, max).trimEnd() + "…"
    : value;
}

// Initialize the UI.
setMode("facts");
