"use strict";

const state = {
  token: sessionStorage.getItem("secure_rag_admin_token") || "",
  principal: null,
  config: null,
  documents: [],
  total: 0,
  page: 1,
  pageSize: 10,
  filter: "",
  editingDocumentId: null,
  pollTimer: null
};

const roleDescriptions = {
  admin: "Platform administrators",
  hr: "Human resources team",
  manager: "People and team managers",
  employee: "All company employees"
};

const classificationDescriptions = {
  public: "General material with no internal access restrictions.",
  internal: "Routine company information intended for employees.",
  confidential: "Sensitive business information with limited distribution.",
  restricted: "Highest sensitivity; grant only essential roles."
};

const elements = {
  tokenForm: document.querySelector("#token-form"),
  tokenInput: document.querySelector("#token-input"),
  connectionCard: document.querySelector("#connection-card"),
  adminSession: document.querySelector("#admin-session"),
  adminName: document.querySelector("#admin-name"),
  logoutButton: document.querySelector("#logout-button"),
  dashboard: document.querySelector("#dashboard"),
  uploadForm: document.querySelector("#upload-form"),
  uploadButton: document.querySelector("#upload-button"),
  fileInput: document.querySelector("#file-input"),
  dropZone: document.querySelector("#drop-zone"),
  selectedFile: document.querySelector("#selected-file"),
  selectedFileName: document.querySelector("#selected-file-name"),
  selectedFileSize: document.querySelector("#selected-file-size"),
  clearFile: document.querySelector("#clear-file"),
  documentName: document.querySelector("#document-name"),
  fileRules: document.querySelector("#file-rules"),
  roleOptions: document.querySelector("#role-options"),
  classification: document.querySelector("#classification"),
  classificationHelp: document.querySelector("#classification-help"),
  documentRows: document.querySelector("#document-rows"),
  loadingState: document.querySelector("#loading-state"),
  emptyState: document.querySelector("#empty-state"),
  searchInput: document.querySelector("#search-input"),
  refreshButton: document.querySelector("#refresh-button"),
  pageSummary: document.querySelector("#page-summary"),
  pageNumber: document.querySelector("#page-number"),
  previousPage: document.querySelector("#previous-page"),
  nextPage: document.querySelector("#next-page"),
  accessDialog: document.querySelector("#access-dialog"),
  accessForm: document.querySelector("#access-form"),
  accessDocumentName: document.querySelector("#access-document-name"),
  dialogRoleOptions: document.querySelector("#dialog-role-options"),
  saveAccess: document.querySelector("#save-access"),
  serviceDot: document.querySelector("#service-dot"),
  serviceLabel: document.querySelector("#service-label"),
  serviceDetail: document.querySelector("#service-detail"),
  toastRegion: document.querySelector("#toast-region")
};

function humanFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 1) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return (bytes / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 1) + " " + units[index];
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short", day: "numeric", year: "numeric"
  }).format(new Date(value));
}

function readableError(data, fallback) {
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map(function (item) { return item.msg || "Invalid value"; }).join("; ");
  }
  return fallback;
}

async function api(path, options) {
  const requestOptions = options || {};
  const headers = new Headers(requestOptions.headers || {});
  if (state.token) headers.set("Authorization", "Bearer " + state.token);
  requestOptions.headers = headers;
  const response = await fetch(path, requestOptions);
  let data = null;
  try { data = await response.json(); } catch (_) { data = null; }
  if (!response.ok) {
    if (response.status === 401) disconnect(false);
    const error = new Error(readableError(data, "Request failed with status " + response.status));
    error.status = response.status;
    throw error;
  }
  return data;
}

function toast(title, message, type) {
  const item = document.createElement("div");
  item.className = "toast " + (type || "");
  const symbol = document.createElement("span");
  symbol.textContent = type === "error" ? "!" : type === "success" ? "✓" : "i";
  const copy = document.createElement("span");
  const heading = document.createElement("strong");
  heading.textContent = title;
  const detail = document.createElement("small");
  detail.textContent = message;
  copy.append(heading, detail);
  item.append(symbol, copy);
  elements.toastRegion.append(item);
  setTimeout(function () { item.remove(); }, 5000);
}

