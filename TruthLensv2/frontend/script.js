"use strict";

// Same-origin when served by api.py; falls back to the local
// API port if the page is opened directly from disk.
const API_BASE =
  window.location.protocol === "file:"
    ? "http://127.0.0.1:8000"
    : "";

// Each paragraph mixes claims the KB can support with a
// planted error or an unsupported detail, so a single demo run
// shows the system discriminating rather than defaulting to
// one verdict.
const EXAMPLES = {
  1:
    "The Eiffel Tower is located in Paris, France, and was " +
    "built by Gustave Eiffel in 1889. It stands over 500 " +
    "meters tall, making it one of the tallest structures in " +
    "Europe at the time.",

  2:
    "The Reserve Bank of India kept the repo rate unchanged " +
    "at its August 2026 policy meeting, marking the fourth " +
    "consecutive pause. The central bank raised its FY27 GDP " +
    "growth forecast to 6.7% from 6.6%, citing resilient " +
    "domestic economic activity. RBI governor Sanjay Malhotra " +
    "led the decision. The committee also announced a " +
    "complete removal of all capital gains tax on equity " +
    "investments.",

  3:
    "Ola Electric Mobility signed a Memorandum of " +
    "Understanding with Axis Energy to deploy up to 20 GWh of " +
    "battery energy storage. The deal marks the company's " +
    "expansion into utility-scale energy storage beyond its " +
    "two-wheeler business. Ola Electric shares rallied more " +
    "than 7% on the BSE following the announcement. The " +
    "company also confirmed it has acquired Tesla's Indian " +
    "manufacturing division outright.",
};

const VERDICT_LABEL = {
  SUPPORTED: "SUPPORTED",
  CONTRADICTED: "CONTRADICTED",
  PARTIALLY_SUPPORTED: "PARTIALLY SUPPORTED",
  INSUFFICIENT_INFORMATION: "INSUFFICIENT INFO",
};

const inputEl = document.getElementById("input-text");
const btnEl = document.getElementById("verify-btn");
const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const resultsEl = document.getElementById("results");
const factualInputEl = document.getElementById("factual-input");
const mathInputEl = document.getElementById("math-input");
const mathQuestionEl = document.getElementById("math-question");
const mathAnswerEl = document.getElementById("math-answer");
let activeMode = "facts";

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
  if (activeMode === "math") {
    verifyMath();
  } else {
    verify();
  }
});

function setMode(mode) {
  activeMode = mode;
  factualInputEl.hidden = mode !== "facts";
  mathInputEl.hidden = mode !== "math";
  btnEl.textContent = mode === "math" ? "Verify math" : "Verify";
  statusEl.textContent = "";
  summaryEl.hidden = true;
  resultsEl.innerHTML = "";
  document.querySelectorAll(".mode-button").forEach((button) => {
    const selected = button.dataset.mode === mode;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
}

async function verify() {
  const text = inputEl.value.trim();

  resultsEl.innerHTML = "";
  summaryEl.hidden = true;

  if (!text) {
    showError("Please enter or select some text to verify.");
    return;
  }

  btnEl.disabled = true;
  statusEl.innerHTML =
    '<span class="spinner"></span>Extracting claims and ' +
    "verifying against the Knowledge Base…";

  try {
    const response = await fetch(API_BASE + "/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      throw new Error("API returned " + response.status);
    }

    const data = await response.json();

    if (data.error) {
      showError(data.error);
      return;
    }

    if (!data.claims || data.claims.length === 0) {
      showError(
        "No factual claims were extracted from this text."
      );
      return;
    }

    render(data);
    statusEl.textContent = "";
  } catch (err) {
    showError(
      "Could not reach the TruthLens API. Start it with " +
        "`uvicorn api:app --port 8000` from the TruthLensv2 " +
        "directory. (" + err.message + ")"
    );
  } finally {
    btnEl.disabled = false;
  }
}

async function verifyMath() {
  const question = mathQuestionEl.value.trim();
  const answer = mathAnswerEl.value.trim();

  resultsEl.innerHTML = "";
  summaryEl.hidden = true;

  if (!question || !answer) {
    showError("Enter both the original math question and the LLM answer.");
    return;
  }

  btnEl.disabled = true;
  statusEl.innerHTML =
    '<span class="spinner"></span>Independently checking the calculation…';

  try {
    const response = await fetch(API_BASE + "/verify/math", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, answer }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "API returned " + response.status);
    }

    renderMath(await response.json());
    statusEl.textContent = "";
  } catch (err) {
    showError(
      "Could not verify this math answer. Start the TruthLens API with " +
        "`uvicorn api:app --port 8000` from the TruthLensv2 directory. (" +
        err.message + ")"
    );
  } finally {
    btnEl.disabled = false;
  }
}

