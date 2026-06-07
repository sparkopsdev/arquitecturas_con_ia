let token = localStorage.getItem("paresToken") || "";
let role = localStorage.getItem("paresRole") || "";
let username = localStorage.getItem("paresUsername") || "";

const sessionLabel = document.getElementById("sessionLabel");
const adminOutput = document.getElementById("adminOutput");
const answerOutput = document.getElementById("answerOutput");
const factsList = document.getElementById("factsList");

function refreshSession() {
  sessionLabel.textContent = token ? `Sesion: ${username} (${role})` : "Sin sesion";
}

function headers(json = true) {
  const result = {};
  if (json) result["Content-Type"] = "application/json";
  if (token) result.Authorization = `Bearer ${token}`;
  return result;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status}: ${text}`);
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return response.json();
  return response.text();
}

async function login(nextRole) {
  const data = await api("/api/auth/demo-login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role: nextRole })
  });
  token = data.access_token;
  role = data.role;
  username = data.username;
  localStorage.setItem("paresToken", token);
  localStorage.setItem("paresRole", role);
  localStorage.setItem("paresUsername", username);
  refreshSession();
}

function showJson(target, value) {
  target.textContent = JSON.stringify(value, null, 2);
}

function renderFacts(items) {
  if (!items.length) {
    factsList.innerHTML = "<p>No hay hechos para mostrar. Carga los documentos demo primero.</p>";
    return;
  }
  factsList.innerHTML = items.map(item => {
    const badges = [...item.people, ...item.places, ...item.ships]
      .slice(0, 8)
      .map(x => `<span class="badge">${x}</span>`).join("");
    return `<article class="fact">
      <h3>${item.event_name}</h3>
      <p><strong>Fecha:</strong> ${item.date_text || "No identificada"} · <strong>Confianza:</strong> ${item.confidence}</p>
      <p>${item.summary}</p>
      <p><small>Documento ${item.document_id}: ${item.document_title}</small></p>
      <div class="badges">${badges}</div>
    </article>`;
  }).join("");
}

async function seedSamples() {
  const data = await api("/api/admin/ingest/samples", {
    method: "POST",
    headers: headers()
  });
  showJson(adminOutput, data);
}

async function loadAudit() {
  const data = await api("/api/admin/audit", { headers: headers(false) });
  showJson(adminOutput, data);
}

async function loadModel() {
  const data = await api("/api/admin/model-control", { headers: headers(false) });
  showJson(adminOutput, data);
}

async function uploadDocument() {
  const input = document.getElementById("fileInput");
  if (!input.files.length) {
    adminOutput.textContent = "Selecciona un fichero primero.";
    return;
  }
  const form = new FormData();
  form.append("file", input.files[0]);
  const response = await fetch("/api/admin/documents", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form
  });
  if (!response.ok) throw new Error(await response.text());
  showJson(adminOutput, await response.json());
}

async function searchFacts() {
  const q = document.getElementById("searchInput").value || "San Miguel";
  const data = await api(`/api/search?q=${encodeURIComponent(q)}`, { headers: headers(false) });
  renderFacts(data);
}

async function loadFacts() {
  const data = await api("/api/facts", { headers: headers(false) });
  renderFacts(data);
}

async function ask(format) {
  const question = document.getElementById("questionInput").value;
  const response = await fetch("/api/query", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ question, output_format: format, top_k: 6 })
  });
  if (!response.ok) throw new Error(await response.text());
  if (format === "pdf") {
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "respuesta-pares-ai.pdf";
    link.click();
    URL.revokeObjectURL(url);
    answerOutput.textContent = "PDF generado y descargado.";
  } else {
    const data = await response.json();
    answerOutput.textContent = `${data.answer}\n\nFuentes:\n` + data.sources.map(s => `- ${s.document_title} / chunk ${s.chunk_id} / score ${s.score}`).join("\n");
  }
}

function bind(id, fn) {
  document.getElementById(id).addEventListener("click", () => fn().catch(err => {
    console.error(err);
    alert(err.message);
  }));
}

bind("loginAdmin", () => login("admin"));
bind("loginUser", () => login("user"));
bind("seedSamples", seedSamples);
bind("loadAudit", loadAudit);
bind("loadModel", loadModel);
bind("uploadBtn", uploadDocument);
bind("searchBtn", searchFacts);
bind("factsBtn", loadFacts);
bind("askBtn", () => ask("text"));
bind("askPdfBtn", () => ask("pdf"));

refreshSession();
