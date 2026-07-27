const API_ROOT = "/webui/plugin-market/api";

const state = {
  plugins: [],
  selectedPlugin: null,
  installing: new Set(),
  installEnabled: false,
};

const elements = {
  summary: document.querySelector("#market-summary"),
  refresh: document.querySelector("#refresh-button"),
  search: document.querySelector("#search-input"),
  clearSearch: document.querySelector("#clear-search"),
  category: document.querySelector("#category-select"),
  sort: document.querySelector("#sort-select"),
  status: document.querySelector("#status-panel"),
  statusTitle: document.querySelector("#status-title"),
  statusMessage: document.querySelector("#status-message"),
  results: document.querySelector("#results-section"),
  count: document.querySelector("#results-count"),
  activeFilter: document.querySelector("#active-filter"),
  grid: document.querySelector("#plugin-grid"),
  empty: document.querySelector("#empty-state"),
  dialog: document.querySelector("#install-dialog"),
  dialogMessage: document.querySelector("#dialog-message"),
  dialogMeta: document.querySelector("#dialog-plugin-meta"),
  installToken: document.querySelector("#install-token"),
  installTokenField: document.querySelector("#install-token-field"),
  confirmInstall: document.querySelector("#confirm-install"),
  toastRegion: document.querySelector("#toast-region"),
};

