const state = {
  sessionId: null,
  editorSelection: { start: 0, end: 0, hadSelection: false },
  lastApplyTarget: null,
  undoStack: []
};

const elements = {
  apiBase: document.getElementById("apiBase"),
  healthButton: document.getElementById("healthButton"),
  healthStatus: document.getElementById("healthStatus"),
  sessionBadge: document.getElementById("sessionBadge"),
  fileInput: document.getElementById("fileInput"),
  openButton: document.getElementById("openButton"),
  saveButton: document.getElementById("saveButton"),
  clearButton: document.getElementById("clearButton"),
  documentTitle: document.getElementById("documentTitle"),
  activeScope: document.getElementById("activeScope"),
  editor: document.getElementById("editor"),
  selectionStatus: document.getElementById("selectionStatus"),
  editorStats: document.getElementById("editorStats"),
  documentSummary: document.getElementById("documentSummary"),
  writingGoals: document.getElementById("writingGoals"),
  keyTerms: document.getElementById("keyTerms"),
  userPreferences: document.getElementById("userPreferences"),
  saveMemoryButton: document.getElementById("saveMemoryButton"),
  loadMemoryButton: document.getElementById("loadMemoryButton"),
  chatLog: document.getElementById("chatLog"),
  errorBox: document.getElementById("errorBox"),
  loading: document.getElementById("loading"),
  agentInput: document.getElementById("agentInput"),
  newSessionButton: document.getElementById("newSessionButton"),
  undoApplyButton: document.getElementById("undoApplyButton"),
  sendButton: document.getElementById("sendButton")
};

function apiUrl(path) {
  return `${elements.apiBase.value.replace(/\/$/, "")}${path}`;
}

function setBusy(isBusy) {
  elements.loading.hidden = !isBusy;
  [
    elements.healthButton,
    elements.saveMemoryButton,
    elements.loadMemoryButton,
    elements.newSessionButton,
    elements.undoApplyButton,
    elements.sendButton
  ].forEach((button) => {
    button.disabled = isBusy || (button === elements.undoApplyButton && state.undoStack.length === 0);
  });
}

function showError(message) {
  elements.errorBox.hidden = !message;
  elements.errorBox.textContent = message || "";
}

async function requestJson(method, path, payload = null) {
  const options = { method, headers: {} };
  if (payload !== null) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(payload);
  }

  const response = await fetch(apiUrl(path), options);
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || JSON.stringify(data, null, 2));
  }
  return data;
}

async function ensureSession() {
  if (state.sessionId) {
    return state.sessionId;
  }
  const title = elements.documentTitle.value.trim() || "agent-demo";
  const session = await requestJson("POST", "/agent/sessions", { title });
  state.sessionId = session.id;
  updateSessionBadge();
  appendSystemMessage(`Session created: ${session.id}`);
  await saveMemory();
  return state.sessionId;
}

async function newSession() {
  state.sessionId = null;
  elements.chatLog.innerHTML = "";
  updateSessionBadge();
  await ensureSession();
}

function updateSessionBadge() {
  elements.sessionBadge.textContent = state.sessionId
    ? `Session ${state.sessionId.slice(0, 8)}`
    : "No session";
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
  const start = elements.editor.selectionStart;
  const end = elements.editor.selectionEnd;
  state.editorSelection = { start, end, hadSelection: end > start };
  updateSelectionStatus();
}

function getDocumentContext() {
  const text = elements.editor.value;
  const range = getActiveEditorRange();
  const activeScope = elements.activeScope.value;
  const hasSelection = range.hadSelection;
  const selectedText = hasSelection ? text.slice(range.start, range.end) : null;

  state.lastApplyTarget = {
    start: hasSelection ? range.start : 0,
    end: hasSelection ? range.end : text.length
  };

  return {
    title: elements.documentTitle.value.trim() || null,
    document_text: text,
    selection: hasSelection
      ? {
          text: selectedText,
          start: range.start,
          end: range.end
        }
      : null,
    active_scope: activeScope,
    context_window_chars: 1200
  };
}

async function sendAgentMessage() {
  const message = elements.agentInput.value.trim();
  if (!message) {
    return;
  }
  if (!elements.editor.value.trim()) {
    showError("Document text is empty.");
    return;
  }

  setBusy(true);
  showError("");
  appendChatMessage("user", message);
  elements.agentInput.value = "";

  try {
    const sessionId = await ensureSession();
    const result = await requestJson(
      "POST",
      `/agent/sessions/${sessionId}/messages`,
      {
        message,
        document_context: getDocumentContext()
      }
    );
    appendAgentResponse(result.response);
  } catch (error) {
    showError(error.message || String(error));
  } finally {
    setBusy(false);
  }
}

