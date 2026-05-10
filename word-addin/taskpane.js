const state = {
  lastResult: null,
  lastTextSource: null,
  agentHistory: [],
  officeReady: false
};

const elements = {
  hostStatus: document.getElementById("hostStatus"),
  apiBase: document.getElementById("apiBase"),
  healthButton: document.getElementById("healthButton"),
  healthStatus: document.getElementById("healthStatus"),
  refreshButton: document.getElementById("refreshButton"),
  scopeLabel: document.getElementById("scopeLabel"),
  selectedPreview: document.getElementById("selectedPreview"),
  syntaxButton: document.getElementById("syntaxButton"),
  wordButton: document.getElementById("wordButton"),
  styleInput: document.getElementById("styleInput"),
  styleButton: document.getElementById("styleButton"),
  instructionInput: document.getElementById("instructionInput"),
  chatLog: document.getElementById("chatLog"),
  agentInput: document.getElementById("agentInput"),
  agentButton: document.getElementById("agentButton"),
  resetAgentButton: document.getElementById("resetAgentButton"),
  loading: document.getElementById("loading"),
  errorBox: document.getElementById("errorBox"),
  replyBox: document.getElementById("replyBox"),
  finalTextBox: document.getElementById("finalTextBox"),
  actionsBox: document.getElementById("actionsBox"),
  applyButton: document.getElementById("applyButton")
};

Office.onReady((info) => {
  state.officeReady = info.host === Office.HostType.Word;
  elements.hostStatus.textContent = state.officeReady
    ? "Connected to Word"
    : "Open this pane inside Microsoft Word.";
  setTaskButtonsDisabled(!state.officeReady);
  if (state.officeReady) {
    refreshSelection();
  }
  checkHealth();
});

function apiUrl(path) {
  return `${elements.apiBase.value.replace(/\/$/, "")}${path}`;
}

function setBusy(isBusy) {
  elements.loading.hidden = !isBusy;
  [
    elements.healthButton,
    elements.refreshButton,
    elements.syntaxButton,
    elements.wordButton,
    elements.styleButton,
    elements.agentButton,
    elements.applyButton
  ].forEach((button) => {
    button.disabled = isBusy || (!state.officeReady && button !== elements.healthButton);
  });
  if (!isBusy) {
    elements.applyButton.disabled = !getApplicableText(state.lastResult);
  }
}

function setTaskButtonsDisabled(disabled) {
  [
    elements.refreshButton,
    elements.syntaxButton,
    elements.wordButton,
    elements.styleButton,
    elements.agentButton,
    elements.applyButton
  ].forEach((button) => {
    button.disabled = disabled;
  });
}

function showError(message) {
  elements.errorBox.hidden = !message;
  elements.errorBox.textContent = message || "";
}

async function getWordPayload() {
  if (!state.officeReady) {
    throw new Error("This task pane is not connected to Word.");
  }

  return Word.run(async (context) => {
    const selection = context.document.getSelection();
    const body = context.document.body;
    selection.load("text");
    body.load("text");
    await context.sync();

    const selectedText = selection.text || "";
    const bodyText = body.text || "";
    const hasSelection = selectedText.trim().length > 0;
    const text = hasSelection ? selectedText : bodyText;
    const contextWindow = getContextWindow(bodyText, selectedText);

    state.lastTextSource = {
      kind: hasSelection ? "selection" : "document"
    };

    return {
      text,
      context: contextWindow,
      instruction: elements.instructionInput.value.trim() || null
    };
  });
}

function getContextWindow(bodyText, selectedText) {
  if (!selectedText) {
    return { before: "", after: "" };
  }

  const index = bodyText.indexOf(selectedText);
  if (index < 0) {
    return { before: "", after: "" };
  }

  return {
    before: bodyText.slice(Math.max(0, index - 500), index),
    after: bodyText.slice(index + selectedText.length, index + selectedText.length + 500)
  };
}

async function refreshSelection() {
  try {
    const payload = await getWordPayload();
    const source = state.lastTextSource && state.lastTextSource.kind === "selection"
      ? "Current selection"
      : "Full document";
    elements.scopeLabel.textContent = `${source} (${payload.text.length} chars)`;
    elements.selectedPreview.textContent = payload.text || "(empty)";
  } catch (error) {
    showError(error.message || String(error));
  }
}

