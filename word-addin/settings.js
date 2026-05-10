const elements = {
  apiBase: document.getElementById("apiBase"),
  healthButton: document.getElementById("healthButton"),
  healthStatus: document.getElementById("healthStatus"),
  messageBox: document.getElementById("messageBox")
};

function apiUrl(path) {
  return `${elements.apiBase.value.replace(/\/$/, "")}${path}`;
}

function showMessage(message, isError = false) {
  elements.messageBox.hidden = !message;
  elements.messageBox.textContent = message || "";
  elements.messageBox.classList.toggle("error", isError);
}

async function checkHealth() {
  elements.healthStatus.className = "status-dot";
  showMessage("");
  try {
    const response = await fetch(apiUrl("/health"));
    const data = await response.json();
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    elements.healthStatus.className = "status-dot ok";
    showMessage(`Connected.\nAI configured: ${Boolean(data.ai_configured)}`);
  } catch (error) {
    elements.healthStatus.className = "status-dot error";
    showMessage(`Health check failed: ${error.message || String(error)}`, true);
  }
}

elements.healthButton.addEventListener("click", checkHealth);
checkHealth();