async function checkService() {
  try {
    const ready = await fetch("/ready");
    const result = await ready.json();
    const healthy = ready.ok;
    elements.serviceDot.className = "service-dot " + (healthy ? "healthy" : "unhealthy");
    elements.serviceLabel.textContent = healthy ? "All systems ready" : "Service unavailable";
    elements.serviceDetail.textContent = "DB " + result.database + " · Redis " + result.redis;
  } catch (_) {
    elements.serviceDot.className = "service-dot unhealthy";
    elements.serviceLabel.textContent = "Cannot reach service";
    elements.serviceDetail.textContent = "Check the API container";
  }
}

function createRoleOption(role, checked, groupName) {
  const label = document.createElement("label");
  label.className = "role-option" + (checked ? " checked" : "");
  const input = document.createElement("input");
  input.type = "checkbox";
  input.name = groupName;
  input.value = role;
  input.checked = checked;
  input.addEventListener("change", function () {
    label.classList.toggle("checked", input.checked);
  });
  const marker = document.createElement("span");
  marker.className = "role-check";
  const copy = document.createElement("span");
  const title = document.createElement("strong");
  title.textContent = role;
  const detail = document.createElement("small");
  detail.textContent = roleDescriptions[role] || "Authorized role";
  copy.append(title, detail);
  label.append(input, marker, copy);
  return label;
}

function renderConfiguration() {
  elements.roleOptions.replaceChildren();
  elements.dialogRoleOptions.replaceChildren();
  state.config.allowed_roles.forEach(function (role) {
    elements.roleOptions.append(createRoleOption(role, role === "admin", "allowed-role"));
    elements.dialogRoleOptions.append(createRoleOption(role, false, "dialog-role"));
  });
  elements.classification.replaceChildren();
  state.config.classifications.forEach(function (value) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value.charAt(0).toUpperCase() + value.slice(1);
    option.selected = value === "internal";
    elements.classification.append(option);
  });
  elements.fileRules.textContent = "PDF only · maximum " + humanFileSize(state.config.max_upload_size_bytes);
  updateClassificationHelp();
}

function updateClassificationHelp() {
  elements.classificationHelp.textContent = classificationDescriptions[elements.classification.value] || "Choose the document sensitivity.";
}

function selectedRoles(container) {
  return Array.from(container.querySelectorAll("input:checked")).map(function (input) { return input.value; });
}

function setConnected(connected) {
  elements.dashboard.classList.toggle("locked", !connected);
  elements.connectionCard.classList.toggle("hidden", connected);
  elements.adminSession.classList.toggle("hidden", !connected);
}

async function connect(token) {
  state.token = token.trim();
  const principal = await api("/v1/auth/me");
  if (!principal.roles.includes("admin")) {
    state.token = "";
    throw new Error("This token is valid but does not contain the admin role.");
  }
  state.principal = principal;
  sessionStorage.setItem("secure_rag_admin_token", state.token);
  elements.adminName.textContent = principal.user_id;
  const values = await Promise.all([api("/v1/documents/config"), loadDocuments(false)]);
  state.config = values[0];
  renderConfiguration();
  setConnected(true);
  schedulePolling();
}

function disconnect(showMessage) {
  state.token = "";
  state.principal = null;
  state.documents = [];
  sessionStorage.removeItem("secure_rag_admin_token");
  clearTimeout(state.pollTimer);
  setConnected(false);
  elements.tokenInput.value = "";
  renderDocuments();
  if (showMessage !== false) toast("Session disconnected", "The token was removed from this browser tab.", "success");
}

function setLoading(loading) {
  elements.loadingState.classList.toggle("hidden", !loading);
  elements.refreshButton.disabled = loading;
}

async function loadDocuments(showSuccess) {
  setLoading(true);
  try {
    const result = await api("/v1/documents?limit=100&offset=0");
    state.documents = result.items;
    state.total = result.total;
    renderDocuments();
    if (showSuccess) toast("Library refreshed", "Document statuses are up to date.", "success");
    return result;
  } finally {
    setLoading(false);
  }
}

function updateMetrics() {
  const count = function (status) { return state.documents.filter(function (doc) { return doc.status === status; }).length; };
  document.querySelector("#metric-total").textContent = String(state.total);
  document.querySelector("#metric-active").textContent = String(count("active"));
  document.querySelector("#metric-processing").textContent = String(count("processing"));
  document.querySelector("#metric-attention").textContent = String(count("failed") + count("quarantined"));
}