function readMemoryForm() {
  return {
    document_summary: elements.documentSummary.value.trim() || null,
    writing_goals: readLines(elements.writingGoals.value),
    key_terms: readLines(elements.keyTerms.value),
    user_preferences: readLines(elements.userPreferences.value)
  };
}

function fillMemoryForm(memory) {
  elements.documentSummary.value = memory.document_summary || "";
  elements.writingGoals.value = (memory.writing_goals || []).join("\n");
  elements.keyTerms.value = (memory.key_terms || []).join("\n");
  elements.userPreferences.value = (memory.user_preferences || []).join("\n");
}

async function saveMemory() {
  if (!state.sessionId) {
    return;
  }
  const memory = await requestJson(
    "PUT",
    `/agent/sessions/${state.sessionId}/memory`,
    readMemoryForm()
  );
  fillMemoryForm(memory);
}

async function loadMemory() {
  if (!state.sessionId) {
    return;
  }
  const memory = await requestJson("GET", `/agent/sessions/${state.sessionId}/memory`);
  fillMemoryForm(memory);
}

function appendAgentResponse(response) {
  const wrapper = document.createElement("article");
  wrapper.className = "chat-message assistant";

  const reply = document.createElement("div");
  reply.className = "message-text";
  reply.textContent = response.reply || "";
  wrapper.appendChild(reply);

  if (response.final_text) {
    const finalText = document.createElement("pre");
    finalText.className = "final-text";
    finalText.textContent = response.final_text;
    wrapper.appendChild(finalText);
  }

  const actions = response.actions || [];
  actions.forEach((action) => {
    wrapper.appendChild(renderAction(action, response.final_text));
  });

  elements.chatLog.appendChild(wrapper);
  scrollChatToBottom();
}

function renderAction(action, fallbackText) {
  const item = document.createElement("div");
  item.className = "action-item";

  const title = document.createElement("div");
  title.className = "action-title";
  title.textContent = `${action.type || "action"} · ${action.risk_level || "info"}`;
  item.appendChild(title);

  if (action.reason) {
    const reason = document.createElement("p");
    reason.textContent = action.reason;
    item.appendChild(reason);
  }

  const replacement = action.replacement || fallbackText;
  if (replacement && action.type === "replace_selection") {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Apply";
    button.addEventListener("click", () => applyReplacement(replacement));
    item.appendChild(button);
  }

  return item;
}

function appendChatMessage(role, content) {
  const message = document.createElement("article");
  message.className = `chat-message ${role}`;
  const text = document.createElement("div");
  text.className = "message-text";
  text.textContent = content;
  message.appendChild(text);
  elements.chatLog.appendChild(message);
  scrollChatToBottom();
}

function appendSystemMessage(content) {
  const message = document.createElement("div");
  message.className = "system-message";
  message.textContent = content;
  elements.chatLog.appendChild(message);
  scrollChatToBottom();
}

function applyReplacement(replacement) {
  const target = state.lastApplyTarget;
  if (!target) {
    return;
  }
  const editor = elements.editor;
  state.undoStack.push({
    value: editor.value,
    selection: {
      start: editor.selectionStart,
      end: editor.selectionEnd,
      hadSelection: editor.selectionEnd > editor.selectionStart
    },
    cachedSelection: { ...state.editorSelection },
    lastApplyTarget: state.lastApplyTarget ? { ...state.lastApplyTarget } : null
  });
  editor.value =
    editor.value.slice(0, target.start) +
    replacement +
    editor.value.slice(target.end);
  const end = target.start + replacement.length;
  editor.focus();
  editor.setSelectionRange(target.start, end);
  state.editorSelection = { start: target.start, end, hadSelection: true };
  updateStats();
  updateSelectionStatus();
  updateUndoButton();
}

function undoApply() {
  const previous = state.undoStack.pop();
  if (!previous) {
    updateUndoButton();
    return;
  }
  const editor = elements.editor;
  editor.value = previous.value;
  state.editorSelection = previous.cachedSelection;
  state.lastApplyTarget = previous.lastApplyTarget;
  editor.focus();
  editor.setSelectionRange(previous.selection.start, previous.selection.end);
  updateStats();
  updateSelectionStatus();
  updateUndoButton();
}