function renderMath(result) {
  const card = document.createElement("article");
  card.className = "math-card math-" + result.verdict;

  const title = document.createElement("div");
  title.className = "math-result-head";
  const heading = document.createElement("h2");
  heading.textContent = "Independent math verification";
  const badge = document.createElement("span");
  badge.className = "badge math-badge-" + result.verdict;
  badge.textContent = result.verdict.replace(/_/g, " ");
  title.append(heading, badge);
  card.appendChild(title);

  appendMathField(card, "Original question", result.original_question);
  appendMathField(card, "LLM answer", result.llm_answer);
  appendMathField(
    card,
    "Extracted final answer",
    result.original_answer || "No final numeric answer extracted"
  );
  appendMathField(
    card,
    "Question-derived expression",
    result.extracted_expression || "Not reconstructed"
  );
  appendMathField(
    card,
    "Independently computed result",
    result.computed_result || "Not computed"
  );
  if (
    result.computed_exact_result &&
    result.computed_exact_result !== result.computed_result
  ) {
    appendMathField(
      card,
      "Exact result before rounding",
      result.computed_exact_result
    );
    appendMathField(
      card,
      "Requested rounding",
      result.rounding_digits + " decimal place(s)"
    );
  }
  if (result.expression_tree) {
    appendMathField(
      card,
      "Structured expression",
      JSON.stringify(result.expression_tree, null, 2)
    );
  }
  if (result.quantities && result.quantities.length) {
    appendMathField(
      card,
      "Question quantities and roles",
      result.quantities
        .map((item) => item.value + (item.unit ? " " + item.unit : "") +
          " — " + item.semantic_role + " (evidence: " + item.evidence + ")")
        .join("\n")
    );
  }
  if (result.solution_trace && result.solution_trace.length) {
    appendMathField(
      card,
      "Solution trace",
      result.solution_trace.join("\n")
    );
  }
  if (result.reasoning_assertions && result.reasoning_assertions.length) {
    appendMathField(
      card,
      "Reasoning assertions checked",
      result.reasoning_assertions
        .map((item) => item.expression + " = " + item.stated_result +
          " — " + item.status + ": " + item.explanation)
        .join("\n")
    );
  }
  if (result.intermediate_errors && result.intermediate_errors.length) {
    appendMathField(
      card,
      "Intermediate errors",
      result.intermediate_errors
        .map((item) => item.expression + " = " + item.stated_result)
        .join("\n")
    );
  }
  if (result.verification_coverage) {
    appendMathField(
      card,
      "Verification coverage",
      JSON.stringify(result.verification_coverage, null, 2)
    );
  }
  appendMathField(
    card,
    "Conclusive",
    result.is_conclusive ? "Yes" : "No — unable to verify"
  );
  if (result.inconclusive_reason) {
    appendMathField(
      card,
      "Inconclusive reason",
      result.inconclusive_reason
    );
  }
  appendMathField(
    card,
    "Verification diagnostics",
    "Interpreter: " + (result.interpreter || "deterministic") +
      "; model calls: " + (result.model_calls || 0) +
      "; latency: " + (result.latency_ms || 0) + " ms"
  );
  appendMathField(card, "Explanation", result.explanation);
  resultsEl.appendChild(card);
}

function appendMathField(container, label, value) {
  const field = document.createElement("div");
  field.className = "math-field";
  const name = document.createElement("div");
  name.className = "math-field-label";
  name.textContent = label;
  const content = document.createElement("p");
  content.textContent = value;
  field.append(name, content);
  container.appendChild(field);
}

function render(data) {
  renderSummary(data.summary, data.claims.length);

  const heading = document.createElement("h2");
  heading.className = "results-heading";
  heading.textContent =
    data.claims.length +
    " claims extracted and verified independently";
  resultsEl.appendChild(heading);

  data.claims.forEach((claim, index) => {
    resultsEl.appendChild(renderClaim(claim, index + 1));
  });
}