function roleBadges(roles) {
  const wrap = document.createElement("div");
  wrap.className = "role-badges";
  roles.forEach(function (role) {
    const badge = document.createElement("span");
    badge.className = "badge " + role;
    badge.textContent = role;
    wrap.append(badge);
  });
  return wrap;
}

function actionButton(label, text, handler, disabled) {
  const button = document.createElement("button");
  button.className = "icon-button";
  button.type = "button";
  button.title = label;
  button.setAttribute("aria-label", label);
  button.textContent = text;
  button.disabled = Boolean(disabled);
  button.addEventListener("click", handler);
  return button;
}

function renderDocuments() {
  const query = state.filter.toLowerCase();
  const filtered = state.documents.filter(function (doc) {
    return !query || doc.name.toLowerCase().includes(query) || doc.original_filename.toLowerCase().includes(query);
  });
  const maxPage = Math.max(1, Math.ceil(filtered.length / state.pageSize));
  state.page = Math.min(state.page, maxPage);
  const start = (state.page - 1) * state.pageSize;
  const visible = filtered.slice(start, start + state.pageSize);
  elements.documentRows.replaceChildren();

  visible.forEach(function (doc) {
    const row = document.createElement("tr");
    const documentColumn = document.createElement("td");
    const documentCell = document.createElement("div");
    documentCell.className = "document-cell";
    const icon = document.createElement("span");
    icon.className = "document-icon";
    icon.textContent = "PDF";
    const names = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = doc.name;
    name.title = doc.name;
    const filename = document.createElement("small");
    filename.textContent = doc.original_filename + " · " + humanFileSize(doc.size_bytes);
    names.append(name, filename);
    documentCell.append(icon, names);
    documentColumn.append(documentCell);

    const rolesColumn = document.createElement("td");
    rolesColumn.append(roleBadges(doc.allowed_roles));
    const classificationColumn = document.createElement("td");
    const classification = document.createElement("span");
    classification.className = "classification";
    classification.textContent = doc.classification;
    classificationColumn.append(classification);
    const statusColumn = document.createElement("td");
    const status = document.createElement("span");
    status.className = "status-badge status-" + doc.status;
    status.textContent = doc.status;
    statusColumn.append(status);
    const dateColumn = document.createElement("td");
    dateColumn.textContent = formatDate(doc.created_at);
    const actionColumn = document.createElement("td");
    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.append(actionButton("Edit permissions", "✎", function () { openAccessDialog(doc); }, doc.status === "inactive"));
    if (doc.status === "failed" || doc.status === "quarantined") {
      actions.append(actionButton("Retry processing", "↻", function () { retryDocument(doc); }, false));
    }
    if (doc.status === "inactive") {
      const activate = actionButton("Activate document", "Activate", function () { activateDocument(doc); }, false);
      activate.classList.add("activate-action", "lifecycle-button");
      actions.append(activate);
    } else {
      const deactivate = actionButton("Deactivate document", "Deactivate", function () { deactivateDocument(doc); }, false);
      deactivate.classList.add("lifecycle-button");
      actions.append(deactivate);
    }
    const permanentDelete = actionButton("Permanently delete document", "Delete permanently", function () { permanentlyDeleteDocument(doc); }, false);
    permanentDelete.classList.add("danger-action", "permanent-delete-button");
    actions.append(permanentDelete);
    actionColumn.append(actions);
    row.append(documentColumn, rolesColumn, classificationColumn, statusColumn, dateColumn, actionColumn);
    elements.documentRows.append(row);
  });

  elements.emptyState.classList.toggle("hidden", visible.length > 0 || !elements.loadingState.classList.contains("hidden"));
  elements.pageSummary.textContent = filtered.length === 0 ? "Showing 0 documents" : "Showing " + (start + 1) + "–" + Math.min(start + state.pageSize, filtered.length) + " of " + filtered.length + (state.total > state.documents.length ? " (first 100 loaded)" : "");
  elements.pageNumber.textContent = "Page " + state.page;
  elements.previousPage.disabled = state.page <= 1;
  elements.nextPage.disabled = state.page >= maxPage;
  updateMetrics();
}

