# 光之耀面项目源码说明

## 项目简介

光之耀面（Radiant Surface）是一个面向企业研究、投研分析与智能问答场景的项目源码仓库。当前项目主要采用 `React + Vite` 前端与 `FastAPI` 后端的前后端分离架构，支持多轮对话、公司研究、财务分析、对比分析、文件解析和研究报告生成等功能。

当前目录保留的是项目运行所需的核心源码、配置文件和启动脚本。

## 文件夹作用

本文件夹用于存放项目核心源码、运行配置文件、依赖清单和启动脚本，是项目当前的主源码目录。

## 主要功能

- 多轮对话与会话管理
- 流式聊天输出
- 公司识别与研究问答
- 财务指标分析与展示
- 可比公司对比分析
- 文件上传与内容解析
- 报告生成与 PDF 导出
- 前端图表展示

## 技术架构

- 前端：React 18、TypeScript、Vite、ECharts
- 后端：FastAPI、Uvicorn
- 数据与分析能力：pandas、akshare、pdfplumber、langchain、faiss-cpu、rank-bm25
- 模型接入：Volcengine Ark、Doubao Seed Lite

## 当前保留的源码结构说明

### 目录说明

- `frontend/`
  前端源码目录，包含 React 页面、组件、样式及前端构建配置，用于实现用户界面展示与交互。

- `backend/`
  后端接口目录，包含 FastAPI 接口层代码，用于提供聊天、会话管理、财务分析、对比分析、报告生成等 API 服务。

- `src/`
  核心业务源码目录，包含业务服务层、基础设施层、共享模块、领域模型以及兼容界面代码，是项目主要功能逻辑所在位置。

- `static/`
  静态资源目录，用于存放项目运行时需要使用的静态文件和样式资源。

- `utils/`
  工具目录，用于存放项目运行或开发过程中使用的辅助脚本和通用处理函数。

- `.streamlit/`
  Streamlit 相关配置目录，用于兼容项目早期或备用界面运行方式。

### 主要文件说明

- `agent_engine.py`
  项目核心智能体引擎文件，用于组织研究助手提示词、模型调用及部分分析处理逻辑。

- `api_server.py`
  后端服务启动入口文件，用于启动 FastAPI 服务。

- `app.py`
  Streamlit 兼容启动入口文件，用于启动旧版或兼容界面。

- `start_dev.ps1`
  Windows PowerShell 启动脚本，用于一键启动前后端开发环境，并可在首次使用时安装依赖。

- `start_dev.bat`
  Windows 批处理启动脚本，用于封装 PowerShell 启动流程，便于双击运行。

- `requirements.txt`
  Python 依赖清单文件，用于安装项目后端及数据分析相关依赖。

- `docker-compose.yml`
  Docker 编排文件，用于通过容器方式统一启动前端和后端服务。

- `Dockerfile.backend`
  后端 Docker 镜像构建文件，用于构建项目后端运行镜像。

- `.env.example`
  环境变量示例文件，用于说明项目运行所需的接口密钥及配置项。

- `.env`
  本地环境变量配置文件，用于保存实际运行所需的密钥和参数配置。

- `.gitignore`
  Git 忽略配置文件，用于指定不纳入版本管理的本地数据、日志、缓存及归档文件。

- `.dockerignore`
  Docker 忽略配置文件，用于控制镜像构建时不需要打包的文件与目录。

- `readme.txt`
  纯文本目录说明文件，用于按提交要求说明本文件夹作用及各文件内容。

- `README.md`
  Markdown 版项目说明文档，用于展示项目简介、结构说明和运行方式。

## 运行环境

- Python 3.10 及以上
- Node.js 18 及以上
- npm 9 及以上

## 环境变量

首次运行前，请根据示例文件创建 `.env`：

```powershell
Copy-Item .env.example .env
```

当前示例变量如下：

```env
ARK_API_KEY=your_ark_api_key_here
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_SEED_LITE_KEY=your_doubao_seed_lite_key_here
DOUBAO_SEED_LITE_ENDPOINT=your_endpoint_id_here
```

## 启动方式

### 推荐方式

Windows 下推荐直接使用项目自带脚本：

```powershell
.\start_dev.ps1
```

首次安装依赖可使用：

```powershell
.\start_dev.ps1 -InstallDeps
```

也可以使用：

```text
start_dev.bat
```

默认访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`

### 手动启动

1. 安装 Python 依赖

```powershell
pip install -r requirements.txt
```

2. 启动后端

```powershell
python api_server.py
```

或：

```powershell
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

3. 启动前端

```powershell
Set-Location frontend
npm install
npm run dev
```

## Docker 启动

```powershell
docker compose up --build
```

当前容器服务包括：

- `backend`：暴露 `8000`
- `frontend`：暴露 `5173`

## 后端接口概览

当前主要接口包括：

- `GET /api/health`
- `GET /api/dashboard/overview`
- `GET /api/dashboard/system-status`
- `GET /api/sessions`
- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `PUT /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `POST /api/chat`
- `POST /api/chat/stream`
- `GET /api/financial/{target}`
- `GET /api/comparison/{symbol}`
- `POST /api/report`
- `POST /api/report/pdf`

## 补充说明

- 当前项目主运行结构为 `frontend/ + backend/ + src/ + 根目录启动文件`。
- `app.py`、`.streamlit/`、`src/presentation/` 仍保留，用于兼容旧版 Streamlit 运行方式。
