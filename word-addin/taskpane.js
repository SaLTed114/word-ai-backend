(function () {
  const EVENT_KEY = "wordAiEvents";
  const shared = window.WordAIShared;

  const state = {
    officeReady: false,
    currentSessionId: null,
    lastEventIds: new Set(),
    sending: false,
    historyLoaded: false,
    lastApplied: null,
  };

  const elements = {
    healthStatus: document.getElementById("healthStatus"),
    scopeLabel: document.getElementById("scopeLabel"),
    selectedPreview: document.getElementById("selectedPreview"),
    sessionSelect: document.getElementById("sessionSelect"),
    openSessionButton: document.getElementById("openSessionButton"),
    newSessionButton: document.getElementById("newSessionButton"),
    refreshSessionsButton: document.getElementById("refreshSessionsButton"),
    chatLog: document.getElementById("chatLog"),
    agentInput: document.getElementById("agentInput"),
    agentButton: document.getElementById("agentButton"),
    loading: document.getElementById("loading"),
    errorBox: document.getElementById("errorBox"),
    historyTitle: document.getElementById("historyTitle"),
  };

  const channel = "BroadcastChannel" in window ? new BroadcastChannel("word-ai") : null;

  const copy = {
    en: {
      title: "Agent",
      connecting: "Connecting to Word...",
      connected: "Connected to Word",
      outsideWord: "Open this pane inside Microsoft Word.",
      history: "History",
      open: "Open",
      refresh: "Refresh",
      send: "Send",
      newSession: "New",
      selectionAuto: "Selection auto-detected",
      currentSelection: "Current selection",
      fullDocument: "Full document",
      selectHint: "(Select text in Word, then ask the agent.)",
      placeholder: "Ask about the selected text or document.",
      processing: "Processing...",
      backendReady: "Backend connected.",
      backendRetry: "Backend unavailable. Sending will retry the connection.",
      emptyHistory: "No saved sessions",
      enterMessage: "Enter an agent message.",
      applyResult: "Apply result",
      apply: "Apply",
      applyEquation: "Apply formula",
      details: "Details",
      appliedSelection: "replaced selection",
      autoApplied: "Auto-applied",
      undo: "Undo",
      undone: "Undone",
      review: "Review",
      reviewTitle: "Review changes",
      reviewBefore: "Before",
      reviewAfter: "After",
      reviewClose: "Close",
      nothingToUndo: "Nothing to undo.",
      openFailed: "Failed to open session",
      loadHistoryFailed: "Failed to load history",
    },
    "zh-CN": {
      title: "Agent",
      connecting: "正在连接 Word...",
      connected: "已连接到 Word",
      outsideWord: "请在 Microsoft Word 中打开此侧边栏。",
      history: "历史会话",
      open: "打开",
      refresh: "刷新",
      send: "发送",
      newSession: "新会话",
      selectionAuto: "已自动识别选区",
      currentSelection: "当前选区",
      fullDocument: "全文",
      selectHint: "（请先在 Word 中选中文字，再向助手提问。）",
      placeholder: "询问选中文本或整篇文档。",
      processing: "处理中...",
      backendReady: "后端已连接。",
      backendRetry: "后端暂不可用，发送时会再次尝试。",
      emptyHistory: "暂无历史会话",
      enterMessage: "请输入消息。",
      applyResult: "应用结果",
      apply: "应用",
      applyEquation: "应用公式",
      details: "详情",
      appliedSelection: "已替换选区",
      autoApplied: "已自动应用",
      undo: "撤销",
      undone: "已撤销",
      review: "审查",
      reviewTitle: "变更审查",
      reviewBefore: "替换前",
      reviewAfter: "替换后",
      reviewClose: "关闭",
      nothingToUndo: "没有可撤销的操作。",
      openFailed: "打开会话失败",
      loadHistoryFailed: "加载历史失败",
    },
  };

  function settings() {
    return shared.loadSettings();
  }

  function language() {
    return settings().language || "zh-CN";
  }

  function t(key) {
    return (copy[language()] && copy[language()][key]) || copy.en[key] || key;
  }

  function apiBase() {
    return (settings().apiBase || "http://127.0.0.1:8000").replace(/\/+$/, "");
  }

  function applySettings() {
    document.documentElement.lang = language();
    document.documentElement.style.setProperty("--font-size", `${settings().fontSize || 14}px`);
    elements.historyTitle.textContent = t("history");
    elements.openSessionButton.textContent = t("open");
    elements.newSessionButton.textContent = t("newSession");
    elements.refreshSessionsButton.textContent = t("refresh");
    elements.agentButton.textContent = t("send");
    elements.agentInput.placeholder = t("placeholder");
    if (!elements.selectedPreview.textContent.trim()) {
      elements.selectedPreview.textContent = t("selectHint");
    }

    var reviewUndoFromDialog = document.getElementById("reviewUndoFromDialog");
    var reviewCloseFooter = document.getElementById("reviewCloseFooter");
    if (reviewUndoFromDialog) reviewUndoFromDialog.textContent = t("undo");
    if (reviewCloseFooter) reviewCloseFooter.textContent = t("reviewClose");
  }

  function setBusy(isBusy) {
    state.sending = isBusy;
    elements.loading.hidden = !isBusy;
    elements.loading.textContent = t("processing");
    elements.agentButton.disabled = isBusy || !state.officeReady;
  }

  function showError(message) {
    elements.errorBox.hidden = !message;
    elements.errorBox.textContent = message || "";
  }

  function setHealthClass(name, title) {
    elements.healthStatus.className = `status-dot${name ? ` ${name}` : ""}`;
    elements.healthStatus.title = title || "";
  }

  async function requestJson(path, init) {
    const response = await fetch(`${apiBase()}${path}`, init);
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
    if (!response.ok) {
      const detail = typeof data === "string" ? data : data.detail || JSON.stringify(data, null, 2);
      throw new Error(detail);
    }
    return data;
  }

  async function getWordPayload() {
    if (!state.officeReady) {
      throw new Error(t("outsideWord"));
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

      return {
        text: hasSelection ? selectedText : bodyText,
        documentText: bodyText,
        selectionText: hasSelection ? selectedText : "",
        context: getContextWindow(bodyText, selectedText),
        source: hasSelection ? "selection" : "document",
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
      after: bodyText.slice(index + selectedText.length, index + selectedText.length + 500),
    };
  }

  async function refreshSelectionPreview() {
    if (!state.officeReady) {
      return;
    }
    try {
      const payload = await getWordPayload();
      const label = payload.source === "selection" ? t("currentSelection") : t("fullDocument");
      elements.scopeLabel.textContent = `${label} (${payload.text.length} chars)`;
      elements.selectedPreview.textContent = payload.text || "(empty)";
    } catch (error) {
      showError(error.message || String(error));
    }
  }

  function parseList(value) {
    return String(value || "")
      .split(/\r?\n|,/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  async function ensureSession() {
    if (state.currentSessionId) {
      return state.currentSessionId;
    }
    const session = await requestJson("/agent/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: null }),
    });
    state.currentSessionId = session.id;

    const currentSettings = settings();
    await requestJson(`/agent/sessions/${session.id}/memory`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_summary: currentSettings.documentSummary || null,
        writing_goals: parseList(currentSettings.writingGoals),
        key_terms: parseList(currentSettings.keyTerms),
        user_preferences: parseList(currentSettings.userPreferences),
      }),
    });

    await loadSessions();
    return session.id;
  }

  async function loadSessions() {
    try {
      const sessions = await requestJson("/agent/sessions");
      elements.sessionSelect.innerHTML = "";
      if (!sessions.length) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = t("emptyHistory");
        elements.sessionSelect.appendChild(option);
        elements.sessionSelect.disabled = true;
        return;
      }
      elements.sessionSelect.disabled = false;
      sessions.forEach((session) => {
        const option = document.createElement("option");
        option.value = session.id;
        option.textContent = session.title || session.id.slice(0, 8);
        if (session.id === state.currentSessionId) {
          option.selected = true;
        }
        elements.sessionSelect.appendChild(option);
      });
      state.historyLoaded = true;
    } catch (error) {
      elements.sessionSelect.innerHTML = "";
      const option = document.createElement("option");
      option.value = "";
      option.textContent = t("emptyHistory");
      elements.sessionSelect.appendChild(option);
      elements.sessionSelect.disabled = true;
      if (!state.historyLoaded) {
        showError(`${t("loadHistoryFailed")}: ${error.message || String(error)}`);
      }
    }
  }

  async function openSelectedSession() {
    const sessionId = elements.sessionSelect.value;
    if (!sessionId) {
      return;
    }
    try {
      const messages = await requestJson(`/agent/sessions/${sessionId}/messages`);
      state.currentSessionId = sessionId;
      elements.chatLog.innerHTML = "";
      messages.forEach(function (message) {
        if (message.response) {
          appendResult(message.role, message.response, { title: message.role === "assistant" ? t("title") : message.role, skipAutoApply: true });
        } else {
          appendChat(message.role, message.content);
        }
      });
      await loadSessions();
    } catch (error) {
      showError(`${t("openFailed")}: ${error.message || String(error)}`);
    }
  }

  async function runAgent() {
    const message = elements.agentInput.value.trim();
    if (!message) {
      showError(t("enterMessage"));
      return;
    }

    try {
      setBusy(true);
      showError("");
      setHealthClass("busy", t("processing"));

      const selection = await getWordPayload();
      const sessionId = await ensureSession();

      appendChat("user", message);
      elements.agentInput.value = "";
      await refreshSelectionPreview();

      const payload = { message };
      if ((selection.selectionText || "").trim() || (selection.documentText || "").trim()) {
        payload.document_context = {
          document_text: selection.documentText || null,
          active_scope: selection.selectionText.trim() ? "selection" : "document",
          selection: selection.selectionText.trim() ? { text: selection.selectionText } : null,
        };
      }

      const result = await requestJson(`/agent/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      await appendResult("assistant", result.response, {
        title: t("title"),
      });

      setHealthClass("ok", t("backendReady"));
      await refreshSelectionPreview();
      await loadSessions();
    } catch (error) {
      setHealthClass("error", error.message || String(error));
      showError(error.message || String(error));
    } finally {
      setBusy(false);
    }
  }

  async function appendResult(role, result, meta = {}) {
    const title = meta.title || role;
    const message = document.createElement("div");
    message.className = role === "user" ? "chat-message user-message" : "chat-message";

    const roleEl = document.createElement("strong");
    roleEl.textContent = title;
    message.appendChild(roleEl);

    if (result.reply) {
      const reply = document.createElement("pre");
      reply.textContent = result.reply;
      message.appendChild(reply);
    }

    if (result.final_text) {
      const finalText = document.createElement("pre");
      finalText.textContent = result.final_text;
      message.appendChild(finalText);
    }

    const formulaAction = getApplicableFormulaAction(result);
    const replacement = getApplicableText(result);
    const currentSettings = settings();
    const skipAutoApply = meta.skipAutoApply === true;

    if (formulaAction || replacement) {
      const actionsRow = document.createElement("div");
      actionsRow.className = "message-actions";

      var hasActionsRow = false;

      if (currentSettings.autoApply && !skipAutoApply) {
        try {
          var payload = await getWordPayload();
          var source = payload.source;
          var originalText = source === "selection"
            ? (payload.selectionText || payload.text)
            : payload.text;

          if (formulaAction) {
            await applyEquationAction(source, formulaAction);
          } else {
            await replaceCurrentText(source, replacement);
          }

          state.lastApplied = {
            source: source,
            originalText: originalText,
            replacementText: formulaAction
              ? (formulaAction.formula || formulaAction.replacement || "")
              : (replacement || ""),
            isFormula: !!formulaAction,
            _actionsRow: actionsRow,
          };

          await refreshSelectionPreview();

          if (currentSettings.showUndoReview !== false) {
            actionsRow.className = "auto-apply-row";
            hasActionsRow = true;

            var undoBtn = document.createElement("button");
            undoBtn.type = "button";
            undoBtn.className = "undo-button";
            undoBtn.textContent = t("undo");
            undoBtn.addEventListener("click", function () {
              undoLastApply(actionsRow);
            });
            actionsRow.appendChild(undoBtn);

            var reviewBtn = document.createElement("button");
            reviewBtn.type = "button";
            reviewBtn.className = "review-button";
            reviewBtn.textContent = t("review");
            reviewBtn.addEventListener("click", function () { openReview(actionsRow); });
            actionsRow.appendChild(reviewBtn);
          }
        } catch (error) {
          showError(error.message || String(error));
        }
      } else {
        hasActionsRow = true;
        var applyButton = document.createElement("button");
        applyButton.type = "button";
        applyButton.textContent = formulaAction
          ? t("applyEquation")
          : result.final_text
          ? t("applyResult")
          : t("apply");
        applyButton.addEventListener("click", async function () {
          try {
            var src = await currentReplaceSource();
            if (formulaAction) {
              await applyEquationAction(src, formulaAction);
            } else {
              await replaceCurrentText(src, replacement);
            }
            await refreshSelectionPreview();
          } catch (error) {
            showError(error.message || String(error));
          }
        });
        actionsRow.appendChild(applyButton);
      }

      if (hasActionsRow) {
        message.appendChild(actionsRow);
      }
    }

    if ((result.actions || []).length && currentSettings.showDetails !== false) {
      var details = document.createElement("details");
      details.className = "details-box";
      var summary = document.createElement("summary");
      summary.textContent = t("details") + " (" + result.actions.length + ")";
      details.appendChild(summary);

      var metaLines = result.actions.map(function (action, index) {
        var lines = [(index + 1) + ". " + (action.type || "action") + " (" + (action.risk_level || "info") + ")"];
        if (action.original) {
          lines.push("Original: " + action.original);
        }
        if (action.replacement) {
          lines.push("Replacement: " + action.replacement);
        }
        if (action.reason) {
          lines.push("Reason: " + action.reason);
        }
        return lines.join("\n");
      });

      var pre = document.createElement("pre");
      pre.textContent = metaLines.join("\n\n");
      details.appendChild(pre);
      message.appendChild(details);
    }

    elements.chatLog.appendChild(message);
    elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
  }

  function getApplicableText(result) {
    if (!result) {
      return null;
    }
    const replaceAction = (result.actions || []).find(
      (action) => action.type === "replace_selection" && action.replacement
    );
    return result.final_text || (replaceAction && replaceAction.replacement) || null;
  }

  function getApplicableFormulaAction(result) {
    if (!result) {
      return null;
    }
    return (result.actions || []).find((action) => {
      return (
        (action.type === "replace_selection_equation" || action.type === "insert_equation") &&
        (action.formula || action.replacement)
      );
    }) || null;
  }

  async function currentReplaceSource() {
    const payload = await getWordPayload();
    return payload.source;
  }

  async function applyEquationAction(source, action) {
    const formula = action.formula || action.replacement || "";
    const format = action.formula_format || "latex";
    const ooxml = format === "omml" ? formula : formulaToOoxml(formula);

    await Word.run(async (context) => {
      if (action.type === "insert_equation") {
        context.document.getSelection().insertOoxml(ooxml, Word.InsertLocation.after);
      } else if (source === "document") {
        context.document.body.insertOoxml(ooxml, Word.InsertLocation.replace);
      } else {
        context.document.getSelection().insertOoxml(ooxml, Word.InsertLocation.replace);
      }
      await context.sync();
    });
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

  async function undoLastApply(actionsRow) {
    if (!state.lastApplied) {
      showError(t("nothingToUndo"));
      return;
    }
    var applied = state.lastApplied;
    try {
      await Word.run(async function (context) {
        if (applied.source === "document") {
          context.document.body.insertText(applied.originalText, Word.InsertLocation.replace);
        } else {
          context.document.getSelection().insertText(applied.originalText, Word.InsertLocation.replace);
        }
        await context.sync();
      });
      state.lastApplied = null;
      var undoBtn = actionsRow.querySelector(".undo-button");
      if (undoBtn) undoBtn.disabled = true;
      await refreshSelectionPreview();
    } catch (error) {
      showError(error.message || String(error));
    }
  }

  function openReview(actionsRow) {
    if (!state.lastApplied) {
      showError(t("nothingToUndo"));
      return;
    }
    var dialog = document.getElementById("reviewDialog");
    document.getElementById("reviewBefore").textContent = state.lastApplied.originalText || "(empty)";
    document.getElementById("reviewAfter").textContent = state.lastApplied.replacementText || "(empty)";
    dialog._actionsRow = actionsRow || state.lastApplied._actionsRow || null;
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
  }

  function closeReview() {
    var dialog = document.getElementById("reviewDialog");
    if (typeof dialog.close === "function") {
      dialog.close();
    } else {
      dialog.removeAttribute("open");
    }
  }

  function undoFromReview() {
    var dialog = document.getElementById("reviewDialog");
    var actionsRow = dialog._actionsRow;
    closeReview();
    if (actionsRow) {
      undoLastApply(actionsRow);
    }
  }

  function formulaToOoxml(formula) {
    const math = parseLatexFormula(formula);
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<pkg:package xmlns:pkg="http://schemas.microsoft.com/office/2006/xmlPackage">
  <pkg:part pkg:name="/_rels/.rels" pkg:contentType="application/vnd.openxmlformats-package.relationships+xml">
    <pkg:xmlData>
      <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
        <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
      </Relationships>
    </pkg:xmlData>
  </pkg:part>
  <pkg:part pkg:name="/word/document.xml" pkg:contentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml">
    <pkg:xmlData>
      <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
        <w:body>
          <w:p>
            <m:oMathPara>
              <m:oMath>${math}</m:oMath>
            </m:oMathPara>
          </w:p>
        </w:body>
      </w:document>
    </pkg:xmlData>
  </pkg:part>
</pkg:package>`;
  }

  function parseLatexFormula(source) {
    const parser = new FormulaParser(cleanFormulaSource(source));
    return parser.parseGroup();
  }

  function cleanFormulaSource(source) {
    return String(source || "")
      .trim()
      .replace(/^\$\$?/, "")
      .replace(/\$\$?$/, "")
      .replace(/^\\\(/, "")
      .replace(/\\\)$/, "")
      .trim();
  }

  function escapeXml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
  }

  function mathRun(text) {
    return `<m:r><m:t>${escapeXml(text)}</m:t></m:r>`;
  }

  class FormulaParser {
    constructor(source) {
      this.source = source;
      this.index = 0;
    }

    parseGroup(stopChar) {
      const nodes = [];
      while (this.index < this.source.length) {
        const char = this.source[this.index];
        if (stopChar && char === stopChar) {
          this.index += 1;
          break;
        }
        if (char === "}") {
          break;
        }
        nodes.push(this.parseAtom());
      }
      return nodes.join("");
    }

    parseAtom() {
      this.skipSpaces();
      let base = this.parseBase();
      this.skipSpaces();

      let sub = null;
      let sup = null;
      while (this.peek() === "_" || this.peek() === "^") {
        const marker = this.source[this.index++];
        const script = this.parseScript();
        if (marker === "_") {
          sub = script;
        } else {
          sup = script;
        }
        this.skipSpaces();
      }

      if (sub && sup) {
        return `<m:sSubSup><m:e>${base}</m:e><m:sub>${sub}</m:sub><m:sup>${sup}</m:sup></m:sSubSup>`;
      }
      if (sub) {
        return `<m:sSub><m:e>${base}</m:e><m:sub>${sub}</m:sub></m:sSub>`;
      }
      if (sup) {
        return `<m:sSup><m:e>${base}</m:e><m:sup>${sup}</m:sup></m:sSup>`;
      }
      return base;
    }

    parseBase() {
      const char = this.peek();
      if (!char) {
        return "";
      }
      if (char === "{") {
        this.index += 1;
        return this.parseGroup("}");
      }
      if (char === "\\") {
        return this.parseCommand();
      }
      this.index += 1;
      return mathRun(char);
    }

    parseCommand() {
      this.index += 1;
      const name = this.readCommandName();
      if (name === "frac") {
        const numerator = this.parseRequiredGroup();
        const denominator = this.parseRequiredGroup();
        return `<m:f><m:num>${numerator}</m:num><m:den>${denominator}</m:den></m:f>`;
      }
      if (name === "sqrt") {
        const value = this.parseRequiredGroup();
        return `<m:rad><m:radPr><m:degHide m:val="on"/></m:radPr><m:deg/><m:e>${value}</m:e></m:rad>`;
      }
      if (name === "left" || name === "right") {
        this.skipSpaces();
        const delimiter = this.source[this.index++] || "";
        return delimiter === "." ? "" : mathRun(delimiter);
      }
      if (name === "cdot") {
        return mathRun("·");
      }
      if (name === "times") {
        return mathRun("×");
      }
      if (name === "leq") {
        return mathRun("≤");
      }
      if (name === "geq") {
        return mathRun("≥");
      }
      if (name === "neq") {
        return mathRun("≠");
      }
      if (GREEK_LETTERS[name]) {
        return mathRun(GREEK_LETTERS[name]);
      }
      return mathRun(`\\${name}`);
    }

    parseScript() {
      this.skipSpaces();
      if (this.peek() === "{") {
        this.index += 1;
        return this.parseGroup("}");
      }
      return this.parseBase();
    }

    parseRequiredGroup() {
      this.skipSpaces();
      if (this.peek() !== "{") {
        return this.parseBase();
      }
      this.index += 1;
      return this.parseGroup("}");
    }

    readCommandName() {
      const start = this.index;
      while (/[A-Za-z]/.test(this.source[this.index] || "")) {
        this.index += 1;
      }
      if (start === this.index) {
        return this.source[this.index++] || "";
      }
      return this.source.slice(start, this.index);
    }

    skipSpaces() {
      while (/\s/.test(this.source[this.index] || "")) {
        this.index += 1;
      }
    }

    peek() {
      return this.source[this.index];
    }
  }

  const GREEK_LETTERS = {
    alpha: "α",
    beta: "β",
    gamma: "γ",
    delta: "δ",
    epsilon: "ε",
    theta: "θ",
    lambda: "λ",
    mu: "μ",
    pi: "π",
    rho: "ρ",
    sigma: "σ",
    tau: "τ",
    phi: "φ",
    omega: "ω",
    Delta: "Δ",
    Theta: "Θ",
    Lambda: "Λ",
    Pi: "Π",
    Sigma: "Σ",
    Phi: "Φ",
    Omega: "Ω",
  };

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
    state.currentSessionId = null;
    state.lastEventIds.clear();
    elements.chatLog.innerHTML = "";
    localStorage.removeItem(EVENT_KEY);
  }

  async function checkHealth() {
    setHealthClass("", "Backend status");
    try {
      const response = await fetch(`${apiBase()}/health`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      setHealthClass("ok", t("backendReady"));
    } catch (error) {
      setHealthClass("error", error.message || String(error));
      showError(`Health check failed: ${error.message || String(error)}`);
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

  async function renderCommandEvent(event) {
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
    await appendResult("assistant", event.result || {}, { title: event.title || "Ribbon command", skipAutoApply: true });
  }

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
    if (event.key === shared.STORAGE_KEY) {
      applySettings();
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      applySettings();
      refreshSelectionPreview();
      hydrateCommandEvents();
      loadSessions();
      checkHealth();
    }
  });

  function bindEvents() {
    elements.agentButton.addEventListener("click", runAgent);
    elements.refreshSessionsButton.addEventListener("click", loadSessions);
    elements.openSessionButton.addEventListener("click", openSelectedSession);
    elements.newSessionButton.addEventListener("click", () => {
      state.currentSessionId = null;
      elements.chatLog.innerHTML = "";
      loadSessions();
    });
    elements.agentInput.addEventListener("focus", refreshSelectionPreview);
    elements.agentInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        runAgent();
      }
    });

    var reviewCloseBtn = document.getElementById("reviewCloseBtn");
    var reviewCloseFooter = document.getElementById("reviewCloseFooter");
    var reviewUndoFromDialog = document.getElementById("reviewUndoFromDialog");
    if (reviewCloseBtn) reviewCloseBtn.addEventListener("click", closeReview);
    if (reviewCloseFooter) reviewCloseFooter.addEventListener("click", closeReview);
    if (reviewUndoFromDialog) reviewUndoFromDialog.addEventListener("click", undoFromReview);
  }

  function initializeOffice() {
    Office.onReady((info) => {
      state.officeReady = info.host === Office.HostType.Word;
      setBusy(false);
      refreshSelectionPreview();
      hydrateCommandEvents();
      loadSessions();
      checkHealth();
    });
  }

  function initializeWebFallback() {
    state.officeReady = true;
    setBusy(false);
    elements.scopeLabel.textContent = t("selectionAuto");
    elements.selectedPreview.textContent = t("selectHint");
    loadSessions();
    checkHealth();
  }

  applySettings();
  bindEvents();

  if (typeof Office !== "undefined" && Office.onReady) {
    initializeOffice();
  } else {
    initializeWebFallback();
  }
})();