function showSelectedFile(file) {
  if (!file) {
    elements.selectedFile.classList.add("hidden");
    return;
  }
  elements.selectedFileName.textContent = file.name;
  elements.selectedFileSize.textContent = humanFileSize(file.size);
  elements.selectedFile.classList.remove("hidden");
  if (!elements.documentName.value.trim()) {
    elements.documentName.value = file.name.replace(/\.pdf$/i, "").replace(/[_-]+/g, " ");
  }
}

function validateFile(file) {
  if (!file || !file.name.toLowerCase().endsWith(".pdf")) throw new Error("Choose a PDF document.");
  if (state.config && file.size > state.config.max_upload_size_bytes) {
    throw new Error("This PDF exceeds the " + humanFileSize(state.config.max_upload_size_bytes) + " upload limit.");
  }
}

function resetUploadForm() {
  elements.uploadForm.reset();
  elements.selectedFile.classList.add("hidden");
  elements.roleOptions.querySelectorAll("input").forEach(function (input) {
    input.checked = input.value === "admin";
    input.closest(".role-option").classList.toggle("checked", input.checked);
  });
  elements.classification.value = "internal";
  updateClassificationHelp();
}

async function uploadDocument(event) {
  event.preventDefault();
  const file = elements.fileInput.files[0];
  const roles = selectedRoles(elements.roleOptions);
  try {
    validateFile(file);
    if (roles.length === 0) throw new Error("Select at least one allowed role.");
    elements.uploadButton.disabled = true;
    elements.uploadButton.querySelector("span").textContent = "Uploading…";
    const body = new FormData();
    body.append("file", file);
    body.append("name", elements.documentName.value.trim());
    body.append("allowed_roles", JSON.stringify(roles));
    body.append("classification", elements.classification.value);
    const result = await api("/v1/documents", { method: "POST", body: body });
    toast("Document accepted", "Processing started for document " + result.document_id.slice(0, 8) + "…", "success");
    resetUploadForm();
    await loadDocuments(false);
    document.querySelector("#library-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    schedulePolling();
  } catch (error) {
    toast("Upload failed", error.message, "error");
  } finally {
    elements.uploadButton.disabled = false;
    elements.uploadButton.querySelector("span").textContent = "Upload and process";
  }
}

function openAccessDialog(doc) {
  state.editingDocumentId = doc.id;
  elements.accessDocumentName.textContent = doc.name;
  elements.dialogRoleOptions.querySelectorAll("input").forEach(function (input) {
    input.checked = doc.allowed_roles.includes(input.value);
    input.closest(".role-option").classList.toggle("checked", input.checked);
  });
  elements.accessDialog.showModal();
}

async function saveAccess(event) {
  event.preventDefault();
  const roles = selectedRoles(elements.dialogRoleOptions);
  if (roles.length === 0) {
    toast("Permission required", "Select at least one allowed role.", "error");
    return;
  }
  elements.saveAccess.disabled = true;
  try {
    await api("/v1/documents/" + state.editingDocumentId + "/access", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ allowed_roles: roles })
    });
    elements.accessDialog.close();
    toast("Permissions updated", "The new roles apply to retrieval immediately.", "success");
    await loadDocuments(false);
  } catch (error) {
    toast("Update failed", error.message, "error");
  } finally {
    elements.saveAccess.disabled = false;
  }
}

async function retryDocument(doc) {
  try {
    await api("/v1/documents/" + doc.id + "/process", { method: "POST" });
    toast("Processing restarted", doc.name + " has returned to the ingestion queue.", "success");
    await loadDocuments(false);
    schedulePolling();
  } catch (error) {
    toast("Retry failed", error.message, "error");
  }
}

async function deactivateDocument(doc) {
  if (!window.confirm("Deactivate “" + doc.name + "”? It will immediately disappear from retrieval.")) return;
  try {
    await api("/v1/documents/" + doc.id, { method: "DELETE" });
    toast("Document deactivated", doc.name + " is no longer available to RAG.", "success");
    await loadDocuments(false);
  } catch (error) {
    toast("Deactivation failed", error.message, "error");
  }
}

async function activateDocument(doc) {
  try {
    const result = await api("/v1/documents/" + doc.id + "/activate", { method: "POST" });
    if (result.reprocessing) {
      toast("Document processing", doc.name + " had no reusable vectors and is being processed again.", "success");
      schedulePolling();
    } else {
      toast("Document activated", doc.name + " is available to its allowed roles again.", "success");
    }
    await loadDocuments(false);
    schedulePolling();
  } catch (error) {
    toast("Activation failed", error.message, "error");
  }
}

