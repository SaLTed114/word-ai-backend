const EVENT_KEY = "wordAiEvents";
const SETTINGS_PAGE_URL = "https://localhost:3443/settings.html?v=20260606-3";
const TASKPANE_URL = "https://localhost:3443/taskpane.html";

const COMMANDS = {
  syntax: {
    title: "Syntax",
    endpoint: "/tasks/syntax",
    instruction: null,
  },
  wordChoice: {
    title: "Word Choice",
    endpoint: "/tasks/word-choice",
    instruction: null,
  },
  rewrite: {
    title: "Rewrite",
    endpoint: "/tasks/style",
    instruction: null,
    style: "polished",
  },
  formula: {
    title: "Formula",
    endpoint: "/tasks/formula",
    instruction: "Convert the selected text into a Word equation.",
  },
};

Office.onReady(() => {
  Office.actions.associate("runSyntax", runSyntax);
  Office.actions.associate("runWordChoice", runWordChoice);
  Office.actions.associate("runRewrite", runRewrite);
  Office.actions.associate("runFormula", runFormula);
  Office.actions.associate("openAgent", openAgent);
  Office.actions.associate("openSettings", openSettings);
});

function runSyntax(event) {
  runCommand("syntax", event);
}

function runWordChoice(event) {
  runCommand("wordChoice", event);
}

function runRewrite(event) {
  runCommand("rewrite", event);
}

function runFormula(event) {
  runCommand("formula", event);
}

function openAgent(event) {
  Office.context.ui.displayDialogAsync(TASKPANE_URL, { height: 70, width: 35 });
  completeEvent(event);
}

function openSettings(event) {
  Office.context.ui.displayDialogAsync(SETTINGS_PAGE_URL, { height: 70, width: 45 });
  completeEvent(event);
}

async function runCommand(name, event) {
  const command = COMMANDS[name];
  publishEvent({
    status: "started",
    title: command.title,
    message: `${command.title} started.`,
  });

  try {
    const payload = await getWordPayload(command);
    const result = await requestJson(command.endpoint, payload.request);
    const applied = await applyResult(payload.source, result);
    publishEvent({
      status: "finished",
      title: command.title,
      result,
      replaced: applied,
    });
  } catch (error) {
    publishEvent({
      status: "error",
      title: command.title,
      message: error.message || String(error),
    });
  } finally {
    completeEvent(event);
  }
}

async function getWordPayload(command) {
  return Word.run(async (context) => {
    const selection = context.document.getSelection();
    const body = context.document.body;
    selection.load("text");
    body.load("text");
    await context.sync();

    const selectedText = selection.text || "";
    const documentText = body.text || "";
    const hasSelection = selectedText.trim().length > 0;
    const text = hasSelection ? selectedText : documentText;

    if (!text.trim()) {
      throw new Error("No selected text or document text was found.");
    }

    return {
      source: hasSelection ? "selection" : "document",
      request: {
        text,
        context: getContextWindow(documentText, selectedText),
        instruction: command.instruction,
        style: command.style || null,
      },
    };
  });
}

function getContextWindow(documentText, selectedText) {
  if (!selectedText) {
    return { before: "", after: "" };
  }
  const index = documentText.indexOf(selectedText);
  if (index < 0) {
    return { before: "", after: "" };
  }
  return {
    before: documentText.slice(Math.max(0, index - 500), index),
    after: documentText.slice(index + selectedText.length, index + selectedText.length + 500),
  };
}

async function requestJson(path, payload) {
  const response = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || JSON.stringify(data));
  }
  return data;
}

function apiBase() {
  if (window.WordAIShared && window.WordAIShared.loadSettings) {
    return (window.WordAIShared.loadSettings().apiBase || "http://127.0.0.1:8000").replace(/\/+$/, "");
  }
  return "http://127.0.0.1:8000";
}

async function applyResult(source, result) {
  const formulaAction = getFormulaAction(result);
  if (formulaAction) {
    await applyEquationAction(source, formulaAction);
    return true;
  }

  const replacement = getReplacement(result);
  if (!replacement) {
    return false;
  }

  await Word.run(async (context) => {
    if (source === "document") {
      context.document.body.insertText(replacement, Word.InsertLocation.replace);
    } else {
      context.document.getSelection().insertText(replacement, Word.InsertLocation.replace);
    }
    await context.sync();
  });
  return true;
}

function getReplacement(result) {
  const replaceAction = (result.actions || []).find((action) => {
    return action.type === "replace_selection" && action.replacement;
  });
  return result.final_text || (replaceAction && replaceAction.replacement) || null;
}

function getFormulaAction(result) {
  return (result.actions || []).find((action) => {
    return (
      (action.type === "replace_selection_equation" || action.type === "insert_equation") &&
      (action.formula || action.replacement)
    );
  }) || null;
}

async function applyEquationAction(source, action) {
  const formula = action.formula || action.replacement || "";
  const ooxml = action.formula_format === "omml" ? formula : formulaToOoxml(formula);

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
        <w:body><w:p><m:oMathPara><m:oMath>${math}</m:oMath></m:oMathPara></w:p></w:body>
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
    if (name === "cdot") return mathRun("·");
    if (name === "times") return mathRun("×");
    if (name === "leq") return mathRun("≤");
    if (name === "geq") return mathRun("≥");
    if (name === "neq") return mathRun("≠");
    if (GREEK_LETTERS[name]) return mathRun(GREEK_LETTERS[name]);
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

function publishEvent(payload) {
  const event = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    ...payload,
  };
  try {
    const events = JSON.parse(localStorage.getItem(EVENT_KEY) || "[]");
    events.push(event);
    localStorage.setItem(EVENT_KEY, JSON.stringify(events.slice(-50)));
  } catch {
    localStorage.setItem(EVENT_KEY, JSON.stringify([event]));
  }
  if ("BroadcastChannel" in window) {
    const channel = new BroadcastChannel("word-ai");
    channel.postMessage({ type: "word-ai-event", payload: event });
    channel.close();
  }
}

function completeEvent(event) {
  if (event && typeof event.completed === "function") {
    event.completed();
  }
}