async function requestJson(path, payload) {
  setBusy(true);
  showError("");
  try {
    const response = await fetch(apiUrl(path), {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || JSON.stringify(data, null, 2));
    }
    return data;
  } finally {
    setBusy(false);
  }
}

async function runTask(path, extra = {}) {
  try {
    const payload = {
      ...(await getWordPayload()),
      ...extra
    };
    if (!payload.text.trim()) {
      showError("Select text or add text to the document before running a task.");
      return;
    }
    await refreshSelection();
    const result = await requestJson(path, payload);
    renderResult(result);
  } catch (error) {
    showError(error.message || String(error));
  }
}

async function runAgent() {
  const message = elements.agentInput.value.trim();
  if (!message) {
    showError("Enter an agent message.");
    return;
  }

  try {
    const selection = await getWordPayload();
    const payload = {
      message,
      selection: selection.text.trim() ? selection : null,
      history: state.agentHistory
    };

    appendChat("user", message);
    elements.agentInput.value = "";

    const result = await requestJson("/agent/chat", payload);
    renderResult(result);
    appendChat("assistant", result.reply);
    state.agentHistory.push({ role: "user", content: message });
    state.agentHistory.push({ role: "assistant", content: result.reply });
  } catch (error) {
    showError(error.message || String(error));
  }
}

function renderResult(result) {
  state.lastResult = result;
  elements.replyBox.textContent = result.reply || "";
  elements.finalTextBox.textContent = result.final_text || "";
  elements.actionsBox.innerHTML = "";

  (result.actions || []).forEach((action, index) => {
    const item = document.createElement("div");
    item.className = "action-item";
    item.innerHTML = `
      <b>${index + 1}. ${escapeHtml(action.type || "action")} (${escapeHtml(action.severity || "info")})</b>
      ${action.original ? `<p>Original: ${escapeHtml(action.original)}</p>` : ""}
      ${action.replacement ? `<p>Replacement: ${escapeHtml(action.replacement)}</p>` : ""}
      ${action.reason ? `<p>Reason: ${escapeHtml(action.reason)}</p>` : ""}
    `;
    elements.actionsBox.appendChild(item);
  });

  elements.applyButton.disabled = !getApplicableText(result);
}

function getApplicableText(result) {
  if (!result) {
    return null;
  }
  const replaceAction = (result.actions || []).find((action) => {
    return action.type === "replace_selection" && action.replacement;
  });
  return result.final_text || (replaceAction && replaceAction.replacement) || null;
}

async function applyResult() {
  const text = getApplicableText(state.lastResult);
  if (!text || !state.lastTextSource) {
    return;
  }

  try {
    await Word.run(async (context) => {
      if (state.lastTextSource.kind === "document") {
        context.document.body.insertText(text, Word.InsertLocation.replace);
      } else {
        const selection = context.document.getSelection();
        selection.insertText(text, Word.InsertLocation.replace);
      }
      await context.sync();
    });
    await refreshSelection();
  } catch (error) {
    showError(error.message || String(error));
  }
}

function appendChat(role, content) {
  const message = document.createElement("div");
  message.className = "chat-message";
  message.innerHTML = `<strong>${escapeHtml(role)}</strong>${escapeHtml(content)}`;
  elements.chatLog.appendChild(message);
  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
}

function resetAgent() {
  state.agentHistory = [];
  elements.chatLog.innerHTML = "";
}

async function checkHealth() {
  elements.healthStatus.className = "status-dot";
  try {
    const response = await fetch(apiUrl("/health"));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    elements.healthStatus.className = "status-dot ok";
  } catch (error) {
    elements.healthStatus.className = "status-dot error";
    showError(`Health check failed: ${error.message || String(error)}`);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

elements.healthButton.addEventListener("click", checkHealth);
elements.refreshButton.addEventListener("click", refreshSelection);
elements.syntaxButton.addEventListener("click", () => runTask("/tasks/syntax"));
elements.wordButton.addEventListener("click", () => runTask("/tasks/word-choice"));
elements.styleButton.addEventListener("click", () => {
  runTask("/tasks/style", { style: elements.styleInput.value.trim() || "polished" });
});
elements.agentButton.addEventListener("click", runAgent);
elements.resetAgentButton.addEventListener("click", resetAgent);
elements.applyButton.addEventListener("click", applyResult);