async function permanentlyDeleteDocument(doc) {
  const warning = "Permanently delete “" + doc.name + "”?\n\nThis removes its PDF, vector chunks, permissions, and security findings. This action cannot be undone.";
  if (!window.confirm(warning)) return;
  try {
    const result = await api("/v1/documents/" + doc.id + "/permanent", { method: "DELETE" });
    state.documents = state.documents.filter(function (item) { return item.id !== doc.id; });
    state.total = Math.max(0, state.total - 1);
    renderDocuments();
    const message = result.file_deleted
      ? doc.name + " and all indexed data were permanently removed."
      : doc.name + " was removed from RAG; stored-file cleanup requires administrator attention.";
    toast("Document permanently deleted", message, result.file_deleted ? "success" : "error");
  } catch (error) {
    toast("Permanent deletion failed", error.message, "error");
  }
}

function schedulePolling() {
  clearTimeout(state.pollTimer);
  if (!state.token || !state.documents.some(function (doc) { return doc.status === "processing"; })) return;
  state.pollTimer = setTimeout(async function () {
    try { await loadDocuments(false); } catch (_) { return; }
    schedulePolling();
  }, 8000);
}

elements.tokenForm.addEventListener("submit", async function (event) {
  event.preventDefault();
  const button = elements.tokenForm.querySelector("button");
  button.disabled = true;
  try {
    await connect(elements.tokenInput.value);
    toast("Admin verified", "Document controls are now unlocked.", "success");
  } catch (error) {
    disconnect(false);
    toast("Connection failed", error.message, "error");
  } finally {
    button.disabled = false;
  }
});

elements.logoutButton.addEventListener("click", function () { disconnect(true); });
elements.uploadForm.addEventListener("submit", uploadDocument);
elements.fileInput.addEventListener("change", function () {
  try { validateFile(elements.fileInput.files[0]); showSelectedFile(elements.fileInput.files[0]); }
  catch (error) { elements.fileInput.value = ""; showSelectedFile(null); toast("Invalid file", error.message, "error"); }
});
elements.clearFile.addEventListener("click", function (event) {
  event.stopPropagation(); elements.fileInput.value = ""; showSelectedFile(null);
});
elements.dropZone.addEventListener("keydown", function (event) {
  if (event.key === "Enter" || event.key === " ") { event.preventDefault(); elements.fileInput.click(); }
});
["dragenter", "dragover"].forEach(function (name) {
  elements.dropZone.addEventListener(name, function (event) { event.preventDefault(); elements.dropZone.classList.add("dragover"); });
});
["dragleave", "drop"].forEach(function (name) {
  elements.dropZone.addEventListener(name, function (event) { event.preventDefault(); elements.dropZone.classList.remove("dragover"); });
});
elements.dropZone.addEventListener("drop", function (event) {
  if (!event.dataTransfer.files.length) return;
  try {
    validateFile(event.dataTransfer.files[0]);
    elements.fileInput.files = event.dataTransfer.files;
    showSelectedFile(event.dataTransfer.files[0]);
  } catch (error) { toast("Invalid file", error.message, "error"); }
});
elements.classification.addEventListener("change", updateClassificationHelp);
elements.refreshButton.addEventListener("click", async function () {
  try { await loadDocuments(true); schedulePolling(); } catch (error) { toast("Refresh failed", error.message, "error"); }
});
elements.searchInput.addEventListener("input", function () { state.filter = elements.searchInput.value.trim(); state.page = 1; renderDocuments(); });
elements.previousPage.addEventListener("click", function () { state.page -= 1; renderDocuments(); });
elements.nextPage.addEventListener("click", function () { state.page += 1; renderDocuments(); });
elements.accessForm.addEventListener("submit", saveAccess);
document.querySelectorAll("[data-scroll]").forEach(function (button) {
  button.addEventListener("click", function () {
    document.querySelectorAll(".nav-item").forEach(function (item) { item.classList.remove("active"); });
    button.classList.add("active");
    document.querySelector("#" + button.dataset.scroll).scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

checkService();
if (state.token) {
  connect(state.token).catch(function (error) {
    disconnect(false);
    toast("Session expired", error.message, "error");
  });
} else {
  setConnected(false);
  renderDocuments();
}
