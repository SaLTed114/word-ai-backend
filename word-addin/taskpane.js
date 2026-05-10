const EVENT_KEY = "wordAiEvents";

const state = {
  agentHistory: [],
  officeReady: false,
  lastEventIds: new Set()
};

const elements = {
  hostStatus: document.getElementById("hostStatus"),
  healthStatus: document.getElementById("healthStatus"),
  scopeLabel: document.getElementById("scopeLabel"),
  selectedPreview: document.getElementById("selectedPreview"),
  chatLog: document.getElementById("chatLog"),
  agentInput: document.getElementById("agentInput"),
  agentButton: document.getElementById("agentButton"),
  resetAgentButton: document.getElementById("resetAgentButton"),
  loading: document.getElementById("loading"),
  errorBox: document.getElementById("errorBox")
};

const channel = "BroadcastChannel" in window ? new BroadcastChannel("word-ai") : null;

Office.onReady((info) => {
  state.officeReady = info.host === Office.HostType.Word;
  elements.hostStatus.textContent = state.officeReady
    ? "Connected to Word"
    : "Open this pane inside Microsoft Word.";
  setBusy(false);
  refreshSelectionPreview();
  hydrateCommandEvents();
  checkHealth();
});

if (channel) {
  channel.addEventListener("message", (event) => {
    if (event.data && event.data.type === "word-ai-event") {
      renderCommandEvent(event.data.payload);
    }
  });
}

window.addEventListener("storage", (event) => {
  if (event.key === EVENT_KEY) {
    hydrateCommandEvents();
  }
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) {
    refreshSelectionPreview();
    hydrateCommandEvents();
  }
});

function setBusy(isBusy) {
  elements.loading.hidden = !isBusy;
  elements.agentButton.disabled = isBusy || !state.officeReady;
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

    return {
      text,
      context: getContextWindow(bodyText, selectedText),
      source: hasSelection ? "selection" : "document"
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

async function refreshSelectionPreview() {
  if (!state.officeReady) {
    return;
  }

  try {
    const payload = await getWordPayload();
    const label = payload.source === "selection" ? "Current selection" : "Full document";
    elements.scopeLabel.textContent = `${label} (${payload.text.length} chars)`;
    elements.selectedPreview.textContent = payload.text || "(empty)";
  } catch (error) {
    showError(error.message || String(error));
  }
}

async function requestJson(path, payload) {
  setBusy(true);
  showError("");
  try {
    const response = await fetch(`http://127.0.0.1:8000${path}`, {
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
      selection: selection.text.trim()
        ? {
            text: selection.text,
            context: selection.context,
            instruction: null
          }
        : null,
      history: state.agentHistory
    };

    appendChat("user", message);
    elements.agentInput.value = "";
    await refreshSelectionPreview();

    const result = await requestJson("/agent/chat", payload);
    const replacement = getApplicableText(result);
    if (replacement) {
      await replaceCurrentText(selection.source, replacement);
    }
    appendResult("assistant", result, {
      title: "Agent",
      replaced: Boolean(replacement)
    });
    if (replacement) {
      await refreshSelectionPreview();
    }
    state.agentHistory.push({ role: "user", content: message });
    state.agentHistory.push({ role: "assistant", content: result.reply });
  } catch (error) {
    showError(error.message || String(error));
  }
}

function hydrateCommandEvents() {
  const events = readStoredEvents();
  events.forEach(renderCommandEvent);
}

function readStoredEvents() {
  try {
    const events = JSON.parse(localStorage.getItem(EVENT_KEY) || "[]");
    return Array.isArray(events) ? events : [];
  } catch {
    return [];
  }
}

function renderCommandEvent(event) {
  if (!event || state.lastEventIds.has(event.id)) {
    return;
  }
  state.lastEventIds.add(event.id);

  if (event.status === "error") {
    appendChat("system", `${event.title || "Command"} failed: ${event.message}`);
    return;
  }

  if (event.status === "started") {
    appendChat("system", event.message || `${event.title || "Command"} started.`);
    return;
  }

  appendResult("assistant", event.result, {
    title: event.title || "Ribbon command",
    replaced: event.replaced
  });
}

function appendResult(role, result, meta = {}) {
  const title = meta.title ? `${meta.title}${meta.replaced ? " - replaced selection" : ""}` : role;
  const parts = [];
  if (result.reply) {
    parts.push(result.reply);
  }
  if (result.final_text) {
    parts.push(`Result:\n${result.final_text}`);
  }
  (result.actions || []).forEach((action, index) => {
    const lines = [`${index + 1}. ${action.type || "action"} (${action.severity || "info"})`];
    if (action.original) {
      lines.push(`Original: ${action.original}`);
    }
    if (action.replacement) {
      lines.push(`Replacement: ${action.replacement}`);
    }
    if (action.reason) {
      lines.push(`Reason: ${action.reason}`);
    }
    parts.push(lines.join("\n"));
  });
  appendChat(title, parts.join("\n\n") || "(empty result)");
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

async function replaceCurrentText(source, text) {
  await Word.run(async (context) => {
    if (source === "document") {
      context.document.body.insertText(text, Word.InsertLocation.replace);
    } else {
      context.document.getSelection().insertText(text, Word.InsertLocation.replace);
    }
    await context.sync();
  });
}

function appendChat(role, content) {
  const message = document.createElement("div");
  message.className = role === "user" ? "chat-message user-message" : "chat-message";

  const roleEl = document.createElement("strong");
  roleEl.textContent = role;
  const contentEl = document.createElement("pre");
  contentEl.textContent = content;

  message.appendChild(roleEl);
  message.appendChild(contentEl);
  elements.chatLog.appendChild(message);
  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
}

function resetAgent() {
  state.agentHistory = [];
  state.lastEventIds.clear();
  elements.chatLog.innerHTML = "";
  localStorage.removeItem(EVENT_KEY);
}

async function checkHealth() {
  elements.healthStatus.className = "status-dot";
  try {
    const response = await fetch("http://127.0.0.1:8000/health");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    elements.healthStatus.className = "status-dot ok";
  } catch (error) {
    elements.healthStatus.className = "status-dot error";
    showError(`Health check failed: ${error.message || String(error)}`);
  }
}

elements.agentButton.addEventListener("click", runAgent);
elements.resetAgentButton.addEventListener("click", resetAgent);
elements.agentInput.addEventListener("focus", refreshSelectionPreview);
elements.agentInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    runAgent();
  }
});
