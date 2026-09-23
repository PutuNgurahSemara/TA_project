/* ============================================================
   chat.js — Streaming Chat Handler (Gemini-Inspired UX)
   ============================================================ */

const chatList = document.getElementById("chatList");
const chatScroll = document.getElementById("chatScroll");
const chatInput = document.getElementById("chatInput");
const btnSend = document.getElementById("btnSend");
const btnClearChat = document.getElementById("btnClearChat");
const heroGreeting = document.getElementById("heroGreeting");
const statusIndicator = document.getElementById("statusIndicator");
const statusText = document.getElementById("statusText");

let isStreaming = false;

// ── Robust Markdown Parser (Zero Dependencies) ───────────────
function formatInline(text) {
  if (!text) return "";

  // Inline code: `code`
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Bold: **text** or __text__
  text = text.replace(/\*\*([^\*\n]+?)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/__([^_\n]+?)__/g, "<strong>$1</strong>");

  // Italic: *text* or _text_ (single asterisks/underscores, must not span newlines)
  text = text.replace(/(^|[^\*])\*([^\*\s\n](?:[^\*\n]*?[^\*\s\n])?)\*(?!\*)/g, "$1<em>$2</em>");
  text = text.replace(/(^|[^_])_([^_\s\n](?:[^_\n]*?[^_\s\n])?)_(?!_)/g, "$1<em>$2</em>");

  return text;
}

