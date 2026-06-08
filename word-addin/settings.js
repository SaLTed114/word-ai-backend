(function () {
  const shared = window.WordAIShared;
  const PRESETS = {
    custom: {},
    openai: {
      base_url: "https://api.openai.com/v1",
      api_endpoint: "https://genaiapi.shanghaitech.edu.cn/api/v1/start",
      model: "GPT-5.4",
      use_json_mode: true,
      trust_env: false,
    },
    deepseek: {
      base_url: "https://api.deepseek.com",
      api_endpoint: "",
      model: "deepseek-chat",
      use_json_mode: true,
      trust_env: false,
    },
    qwen: {
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
      api_endpoint: "https://genaiapi.shanghaitech.edu.cn/api/v1/start",
      model: "qwen-instruct",
      use_json_mode: true,
      trust_env: false,
    },
  };

  const elements = {
    statusPill: document.getElementById("statusPill"),
    message: document.getElementById("message"),
    language: document.getElementById("language"),
    fontSize: document.getElementById("fontSize"),
    historyContextChars: document.getElementById("historyContextChars"),
    apiBase: document.getElementById("apiBase"),
    documentSummary: document.getElementById("documentSummary"),
    writingGoals: document.getElementById("writingGoals"),
    keyTerms: document.getElementById("keyTerms"),
    userPreferences: document.getElementById("userPreferences"),
    providerPreset: document.getElementById("providerPreset"),
    presetHint: document.getElementById("presetHint"),
    openaiApiKey: document.getElementById("openaiApiKey"),
    openaiModel: document.getElementById("openaiModel"),
    openaiBaseUrl: document.getElementById("openaiBaseUrl"),
    openaiApiEndpoint: document.getElementById("openaiApiEndpoint"),
    openaiProxyUrl: document.getElementById("openaiProxyUrl"),
    autoApply: document.getElementById("autoApply"),
    showDetails: document.getElementById("showDetails"),
    showUndoReview: document.getElementById("showUndoReview"),
    showSubagentStatus: document.getElementById("showSubagentStatus"),
    autoSubagents: document.getElementById("autoSubagents"),
    subagentExecutionMode: document.getElementById("subagentExecutionMode"),
    openaiTrustEnv: document.getElementById("openaiTrustEnv"),
    openaiUseJsonMode: document.getElementById("openaiUseJsonMode"),
    saveButton: document.getElementById("saveButton"),
    checkButton: document.getElementById("checkButton"),
  };

  const copy = {
    en: {
      settingsTitle: "Settings",
      settingsSubtitle: "Adjust the interface, memory, and model configuration.",
      statusIdle: "Unsaved",
      statusSaving: "Saving",
      statusSaved: "Saved",
      statusWarning: "Check settings",
      languageLabel: "Language",
      fontSizeLabel: "Agent font size",
      historyContextLabel: "History context chars",
      apiBaseLabel: "Backend API",
      behaviorTitle: "Interface behavior",
      autoApplyLabel: "Auto-apply edits",
      showDetailsLabel: "Show action details",
      showUndoReviewLabel: "Show undo/review buttons",
      showSubagentStatusLabel: "Use and show subagent status",
      subagentsTitle: "Subagents",
      subagentsHint: "Let the agent decide whether to call dynamic subagents and which skills each subagent should use.",
      autoSubagentsLabel: "Let agent choose subagents automatically",
      subagentExecutionModeLabel: "Execution mode",
      subagentModePipeline: "Pipeline",
      subagentModeParallel: "Parallel",
      memoryTitle: "Memory",
      documentSummaryLabel: "Document summary",
      writingGoalsLabel: "Writing goals",
      keyTermsLabel: "Key terms",
      userPreferencesLabel: "User preferences",
      aiConfigTitle: "Model configuration",
      providerPresetLabel: "API preset",
      providerPresetCustom: "Custom",
      providerPresetOpenAI: "OpenAI",
      providerPresetDeepSeek: "DeepSeek",
      providerPresetQwen: "Qwen",
      providerPresetHint: "Choosing a preset fills in a recommended base URL. You can still edit every field manually.",
      saveButton: "Save settings",
      checkButton: "Check connection",
      saveInProgress: "Saving settings...",
      saveSuccess: "Settings saved.",
      saveFailure: "Settings were not fully saved.",
      checkSuccess: "Backend connection looks good.",
      checkFailure: "Backend connection failed.",
      loadFailure: "Could not load backend model settings.",
    },
    "zh-CN": {
      settingsTitle: "设置",
      settingsSubtitle: "调整界面、记忆与模型配置。",
      statusIdle: "未保存",
      statusSaving: "保存中",
      statusSaved: "已保存",
      statusWarning: "请检查设置",
      languageLabel: "界面语言",
      fontSizeLabel: "Agent 字体大小",
      historyContextLabel: "History 上下文字符数",
      apiBaseLabel: "后端 API",
      behaviorTitle: "界面行为",
      autoApplyLabel: "自动应用编辑",
      showDetailsLabel: "显示操作详情",
      showUndoReviewLabel: "显示撤销/审查按钮",
      memoryTitle: "记忆",
      documentSummaryLabel: "文档摘要",
      writingGoalsLabel: "写作目标",
      keyTermsLabel: "关键词",
      userPreferencesLabel: "用户偏好",
      aiConfigTitle: "模型配置",
      providerPresetLabel: "接口预设",
      providerPresetCustom: "自定义",
      providerPresetOpenAI: "OpenAI",
      providerPresetDeepSeek: "DeepSeek",
      providerPresetQwen: "Qwen / 通义千问",
      providerPresetHint: "选择预设会自动填充推荐的 base URL，你仍然可以继续手动修改所有字段。",
      saveButton: "保存设置",
      checkButton: "检查连接",
      saveInProgress: "正在保存设置...",
      saveSuccess: "设置已保存。",
      saveFailure: "设置未能完整保存。",
      checkSuccess: "后端连接正常。",
      checkFailure: "后端连接失败。",
      loadFailure: "读取后端模型设置失败。",
    },
  };

  const zhOverrides = {
    settingsTitle: "设置",
    settingsSubtitle: "调整界面、记忆与模型配置。",
    statusIdle: "未保存",
    statusSaving: "保存中",
    statusSaved: "已保存",
    statusWarning: "请检查设置",
    languageLabel: "界面语言",
    fontSizeLabel: "Agent 字体大小",
    historyContextLabel: "History 上下文字符数",
    apiBaseLabel: "后端 API",
    behaviorTitle: "界面行为",
    autoApplyLabel: "自动应用编辑",
    showDetailsLabel: "显示操作详情",
    showUndoReviewLabel: "显示撤销/审查按钮",
    showSubagentStatusLabel: "显示 subagent 执行情况",
    subagentsTitle: "Subagent 设置",
    subagentsHint: "让 agent 自行判断是否需要调用动态 subagent，并决定每个 subagent 使用哪些 skill。",
    autoSubagentsLabel: "让 agent 自动选择 subagent",
    subagentExecutionModeLabel: "Subagent 执行模式",
    subagentModePipeline: "Pipeline（顺序）",
    subagentModeParallel: "Parallel（并行）",
    memoryTitle: "记忆",
    documentSummaryLabel: "文档摘要",
    writingGoalsLabel: "写作目标",
    keyTermsLabel: "关键词",
    userPreferencesLabel: "用户偏好",
    aiConfigTitle: "模型配置",
    providerPresetLabel: "接口预设",
    providerPresetCustom: "自定义",
    providerPresetDeepSeek: "DeepSeek",
    providerPresetQwen: "Qwen / 通义千问",
    providerPresetHint: "选择预设会自动填入推荐的 base URL；你仍然可以继续手动修改所有字段。",
    saveButton: "保存设置",
    checkButton: "检查连接",
    saveInProgress: "正在保存设置...",
    saveSuccess: "设置已保存。",
    saveFailure: "设置未能完整保存。",
    checkSuccess: "后端连接正常。",
    checkFailure: "后端连接失败。",
    loadFailure: "读取后端模型设置失败。",
  };

  function t(language, key) {
    if (language === "zh-CN" && zhOverrides[key]) {
      return zhOverrides[key];
    }
    const table = copy[language] || copy.en;
    return table[key] || copy.en[key] || key;
  }

  function applyLanguage(language) {
    document.documentElement.lang = language === "zh-CN" ? "zh-CN" : "en";
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.getAttribute("data-i18n");
      node.textContent = t(language, key);
    });
  }

  function setStatus(state, text) {
    elements.statusPill.dataset.state = state;
    elements.statusPill.textContent = text;
  }

  function setMessage(text, kind) {
    elements.message.textContent = text || "";
    elements.message.style.color =
      kind === "error" ? "#b91c1c" : kind === "success" ? "#166534" : "#6b7280";
  }

  function localSettingsFromForm() {
    const apiBase = (elements.apiBase.value.trim() || shared.getRuntimeConfig().apiBase).replace(/\/+$/, "");
    const runtimeApiBase = (shared.getRuntimeConfig().apiBase || "").replace(/\/+$/, "");
    return {
      language: elements.language.value,
      languageExplicit: true,
      fontSize: Number.parseInt(elements.fontSize.value, 10) || 14,
      historyContextChars: Number.parseInt(elements.historyContextChars.value, 10) || 0,
      apiBase,
      apiBaseExplicit: apiBase !== runtimeApiBase,
      autoApply: elements.autoApply.checked,
      showDetails: elements.showDetails.checked,
      showUndoReview: elements.showUndoReview.checked,
      showSubagentStatus: elements.showSubagentStatus.checked,
      autoSubagents: elements.autoSubagents.checked,
      subagentExecutionMode: elements.subagentExecutionMode.value,
      documentSummary: elements.documentSummary.value.trim(),
      writingGoals: elements.writingGoals.value.trim(),
      keyTerms: elements.keyTerms.value.trim(),
      userPreferences: elements.userPreferences.value.trim(),
    };
  }

  function remoteSettingsFromForm() {
    return {
      api_key: elements.openaiApiKey.value,
      model: elements.openaiModel.value.trim(),
      base_url: elements.openaiBaseUrl.value.trim(),
      api_endpoint: elements.openaiApiEndpoint.value.trim(),
      proxy_url: elements.openaiProxyUrl.value.trim(),
      trust_env: elements.openaiTrustEnv.checked,
      use_json_mode: elements.openaiUseJsonMode.checked,
    };
  }

  function fillLocalSettings(settings) {
    elements.language.value = settings.language;
    elements.fontSize.value = String(settings.fontSize);
    elements.historyContextChars.value = String(settings.historyContextChars);
    elements.apiBase.value = settings.apiBase;
    elements.autoApply.checked = settings.autoApply !== false;
    elements.showDetails.checked = settings.showDetails !== false;
    elements.showUndoReview.checked = settings.showUndoReview !== false;
    elements.showSubagentStatus.checked = settings.showSubagentStatus !== false;
    elements.autoSubagents.checked = settings.autoSubagents === true;
    elements.subagentExecutionMode.value = settings.subagentExecutionMode || "pipeline";
    elements.documentSummary.value = settings.documentSummary || "";
    elements.writingGoals.value = settings.writingGoals || "";
    elements.keyTerms.value = settings.keyTerms || "";
    elements.userPreferences.value = settings.userPreferences || "";
  }

  function fillRemoteSettings(config) {
    elements.openaiApiKey.value = config.api_key || "";
    elements.openaiModel.value = config.model || "";
    elements.openaiBaseUrl.value = config.base_url || "";
    elements.openaiApiEndpoint.value = config.api_endpoint || "";
    elements.openaiProxyUrl.value = config.proxy_url || "";
    elements.openaiTrustEnv.checked = Boolean(config.trust_env);
    elements.openaiUseJsonMode.checked = Boolean(config.use_json_mode);
    updatePresetSelection();
  }

  function currentRemoteSignature() {
    return {
      model: elements.openaiModel.value.trim(),
      base_url: elements.openaiBaseUrl.value.trim(),
      api_endpoint: elements.openaiApiEndpoint.value.trim(),
      trust_env: elements.openaiTrustEnv.checked,
      use_json_mode: elements.openaiUseJsonMode.checked,
    };
  }

  function matchesPreset(name) {
    const preset = PRESETS[name];
    const current = currentRemoteSignature();
    return (
      current.base_url === (preset.base_url || "") &&
      current.api_endpoint === (preset.api_endpoint || "") &&
      current.model === (preset.model || "") &&
      current.trust_env === Boolean(preset.trust_env) &&
      current.use_json_mode === Boolean(preset.use_json_mode)
    );
  }

  function updatePresetSelection() {
    const preset = ["openai", "deepseek", "qwen"].find(matchesPreset) || "custom";
    elements.providerPreset.value = preset;
  }

  function applyPreset(name) {
    const preset = PRESETS[name];
    if (!preset || name === "custom") {
      return;
    }
    if (preset.model) {
      elements.openaiModel.value = preset.model;
    }
    elements.openaiBaseUrl.value = preset.base_url || "";
    elements.openaiApiEndpoint.value = preset.api_endpoint || "";
    elements.openaiTrustEnv.checked = Boolean(preset.trust_env);
    elements.openaiUseJsonMode.checked = Boolean(preset.use_json_mode);
  }

  async function requestJson(url, init, timeoutMs) {
    const controller = "AbortController" in window ? new AbortController() : null;
    const timeout = controller
      ? window.setTimeout(() => controller.abort(), timeoutMs || 10000)
      : null;

    let response;
    try {
      response = await fetch(url, {
        ...(init || {}),
        signal: controller ? controller.signal : undefined,
      });
    } catch (error) {
      if (error && error.name === "AbortError") {
        throw new Error("Request timed out. Make sure Word AI is running.");
      }
      throw error;
    } finally {
      if (timeout) {
        window.clearTimeout(timeout);
      }
    }

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const data = await response.json();
        detail = data.detail || JSON.stringify(data);
      } catch (error) {
        // ignore
      }
      throw new Error(detail);
    }
    return response.json();
  }

  async function loadRemoteSettings() {
    const settings = shared.loadSettings();
    const config = await requestJson(`${settings.apiBase}/settings/ai-config`);
    fillRemoteSettings(config);
  }

  async function saveAll() {
    const localSettings = shared.saveSettings(localSettingsFromForm());
    applyLanguage(localSettings.language);
    notifyTaskpane();
    setStatus("saving", t(localSettings.language, "statusSaving"));
    setMessage(t(localSettings.language, "saveInProgress"), "");
    elements.saveButton.disabled = true;
    elements.checkButton.disabled = true;

    try {
      const config = await requestJson(`${localSettings.apiBase}/settings/ai-config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(remoteSettingsFromForm()),
      }, 10000);
      fillRemoteSettings(config);
      setStatus("saved", t(localSettings.language, "statusSaved"));
      setMessage(t(localSettings.language, "saveSuccess"), "success");
    } catch (error) {
      setStatus("warning", t(localSettings.language, "statusWarning"));
      setMessage(`${t(localSettings.language, "saveFailure")} ${error.message}`, "error");
    } finally {
      elements.saveButton.disabled = false;
      elements.checkButton.disabled = false;
    }
  }

  function notifyTaskpane() {
    if ("BroadcastChannel" in window) {
      var channel = new BroadcastChannel("word-ai");
      channel.postMessage({ type: "settings-changed" });
      channel.close();
    }
  }

  async function checkConnection() {
    const settings = shared.saveSettings(localSettingsFromForm());
    setStatus("saving", t(settings.language, "statusSaving"));
    setMessage(t(settings.language, "saveInProgress"), "");
    elements.saveButton.disabled = true;
    elements.checkButton.disabled = true;
    try {
      await requestJson(`${settings.apiBase}/health`, undefined, 8000);
      setStatus("saved", t(settings.language, "statusSaved"));
      setMessage(t(settings.language, "checkSuccess"), "success");
    } catch (error) {
      setStatus("warning", t(settings.language, "statusWarning"));
      setMessage(`${t(settings.language, "checkFailure")} ${error.message}`, "error");
    } finally {
      elements.saveButton.disabled = false;
      elements.checkButton.disabled = false;
    }
  }

  function bindPresetInputs() {
    [
      elements.openaiModel,
      elements.openaiBaseUrl,
      elements.openaiApiEndpoint,
      elements.openaiTrustEnv,
      elements.openaiUseJsonMode,
    ].forEach((element) => {
      element.addEventListener("input", updatePresetSelection);
      element.addEventListener("change", updatePresetSelection);
    });

    elements.providerPreset.addEventListener("change", () => {
      applyPreset(elements.providerPreset.value);
      updatePresetSelection();
    });
  }

  async function initialize() {
    if (shared.loadRuntimeConfig) {
      await shared.loadRuntimeConfig();
    }
    const settings = shared.loadSettings();
    fillLocalSettings(settings);
    applyLanguage(settings.language);
    setStatus("idle", t(settings.language, "statusIdle"));

    elements.language.addEventListener("change", () => {
      applyLanguage(elements.language.value);
      setStatus("idle", t(elements.language.value, "statusIdle"));
    });
    elements.saveButton.addEventListener("click", saveAll);
    elements.checkButton.addEventListener("click", checkConnection);
    bindPresetInputs();

    try {
      await loadRemoteSettings();
    } catch (error) {
      setStatus("warning", t(settings.language, "statusWarning"));
      setMessage(`${t(settings.language, "loadFailure")} ${error.message}`, "error");
      updatePresetSelection();
    }
  }

  if (typeof Office !== "undefined" && Office.onReady) {
    Office.onReady(initialize);
  } else {
    initialize();
  }
})();
