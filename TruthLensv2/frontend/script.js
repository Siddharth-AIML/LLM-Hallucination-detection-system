
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
    renderFullReliability(data);

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

function renderFullReliability(data) {
  resultsEl.replaceChildren();

  const overview = createCard("Unified Reliability Report");
  showField(overview, "Workflow status", data.status);
  showField(overview, "Question", data.question);
  showField(overview, "Answer being audited", data.answer);

  if (data.note) showField(overview, "Important note", data.note);

  if (data.errors && Object.keys(data.errors).length) {
    showField(overview, "Analysis errors", data.errors);
  }

  resultsEl.appendChild(overview);

  const auditCard = createCard("1. Contextual Auditing");

  if (data.contextual_audit == null) {
    showField(auditCard, "Status", "Contextual audit did not complete.");
  } else {
    showObject(auditCard, data.contextual_audit);
  }

  resultsEl.appendChild(auditCard);

  const memoryCard = createCard("2. Context Memory Analysis");

  if (data.memory_analysis == null) {
    showField(memoryCard, "Status", "Memory analysis did not complete.");
  } else {
    renderMemoryFields(memoryCard, data.memory_analysis);
  }

  resultsEl.appendChild(memoryCard);

  if (data.scope) {
    const scopeCard = createCard("3. Analysis Scope");
    showObject(scopeCard, data.scope);
    resultsEl.appendChild(scopeCard);
  }

  // Mitigation action uses the same question, answer, context,
  // history and instructions that were used for the initial audit.
  const mitigationCard = createCard("4. Targeted Mitigation");

  const explanation = document.createElement("p");
  explanation.className = "explanation";
  explanation.textContent =
    "Ask TruthLens to propose a correction for actionable contextual " +
    "or memory conflicts, then independently re-audit the corrected answer. " +
    "The original answer will not be replaced automatically.";

  mitigationCard.appendChild(explanation);

  const mitigateButton = document.createElement("button");
  mitigateButton.type = "button";
  mitigateButton.className = "primary";
  mitigateButton.textContent = "Suggest Correction & Re-verify";

  mitigateButton.addEventListener("click", () => {
    runContextMitigation(getContextPayload(), mitigateButton);
  });

  mitigationCard.appendChild(mitigateButton);
  resultsEl.appendChild(mitigationCard);
}

// ============================================================
// TARGETED MITIGATION
// POST /verify/context/mitigate
// ============================================================

async function runContextMitigation(payload, clickedButton) {
  if (!payload.question || !payload.answer) {
    showError("The question and answer are required for mitigation.");
    return;
  }

  // Prevent duplicate mitigation requests.
  if (clickedButton) clickedButton.disabled = true;
  btnEl.disabled = true;

  statusEl.textContent =
    "Generating a proposed correction and re-verifying it…";

  try {
    const data = await postJSON("/verify/context/mitigate", payload);

    renderMitigationResult(data);

    statusEl.textContent =
      "Mitigation response received. Review the proposed correction and audit.";
  } catch (error) {
    showError(
      "Mitigation failed: " + error.message +
      ". Confirm that POST /verify/context/mitigate exists and " +
      "ContextualAuditor.audit_and_mitigate() is implemented."
    );
  } finally {
    if (clickedButton) clickedButton.disabled = false;
    btnEl.disabled = false;
  }
}