function renderMarkdown(raw) {
  if (!raw) return "";

  // 1. Escape HTML tags to prevent XSS
  let text = raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // 2. Extract code blocks (```lang\n...```)
  const codeBlocks = [];
  text = text.replace(/```([\w]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
    codeBlocks.push(`<pre><code>${code.trim()}</code></pre>`);
    return placeholder;
  });

  // 3. Process line by line for block elements (lists, headers, quotes, paragraphs)
  let lines = text.split("\n");
  let formatted = [];
  let currentList = null; // 'ul' or 'ol'

  function closeList() {
    if (currentList) {
      formatted.push(`</${currentList}>`);
      currentList = null;
    }
  }

  for (let line of lines) {
    let trimmed = line.trim();

    if (!trimmed) {
      closeList();
      continue;
    }

    if (trimmed.startsWith("__CODE_BLOCK_") && trimmed.endsWith("__")) {
      closeList();
      formatted.push(trimmed);
      continue;
    }

    // Headers: # ## ### ####
    let headerMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headerMatch) {
      closeList();
      let level = headerMatch[1].length;
      formatted.push(`<h${level}>${formatInline(headerMatch[2])}</h${level}>`);
      continue;
    }

    // Blockquotes: > quote
    if (trimmed.startsWith("&gt; ") || trimmed.startsWith("> ")) {
      closeList();
      let quoteText = trimmed.replace(/^(&gt;|>)\s*/, "");
      formatted.push(`<blockquote>${formatInline(quoteText)}</blockquote>`);
      continue;
    }

    // Unordered list: starts with "- ", "* ", "+ ", or "• "
    let ulMatch = trimmed.match(/^(\*|-|\+|\u2022)\s+(.*)$/);
    if (ulMatch) {
      if (currentList !== "ul") {
        closeList();
        formatted.push("<ul>");
        currentList = "ul";
      }
      formatted.push(`<li>${formatInline(ulMatch[2])}</li>`);
      continue;
    }

    // Ordered list: starts with "1. ", "2. ", etc.
    let olMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (olMatch) {
      if (currentList !== "ol") {
        closeList();
        formatted.push("<ol>");
        currentList = "ol";
      }
      formatted.push(`<li>${formatInline(olMatch[2])}</li>`);
      continue;
    }

    // Regular paragraph
    closeList();
    formatted.push(`<p>${formatInline(trimmed)}</p>`);
  }

  closeList();

  let html = formatted.join("");

  // Restore code blocks
  codeBlocks.forEach((block, idx) => {
    html = html.replace(`__CODE_BLOCK_${idx}__`, block);
  });

  return html;
}

// ── Auto-resize Textarea ──────────────────────────────────────
chatInput.addEventListener("input", () => {
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 180) + "px";
  btnSend.disabled = chatInput.value.trim().length === 0 || isStreaming;
});

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (!btnSend.disabled) {
      sendMessage();
    }
  }
});

function usePrompt(text) {
  chatInput.value = text;
  chatInput.dispatchEvent(new Event("input"));
  chatInput.focus();
}

// ── Health Check & Access Key Checking ────────────────────────
async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error();
    const data = await res.json();
    const dot = statusIndicator.querySelector(".status-dot");
    if (data.ollama && data.ollama.connected) {
      dot.className = "status-dot";
      const docCount = data.database.documents_count || 0;
      statusText.textContent = `${data.ollama.llm_model} • ${docCount} Dokumen`;
    } else {
      dot.className = "status-dot error";
      statusText.textContent = "Ollama Offline";
    }

    // Cek jika server mewajibkan kode akses dan belum tersimpan
    if (data.security && data.security.access_key_required) {
      if (!localStorage.getItem("chat_access_key")) {
        showAccessKeyModal();
      }
    }
  } catch {
    const dot = statusIndicator.querySelector(".status-dot");
    dot.className = "status-dot error";
    statusText.textContent = "Server Terputus";
  }
}
checkHealth();
setInterval(checkHealth, 15000);

// ── Modal Kode Akses (Proteksi Sesi Chat) ────────────────────
function showAccessKeyModal(errorMsg = "") {
  const modal = document.getElementById("accessKeyModal");
  const err = document.getElementById("accessKeyError");
  const input = document.getElementById("inputAccessKey");
  if (modal) modal.style.display = "flex";
  if (err) {
    if (errorMsg) {
      err.textContent = errorMsg;
      err.style.display = "block";
    } else {
      err.style.display = "none";
    }
  }
  if (input) {
    input.value = "";
    setTimeout(() => input.focus(), 150);
  }
}

function submitAccessKey() {
  const input = document.getElementById("inputAccessKey");
  const val = input ? input.value.trim() : "";
  if (!val) return;
  localStorage.setItem("chat_access_key", val);
  const modal = document.getElementById("accessKeyModal");
  if (modal) modal.style.display = "none";
  showToast("Kode akses tersimpan.");
}

// ── Chat Logic ────────────────────────────────────────────────
function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function appendUserMessage(text) {
  if (heroGreeting) {
    heroGreeting.style.display = "none";
  }

  const row = document.createElement("div");
  row.className = "message-row user";
  row.innerHTML = `<div class="user-bubble">${escapeHtml(text)}</div>`;
  chatList.appendChild(row);
  scrollToBottom();
}

function createAssistantMessage() {
  const row = document.createElement("div");
  row.className = "message-row assistant";

  row.innerHTML = `
    <div class="assistant-avatar" title="Gemini AI">
      <svg class="gemini-sparkle-icon" viewBox="0 0 24 24" style="width: 22px; height: 22px;">
        <path d="M12 0C12 6.627 6.627 12 0 12c6.627 0 12 5.373 12 12 0-6.627 5.373-12 12-12-6.627 0-12-5.373-12-12z" />
      </svg>
    </div>
    <div class="assistant-content">
      <!-- Real-time Thinking Pill -->
      <div class="thinking-container">
        <div class="thinking-pill">
          <span class="thinking-spinner">
            <svg class="thinking-sparkle" viewBox="0 0 24 24">
              <path d="M12 0C12 6.627 6.627 12 0 12c6.627 0 12 5.373 12 12 0-6.627 5.373-12 12-12-6.627 0-12-5.373-12-12z" />
            </svg>
          </span>
          <span class="thinking-status">Menganalisis pertanyaan...</span>
          <span class="thinking-timer">0.0s</span>
        </div>
      </div>

      <div class="answer-body"><span class="typing-cursor"></span></div>
      <div class="sources-container" style="display:none;">
        <div class="sources-header">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Sumber Referensi
        </div>
        <div class="source-chips"></div>
        <div class="source-excerpt-card"></div>
      </div>
      <div class="assistant-actions" style="display:none;">
        <button class="btn-action-icon btn-copy" title="Salin jawaban">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
        <span class="response-time-badge"></span>
      </div>
    </div>
  `;

  chatList.appendChild(row);
  scrollToBottom();

  const thinkingContainer = row.querySelector(".thinking-container");
  const thinkingStatus = row.querySelector(".thinking-status");
  const thinkingTimer = row.querySelector(".thinking-timer");
  const answerBody = row.querySelector(".answer-body");
  const sourcesContainer = row.querySelector(".sources-container");
  const sourceChips = row.querySelector(".source-chips");
  const sourceExcerpt = row.querySelector(".source-excerpt-card");
  const actionsBar = row.querySelector(".assistant-actions");
  const btnCopy = row.querySelector(".btn-copy");
  const responseTimeBadge = row.querySelector(".response-time-badge");

  btnCopy.addEventListener("click", () => {
    navigator.clipboard.writeText(answerBody.innerText).then(() => {
      showToast("Jawaban berhasil disalin ke clipboard.");
    });
  });

  return {
    row,
    thinkingContainer,
    thinkingStatus,
    thinkingTimer,
    answerBody,
    sourcesContainer,
    sourceChips,
    sourceExcerpt,
    actionsBar,
    responseTimeBadge,
  };
}

async function sendMessage() {
  const question = chatInput.value.trim();
  if (!question || isStreaming) return;

  isStreaming = true;
  btnSend.disabled = true;
  chatInput.value = "";
  chatInput.style.height = "auto";

  appendUserMessage(question);
  const assistant = createAssistantMessage();

  let accumulatedText = "";
  let sources = [];
  const startTime = performance.now();
  let firstTokenReceived = false;
  let thinkingDuration = "0.0";

  // Real-time ticking stopwatch
  const timerInterval = setInterval(() => {
    if (!firstTokenReceived) {
      const elapsed = (performance.now() - startTime) / 1000;
      assistant.thinkingTimer.textContent = `${elapsed.toFixed(1)}s`;

      if (elapsed > 20 && !assistant.thinkingStatus.dataset.custom) {
        assistant.thinkingStatus.textContent = "Sedang merumuskan jawaban mendalam...";
      } else if (elapsed > 8 && !assistant.thinkingStatus.dataset.custom) {
        assistant.thinkingStatus.textContent = "Memproses dengan model AI lokal...";
      }
    }
  }, 80);

  try {
    const accessKey = localStorage.getItem("chat_access_key") || "";
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Access-Key": accessKey,
      },
      body: JSON.stringify({ question: question }),
    });

    if (!res.ok) {
      let errMsg = `Server error: ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) errMsg = errJson.detail;
      } catch { }

      if (res.status === 403) {
        localStorage.removeItem("chat_access_key");
        showAccessKeyModal(errMsg);
      }
      throw new Error(errMsg);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // keep remainder

      for (const block of lines) {
        if (!block.trim()) continue;

        let eventType = "message";
        let eventData = "";

        for (const line of block.split("\n")) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            eventData = line.slice(6);
          }
        }

        if (eventType === "status") {
          try {
            const data = JSON.parse(eventData);
            if (data.message && !firstTokenReceived) {
              assistant.thinkingStatus.textContent = data.message;
              assistant.thinkingStatus.dataset.custom = "true";
            }
          } catch (e) {
            console.error("Error parsing status event", e);
          }
        } else if (eventType === "sources") {
          try {
            const data = JSON.parse(eventData);
            sources = data.sources || [];
            if (sources.length > 0) {
              renderSources(sources, assistant.sourcesContainer, assistant.sourceChips, assistant.sourceExcerpt);
            }
            if (!firstTokenReceived) {
              assistant.thinkingStatus.textContent = `Ditemukan ${sources.length} referensi. Menghubungkan model...`;
              assistant.thinkingStatus.dataset.custom = "true";
            }
          } catch (e) {
            console.error("Error parsing sources", e);
          }
        } else if (eventType === "token") {
          try {
            const data = JSON.parse(eventData);

            // Lock thinking time at first token (TTFT - Time to First Token)
            if (!firstTokenReceived) {
              firstTokenReceived = true;
              thinkingDuration = ((performance.now() - startTime) / 1000).toFixed(1);
              assistant.thinkingContainer.classList.add("completed");
              assistant.thinkingStatus.textContent = "Berpikir selama";
              assistant.thinkingTimer.textContent = `${thinkingDuration} detik`;
            }

            accumulatedText += data.token;
            assistant.answerBody.innerHTML = renderMarkdown(accumulatedText) + '<span class="typing-cursor"></span>';
            scrollToBottom();
          } catch (e) {
            console.error("Error parsing token", e);
          }
        } else if (eventType === "done") {
          // Finished streaming
        } else if (eventType === "error") {
          try {
            const data = JSON.parse(eventData);
            accumulatedText += `\n\n*(Terjadi kesalahan: ${data.error})*`;
          } catch { }
        }
      }
    }

    // Finalize answer text without cursor
    clearInterval(timerInterval);
    const totalDuration = ((performance.now() - startTime) / 1000).toFixed(1);

    if (!firstTokenReceived) {
      firstTokenReceived = true;
      assistant.thinkingContainer.classList.add("completed");
      assistant.thinkingStatus.textContent = "Selesai dalam";
      assistant.thinkingTimer.textContent = `${totalDuration} detik`;
    }

    assistant.answerBody.innerHTML = renderMarkdown(accumulatedText);
    assistant.responseTimeBadge.textContent = `Total Durasi: ${totalDuration}s`;
    assistant.actionsBar.style.display = "flex";

  } catch (err) {
    clearInterval(timerInterval);
    const failDuration = ((performance.now() - startTime) / 1000).toFixed(1);
    assistant.thinkingContainer.classList.add("error");
    assistant.thinkingStatus.textContent = "Gagal memproses";
    assistant.thinkingTimer.textContent = `${failDuration}s`;
    assistant.answerBody.innerHTML = `<p style="color: var(--danger);">Gagal mendapatkan respon: ${escapeHtml(err.message)}</p>`;
  } finally {
    clearInterval(timerInterval);
    isStreaming = false;
    btnSend.disabled = chatInput.value.trim().length === 0;
    chatInput.focus();
  }
}

