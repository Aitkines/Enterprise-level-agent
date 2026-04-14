《作品与答辩材料》目录说明（最新版）

一、目录用途
本目录用于集中存放作品展示、运行访问、部署说明与部署包，便于评审老师或答辩现场快速查看与验证。

二、目录结构
1. 可执行文档
存放系统部署、系统使用、上线清单等文本说明。

2. 部署包
存放部署压缩包与部署包说明。

3. 运行网址.txt
系统当前对外访问网址（与“可执行文档”同级）。

4. 系统访问二维码.png
对应运行网址的二维码图片（与“可执行文档”同级）。

三、当前访问地址
https://aroma-espresso-patience.ngrok-free.dev

四、维护方式
1. 使用固定域名启动命令：
.\start_public.ps1 -NgrokDomain aroma-espresso-patience.ngrok-free.dev
2. 每次启动后会自动更新：
- 运行网址.txt
- 系统访问二维码.png
- public_runtime 下的运行记录文件