function renderSummary(summary, total) {
  const counts = (summary && summary.verdict_counts) || {};

  const tally = Object.keys(counts)
    .map(
      (verdict) =>
        '<span class="tally-item b-' +
        verdict +
        '">' +
        (VERDICT_LABEL[verdict] || verdict) +
        ": " +
        counts[verdict] +
        "</span>"
    )
    .join("");

  summaryEl.innerHTML =
    "<h2>Result summary &mdash; " +
    total +
    " claims</h2>" +
    '<div class="tally">' +
    tally +
    "</div>" +
    '<p class="summary-note">' +
    escapeHtml(summary.note || "") +
    "</p>";

  summaryEl.hidden = false;
}

function renderClaim(claim, position) {
  const card = document.createElement("article");
  card.className = "claim-card v-" + claim.verdict;

  const percent = Math.round((claim.confidence || 0) * 100);

  card.innerHTML =
    '<div class="claim-head">' +
    "<div>" +
    '<div class="claim-index">CLAIM ' +
    position +
    "</div>" +
    '<p class="claim-text">' +
    escapeHtml(claim.claim) +
    "</p>" +
    "</div>" +
    '<span class="badge b-' +
    claim.verdict +
    '">' +
    (VERDICT_LABEL[claim.verdict] || claim.verdict) +
    "</span>" +
    "</div>" +
    '<div class="confidence">' +
    '<span class="conf-label">Confidence</span>' +
    '<div class="bar"><div class="bar-fill f-' +
    claim.verdict +
    '" style="width:' +
    percent +
    '%"></div></div>' +
    '<span class="conf-value">' +
    claim.confidence.toFixed(2) +
    "</span>" +
    "</div>";

  if (claim.explanation) {
    const p = document.createElement("p");
    p.className = "explanation";
    p.textContent = claim.explanation;
    card.appendChild(p);
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
  const contradicting = usableEvidence(
    claim.contradicting_evidence
  );
  const total = supporting.length + contradicting.length;

  const details = document.createElement("details");
  details.className = "evidence";

  const summary = document.createElement("summary");
  summary.textContent =
    total === 0
      ? "No evidence retrieved"
      : "Evidence used (" + total + ")";
  details.appendChild(summary);

  if (total === 0) {
    const empty = document.createElement("p");
    empty.className = "ev-empty";
    empty.textContent =
      "The Knowledge Base returned no evidence passing the " +
      "retrieval gate for this claim.";
    details.appendChild(empty);
    return details;
  }

  appendGroup(details, "SUPPORTING", supporting);
  appendGroup(details, "CONTRADICTING", contradicting);

  return details;
}

// KB evidence is scraped news HTML: some items reduce to an
// empty string or a bare anchor fragment once tags are
// stripped. Those render as blank cards, so drop them rather
// than show empty boxes during a demo.
function usableEvidence(items) {
  return (items || []).filter((item) => {
    const text = cleanText(item.text);
    return text.length >= 40 && !/^target=|^oc=\d/.test(text);
  });
}

function appendGroup(container, label, items) {
  if (!items.length) return;

  const heading = document.createElement("div");
  heading.className = "ev-group-label";
  heading.textContent = label + " (" + items.length + ")";
  container.appendChild(heading);

  items.forEach((item) => {
    const wrap = document.createElement("div");
    wrap.className = "ev-item";

    const src = document.createElement("div");
    src.className = "ev-source";
    src.textContent = item.source || "Unknown source";

    const text = document.createElement("p");
    text.className = "ev-text";
    text.textContent = truncate(cleanText(item.text), 320);

    wrap.appendChild(src);
    wrap.appendChild(text);
    container.appendChild(wrap);
  });
}

// KB evidence sometimes carries raw HTML fragments from the
// news scrape; strip tags so the demo never renders markup.
function cleanText(value) {
  const div = document.createElement("div");
  div.innerHTML = String(value || "");
  return (div.textContent || "").replace(/\s+/g, " ").trim();
}

function truncate(value, max) {
  return value.length > max
    ? value.slice(0, max).trimEnd() + "…"
    : value;
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value == null ? "" : value);
  return div.innerHTML;
}

function showError(message) {
  statusEl.textContent = "";
  resultsEl.innerHTML =
    '<div class="error">' + escapeHtml(message) + "</div>";
}
