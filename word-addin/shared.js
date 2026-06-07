(function () {
  const STORAGE_KEY = "wordAiSettings";

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
      apiBase: "http://127.0.0.1:8000",
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
    return {
      apiBase: String((raw && raw.apiBase) || base.apiBase).trim() || base.apiBase,
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
    defaultSettings,
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
