(function () {
  const shared = window.WordAIShared;
  const elements = {
    statusPill: document.getElementById("statusPill"),
    message: document.getElementById("message"),
    language: document.getElementById("language"),
    fontSize: document.getElementById("fontSize"),
    apiBase: document.getElementById("apiBase"),
    documentSummary: document.getElementById("documentSummary"),
    writingGoals: document.getElementById("writingGoals"),
    keyTerms: document.getElementById("keyTerms"),
    userPreferences: document.getElementById("userPreferences"),
    openaiApiKey: document.getElementById("openaiApiKey"),
    openaiModel: document.getElementById("openaiModel"),
    openaiBaseUrl: document.getElementById("openaiBaseUrl"),
    openaiApiEndpoint: document.getElementById("openaiApiEndpoint"),
    openaiProxyUrl: document.getElementById("openaiProxyUrl"),
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
      statusSaved: "Saved",
      statusWarning: "Check settings",
      languageLabel: "Language",
      fontSizeLabel: "Agent font size",
      apiBaseLabel: "Backend API",
      memoryTitle: "Memory",
      documentSummaryLabel: "Document summary",
      writingGoalsLabel: "Writing goals",
      keyTermsLabel: "Key terms",
      userPreferencesLabel: "User preferences",
      aiConfigTitle: "Model configuration",
      saveButton: "Save settings",
      checkButton: "Check connection",
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
      statusSaved: "已保存",
      statusWarning: "请检查设置",
      languageLabel: "界面语言",
      fontSizeLabel: "Agent 字体大小",
      apiBaseLabel: "后端 API",
      memoryTitle: "记忆",
      documentSummaryLabel: "文档摘要",
      writingGoalsLabel: "写作目标",
      keyTermsLabel: "关键词",
      userPreferencesLabel: "用户偏好",
      aiConfigTitle: "模型配置",
      saveButton: "保存设置",
      checkButton: "检查连接",
      saveSuccess: "设置已保存。",
      saveFailure: "设置未能完整保存。",
      checkSuccess: "后端连接正常。",
      checkFailure: "后端连接失败。",
      loadFailure: "读取后端模型设置失败。",
    },
  };

  function t(language, key) {
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
    return {
      language: elements.language.value,
      languageExplicit: true,
      fontSize: Number.parseInt(elements.fontSize.value, 10) || 14,
      apiBase: elements.apiBase.value.trim() || "http://127.0.0.1:8000",
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
    elements.apiBase.value = settings.apiBase;
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
  }

  async function requestJson(url, init) {
    const response = await fetch(url, init);
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

    try {
      const config = await requestJson(`${localSettings.apiBase}/settings/ai-config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(remoteSettingsFromForm()),
      });
      fillRemoteSettings(config);
      setStatus("saved", t(localSettings.language, "statusSaved"));
      setMessage(t(localSettings.language, "saveSuccess"), "success");
    } catch (error) {
      setStatus("warning", t(localSettings.language, "statusWarning"));
      setMessage(`${t(localSettings.language, "saveFailure")} ${error.message}`, "error");
    }
  }

  async function checkConnection() {
    const settings = shared.saveSettings(localSettingsFromForm());
    try {
      await requestJson(`${settings.apiBase}/health`);
      setStatus("saved", t(settings.language, "statusSaved"));
      setMessage(t(settings.language, "checkSuccess"), "success");
    } catch (error) {
      setStatus("warning", t(settings.language, "statusWarning"));
      setMessage(`${t(settings.language, "checkFailure")} ${error.message}`, "error");
    }
  }

  async function initialize() {
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

    try {
      await loadRemoteSettings();
    } catch (error) {
      setStatus("warning", t(settings.language, "statusWarning"));
      setMessage(`${t(settings.language, "loadFailure")} ${error.message}`, "error");
    }
  }

  if (typeof Office !== "undefined" && Office.onReady) {
    Office.onReady(initialize);
  } else {
    initialize();
  }
})();
