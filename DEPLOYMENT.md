# 部署与远端仓库说明

这份文档面向当前 React + FastAPI 结构，包含三部分内容：

- 如何在本地运行项目
- 如何部署到服务器
- 如何绑定并找到远端仓库地址

## 一、本地运行

### 1. 安装后端依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

### 2. 配置 `.env`

项目根目录需要 `.env` 文件，当前核心变量如下：

```env
ARK_API_KEY=你的密钥
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_SEED_LITE_KEY=你的密钥
DOUBAO_SEED_LITE_ENDPOINT=你的endpoint
```

仓库中已经提供：

```text
.env.example
```

你可以先复制：

```bash
copy .env.example .env
```

然后再把占位值替换成真实密钥。

### 2.1 一键启动脚本

当前仓库已经提供 Windows 一键启动脚本：

```text
start_dev.ps1
start_dev.bat
```

首次运行推荐：

```powershell
.\start_dev.ps1 -InstallDeps
```

普通启动：

```powershell
.\start_dev.ps1
```

如果不方便执行 PowerShell 脚本，也可以双击：

```text
start_dev.bat
```

脚本会：

- 检查 `python` 和 `npm`
- 在缺少 `.env` 时自动从 `.env.example` 复制一份
- 可选安装 Python 与前端依赖
- 分别拉起后端和前端窗口

### 3. 启动后端

```bash
python api_server.py
```

或者：

```bash
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

后端启动后，接口地址默认为：

```text
http://127.0.0.1:8000
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认前端访问地址：

```text
http://127.0.0.1:5173
```

### 5. 自定义后端地址

前端默认读取 `VITE_API_BASE`。如果你换了后端地址，先设置环境变量再启动前端。

PowerShell 示例：

```powershell
$env:VITE_API_BASE="http://127.0.0.1:8000"
npm run dev
```

## 二、生产部署

## Docker 部署

当前仓库已经提供：

```text
Dockerfile.backend
frontend/Dockerfile
frontend/nginx.conf
docker-compose.yml
```

### 1. 准备 `.env`

```bash
copy .env.example .env
```

并填入真实模型配置。

### 2. 构建并启动

```bash
docker compose up --build
```

启动后默认访问：

```text
前端: http://127.0.0.1:5173
后端: http://127.0.0.1:8000
```

### 3. 后台运行

```bash
docker compose up -d --build
```

### 4. 停止容器

```bash
docker compose down
```

### 5. Docker 方案说明

- 后端容器基于 `Dockerfile.backend`
- 前端容器基于 `frontend/Dockerfile`
- 前端使用 Nginx 托管构建产物
- Nginx 会将 `/api` 自动代理到后端容器
- 因此浏览器访问前端时，不需要额外手工配置 API 域名
## 原生后端部署

建议使用 Uvicorn 直接启动，或接入进程管理器。

```bash
pip install -r requirements.txt
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

如果部署在 Linux 服务器，建议再加上：

- `systemd` 或 `supervisor` 守护进程
- Nginx 反向代理
- HTTPS 证书

## 原生前端部署

```bash
cd frontend
npm install
npm run build
```

构建完成后会生成：

```text
frontend/dist
```

把这个目录部署到 Nginx、静态站点服务或对象存储即可。

生产构建前建议设置：

```bash
VITE_API_BASE=http://你的后端地址:8000
```

再执行：

```bash
npm run build
```

## 三、绑定远端仓库

### 1. 查看当前是否已绑定远端

```bash
git remote -v
```

如果没有输出，说明当前仓库还没接到远端平台。

### 2. 添加远端仓库

```bash
git remote add origin <远端仓库地址>
```

例如：

```bash
git remote add origin https://github.com/你的用户名/你的仓库名.git
```

或者：

```bash
git remote add origin https://gitee.com/你的用户名/你的仓库名.git
```

### 3. 首次推送

```bash
git push -u origin main
```

以后再推送只需要：

```bash
git push
```

## 四、怎么找到远端仓库地址

### GitHub

1. 登录 GitHub
2. 进入你的仓库页面
3. 点击绿色 `Code` 按钮
4. 在 `HTTPS` 或 `SSH` 标签里复制仓库地址

常见格式：

```text
https://github.com/你的用户名/仓库名.git
```

或：

```text
git@github.com:你的用户名/仓库名.git
```

### Gitee

1. 登录 Gitee
2. 打开你的仓库页面
3. 点击 `克隆/下载`
4. 复制 HTTPS 或 SSH 地址

常见格式：

```text
https://gitee.com/你的用户名/仓库名.git
```

或：

```text
git@gitee.com:你的用户名/仓库名.git
```

## 五、怎么确认远端已经配置成功

执行：

```bash
git remote -v
```

如果看到类似输出，就说明成功了：

```text
origin  https://github.com/你的用户名/仓库名.git (fetch)
origin  https://github.com/你的用户名/仓库名.git (push)
```

## 六、怎么在平台上找到你的项目

绑定并推送成功后，可以这样找：

- GitHub：进入 `https://github.com/你的用户名/仓库名`
- Gitee：进入 `https://gitee.com/你的用户名/仓库名`

你也可以执行下面命令快速查看远端地址：

```bash
git remote get-url origin
```

复制这个地址到浏览器里，通常就能直接打开仓库页面。

## 七、当前仓库状态说明

当前本地仓库已经有一次版本保存提交：

```text
7d9bb90 feat: save current research assistant version
```

但当前尚未配置远端，因此还需要你提供目标仓库地址，我才能继续替你执行：

```bash
git remote add origin <你的远端仓库地址>
git push -u origin main
```