function updateUndoButton() {
  elements.undoApplyButton.disabled = state.undoStack.length === 0;
}

function scrollChatToBottom() {
  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
}

function readLines(value) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

async function checkHealth() {
  elements.healthStatus.className = "status-dot";
  showError("");
  try {
    const health = await requestJson("GET", "/health");
    elements.healthStatus.className = health.ai_configured
      ? "status-dot ok"
      : "status-dot warn";
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
    state.editorSelection = { start: 0, end: 0, hadSelection: false };
    updateStats();
    updateSelectionStatus();
  };
  reader.readAsText(file);
}

function saveTxtFile() {
  const blob = new Blob([elements.editor.value], { type: "text/plain;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "word-ai-agent-demo.txt";
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

function updateSelectionStatus() {
  const range = getActiveEditorRange();
  if (range.hadSelection) {
    const selectedText = elements.editor.value.slice(range.start, range.end);
    elements.selectionStatus.textContent = formatReferenceLabel(selectedText);
    elements.selectionStatus.title = selectedText;
    elements.selectionStatus.classList.add("active");
  } else {
    elements.selectionStatus.textContent = "full";
    elements.selectionStatus.title = "full document";
    elements.selectionStatus.classList.remove("active");
  }
}

function formatReferenceLabel(text) {
  const compact = text.replace(/\s+/g, " ").trim();
  if (!compact) {
    return "full";
  }
  const maxLength = 56;
  if (compact.length <= maxLength) {
    return compact;
  }
  const edgeLength = 24;
  return `${compact.slice(0, edgeLength)} ... ${compact.slice(-edgeLength)}`;
}

elements.healthButton.addEventListener("click", checkHealth);
elements.openButton.addEventListener("click", () => elements.fileInput.click());
elements.fileInput.addEventListener("change", () => openTxtFile(elements.fileInput.files[0]));
elements.saveButton.addEventListener("click", saveTxtFile);
elements.clearButton.addEventListener("click", () => {
  elements.editor.value = "";
  state.undoStack = [];
  state.editorSelection = { start: 0, end: 0, hadSelection: false };
  updateStats();
  updateSelectionStatus();
  updateUndoButton();
});
elements.saveMemoryButton.addEventListener("click", async () => {
  try {
    await ensureSession();
    await saveMemory();
    appendSystemMessage("Memory saved.");
  } catch (error) {
    showError(error.message || String(error));
  }
});
elements.loadMemoryButton.addEventListener("click", async () => {
  try {
    await loadMemory();
    appendSystemMessage("Memory loaded.");
  } catch (error) {
    showError(error.message || String(error));
  }
});
elements.newSessionButton.addEventListener("click", async () => {
  try {
    await newSession();
  } catch (error) {
    showError(error.message || String(error));
  }
});
elements.undoApplyButton.addEventListener("click", undoApply);
elements.sendButton.addEventListener("click", sendAgentMessage);
elements.agentInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendAgentMessage();
  }
});
elements.editor.addEventListener("input", () => {
  updateStats();
  updateSelectionStatus();
});
["select", "keyup", "mouseup", "touchend"].forEach((eventName) => {
  elements.editor.addEventListener(eventName, rememberEditorSelection);
});

[
  elements.sendButton,
  elements.saveMemoryButton,
  elements.loadMemoryButton,
  elements.newSessionButton,
  elements.undoApplyButton
].forEach((button) => {
  button.addEventListener("mousedown", (event) => {
    if (document.activeElement === elements.editor) {
      event.preventDefault();
    }
  });
});

elements.editor.value =
  "Title: Draft Methods Section\n\n" +
  "The proposed pipeline aims to support student writing in biomedical engineering reports.\n\n" +
  "This method is good and useful. It can help users revise grammar and style, but the current wording is too vague for an academic methods section.\n\n" +
  "In future work, the system should preserve domain terms and avoid changing the scientific meaning.";
elements.documentSummary.value =
  "A draft methods section for a biomedical engineering report writing assistant.";
elements.writingGoals.value =
  "Use concise academic English.\nPreserve scientific meaning.\nAvoid vague evaluative wording.";
elements.keyTerms.value =
  "biomedical engineering report\nacademic methods section\nwriting assistant";
elements.userPreferences.value =
  "Explain issues in Chinese.\nProvide rewrites in English.";
updateStats();
updateSelectionStatus();
updateUndoButton();
checkHealth();
