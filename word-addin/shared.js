(function () {
  const STORAGE_KEY = "wordAiSettings";
  const DEFAULT_API_BASE = "http://127.0.0.1:8000";
  const runtimeConfig = {
    apiBase: DEFAULT_API_BASE,
  };

  function normalizeApiBase(value) {
    return String(value || "").trim().replace(/\/+$/, "");
  }

  function applyRuntimeConfig(config) {
    const apiBase = normalizeApiBase(config && config.apiBase);
    if (apiBase) {
      runtimeConfig.apiBase = apiBase;
    }
    return getRuntimeConfig();
  }

  async function loadRuntimeConfig() {
    if (!window.fetch || window.location.protocol === "file:") {
      return getRuntimeConfig();
    }
    try {
      const response = await fetch(`./runtime-config.json?ts=${Date.now()}`, {
        cache: "no-store",
      });
      if (response.ok) {
        applyRuntimeConfig(await response.json());
      }
    } catch (error) {
      // Fall back to the default API address.
    }
    return getRuntimeConfig();
  }

  function getRuntimeConfig() {
    return {
      apiBase: runtimeConfig.apiBase,
    };
  }

  function detectPreferredLanguage() {
    const officeLanguage =
      typeof Office !== "undefined" &&
      Office.context &&
      (Office.context.displayLanguage || Office.context.contentLanguage);
    const language = officeLanguage || navigator.language || "en-US";
    return String(language).toLowerCase().startsWith("zh") ? "zh-CN" : "en";
  }

  function normalizeLanguage(value, explicit) {
    if (!explicit && !value) {
      return detectPreferredLanguage();
    }
    return String(value || "").toLowerCase().startsWith("zh") ? "zh-CN" : "en";
  }

  function normalizeBoolean(value, fallback) {
    if (typeof value === "boolean") {
      return value;
    }
    if (typeof value === "string") {
      return ["1", "true", "yes", "on"].includes(value.trim().toLowerCase());
    }
    return fallback;
  }

  function normalizeFontSize(value) {
    const parsed = Number.parseInt(value, 10);
    return [12, 13, 14, 15, 16, 18].includes(parsed) ? parsed : 14;
  }

  function defaultSettings() {
    return {
      apiBase: runtimeConfig.apiBase,
      apiBaseExplicit: false,
      language: detectPreferredLanguage(),
      languageExplicit: false,
      fontSize: 14,
      historyContextChars: 4000,
      autoApply: true,
      showDetails: true,
      showUndoReview: true,
      showSubagentStatus: true,
      autoSubagents: false,
      subagentExecutionMode: "pipeline",
      activeSubagents: [],
      activeSkills: [],
      documentSummary: "",
      writingGoals: "",
      keyTerms: "",
      userPreferences: "",
    };
  }

  function normalizeSettings(raw) {
    const base = defaultSettings();
    const languageExplicit = normalizeBoolean(raw && raw.languageExplicit, false);
    const apiBaseExplicit = normalizeBoolean(raw && raw.apiBaseExplicit, false);
    return {
      apiBase: apiBaseExplicit
        ? normalizeApiBase((raw && raw.apiBase) || base.apiBase) || base.apiBase
        : base.apiBase,
      apiBaseExplicit,
      language: normalizeLanguage(raw && raw.language, languageExplicit),
      languageExplicit,
      fontSize: normalizeFontSize(raw && raw.fontSize),
      historyContextChars: normalizeHistoryContextChars(raw && raw.historyContextChars),
      autoApply: raw && raw.autoApply !== undefined ? Boolean(raw.autoApply) : base.autoApply,
      showDetails: raw && raw.showDetails !== undefined ? Boolean(raw.showDetails) : base.showDetails,
      showUndoReview: raw && raw.showUndoReview !== undefined ? Boolean(raw.showUndoReview) : base.showUndoReview,
      showSubagentStatus:
        raw && raw.showSubagentStatus !== undefined ? Boolean(raw.showSubagentStatus) : base.showSubagentStatus,
      autoSubagents: raw && raw.autoSubagents !== undefined ? Boolean(raw.autoSubagents) : base.autoSubagents,
      subagentExecutionMode: normalizeSubagentExecutionMode(raw && raw.subagentExecutionMode),
      activeSubagents: normalizeSubagents(raw && raw.activeSubagents),
      activeSkills: Array.isArray(raw && raw.activeSkills) ? raw.activeSkills : base.activeSkills,
      documentSummary: String((raw && raw.documentSummary) || ""),
      writingGoals: String((raw && raw.writingGoals) || ""),
      keyTerms: String((raw && raw.keyTerms) || ""),
      userPreferences: String((raw && raw.userPreferences) || ""),
    };
  }

  function normalizeSubagents(value) {
    const allowed = ["proofread", "academic_polish", "summarize", "translate_zh", "formula"];
    if (!Array.isArray(value)) {
      return [];
    }
    return value.filter(function (item) {
      return allowed.indexOf(item) >= 0;
    });
  }

  function normalizeHistoryContextChars(value) {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) {
      return 4000;
    }
    return Math.min(Math.max(parsed, 0), 20000);
  }

  function normalizeSubagentExecutionMode(value) {
    return value === "parallel" ? "parallel" : "pipeline";
  }

  function loadSettings() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return defaultSettings();
      }
      return normalizeSettings(JSON.parse(raw));
    } catch (error) {
      return defaultSettings();
    }
  }

  function saveSettings(nextValues) {
    const merged = normalizeSettings({
      ...loadSettings(),
      ...(nextValues || {}),
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
    return merged;
  }

  function clearSettings() {
    localStorage.removeItem(STORAGE_KEY);
    return defaultSettings();
  }

  const api = {
    STORAGE_KEY,
    DEFAULT_API_BASE,
    defaultSettings,
    getRuntimeConfig,
    loadRuntimeConfig,
    applyRuntimeConfig,
    detectPreferredLanguage,
    normalizeSettings,
    loadSettings,
    getSettings: loadSettings,
    readSettings: loadSettings,
    saveSettings,
    updateSettings: saveSettings,
    writeSettings: saveSettings,
    clearSettings,
  };

  window.WordAIShared = api;
  window.loadWordAISettings = loadSettings;
  window.saveWordAISettings = saveSettings;
  window.getWordAISettings = loadSettings;
})();
