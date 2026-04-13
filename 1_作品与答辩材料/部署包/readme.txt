【文件夹名称】
部署包

【文件夹作用】
本文件夹用于存放“光之耀面”项目的部署包文件，供评审专家或使用人员按照部署说明在本地环境中完成安装、部署和运行。

【文件内容说明】
1. 光之耀面部署包.zip
该文件为项目部署包，包含系统本地部署运行所需的核心代码、依赖清单、环境变量示例文件、启动脚本及 Docker 配置文件等内容。

【部署包内主要内容说明】
1. frontend
前端工程文件，用于启动系统网页界面。

2. backend
后端接口代码，用于提供系统 API 服务。

3. src
核心业务逻辑代码，用于实现对话、财务分析、公司对比和报告生成等功能。

4. static、utils、.streamlit
分别用于存放静态资源、辅助工具代码以及兼容界面配置。

5. agent_engine.py、api_server.py、app.py
系统主要启动与核心逻辑文件。

6. requirements.txt
Python 依赖清单文件。

7. docker-compose.yml、Dockerfile.backend
Docker 部署配置文件。

8. .env.example
环境变量示例文件。

9. start_dev.ps1、start_dev.bat
本地一键启动脚本。

10. README.md
项目说明文档。

【补充说明】
1. 当前部署包支持以本地部署方式完成系统运行。
2. 使用时请先根据 `.env.example` 配置 `.env` 文件，再按“系统部署说明”完成启动。
