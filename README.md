# 光之耀面

企业级研究助理项目，围绕多轮对话、企业财务分析、同行对比、图表展示与研究报告生成，提供一套面向投研与经营分析场景的交互式工作台。

当前主架构已经切换为 React 前端 + FastAPI 后端。仓库中仍保留部分早期 Streamlit 代码，便于兼容旧原型，但当前推荐使用前后端分离模式启动与部署。

## 项目结构

- `frontend/`
  React + Vite 前端，负责新对话页、会话管理、图表展示、财务/对比/报告页面。
- `backend/api/`
  FastAPI 接口层，提供会话、聊天流式接口、财务接口、对比接口、报告接口。
- `src/application/`
  业务服务层，包括财务分析、同行对比、报告生成、评分等逻辑。
- `src/infrastructure/`
  基础设施能力，包括文件处理、会话存储等。
- `agent_engine.py`
  核心智能体提示词与模型调用封装。
- `api_server.py`
  FastAPI 本地启动入口。
- `app.py`
  早期 Streamlit 入口，当前不是主推荐入口。

## 当前能力

- 多轮研究对话与会话管理
- 上传图片、PDF、Excel、Word、文本文件参与分析
- 自动解析并展示图表
- 财务数据查看
- 同行对比与赛道对标
- 研究报告 HTML 生成
- 研究报告 PDF 导出

## 技术栈

- 前端：React 18、TypeScript、Vite、ECharts
- 后端：FastAPI、Uvicorn
- Python 侧依赖：pandas、akshare、pdfplumber、langchain、openai 等
- 模型接入：当前代码中使用火山引擎 Ark / 豆包接口配置

## 环境要求

- Python 3.10 及以上
- Node.js 18 及以上
- npm 9 及以上

## 环境变量

项目根目录下需要 `.env` 文件。当前代码实际使用到的主要变量如下：

```env
ARK_API_KEY=你的密钥
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_SEED_LITE_KEY=你的密钥
DOUBAO_SEED_LITE_ENDPOINT=你的endpoint
```

说明：

- `.env` 已经在 `.gitignore` 中忽略，不会被自动提交。
- 不建议把真实密钥提交到远端仓库。

## 本地开发启动

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 启动后端

在项目根目录执行：

```bash
python api_server.py
```

或直接使用 Uvicorn：

```bash
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

默认后端地址：

```text
http://127.0.0.1:8000
```

### 3. 启动前端

进入前端目录执行：

```bash
cd frontend
npm install
npm run dev
```

默认前端地址：

```text
http://127.0.0.1:5173
```

### 4. 前后端联调

前端默认通过 `VITE_API_BASE` 读取后端地址；如果未设置，则回退为：

```text
http://127.0.0.1:8000
```

如果你的后端不是这个地址，可在启动前端前设置：

```bash
set VITE_API_BASE=http://127.0.0.1:8000
```

Windows PowerShell 可使用：

```powershell
$env:VITE_API_BASE="http://127.0.0.1:8000"
npm run dev
```

## 前端构建

```bash
cd frontend
npm install
npm run build
```

构建产物位于：

```text
frontend/dist
```

## 生产部署建议

推荐采用“前端静态部署 + 后端 API 服务”模式。

### 后端

```bash
pip install -r requirements.txt
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run build
```

将 `frontend/dist` 交给 Nginx、静态托管平台或其他 Web 服务器提供访问。

生产构建时，建议提前设置：

```bash
VITE_API_BASE=http://你的后端地址:8000
```

然后再执行 `npm run build`。

## Git 与远端仓库

当前仓库可以本地提交，也可以绑定 GitHub / Gitee 远端仓库。

常用命令：

```bash
git status
git add .
git commit -m "你的提交说明"
git remote add origin <远端仓库地址>
git push -u origin main
```

更详细的远端绑定、推送和部署说明，请查看 [DEPLOYMENT.md](/c:/Users/Lenovo/Desktop/项目agent2.0/DEPLOYMENT.md)。

## 兼容说明

- `app.py` 对应的是早期 Streamlit 原型。
- 当前主要交付形态为 React + FastAPI。
- 如果后续继续演进，建议统一围绕 `frontend/ + backend/api/ + src/application/` 这套结构维护。

## 当前版本保存

当前项目已经保存过一次本地 git 提交：

```text
7d9bb90 feat: save current research assistant version
```

如果你要继续往远端推送，可以在绑定远端后直接执行：

```bash
git push -u origin main
```
