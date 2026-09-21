/* ============================================================
   admin.js — Admin Panel Handler (Auth, Upload, Document CRUD)
   ============================================================ */

const loginSection = document.getElementById("loginSection");
const dashboardSection = document.getElementById("dashboardSection");
const loginForm = document.getElementById("loginForm");
const usernameInput = document.getElementById("usernameInput");
const passwordInput = document.getElementById("passwordInput");
const btnLogout = document.getElementById("btnLogout");

const statDocCount = document.getElementById("statDocCount");
const statChunkCount = document.getElementById("statChunkCount");
const docTableBody = document.getElementById("docTableBody");

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const progressContainer = document.getElementById("progressContainer");
const progressStatus = document.getElementById("progressStatus");
const progressPct = document.getElementById("progressPct");
const progressBarFill = document.getElementById("progressBarFill");

let authToken = localStorage.getItem("ta_admin_token") || "";

// ── Auth Helpers ─────────────────────────────────────────────
function getAuthHeaders() {
  return {
    "Authorization": `Bearer ${authToken}`,
  };
}

async function verifyAuth() {
  if (!authToken) {
    showLogin();
    return;
  }
  try {
    const res = await fetch("/api/admin/check-session", {
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      showDashboard();
    } else {
      logout();
    }
  } catch {
    showLogin();
  }
}

function showLogin() {
  loginSection.style.display = "block";
  dashboardSection.style.display = "none";
  btnLogout.style.display = "none";
}

function showDashboard() {
  loginSection.style.display = "none";
  dashboardSection.style.display = "block";
  btnLogout.style.display = "flex";
  loadStats();
  loadDocuments();
}

// ── Login Form ───────────────────────────────────────────────
loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = usernameInput.value.trim();
  const password = passwordInput.value;
  const btn = document.getElementById("btnLogin");

  btn.disabled = true;
  btn.textContent = "Memverifikasi...";

  try {
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await res.json();
    if (res.ok && data.success) {
      authToken = data.token;
      localStorage.setItem("ta_admin_token", authToken);
      passwordInput.value = "";
      showToast("Berhasil masuk sebagai administrator.");
      showDashboard();
    } else {
      showToast(data.detail || "Password atau username salah.");
    }
  } catch (err) {
    showToast("Gagal menghubungi server: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Masuk";
  }
});

function logout() {
  if (authToken) {
    fetch("/api/admin/logout", {
      method: "POST",
      headers: getAuthHeaders(),
    }).catch(() => {});
  }
  authToken = "";
  localStorage.removeItem("ta_admin_token");
  showToast("Anda telah keluar.");
  showLogin();
}

btnLogout.addEventListener("click", logout);

// ── Stats & Documents ────────────────────────────────────────
async function loadStats() {
  try {
    const res = await fetch("/api/admin/stats", { headers: getAuthHeaders() });
    if (res.ok) {
      const data = await res.json();
      statDocCount.textContent = data.document_count || 0;
      statChunkCount.textContent = (data.total_chunks || 0).toLocaleString();
    }
    const healthRes = await fetch("/api/health");
    if (healthRes.ok) {
      const healthData = await healthRes.json();
      const el = document.getElementById("statEmbedModel");
      if (el && healthData.ollama && healthData.ollama.embed_model) {
        el.textContent = healthData.ollama.embed_model;
      }
    }
  } catch (e) {
    console.error("Gagal memuat stats:", e);
  }
}

async function loadDocuments() {
  try {
    const res = await fetch("/api/admin/documents", { headers: getAuthHeaders() });
    if (!res.ok) {
      if (res.status === 401) logout();
      return;
    }
    const data = await res.json();
    const docs = data.documents || [];

    if (docs.length === 0) {
      docTableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align:center; color: var(--text-muted); padding: 32px;">
            Belum ada dokumen yang diunggah. Silakan unggah dokumen di atas.
          </td>
        </tr>
      `;
      return;
    }

    docTableBody.innerHTML = "";
    docs.forEach(doc => {
      const tr = document.createElement("tr");

      // Format date
      let dateStr = doc.upload_date || "";
      try {
        const d = new Date(doc.upload_date);
        dateStr = d.toLocaleDateString("id-ID", {
          year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
        });
      } catch {}

      tr.innerHTML = `
        <td><strong>📄 ${escapeHtml(doc.name)}</strong></td>
        <td>${dateStr}</td>
        <td>${doc.chunk_count || 0} chunks</td>
        <td>
          <button class="btn-delete" data-id="${doc.id}" data-name="${escapeHtml(doc.name)}">
            Hapus
          </button>
        </td>
      `;
      docTableBody.appendChild(tr);
    });

    // Attach delete listeners
    docTableBody.querySelectorAll(".btn-delete").forEach(btn => {
      btn.addEventListener("click", () => {
        const docId = btn.getAttribute("data-id");
        const docName = btn.getAttribute("data-name");
        deleteDoc(docId, docName);
      });
    });

  } catch (e) {
    docTableBody.innerHTML = `
      <tr>
        <td colspan="4" style="text-align:center; color: var(--danger); padding: 20px;">
          Gagal memuat daftar dokumen: ${escapeHtml(e.message)}
        </td>
      </tr>
    `;
  }
}

async function deleteDoc(docId, docName) {
  if (!confirm(`Yakin ingin menghapus dokumen "${docName}" dari database? Tindakan ini tidak dapat dibatalkan.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/admin/documents/${docId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`Dokumen "${docName}" berhasil dihapus.`);
      loadStats();
      loadDocuments();
    } else {
      showToast(data.detail || "Gagal menghapus dokumen.");
    }
  } catch (e) {
    showToast("Error menghapus: " + e.message);
  }
}

// ── File Upload & Dropzone ────────────────────────────────────
dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length > 0) {
    uploadFile(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    uploadFile(fileInput.files[0]);
  }
});

async function uploadFile(file) {
  const allowed = [".pdf", ".docx", ".txt"];
  const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();

  if (!allowed.includes(ext)) {
    showToast("Format file tidak didukung. Harap upload PDF, DOCX, atau TXT.");
    fileInput.value = "";
    return;
  }

  progressContainer.style.display = "block";
  progressStatus.textContent = `Mengunggah & memproses "${file.name}"...`;
  progressPct.textContent = "30%";
  progressBarFill.style.width = "30%";

  const formData = new FormData();
  formData.append("file", file);

  // Smooth simulated progress while backend chunks & embeds
  let pct = 35;
  const progressTimer = setInterval(() => {
    if (pct < 85) {
      pct += 10;
      progressPct.textContent = `${pct}%`;
      progressBarFill.style.width = `${pct}%`;
      if (pct > 50) progressStatus.textContent = "Membuat embedding & indexing ke vector store...";
    }
  }, 400);

  try {
    const res = await fetch("/api/admin/upload", {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData,
    });

    clearInterval(progressTimer);
    const data = await res.json();

    if (res.ok) {
      progressBarFill.style.width = "100%";
      progressPct.textContent = "100%";
      progressStatus.textContent = "Berhasil!";
      showToast(`Sukses: ${data.message}`);
      loadStats();
      loadDocuments();
      setTimeout(() => {
        progressContainer.style.display = "none";
        progressBarFill.style.width = "0%";
      }, 1500);
    } else {
      progressContainer.style.display = "none";
      showToast(data.detail || "Gagal mengunggah dokumen.");
    }
  } catch (err) {
    clearInterval(progressTimer);
    progressContainer.style.display = "none";
    showToast("Error saat upload: " + err.message);
  } finally {
    fileInput.value = "";
  }
}

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

// Initialize check
verifyAuth();
