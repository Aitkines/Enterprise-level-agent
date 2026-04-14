《2026012345-02 素材与源码》目录说明（最新版）

一、目录用途
本目录用于提交“项目源码压缩包”与“智能体交互记录”，对应作品开发过程与源码交付内容。

二、目录文件说明
1. 光之耀面项目源码.zip
项目源码最新版压缩包。已按“可交付源码”方式重新打包，去除了不必要缓存与构建产物。

2. 智能体交互记录.json
项目开发过程中的智能体交互记录文件，用于说明人机协同过程与关键操作记录。

3. readme.txt
本目录说明文件。

三、源码包主要内容（压缩包内）
1. 前端与后端源码目录：
- frontend
- backend
- src

2. 静态资源与工具目录：
- static
- utils
- .streamlit
- data

3. 启动与部署相关文件：
- api_server.py
- app.py
- agent_engine.py
- start_dev.ps1 / start_dev.bat
- start_public.ps1 / start_public.bat
- requirements.txt
- docker-compose.yml
- Dockerfile.backend
- render.yaml
- .env.example

四、更新说明
本次已完成：
1. 光之耀面项目源码.zip 重新打包为最新版。
2. 源码包中已同步纳入固定域名公网启动脚本（start_public.ps1）。
3. 已移除无关缓存目录与构建临时产物，便于评审直接查阅源码。