function renderMitigationResult(data) {
  const card = createCard("Targeted Mitigation Result");

  showField(card, "Status", data.status);
  showField(card, "Message", data.message);
  showField(card, "Original answer", data.original_answer);

  // 1. Refined prompt — the prompt to give the original LLM.
  card.appendChild(makeHeading("1. Refined Prompt", "h3"));

  if (data.refined_prompt) {
    const promptBox = document.createElement("div");
    promptBox.className = "math-field";

    const promptText = document.createElement("textarea");
    promptText.className = "refined-prompt-text";
    promptText.value = String(data.refined_prompt);
    promptText.readOnly = true;
    promptText.rows = 10;
    promptText.setAttribute("aria-label", "Refined prompt");

    promptText.style.width = "100%";
    promptText.style.boxSizing = "border-box";
    promptText.style.resize = "vertical";
    promptText.style.whiteSpace = "pre-wrap";

    const copyPromptButton = document.createElement("button");
    copyPromptButton.type = "button";
    copyPromptButton.className = "primary";
    copyPromptButton.textContent = "Copy Refined Prompt";

    copyPromptButton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(promptText.value);
        copyPromptButton.textContent = "Copied!";
      } catch (error) {
        // Fallback for browsers where Clipboard API is unavailable.
        promptText.focus();
        promptText.select();

        const copied = document.execCommand("copy");
        copyPromptButton.textContent = copied
          ? "Copied!"
          : "Select the prompt and copy it manually";
      }

      setTimeout(() => {
        copyPromptButton.textContent = "Copy Refined Prompt";
      }, 2000);
    });

    promptBox.appendChild(promptText);
    promptBox.appendChild(copyPromptButton);
    card.appendChild(promptBox);

    const promptNote = document.createElement("p");
    promptNote.className = "explanation";
    promptNote.textContent =
      "This prompt is ready to be supplied to the original LLM. " +
      "TruthLens has generated it but has not automatically submitted it.";
    card.appendChild(promptNote);
  } else {
    showField(
      card,
      "Refined prompt",
      "No refined prompt was generated. Check whether the initial audit detected actionable failures."
    );
  }

  // 2. Proposed corrected answer — separate from the refined prompt.
  card.appendChild(makeHeading("2. Proposed Corrected Answer", "h3"));

  if (data.suggested_answer) {
    const answerBox = document.createElement("div");
    answerBox.className = "math-field";

    const answerText = document.createElement("textarea");
    answerText.value = String(data.suggested_answer);
    answerText.readOnly = true;
    answerText.rows = 7;
    answerText.style.width = "100%";
    answerText.style.boxSizing = "border-box";
    answerText.style.resize = "vertical";

    const copyAnswerButton = document.createElement("button");
    copyAnswerButton.type = "button";
    copyAnswerButton.className = "primary";
    copyAnswerButton.textContent = "Copy Corrected Answer";

    copyAnswerButton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(answerText.value);
        copyAnswerButton.textContent = "Copied!";
      } catch (error) {
        answerText.focus();
        answerText.select();

        const copied = document.execCommand("copy");
        copyAnswerButton.textContent = copied
          ? "Copied!"
          : "Select the answer and copy it manually";
      }

      setTimeout(() => {
        copyAnswerButton.textContent = "Copy Corrected Answer";
      }, 2000);
    });

    const useButton = document.createElement("button");
    useButton.type = "button";
    useButton.className = "primary";
    useButton.textContent = "Use Proposed Answer for Re-audit";

    useButton.addEventListener("click", () => {
      contextAnswerEl.value = String(data.suggested_answer);

      contextAnswerEl.scrollIntoView({
        behavior: "smooth",
        block: "center"
      });

      contextAnswerEl.focus();

      statusEl.textContent =
        "Proposed answer placed in the input field. Review it before running another audit.";
    });

    answerBox.appendChild(answerText);
    answerBox.appendChild(copyAnswerButton);
    answerBox.appendChild(useButton);
    card.appendChild(answerBox);
  } else {
    showField(card, "Proposed correction", "No corrected answer was generated.");
  }

  // 3. Audit trail and verification results.
  const auditDetails = document.createElement("details");
  auditDetails.className = "evidence";

  const auditSummary = document.createElement("summary");
  auditSummary.textContent = "View Audit Trail and Re-verification";
  auditDetails.appendChild(auditSummary);

  showField(auditDetails, "Initial audit", data.initial_audit);
  showField(auditDetails, "Detected failures", data.failures);
  showField(auditDetails, "Changes made", data.changes);
  showField(
    auditDetails,
    "Mitigation limitations",
    data.correction_limitations ?? data.limitations
  );
  showField(auditDetails, "Re-verification", data.re_verification);
  showField(auditDetails, "Remaining failures", data.remaining_failures);

  card.appendChild(auditDetails);
  resultsEl.appendChild(card);
}

// ============================================================
// CONTEXT MEMORY RESULT RENDERING
// ============================================================

function renderMemoryFields(card, analysis) {
  if (!analysis || typeof analysis !== "object" || Array.isArray(analysis)) {
    showField(card, "Result", analysis);
    return;
  }

  const memoryItems = analysis.memory_items;

  if (analysis.status !== undefined) {
    showField(card, "Analysis status", analysis.status);
  }

  card.appendChild(
    makeHeading("Extracted User Goals, Preferences, and Decisions", "h3")
  );

  if (Array.isArray(memoryItems)) {
    if (memoryItems.length === 0) {
      showField(card, "Memory items", "No explicit memory items extracted.");
    }

    memoryItems.forEach((item, index) => {
      const itemCard = document.createElement("div");
      itemCard.className = "math-field";

      const itemHeading = document.createElement("div");
      itemHeading.className = "math-field-label";
      itemHeading.textContent = "Memory item " + (index + 1);
      itemCard.appendChild(itemHeading);

      showObject(itemCard, item);
      card.appendChild(itemCard);
    });
  } else {
    showField(card, "Memory items", "No memory_items array was returned.");
  }

  const consistency = analysis.answer_consistency;

  card.appendChild(makeHeading("Answer Consistency", "h3"));

  if (consistency === undefined) {
    showField(card, "Verdict", "No answer-consistency verdict returned.");
  } else if (
    consistency &&
    typeof consistency === "object" &&
    !Array.isArray(consistency)
  ) {
    showObject(card, consistency);
  } else {
    showField(card, "Verdict", consistency);
  }

  const handled = new Set([
    "status",
    "memory_items",
    "answer_consistency"
  ]);

  Object.entries(analysis).forEach(([key, value]) => {
    if (!handled.has(key)) showField(card, key, value);
  });
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

    const card = createCard("Context Memory Analysis");
    renderMemoryFields(card, analysis);
    resultsEl.appendChild(card);

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
