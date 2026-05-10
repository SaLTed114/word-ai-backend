const API_BASE = "http://127.0.0.1:8000";
const EVENT_KEY = "wordAiEvents";

Office.onReady(() => {
  Office.actions.associate("runSyntax", runSyntax);
  Office.actions.associate("runWordChoice", runWordChoice);
  Office.actions.associate("runRewrite", runRewrite);
  Office.actions.associate("openSettings", openSettings);
});

async function runSyntax(event) {
  await runRibbonTask(event, {
    title: "Syntax",
    path: "/tasks/syntax"
  });
}

async function runWordChoice(event) {
  await runRibbonTask(event, {
    title: "Word Choice",
    path: "/tasks/word-choice"
  });
}

async function runRewrite(event) {
  await runRibbonTask(event, {
    title: "Rewrite",
    path: "/tasks/style",
    extra: { style: "academic" }
  });
}

function openSettings(event) {
  Office.context.ui.displayDialogAsync(
    "https://localhost:3443/settings.html",
    {
      height: 42,
      width: 38,
      displayInIframe: true
    },
    (asyncResult) => {
      if (asyncResult.status !== Office.AsyncResultStatus.Succeeded) {
        publishEvent({
          id: createId(),
          status: "error",
          title: "Settings",
          message: asyncResult.error.message
        });
      }
      event.completed();
    }
  );
}

async function runRibbonTask(event, task) {
  try {
    const payload = await getWordPayload();
    if (!payload.text.trim()) {
      throw new Error("Select text or add text to the document first.");
    }

    publishEvent({
      id: createId(),
      status: "started",
      title: task.title,
      message: `Running ${task.title}...`
    });

    const result = await requestJson(task.path, {
      text: payload.text,
      context: payload.context,
      instruction: null,
      ...(task.extra || {})
    });

    const replacement = getApplicableText(result);
    if (replacement) {
      await replaceCurrentText(payload.source, replacement);
    }

    publishEvent({
      id: createId(),
      status: "ok",
      title: task.title,
      result,
      replaced: Boolean(replacement)
    });
  } catch (error) {
    publishEvent({
      id: createId(),
      status: "error",
      title: task.title,
      message: error.message || String(error)
    });
  } finally {
    event.completed();
  }
}

async function getWordPayload() {
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
      source: hasSelection ? "selection" : "document",
      context: getContextWindow(bodyText, selectedText)
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

async function requestJson(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
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
}

function getApplicableText(result) {
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

function publishEvent(event) {
  const events = readEvents();
  events.push({ ...event, createdAt: Date.now() });
  const recentEvents = events.slice(-30);
  localStorage.setItem(EVENT_KEY, JSON.stringify(recentEvents));

  if ("BroadcastChannel" in window) {
    const channel = new BroadcastChannel("word-ai");
    channel.postMessage({
      type: "word-ai-event",
      payload: recentEvents[recentEvents.length - 1]
    });
    channel.close();
  }
}

function readEvents() {
  try {
    const events = JSON.parse(localStorage.getItem(EVENT_KEY) || "[]");
    return Array.isArray(events) ? events : [];
  } catch {
    return [];
  }
}

function createId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
