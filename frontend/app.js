// Filled in once client_config.json has loaded - other pieces (like sending
// a chat message) will read from this instead of hardcoding "/chat".
let apiBaseUrl = "";

async function loadConfig() {
  const response = await fetch("client_config.json");
  return response.json();
}

function applyConfig(config) {
  document.title = config.hotel_name;
  document.getElementById("hotel-name").textContent = config.hotel_name;
  document.getElementById("hotel-tagline").textContent = config.tagline;
  document.getElementById("welcome-bubble").textContent = config.welcome_message;
  document.getElementById("chat-input").placeholder = config.input_placeholder;

  const initial = config.hotel_name.charAt(0);
  document.getElementById("brand-mark").textContent = initial;
  document.getElementById("assistant-avatar").textContent = initial;

  const quickActions = document.getElementById("quick-actions");
  config.quick_actions.forEach((label) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = label;
    quickActions.appendChild(chip);
  });

  apiBaseUrl = config.api_base_url;
}

function appendMessage(text, sender) {
  const messages = document.getElementById("chat-messages");

  const wrapper = document.createElement("div");
  wrapper.className = `message ${sender}`;

  if (sender === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = document.getElementById("assistant-avatar").textContent;
    wrapper.appendChild(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (sender === "assistant") {
    // The AI replies in markdown (bold, tables, etc.) - render it to real
    // HTML, then sanitize that HTML before it touches the page, in case the
    // reply was ever manipulated into containing something like a script tag.
    bubble.innerHTML = DOMPurify.sanitize(marked.parse(text));
  } else {
    bubble.textContent = text;
  }
  wrapper.appendChild(bubble);

  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

async function sendMessage(text) {
  const trimmed = text.trim();
  if (!trimmed) return;

  const roomInput = document.getElementById("room-number");
  const roomNumber = roomInput.value.trim();
  if (!roomNumber) {
    roomInput.focus();
    return;
  }

  appendMessage(trimmed, "guest");

  const sendButton = document.getElementById("send-btn");
  sendButton.disabled = true;

  try {
    const response = await fetch(`${apiBaseUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room_number: roomNumber, message: trimmed }),
    });

    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    const data = await response.json();
    appendMessage(data.reply, "assistant");
  } catch (error) {
    appendMessage("Sorry, something went wrong. Please try again.", "assistant");
  } finally {
    sendButton.disabled = false;
  }
}

function setupEventListeners() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = input.value;
    input.value = "";
    sendMessage(text);
  });

  // Chips are created dynamically in applyConfig(), so we listen on their
  // shared parent instead of attaching a listener to each one individually.
  const quickActions = document.getElementById("quick-actions");
  quickActions.addEventListener("click", (event) => {
    if (event.target.classList.contains("chip")) {
      sendMessage(event.target.textContent);
    }
  });
}

async function init() {
  const config = await loadConfig();
  applyConfig(config);
  setupEventListeners();
}

init();
