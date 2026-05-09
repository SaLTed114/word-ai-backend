const state = {
  lastResult: null,
  lastSelection: null,
  editorSelection: { start: 0, end: 0, hadSelection: false },
  agentHistory: []
};

const elements = {
  apiBase: document.getElementById("apiBase"),
  healthButton: document.getElementById("healthButton"),
  healthStatus: document.getElementById("healthStatus"),
  fileInput: document.getElementById("fileInput"),
  openButton: document.getElementById("openButton"),
  saveButton: document.getElementById("saveButton"),
  clearButton: document.getElementById("clearButton"),
  editor: document.getElementById("editor"),
  selectionStatus: document.getElementById("selectionStatus"),
  editorStats: document.getElementById("editorStats"),
  syntaxButton: document.getElementById("syntaxButton"),
  wordButton: document.getElementById("wordButton"),
  styleInput: document.getElementById("styleInput"),
  styleButton: document.getElementById("styleButton"),
  scopeLabel: document.getElementById("scopeLabel"),
  rangeLabel: document.getElementById("rangeLabel"),
  selectedPreview: document.getElementById("selectedPreview"),
  beforePreview: document.getElementById("beforePreview"),
  afterPreview: document.getElementById("afterPreview"),
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

function apiUrl(path) {
  return `${elements.apiBase.value.replace(/\/$/, "")}${path}`;
}

function setBusy(isBusy) {
  elements.loading.hidden = !isBusy;
  [
    elements.syntaxButton,
    elements.wordButton,
    elements.styleButton,
    elements.agentButton,
    elements.healthButton
  ].forEach((button) => {
    button.disabled = isBusy;
  });
}

function showError(message) {
  elements.errorBox.hidden = !message;
  elements.errorBox.textContent = message || "";
}

function getSelectionPayload() {
  const editor = elements.editor;
  const range = getActiveEditorRange();
  const start = range.start;
  const end = range.end;
  const hasSelection = end > start;
  const text = hasSelection ? editor.value.slice(start, end) : editor.value;
  const before = hasSelection ? editor.value.slice(Math.max(0, start - 500), start) : "";
  const after = hasSelection ? editor.value.slice(end, Math.min(editor.value.length, end + 500)) : "";

  state.lastSelection = {
    start: hasSelection ? start : 0,
    end: hasSelection ? end : editor.value.length,
    hadSelection: hasSelection
  };

  return {
    text,
    context: {
      before,
      after
    },
    instruction: elements.instructionInput.value.trim() || null
  };
}

function getActiveEditorRange() {
  const editor = elements.editor;
  const liveStart = editor.selectionStart;
  const liveEnd = editor.selectionEnd;
  if (liveEnd > liveStart) {
    return { start: liveStart, end: liveEnd, hadSelection: true };
  }

  const cached = state.editorSelection;
  if (
    cached &&
    cached.hadSelection &&
    cached.end > cached.start &&
    cached.end <= editor.value.length
  ) {
    return cached;
  }

  return { start: 0, end: editor.value.length, hadSelection: false };
}

function rememberEditorSelection() {
  const editor = elements.editor;
  const start = editor.selectionStart;
  const end = editor.selectionEnd;
  const hadSelection = end > start;
  state.editorSelection = { start, end, hadSelection };
  updateSelectionStatus();
}

function clearEditorSelectionCache() {
  state.editorSelection = { start: 0, end: 0, hadSelection: false };
  state.lastSelection = null;
  updateSelectionStatus();
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
  const payload = {
    ...getSelectionPayload(),
    ...extra
  };
  if (!payload.text.trim()) {
    showError("Enter text or select text before running a task.");
    return;
  }
  try {
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

  const selection = getSelectionPayload();
  const payload = {
    message,
    selection: selection.text.trim() ? selection : null,
    history: state.agentHistory
  };

  appendChat("user", message);
  elements.agentInput.value = "";

  try {
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

function applyResult() {
  const text = getApplicableText(state.lastResult);
  const selection = state.lastSelection;
  if (!text || !selection) {
    return;
  }

  const editor = elements.editor;
  editor.value =
    editor.value.slice(0, selection.start) +
    text +
    editor.value.slice(selection.end);
  const cursor = selection.start + text.length;
  editor.focus();
  editor.setSelectionRange(selection.start, cursor);
  state.editorSelection = { start: selection.start, end: cursor, hadSelection: true };
  updateStats();
  updateSelectionStatus();
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

function openTxtFile(file) {
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    elements.editor.value = String(reader.result || "");
    clearEditorSelectionCache();
    updateStats();
  };
  reader.readAsText(file);
}

function saveTxtFile() {
  const blob = new Blob([elements.editor.value], { type: "text/plain;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "word-ai-editor.txt";
  document.body.appendChild(link);
  link.click();
  URL.revokeObjectURL(link.href);
  link.remove();
}

function updateStats() {
  const text = elements.editor.value;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  elements.editorStats.textContent = `${text.length} chars, ${words} words`;
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
elements.openButton.addEventListener("click", () => elements.fileInput.click());
elements.fileInput.addEventListener("change", () => openTxtFile(elements.fileInput.files[0]));
elements.saveButton.addEventListener("click", saveTxtFile);
elements.clearButton.addEventListener("click", () => {
  elements.editor.value = "";
  clearEditorSelectionCache();
  updateStats();
});
elements.editor.addEventListener("input", () => {
  clearEditorSelectionCache();
  updateStats();
});
["select", "keyup", "mouseup", "touchend"].forEach((eventName) => {
  elements.editor.addEventListener(eventName, rememberEditorSelection);
});
elements.syntaxButton.addEventListener("click", () => runTask("/tasks/syntax"));
elements.wordButton.addEventListener("click", () => runTask("/tasks/word-choice"));
elements.styleButton.addEventListener("click", () => {
  runTask("/tasks/style", { style: elements.styleInput.value.trim() || "polished" });
});
elements.agentButton.addEventListener("click", runAgent);
elements.resetAgentButton.addEventListener("click", resetAgent);
elements.applyButton.addEventListener("click", applyResult);

[
  elements.healthButton,
  elements.syntaxButton,
  elements.wordButton,
  elements.styleButton,
  elements.applyButton
].forEach((button) => {
  button.addEventListener("mousedown", (event) => {
    if (document.activeElement === elements.editor) {
      event.preventDefault();
    }
  });
});

elements.editor.value = "He dont know what to did yesterday.\n\nThis method is good and useful.";
updateStats();
updateSelectionStatus();
checkHealth();

function updateSelectionStatus() {
  const range = getActiveEditorRange();
  if (range.hadSelection) {
    const length = range.end - range.start;
    elements.selectionStatus.textContent = `Using selection (${length})`;
    elements.selectionStatus.classList.add("active");
  } else {
    elements.selectionStatus.textContent = "Using full text";
    elements.selectionStatus.classList.remove("active");
  }
  updateContextPanel(range);
}

function updateContextPanel(range) {
  const editor = elements.editor;
  const text = editor.value;
  const start = range.hadSelection ? range.start : 0;
  const end = range.hadSelection ? range.end : text.length;
  const selectedText = text.slice(start, end);
  const before = range.hadSelection ? text.slice(Math.max(0, start - 240), start) : "";
  const after = range.hadSelection ? text.slice(end, Math.min(text.length, end + 240)) : "";

  elements.scopeLabel.textContent = range.hadSelection ? "Current selection" : "Full text";
  elements.rangeLabel.textContent = `${start}-${end}`;
  elements.selectedPreview.textContent = selectedText || "(empty)";
  elements.beforePreview.textContent = before || (range.hadSelection ? "(no before context)" : "(not used for full text)");
  elements.afterPreview.textContent = after || (range.hadSelection ? "(no after context)" : "(not used for full text)");
}
