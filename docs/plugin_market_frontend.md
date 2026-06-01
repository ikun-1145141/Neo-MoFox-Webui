# WebUI 插件市场前端对接文档

本文档描述 Neo-MoFox-WebUI 后端提供给前端的插件市场接口。所有接口统一挂载在 `/webui/api/plugin-market` 下，响应结构均为 `BaseResponse<T>`：

```json
{
  "code": 200,
  "data": {},
  "message": "success"
}
```

前端应只在 `api/` 层封装请求，并在全局响应拦截器中处理 `code !== 200` 和 HTTP 错误。

## 1. 数据来源与安装策略

- 市场数据来自远端 Plugin Market API。
- 已安装插件列表不使用 WebUI 存储层缓存，后端会直接读取 Neo-MoFox 核心插件管理器的已加载插件、未加载插件及其 manifest 元数据。
- 安装、更新、降级均直接下载市场版本的插件资产文件并放入本机插件目录，不解压。
- 更新或降级前会备份原插件：
  - 原插件是文件夹：压缩成 zip 后删除原文件夹。
  - 原插件是 zip、mfp 或其他插件文件：直接重命名为备份后缀。

## 2. TypeScript 基础类型

```ts
export interface BaseResponse<T = unknown> {
  code: number;
  data: T | null;
  message: string;
}

export type PluginStatus =
  | 'draft'
  | 'pending_review'
  | 'published'
  | 'deprecated'
  | 'blocked'
  | 'archived';

export type TrustLevel = 'official' | 'verified' | 'community';
export type VersionStatus = 'submitted' | 'pending_review' | 'published' | 'yanked' | 'blocked';
export type SyncStatus = 'none' | 'success' | 'failed';
```

## 3. 市场插件类型

```ts
export interface MarketPlugin {
  plugin_id: string;
  display_name: string;
  summary: string;
  description: string;
  icon_url: string | null;
  has_readme: boolean;
  homepage: string | null;
  repository_url: string;
  license: string;
  categories: string[];
  tags: string[];
  status: PluginStatus;
  owner_id: string;
  owner_login: string | null;
  owner_display_name: string | null;
  owner_avatar_url: string | null;
  maintainers: string[];
  trust_level: TrustLevel;
  risk_notice: string | null;
  created_at: string;
  updated_at: string;
  likes_count: number;
  rating_avg: number;
  rating_count: number;
  comments_count: number;
  downloads_count: number;
  latest_version: string | null;
  latest_version_published_at: string | null;
  viewer_has_liked: boolean;
  viewer_rating: number | null;
}

export interface MarketPluginListResponse {
  items: MarketPlugin[];
  total: number;
}
```

## 4. 获取市场插件列表

`GET /webui/api/plugin-market/plugins`

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---:|---|---|
| `q` | `string` | 否 | - | 搜索关键字 |
| `status` | `PluginStatus` | 否 | - | 发布状态 |
| `category` | `string` | 否 | - | 分类 |
| `tag` | `string` | 否 | - | 标签 |
| `trust_level` | `TrustLevel` | 否 | - | 信任等级 |
| `sort` | `string` | 否 | `updated` | 排序方式 |
| `offset` | `number` | 否 | `0` | 分页偏移 |
| `limit` | `number` | 否 | `50` | 分页大小，范围 1-100 |

响应：`BaseResponse<MarketPluginListResponse>`。

## 5. 获取市场插件详情

`GET /webui/api/plugin-market/plugins/{plugin_id}`

响应：`BaseResponse<MarketPlugin>`。

## 6. 获取 README

```ts
export interface MarketPluginReadmeResponse {
  plugin_id: string;
  exists: boolean;
  html: string | null;
}
```

`GET /webui/api/plugin-market/plugins/{plugin_id}/readme`

响应：`BaseResponse<MarketPluginReadmeResponse>`。

前端渲染 `html` 时必须使用已审核的 HTML 渲染策略，避免不可信 HTML 注入。

## 7. 获取插件版本

```ts
export interface MarketPluginVersion {
  plugin_id: string;
  version: string;
  release_tag: string;
  release_title: string;
  release_url: string;
  asset_name: string;
  asset_download_url: string;
  checksum_sha256: string;
  file_size: number;
  published_at: string;
  is_prerelease: boolean;
  is_yanked: boolean;
  status: VersionStatus;
  plugin_api_version: string;
  min_host_version: string;
  max_host_version: string | null;
  supported_platforms: string[];
  last_sync_status: SyncStatus;
  last_sync_error: string | null;
  download_count: number;
}

export interface MarketPluginVersionListResponse {
  items: MarketPluginVersion[];
  total: number;
}
```