function renderSources(sources, container, chipsContainer, excerptCard) {
  container.style.display = "flex";
  chipsContainer.innerHTML = "";

  sources.forEach((s, idx) => {
    const chip = document.createElement("div");
    chip.className = "source-chip";
    const pageLabel = s.page_num ? `Hal ${s.page_num}` : "Dokumen";
    chip.innerHTML = `<span>📄</span> ${escapeHtml(s.source)} (${pageLabel})`;

    chip.addEventListener("click", () => {
      const isActive = chip.classList.contains("active");
      chipsContainer.querySelectorAll(".source-chip").forEach(c => c.classList.remove("active"));

      if (isActive) {
        excerptCard.classList.remove("show");
      } else {
        chip.classList.add("active");
        excerptCard.innerHTML = `
          <div class="source-card-meta">
            <span>${escapeHtml(s.source)} — Halaman ${s.page_num || '-'}</span>
            <span>Jarak kemiripan: ${s.distance ? s.distance.toFixed(3) : '-'}</span>
          </div>
          <div>"${escapeHtml(s.excerpt)}"</div>
        `;
        excerptCard.classList.add("show");
        scrollToBottom();
      }
    });

    chipsContainer.appendChild(chip);
  });
}

// ── Clear Chat ────────────────────────────────────────────────
btnClearChat.addEventListener("click", () => {
  chatList.innerHTML = "";
  if (heroGreeting) {
    chatList.appendChild(heroGreeting);
    heroGreeting.style.display = "flex";
  }
  showToast("Percakapan telah dibersihkan.");
});

// ── Helpers ───────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showToast(message) {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

btnSend.addEventListener("click", sendMessage);
