/* 灵犀智能助手 —— 前端逻辑 */

const SOURCES_MARKER = "===SOURCES===";
const $ = (sel) => document.querySelector(sel);

const VIEW_META = {
  home: { title: "首页", sub: "灵犀智能助手 · 产品落地页" },
  agent: { title: "智能对话", sub: "与灵犀自由对话，支持工具调用与偏好记忆" },
  kb: { title: "知识库问答", sub: "上传文档，获得带引用溯源的答案" },
};

function goToView(view) {
  document.querySelectorAll(".nav-item").forEach((i) =>
    i.classList.toggle("active", i.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  const target = document.getElementById("view-" + view);
  if (target) target.classList.add("active");
  // 落地页（home）隐藏侧边栏与顶栏，应用视图显示
  document.body.classList.toggle("landing", view === "home");
  const meta = VIEW_META[view] || VIEW_META.home;
  $("#view-title").textContent = meta.title;
  $("#view-subtitle").textContent = meta.sub || "";
}

/* ---------- 鉴权 ---------- */
(function checkAuth() {
  const token = localStorage.getItem("token");
  if (!token) {
    window.location.href = "/login.html";
    return;
  }
  const username = localStorage.getItem("username") || "用户";
  $("#display-name").textContent = username;
  $("#user-avatar").textContent = username.charAt(0).toUpperCase();
})();

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("username");
  window.location.href = "/login.html";
}

/* ---------- 工具 ---------- */
function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.classList.add("hidden"), 3000);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) {
  return escapeHtml(s).replace(/`/g, "&#96;");
}

/* ---------- 导航 ---------- */
document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => goToView(item.dataset.view));
});
const brandEl = document.getElementById("brand");
if (brandEl) brandEl.addEventListener("click", () => goToView("home"));

/* ---------- 健康检查 ---------- */
async function refreshHealth() {
  const badge = $("#health-badge");
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const h = await res.json();
    const deepseekOk = h.deepseek?.configured;
    const ok = h.status === "ok" && deepseekOk;
    badge.textContent = ok ? "系统正常" : "部分异常";
    badge.className = "badge " + (ok ? "badge-ok" : "badge-warn");
  } catch (e) {
    badge.textContent = "服务异常";
    badge.className = "badge badge-err";
  }
}

/* ---------- 消息渲染 ---------- */
function hideWelcome(container) {
  const w = container.querySelector(".welcome");
  if (w) w.remove();
}

function addMessage(container, role, content) {
  hideWelcome(container);
  const div = document.createElement("div");
  div.className = "msg " + (role === "user" ? "user" : "bot");
  div.innerHTML = `<div class="avatar">${role === "user" ? "我" : "✦"}</div>
                   <div class="msg-content">${escapeHtml(content)}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div.querySelector(".msg-content");
}

function addBotPlaceholder(container) {
  hideWelcome(container);
  const div = document.createElement("div");
  div.className = "msg bot loading";
  div.innerHTML = `<div class="avatar">✦</div><div class="msg-content"></div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div.querySelector(".msg-content");
}

/* ---------- 快捷提问 ---------- */
function sendQuick(view, text) {
  if (view === "agent") {
    $("#agent-input").value = text;
    sendAgentMessage();
  } else {
    $("#kb-input").value = text;
    sendKbQuestion();
  }
}

/* ============================================================
   智能对话
   ============================================================ */
const agentMessages = $("#agent-messages");
const agentInput = $("#agent-input");
const agentSend = $("#agent-send");
let agentSessionId = "sess-" + Math.random().toString(36).slice(2, 9);
let agentStreaming = false;

async function sendAgentMessage() {
  const message = agentInput.value.trim();
  if (!message || agentStreaming) return;
  agentInput.value = "";
  agentInput.style.height = "auto";
  agentStreaming = true;
  agentSend.disabled = true;
  agentInput.disabled = true;

  addMessage(agentMessages, "user", message);
  const bubble = addBotPlaceholder(agentMessages);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Authorization": "Bearer " + localStorage.getItem("token"),
      },
      body: JSON.stringify({ message, session_id: agentSessionId }),
    });

    if (res.status === 401) { logout(); return; }
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "", content = "", firstToken = true;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === "token") {
            if (firstToken) { bubble.textContent = ""; firstToken = false; }
            content += data.content;
            bubble.textContent = content;
          } else if (data.type === "done") {
            if (firstToken) bubble.textContent = content || "(空响应)";
          } else if (data.type === "error") {
            bubble.textContent = "出错了：" + (data.content || "未知错误");
            bubble.style.color = "#b0696e";
          }
          agentMessages.scrollTop = agentMessages.scrollHeight;
        } catch (e) { /* 忽略无法解析的行 */ }
      }
    }
  } catch (err) {
    bubble.textContent = "请求失败：" + err.message;
    bubble.style.color = "#b0696e";
  } finally {
    agentStreaming = false;
    agentSend.disabled = false;
    agentInput.disabled = false;
    agentInput.focus();
  }
}

agentSend.addEventListener("click", sendAgentMessage);
agentInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendAgentMessage(); }
});
agentInput.addEventListener("input", () => {
  agentInput.style.height = "auto";
  agentInput.style.height = Math.min(agentInput.scrollHeight, 120) + "px";
});

/* ============================================================
   知识库问答
   ============================================================ */
const kbMessages = $("#kb-messages");
const kbInput = $("#kb-input");
const kbSend = $("#kb-send");

function renderSources(container, sources) {
  if (!sources || !sources.length) {
    container.innerHTML = `<div class="no-sources">未检索到相关内容</div>`;
    return;
  }
  const cards = sources.map((s) => `
    <div class="source-card">
      <div class="src-head"><span>📄 ${escapeHtml(s.source)}</span><span>相似度 ${s.score.toFixed(4)}</span></div>
      <div class="src-text">${escapeHtml(s.text)}</div>
    </div>`).join("");
  container.innerHTML = `<details class="sources"><summary>引用来源（${sources.length} 条）</summary>${cards}</details>`;
}

async function sendKbQuestion() {
  const question = kbInput.value.trim();
  if (!question || kbInput.disabled) return;
  kbInput.value = "";
  kbSend.disabled = true;
  kbInput.disabled = true;

  addMessage(kbMessages, "user", question);
  const bubble = addBotPlaceholder(kbMessages);

  try {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "", done = false;

    while (!done) {
      const { value, done: d } = await reader.read();
      done = d;
      buffer += decoder.decode(value, { stream: !done });
      const markerIdx = buffer.indexOf(SOURCES_MARKER);
      if (markerIdx !== -1) {
        bubble.textContent = buffer.slice(0, markerIdx);
        const sourcesJson = buffer.slice(markerIdx + SOURCES_MARKER.length);
        const srcContainer = document.createElement("div");
        bubble.parentElement.appendChild(srcContainer);
        try { renderSources(srcContainer, JSON.parse(sourcesJson)); }
        catch { srcContainer.innerHTML = `<div class="no-sources">来源解析失败</div>`; }
        done = true;
      } else {
        bubble.textContent = buffer;
      }
      kbMessages.scrollTop = kbMessages.scrollHeight;
    }
  } catch (e) {
    bubble.textContent = "⚠️ " + e.message;
    bubble.style.color = "#b0696e";
  } finally {
    kbSend.disabled = false;
    kbInput.disabled = false;
    kbInput.focus();
  }
}

kbSend.addEventListener("click", sendKbQuestion);
kbInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); sendKbQuestion(); }
});

/* ============================================================
   文档管理
   ============================================================ */
async function refreshDocs() {
  const list = $("#doc-list");
  try {
    const res = await fetch("/api/documents");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const { documents } = await res.json();
    $("#doc-count").textContent = documents.length + " 篇";
    if (!documents.length) {
      list.innerHTML = '<div class="doc-empty">暂无文档，请先上传</div>';
      return;
    }
    list.innerHTML = documents.map((d) => `
      <div class="doc-card">
        <div class="doc-icon">${fileIcon(d.filename)}</div>
        <div class="doc-info">
          <div class="doc-name" title="${escapeHtml(d.filename)}">${escapeHtml(d.filename)}</div>
          <div class="doc-meta">${d.chunk_count} 切片 · ${escapeHtml(d.uploaded_at)}</div>
        </div>
        <button class="doc-del" onclick="deleteDoc('${d.doc_id}', '${escapeAttr(d.filename)}')" title="删除">✕</button>
      </div>`).join("");
  } catch (e) {
    list.innerHTML = `<div class="doc-empty">加载失败：${escapeHtml(e.message)}</div>`;
  }
}

function fileIcon(name) {
  const ext = name.split(".").pop().toLowerCase();
  const map = { pdf: "📕", md: "📘", txt: "📄", csv: "📊", xlsx: "📗" };
  return map[ext] || "📄";
}

async function deleteDoc(docId, filename) {
  if (!confirm(`确定删除文档「${filename}」？将从向量库移除全部切片。`)) return;
  try {
    const res = await fetch(`/api/documents/${docId}`, { method: "DELETE" });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
    toast("已删除 " + filename);
    refreshDocs(); refreshHealth();
  } catch (e) {
    toast("删除失败：" + e.message, true);
  }
}

async function uploadFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  try {
    const res = await fetch("/api/documents/upload", { method: "POST", body: fd });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
    const data = await res.json();
    toast("「" + data.filename + "」入库完成：" + data.chunk_count + " 个切片");
    refreshDocs(); refreshHealth();
  } catch (e) {
    toast("上传失败：" + e.message, true);
  }
}

function bindUpload() {
  const zone = $("#drop-zone");
  const input = $("#file-input");
  $("#pick-file").addEventListener("click", (e) => { e.stopPropagation(); input.click(); });
  zone.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    if (input.files.length) uploadFile(input.files[0]);
    input.value = "";
  });
  ["dragover", "dragenter"].forEach((ev) =>
    zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("dragover"); }));
  ["dragleave", "drop"].forEach((ev) =>
    zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("dragover"); }));
  zone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });
}

/* ---------- 初始化 ---------- */
bindUpload();
refreshHealth();
refreshDocs();
setInterval(refreshHealth, 30000);