接口：

- `GET /webui/api/plugin-market/plugins/{plugin_id}/versions`
- `GET /webui/api/plugin-market/plugins/{plugin_id}/versions/{version}`

响应分别为：

- `BaseResponse<MarketPluginVersionListResponse>`
- `BaseResponse<MarketPluginVersion>`

## 8. 获取本机已安装插件

```ts
export interface InstalledMarketPlugin {
  plugin_id: string;
  display_name: string;
  summary: string;
  installed_version: string;
  latest_version: string | null;
  plugin_path: string;
  is_loaded: boolean;
  source: 'market' | 'local';
  market: MarketPlugin | null;
}

export interface InstalledPluginListResponse {
  items: InstalledMarketPlugin[];
  total: number;
}
```

`GET /webui/api/plugin-market/installed`

响应：`BaseResponse<InstalledPluginListResponse>`。

说明：

- `source = 'market'` 表示插件 ID 能够在市场中匹配到。
- `source = 'local'` 表示本机存在，但市场中未匹配到或市场暂不可用。
- `market` 为匹配到的市场插件详情，否则为 `null`。

## 9. 安装与更新插件

```ts
export interface PluginInstallRequest {
  version?: string | null;
  host_version?: string | null;
  plugin_api_version?: string | null;
  platform?: string | null;
  force?: boolean;
}

export interface PluginInstallResult {
  success: boolean;
  plugin_id: string;
  version: string;
  plugin_path: string;
  loaded: boolean;
  backup_path: string | null;
  message: string;
}
```

### 安装

`POST /webui/api/plugin-market/plugins/{plugin_id}/install`

请求体：`PluginInstallRequest`。

- `version` 为空时，后端会调用市场推荐版本接口。
- 如果插件已存在且未设置 `force`，后端会拒绝覆盖。

### 更新

`POST /webui/api/plugin-market/plugins/{plugin_id}/update`

请求体：`PluginInstallRequest`。

- 更新接口会强制覆盖目标插件。
- 覆盖前后端会生成备份。

## 10. 降级或切换版本

```ts
export interface PluginVersionSwitchRequest {
  version: string;
  force?: boolean;
}
```

`POST /webui/api/plugin-market/plugins/{plugin_id}/versions/switch`

请求体：`PluginVersionSwitchRequest`。

响应：`BaseResponse<PluginInstallResult>`。

该接口用于降级或切换到任意已发布版本，操作前同样会备份当前插件。

## 11. 前端 API 模块建议

建议在 `src/api/modules/pluginMarket.ts` 中集中封装：

```ts
import { request } from '../base';

const base = '/webui/api/plugin-market';

export function listMarketPlugins(params: Record<string, unknown>) {
  return request.get<MarketPluginListResponse>(`${base}/plugins`, { params });
}

export function getMarketPlugin(pluginId: string) {
  return request.get<MarketPlugin>(`${base}/plugins/${pluginId}`);
}

export function getPluginReadme(pluginId: string) {
  return request.get<MarketPluginReadmeResponse>(`${base}/plugins/${pluginId}/readme`);
}

export function listPluginVersions(pluginId: string) {
  return request.get<MarketPluginVersionListResponse>(`${base}/plugins/${pluginId}/versions`);
}

export function listInstalledPlugins() {
  return request.get<InstalledPluginListResponse>(`${base}/installed`);
}

export function installPlugin(pluginId: string, body: PluginInstallRequest) {
  return request.post<PluginInstallResult>(`${base}/plugins/${pluginId}/install`, body);
}

export function updatePlugin(pluginId: string, body: PluginInstallRequest) {
  return request.post<PluginInstallResult>(`${base}/plugins/${pluginId}/update`, body);
}

export function switchPluginVersion(pluginId: string, body: PluginVersionSwitchRequest) {
  return request.post<PluginInstallResult>(`${base}/plugins/${pluginId}/versions/switch`, body);
}
```

## 12. UI 状态建议

- 市场列表页：使用 `ref` 保存 `items`、`total`、`loading`、`query`。
- 插件详情页：进入页面时并发请求详情、README、版本列表。
- 已安装页：进入页面时请求 `/installed`，不要使用前端本地缓存作为真源。
- 安装、更新、降级：按钮触发后显示全局 loading；成功后刷新已安装列表与详情页版本状态。
- 所有失败均交给 `api/base.ts` 全局错误提示，不允许静默失败。