function applyParentTheme() {
  try {
    const parentRoot = window.parent.document.documentElement;
    const apply = () => {
      const theme = parentRoot.dataset.theme;
      document.documentElement.dataset.theme = theme === "dark" ? "dark" : "light";
    };
    apply();
    new MutationObserver(apply).observe(parentRoot, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
  } catch {
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }
}

function authToken() {
  try {
    return window.parent.sessionStorage.getItem("neo_token") || sessionStorage.getItem("neo_token");
  } catch {
    return sessionStorage.getItem("neo_token");
  }
}

async function request(path, options = {}) {
  const token = authToken();
  if (!token) {
    throw new Error("登录状态已失效，请刷新 WebUI 并重新登录。");
  }
  const headers = new Headers(options.headers || {});
  headers.set("X-API-Key", token);
  if (options.body) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_ROOT}${path}`, {...options, headers});
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`服务器返回了无效响应（HTTP ${response.status}）`);
  }
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || `请求失败（HTTP ${response.status}）`);
  }
  if (payload.code !== 200) {
    throw new Error(payload.message || "请求失败");
  }
  return payload.data;
}

function setLoading(title, message) {
  elements.status.hidden = false;
  elements.status.className = "status-panel loading";
  elements.status.querySelector(".status-icon").textContent = "progress_activity";
  elements.statusTitle.textContent = title;
  elements.statusMessage.textContent = message;
  elements.results.hidden = true;
}

function setError(error) {
  elements.status.hidden = false;
  elements.status.className = "status-panel error";
  elements.status.querySelector(".status-icon").textContent = "error";
  elements.statusTitle.textContent = "无法读取插件市场";
  elements.statusMessage.textContent = error.message || String(error);
  elements.results.hidden = true;
}

async function loadPlugins(forceRefresh = false) {
  setLoading("正在读取市场", forceRefresh ? "正在获取最新市场数据" : "正在加载全部插件");
  elements.refresh.classList.add("loading");
  elements.refresh.disabled = true;
  try {
    const data = await request(`/plugins${forceRefresh ? "?refresh=true" : ""}`);
    state.plugins = Array.isArray(data.plugins) ? data.plugins : [];
    state.installEnabled = data.install_enabled === true;
    elements.summary.textContent = `已收录 ${state.plugins.length} 个插件`;
    populateCategories();
    renderPlugins();
    if (forceRefresh) {
      showToast(`市场已刷新，共 ${state.plugins.length} 个插件`, "success");
    }
  } catch (error) {
    setError(error);
  } finally {
    elements.refresh.classList.remove("loading");
    elements.refresh.disabled = false;
  }
}

function populateCategories() {
  const current = elements.category.value;
  const categories = [...new Set(state.plugins.flatMap((plugin) => plugin.categories || []))]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "zh-CN"));
  elements.category.replaceChildren(new Option("全部分类", ""));
  for (const category of categories) {
    elements.category.add(new Option(category, category));
  }
  if (categories.includes(current)) {
    elements.category.value = current;
  }
}

function normalizedSearchText(plugin) {
  return [
    plugin.plugin_id,
    plugin.display_name,
    plugin.summary,
    plugin.description,
    plugin.owner_login,
    plugin.owner_display_name,
    ...(plugin.tags || []),
    ...(plugin.categories || []),
  ].join(" ").toLocaleLowerCase("zh-CN");
}

function visiblePlugins() {
  const query = elements.search.value.trim().toLocaleLowerCase("zh-CN");
  const tokens = query.split(/\s+/).filter(Boolean);
  const category = elements.category.value;
  const filtered = state.plugins.filter((plugin) => {
    if (category && !(plugin.categories || []).includes(category)) return false;
    const haystack = normalizedSearchText(plugin);
    return tokens.every((token) => haystack.includes(token));
  });
  const sort = elements.sort.value;
  filtered.sort((a, b) => {
    if (sort === "downloads") {
      return Number(b.downloads_count || 0) - Number(a.downloads_count || 0)
        || a.display_name.localeCompare(b.display_name, "zh-CN");
    }
    if (sort === "rating") {
      return Number(b.rating_avg || 0) - Number(a.rating_avg || 0)
        || a.display_name.localeCompare(b.display_name, "zh-CN");
    }
    return a.display_name.localeCompare(b.display_name, "zh-CN");
  });
  return filtered;
}

function renderPlugins() {
  const plugins = visiblePlugins();
  elements.status.hidden = true;
  elements.results.hidden = false;
  elements.clearSearch.hidden = elements.search.value.length === 0;
  elements.count.textContent = `${plugins.length} 个插件`;

  const filters = [];
  if (elements.search.value.trim()) filters.push(`搜索：${elements.search.value.trim()}`);
  if (elements.category.value) filters.push(`分类：${elements.category.value}`);
  elements.activeFilter.textContent = filters.join(" · ");
  elements.empty.hidden = plugins.length !== 0;
  elements.grid.replaceChildren(...plugins.map(createPluginCard));
}

function createPluginCard(plugin) {
  const card = node("article", "plugin-card");
  const heading = node("div", "plugin-heading");
  const avatar = node("div", "plugin-avatar");
  const initial = (plugin.display_name || plugin.plugin_id || "P").trim().slice(0, 1).toUpperCase();
  if (isSafeHttpUrl(plugin.icon_url)) {
    const image = document.createElement("img");
    image.src = plugin.icon_url;
    image.alt = "";
    image.loading = "lazy";
    image.addEventListener("error", () => avatar.replaceChildren(document.createTextNode(initial)));
    avatar.append(image);
  } else {
    avatar.textContent = initial;
  }

  const titleWrap = node("div", "plugin-title-wrap");
  const title = node("h2", "plugin-name", plugin.display_name || plugin.plugin_id);
  title.title = plugin.display_name || plugin.plugin_id;
  const id = node("code", "plugin-id", plugin.plugin_id);
  id.title = plugin.plugin_id;
  titleWrap.append(title, id);
  heading.append(avatar, titleWrap);

  const body = node("div", "plugin-body");
  const summary = node("p", "plugin-summary", plugin.summary || plugin.description || "暂无简介");
  summary.title = plugin.summary || plugin.description || "暂无简介";
  const meta = node("div", "plugin-meta");
  meta.append(chip(`v${plugin.latest_version || "暂无版本"}`, "version"));
  meta.append(iconChip("download", formatNumber(plugin.downloads_count || 0)));
  if (Number(plugin.rating_avg || 0) > 0) {
    meta.append(iconChip("star", Number(plugin.rating_avg).toFixed(1)));
  }
  const tags = node("div", "plugin-tags");
  for (const tag of (plugin.tags || []).slice(0, 4)) {
    const tagNode = node("span", "tag-chip", tag);
    tagNode.title = tag;
    tags.append(tagNode);
  }
  body.append(summary, meta, tags);

  const footer = node("footer", "plugin-footer");
  const owner = node(
    "span",
    "owner",
    `作者：${plugin.owner_display_name || plugin.owner_login || "未知"}`,
  );
  const actions = node("div", "card-actions");
  const repo = plugin.repository_url || plugin.homepage;
  if (isSafeHttpUrl(repo)) {
    const link = node("a", "repo-link");
    link.href = repo;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.title = "查看项目主页";
    link.setAttribute("aria-label", "查看项目主页");
    link.append(materialIcon("open_in_new"));
    actions.append(link);
  }
  const action = node("button", "button primary install-button");
  action.type = "button";
  action.dataset.pluginId = plugin.plugin_id;
  if (plugin.has_config) {
    action.append(materialIcon("settings"), document.createTextNode("配置"));
    action.onclick = () => openPluginConfig(plugin.plugin_id);
  } else if (plugin.installed) {
    action.disabled = true;
    action.append(materialIcon("check"), document.createTextNode("已安装"));
  } else if (!state.installEnabled) {
    action.disabled = true;
    action.append(materialIcon("block"), document.createTextNode("安装已关闭"));
  } else {
    action.disabled = !plugin.latest_version;
    action.append(materialIcon("download"), document.createTextNode("安装最新版"));
    action.onclick = () => openInstallDialog(plugin);
  }
  actions.append(action);
  footer.append(owner, actions);
  card.append(heading, body, footer);
  return card;
}

function chip(text, modifier = "") {
  return node("span", `meta-chip ${modifier}`.trim(), text);
}

function iconChip(icon, text) {
  const item = node("span", "meta-chip");
  item.append(materialIcon(icon), document.createTextNode(text));
  return item;
}

function materialIcon(icon) {
  return node("span", "material-symbols-rounded", icon);
}

function node(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = text;
  return element;
}

function isSafeHttpUrl(value) {
  if (!value) return false;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:";
  } catch {
    return false;
  }
}

function openInstallDialog(plugin) {
  state.selectedPlugin = plugin;
  elements.dialogMessage.textContent = `确认安装“${plugin.display_name || plugin.plugin_id}”的最新版本吗？`;
  elements.dialogMeta.textContent = `${plugin.plugin_id} @ ${plugin.latest_version}`;
  elements.installToken.value = "";
  elements.installTokenField.hidden = !state.installEnabled;
  elements.dialog.showModal();
  elements.installToken.focus();
}

function openPluginConfig(pluginId) {
  const target = `/webui/frontend/config/plugins?plugin=${encodeURIComponent(pluginId)}`;
  try {
    window.parent.location.assign(target);
  } catch {
    window.location.assign(target);
  }
}

async function installSelectedPlugin() {
  const plugin = state.selectedPlugin;
  if (!plugin || state.installing.has(plugin.plugin_id)) return;
  const installToken = elements.installToken.value.trim();
  if (!installToken) {
    showToast("请输入安装授权码", "error");
    elements.installToken.focus();
    return;
  }
  state.installing.add(plugin.plugin_id);
  setInstallBusy(plugin.plugin_id, true);
  elements.confirmInstall.disabled = true;
  elements.confirmInstall.classList.add("loading");
  elements.confirmInstall.querySelector(".material-symbols-rounded").textContent = "progress_activity";
  let installedResult = null;
  try {
    const result = await request("/install", {
      method: "POST",
      headers: {"X-Plugin-Install-Token": installToken},
      body: JSON.stringify({plugin_id: plugin.plugin_id, version: plugin.latest_version}),
    });
    elements.dialog.close();
    const suffix = result.loaded ? "，并已立即加载" : "";
    showToast(`${plugin.display_name} v${result.version} 已安装${suffix}`, "success");
    installedResult = result;
  } catch (error) {
    showToast(error.message || String(error), "error", 6500);
  } finally {
    state.installing.delete(plugin.plugin_id);
    setInstallBusy(plugin.plugin_id, false);
    elements.confirmInstall.disabled = false;
    elements.confirmInstall.classList.remove("loading");
    elements.confirmInstall.querySelector(".material-symbols-rounded").textContent = "download";
    elements.installToken.value = "";
    if (installedResult) {
      markInstalled(
        plugin.plugin_id,
        installedResult.version,
        installedResult.has_config === true,
      );
    }
  }
}

function setInstallBusy(pluginId, busy) {
  const button = [...document.querySelectorAll(".install-button")]
    .find((item) => item.dataset.pluginId === pluginId);
  if (!button) return;
  button.disabled = busy;
  button.classList.toggle("loading", busy);
  button.querySelector(".material-symbols-rounded").textContent = busy
    ? "progress_activity"
    : "download";
  button.lastChild.textContent = busy
    ? " 正在下载"
    : " 安装最新版";
}

function markInstalled(pluginId, version, hasConfig) {
  const button = [...document.querySelectorAll(".install-button")]
    .find((item) => item.dataset.pluginId === pluginId);
  if (!button) return;
  button.replaceChildren();
  button.onclick = null;
  if (hasConfig) {
    button.disabled = false;
    button.append(materialIcon("settings"), document.createTextNode("配置"));
    button.onclick = () => openPluginConfig(pluginId);
  } else {
    button.disabled = true;
    button.append(materialIcon("check"), document.createTextNode(`已安装 v${version}`));
  }
}

function showToast(message, type = "success", duration = 4200) {
  const toast = node("div", `toast ${type}`);
  toast.append(
    materialIcon(type === "success" ? "check_circle" : "error"),
    node("span", "", message),
  );
  elements.toastRegion.append(toast);
  window.setTimeout(() => toast.remove(), duration);
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN", {notation: value >= 10000 ? "compact" : "standard"}).format(value);
}

elements.search.addEventListener("input", renderPlugins);
elements.clearSearch.addEventListener("click", () => {
  elements.search.value = "";
  elements.search.focus();
  renderPlugins();
});
elements.category.addEventListener("change", renderPlugins);
elements.sort.addEventListener("change", renderPlugins);
elements.refresh.addEventListener("click", () => loadPlugins(true));
elements.confirmInstall.addEventListener("click", installSelectedPlugin);
elements.dialog.addEventListener("close", () => {
  elements.installToken.value = "";
  if (!state.installing.size) state.selectedPlugin = null;
});

applyParentTheme();
loadPlugins();
