# Neo-MoFox-WebUI 安装文档

> 本文档将指导您完成 Neo-MoFox-WebUI 的完整安装流程，包括环境准备、前后端配置和服务启动。

---

## 目录

- [⭐ 快速部署（推荐）](#⭐-快速部署推荐)
- [完整开发环境部署](#完整开发环境部署)
  - [环境要求](#环境要求)
  - [安装 Node.js 和 npm](#安装-nodejs-和-npm)
  - [获取项目](#获取项目)
  - [安装前端依赖](#安装前端依赖)
  - [配置后端插件](#配置后端插件)
  - [配置 Neo-MoFox](#配置-neo-mofox)
  - [启动服务](#启动服务)
  - [访问 WebUI](#访问-webui)
- [常见问题](#常见问题)

---

## ⭐ 快速部署（推荐）

> **适用场景**：生产环境使用，无需 Node.js/npm，无需构建前端，开箱即用。

### 环境要求

- **Neo-MoFox**：已安装并配置完成
- **Python**：3.10 或更高版本
- **Git**：用于克隆项目

### 部署步骤

#### 1. 克隆预构建版本到插件目录

**方式一：直接克隆到插件目录（推荐）**

```bash
# 进入 Neo-MoFox 的插件目录
cd /path/to/Neo-MoFox/plugins

# 克隆 webui-static 分支（包含预构建的前端静态文件）
git clone -b webui-static https://github.com/ikun-1145141/Neo-MoFox-Webui webui
```

**Windows 用户：**

```powershell
# 进入 Neo-MoFox 的插件目录
cd C:\path\to\Neo-MoFox\plugins

# 克隆 webui-static 分支
git clone -b webui-static https://github.com/ikun-1145141/Neo-MoFox-Webui webui
```

#### 2. 验证插件文件结构

确保插件目录结构如下：

```
Neo-MoFox/
└── plugins/
    └── webui/
        ├── manifest.json
        ├── plugin.py
        ├── static/              # 预构建的前端静态文件
        │   ├── index.html
        │   ├── assets/
        │   └── ...
        ├── adapter/
        ├── event_handler/
        ├── router/
        ├── services/
        └── utils/
```

#### 3. 配置 Neo-MoFox

编辑 `config/core.toml`：

```toml
[http_router]
# 启用 HTTP 路由
enable_http_router = true

# 监听地址（127.0.0.1 仅本地，0.0.0.0 允许外部访问）
http_router_host = "127.0.0.1"

# 监听端口
http_router_port = 8005

# API 访问密钥（请修改为强密码）
api_keys = ["your-secure-api-key-here"]
```

#### 4. 启动 Neo-MoFox

```bash
# 进入 Neo-MoFox 目录
cd /path/to/Neo-MoFox

# 启动
uv run main.py
```

#### 5. 访问 WebUI

在浏览器中打开：

```
http://localhost:8005
```

使用您在 `core.toml` 中配置的 `api_keys` 登录。

### 更新插件

当需要更新到最新版本时：

```bash
# 进入插件目录
cd /path/to/Neo-MoFox/plugins/webui

# 拉取最新版本
git pull origin webui-static

# 重启 Neo-MoFox
```

---

## 完整开发环境部署

> **适用场景**：需要修改前端代码、参与开发或自定义 UI。

### 环境要求

在开始安装之前，请确保您的系统满足以下要求：

- **操作系统**：Linux / Windows / macOS
- **Node.js**：v18.0.0 或更高版本
- **npm**：v9.0.0 或更高版本（通常随 Node.js 一起安装）
- **Neo-MoFox**：已安装并配置完成
- **Python**：3.10 或更高版本（Neo-MoFox 运行环境）

---

## 安装 Node.js 和 npm

### Linux

#### 使用包管理器安装（推荐）

**Ubuntu/Debian：**

```bash
# 安装 NodeSource 仓库（Node.js 20.x LTS）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# 安装 Node.js 和 npm
sudo apt-get install -y nodejs

# 验证安装
node --version
npm --version
```

**Fedora/CentOS/RHEL：**

```bash
# 安装 NodeSource 仓库（Node.js 20.x LTS）
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -

# 安装 Node.js 和 npm
sudo dnf install -y nodejs

# 验证安装
node --version
npm --version
```

**Arch Linux：**

```bash
# 使用 pacman 安装
sudo pacman -S nodejs npm

# 验证安装
node --version
npm --version
```

#### 使用 nvm 安装（推荐用于开发环境）

```bash
# 安装 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# 重新加载 shell 配置
source ~/.bashrc  # 或 ~/.zshrc

# 安装 Node.js LTS 版本
nvm install --lts

# 设置默认版本
nvm use --lts
nvm alias default node

# 验证安装
node --version
npm --version
```

### Windows

#### 方式一：官方安装包（推荐）

1. 访问 [Node.js 官网](https://nodejs.org/)
2. 下载 LTS（长期支持）版本的 Windows 安装包（`.msi`）
3. 运行安装包，按照安装向导完成安装
4. 打开命令提示符或 PowerShell，验证安装：

```powershell
node --version
npm --version
```

#### 方式二：使用 Chocolatey

```powershell
# 以管理员权限运行 PowerShell
choco install nodejs-lts -y

# 验证安装
node --version
npm --version
```

#### 方式三：使用 Scoop

```powershell
# 安装 Scoop（如果尚未安装）
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

# 安装 Node.js
scoop install nodejs-lts

# 验证安装
node --version
npm --version
```

### macOS

#### 方式一：使用 Homebrew（推荐）

```bash
# 安装 Homebrew（如果尚未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Node.js
brew install node

# 验证安装
node --version
npm --version
```

#### 方式二：官方安装包

1. 访问 [Node.js 官网](https://nodejs.org/)
2. 下载 LTS 版本的 macOS 安装包（`.pkg`）
3. 运行安装包，按照安装向导完成安装
4. 打开终端，验证安装：

```bash
node --version
npm --version
```

#### 方式三：使用 nvm

```bash
# 安装 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# 重新加载 shell 配置
source ~/.zshrc  # 或 ~/.bash_profile

# 安装 Node.js LTS 版本
nvm install --lts
nvm use --lts
nvm alias default node

# 验证安装
node --version
npm --version
```

---

## 获取项目

### 克隆项目（推荐）

```bash
# 克隆项目到本地
git clone https://github.com/ikun-1145141/Neo-MoFox-Webui
cd Neo-MoFox-Webui
```

### 下载压缩包

1. 访问项目的 GitHub Release 页面
2. 下载最新版本的源码压缩包（`.zip` 或 `.tar.gz`）
3. 解压到您希望安装的目录

---

## 安装前端依赖

进入前端目录并安装依赖：

```bash
# 进入前端目录
cd frontend

# 安装依赖（推荐使用 pnpm 以提升安装速度和节省磁盘空间）
# 方式一：使用 npm
npm install
```

安装完成后，前端依赖将被下载到 `frontend/node_modules` 目录。

---

## 配置后端插件

Neo-MoFox-WebUI 的后端以插件形式集成到 Neo-MoFox 框架中。

### 复制插件到 Neo-MoFox

**Linux / macOS：**

```bash
# 方式一：复制文件（推荐用于生产环境）
cp -r Plugin /path/to/Neo-MoFox/plugins/webui
```

**Windows（命令提示符，需管理员权限）：**

```cmd
REM 方式一：复制文件
xcopy /E /I Plugin C:\path\to\Neo-MoFox\plugins\webui
```

**Windows（PowerShell，需管理员权限）：**

```powershell
# 方式一：复制文件
Copy-Item -Path .\Plugin -Destination C:\path\to\Neo-MoFox\plugins\webui -Recurse
```

### 验证插件文件结构

确保插件目录结构如下：

```
Neo-MoFox/
└── plugins/
    └── webui/
        ├── manifest.json
        ├── plugin.py
        ├── components/
        ├── managers/
        ├── storage/
        └── utils/
```

---

## 配置 Neo-MoFox

### 编辑配置文件

打开 Neo-MoFox 的配置文件：`config/core.toml`

### 配置 HTTP 路由端口

找到 `[http_router]` 配置节，确认或修改以下配置：

```toml
[http_router]
# 是否启用 HTTP 路由
enable_http_router = true

# HTTP 路由监听地址（127.0.0.1 表示仅本地访问，0.0.0.0 表示允许外部访问）
http_router_host = "127.0.0.1"

# HTTP 路由监听端口（与前端 vite.config.ts 中的代理目标端口(8005)一致）
http_router_port = 8005
```

> **安全提示**：
> - 如果仅在本地使用，请保持 `http_router_host = "127.0.0.1"`
> - 如果需要远程访问，可改为 `http_router_host = "0.0.0.0"`，但请务必配置防火墙和认证

### 配置 API 密钥

在同一配置节中，设置 `api_keys`：

```toml
# WebUI API 访问密钥列表，留空则禁用认证（不推荐）
api_keys = ["your-secret-api-key-here"]
```

> **重要**：
> - `api_keys` 是一个字符串数组，可以配置多个密钥
> - 请务必修改默认密钥为强密码（建议使用随机生成的长字符串）
> - 示例：`api_keys = ["a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"]`
> - 前端登录时需要使用此密钥进行认证

### 完整配置示例

```toml
[http_router]
enable_http_router = true
http_router_host = "127.0.0.1"
http_router_port = 8005
api_keys = ["your-secure-api-key-replace-this"]
```

### 保存配置

保存 `core.toml` 文件后，配置即生效。

---

## 启动服务

### 启动后端（Neo-MoFox）

进入 Neo-MoFox 目录并启动：

**Linux / macOS：**

```bash
# 进入 Neo-MoFox 目录
cd /path/to/Neo-MoFox

# 启动 Neo-MoFox
uv run main.py
```

**Windows：**

```cmd
REM 进入 Neo-MoFox 目录
cd C:\path\to\Neo-MoFox

REM 启动 Neo-MoFox
uv run main.py
```

**验证后端启动成功：**

在终端输出中查看类似以下的日志：

```
WebUI 插件 vXXX 已加载"
```

### 启动前端开发服务器

打开新的终端窗口，进入前端目录并启动：

**Linux / macOS / Windows：**

```bash
# 进入前端目录
cd /path/to/Neo-MoFox-Webui/frontend

# 启动开发服务器
npm run dev
```

**验证前端启动成功：**

终端将显示类似以下输出：

```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:9178/
➜  Network: http://192.168.x.x:9178/
➜  press h + enter to show help
```

---

## 访问 WebUI

### 本地访问

在浏览器中打开：

```
http://localhost:9178
```

### 首次登录

1. 在登录页面输入您在 `core.toml` 中配置的 `api_keys` 中的任意一个密钥
2. 点击「登录」按钮
3. 登录成功后将进入 WebUI 主界面

---

## 常见问题

### 前端无法连接后端

**问题表现：**
- 前端页面显示网络错误或连接超时
- 浏览器控制台显示 `Failed to fetch` 或 `ERR_CONNECTION_REFUSED`

**解决方案：**

1. **确认后端已启动：**
   - 检查 Neo-MoFox 是否正在运行
   - 确认终端输出显示 HTTP Router 已启动

2. **检查端口配置：**
   - 确认 `core.toml` 中的 `http_router_port` 为 `8005`
   - 确认 `vite.config.ts` 中的代理目标为 `http://localhost:8005`

3. **检查防火墙：**
   - 确保防火墙未阻止 8005 和 9178 端口

4. **检查端口占用：**
   ```bash
   # Linux/macOS
   lsof -i :8005
   lsof -i :9178
   
   # Windows
   netstat -ano | findstr :8005
   netstat -ano | findstr :9178
   ```

### 登录失败提示 401 错误

**问题表现：**
- 输入密钥后提示「登录失败」或「Unauthorized」

**解决方案：**

1. **确认密钥正确：**
   - 检查输入的密钥与 `core.toml` 中的 `api_keys` 完全一致
   - 注意密钥区分大小写，不要有多余的空格

2. **重启后端：**
   - 修改 `core.toml` 后需要重启 Neo-MoFox 才能生效

### 前端依赖安装失败

**问题表现：**
- `npm install` 卡住或报错
- 网络连接超时

**解决方案：**

1. **配置国内镜像源（中国大陆用户）：**
   ```bash
   # 使用淘宝镜像
   npm config set registry https://registry.npmmirror.com
   
   # 或使用腾讯镜像
   npm config set registry https://mirrors.cloud.tencent.com/npm/
   
   # 重新安装
   npm install
   ```

2. **清除缓存后重试：**
   ```bash
   npm cache clean --force
   npm install
   ```

3. **使用代理：**
   ```bash
   npm config set proxy http://127.0.0.1:7890
   npm config set https-proxy http://127.0.0.1:7890
   ```

### 后端插件未加载

**问题表现：**
- Neo-MoFox 启动日志中未显示 WebUI Plugin 加载信息
- 访问 API 接口返回 404

**解决方案：**

1. **检查插件目录：**
   - 确认插件已正确复制/链接到 `Neo-MoFox/plugins/webui`
   - 检查目录结构是否完整（包含 `manifest.json` 和 `plugin.py`）

2. **检查插件配置：**
   - 确认 `manifest.json` 格式正确
   - 检查是否有 Python 语法错误

3. **查看错误日志：**
   - 查看 Neo-MoFox 的日志文件（通常在 `logs/` 目录下）
   - 寻找与 WebUI Plugin 相关的错误信息

---

## 获取帮助

如果遇到问题，请：

1. 查看本文档的「常见问题」章节
2. 查看项目的 [GitHub Issues](https://github.com/your-org/Neo-MoFox-Webui/issues)
3. 加入社区讨论群获取支持

---

**安装文档版本：** v1.0.0  
**最后更新：** 2026年5月4日
