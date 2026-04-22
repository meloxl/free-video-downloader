---
name: Universal Video Downloader
overview: 基于 yt-dlp 的轻量“万能视频下载”Web 应用：同一套 FastAPI 服务既可本地运行也可公网部署；支持单链接/批量队列、实时进度、临时存储；cookies 能力默认关闭并由管理员开关控制。前端风格对齐你给的参考站点（大标题+蓝色强调、圆角胶囊搜索、卡片瀑布流、柔和阴影与插画感）。
todos:
  - id: ui_spec
    content: 复刻参考站核心视觉：Hero大标题蓝色强调、胶囊输入、卡片瀑布流、移动端布局与付费引导文案
    status: completed
  - id: backend_mvp
    content: 实现 FastAPI + yt-dlp 封装：批量创建任务、后台下载、进度上报（SSE优先）、临时存储与TTL清理
    status: completed
  - id: cookies_gate
    content: 加入 cookies 能力但默认关闭：管理员开关 + 单任务 cookies.txt 临时使用与销毁
    status: completed
  - id: validation_limits
    content: 加基础风控：并发/队列限制、输入校验、最大文件/时长策略（不引入数据库）
    status: completed
  - id: tests
    content: pytest 单测 + 本地集成验证脚本（覆盖单条/批量/失败重试/过期清理）
    status: completed
  - id: handoff
    content: 准备验收清单与部署方式：本地一键启动 + Docker公网部署指南
    status: completed
isProject: false
---

## 目标与边界
- **目标**: 做一个“粘贴链接→选择/直接下载→手机也能保存”的万能视频下载站；核心下载能力站在 `yt-dlp` 肩膀上，后端 Python 为主，**无数据库**。
- **边界/风控**:
  - 强制展示版权与封号风险提示；默认仅支持公开可下载内容。
  - **cookies 支持默认关闭**，通过管理员开关启用（你已确认）。
  - 公网模式文件 **临时存储**（你已确认），到期清理。

## 参考 UI（已通过浏览器访问并截图理解）
参考站点 `https://ai.codefather.cn/painting` 的关键风格特征（需要在我们产品中复刻到“下载”场景）：
- **Hero 大标题**：超大黑体主标题 + 右侧/后半句高饱和蓝色强调（例如“万能视频下载， 一键保存”）。
- **胶囊搜索条**：圆角 pill 输入框，左侧图标 + placeholder；右侧蓝色圆角按钮。
- **卡片瀑布流**：大圆角、柔和阴影、留白充足；卡片内图片/插画占比大，标题与标签（#）在下方。
- **极简顶部栏**：左侧汉堡菜单/Logo，右侧头像/入口。

## 技术方案（尽量少改动、封装 yt-dlp）
### 架构
- **后端**：FastAPI（Python）
  - API：创建下载任务、查询任务状态、下载文件。
  - 任务队列：内存 JobStore + 后台线程/线程池（避免阻塞 event loop）。
  - 进度推送：优先 **SSE**（Server-Sent Events）或轻量轮询（前端实现更简单，但 SSE 体验更像参考站）。
- **前端**：服务端渲染（Jinja2）+ TailwindCSS（轻量、移动端友好、易做出参考风格）
  - 进度更新：HTMX（可选）或原生 fetch + EventSource（SSE）。
- **下载引擎**：`yt-dlp` Python 库封装（而不是自己写解析）
  - `YoutubeDL.extract_info(url, download=False)` 获取元信息/可用 formats
  - `progress_hooks` 收集实时进度（速度、百分比、文件名）
  - `outtmpl` 控制输出路径/命名
  - 音频提取未来用 postprocessors（FFmpegExtractAudio）

### 核心流程（无数据库）
```mermaid
graph TD
  User[User] --> WebUI[WebUI]
  WebUI --> ApiCreate[POST /api/jobs]
  ApiCreate --> JobStore[InMemoryJobStore]
  ApiCreate --> Worker[BackgroundWorker]
  Worker --> YtDlp[yt-dlp YoutubeDL]
  YtDlp --> TempFiles[TempDir Files]
  WebUI --> ApiEvents[GET /api/jobs/{id}/events(SSE)]
  WebUI --> ApiStatus[GET /api/jobs/{id}]
  WebUI --> ApiDownload[GET /api/jobs/{id}/file]
  ApiDownload --> TempFiles
```

### 关键 API 设计（MVP）
- `POST /api/jobs`：支持单条或多条 URL（批量）；返回 job_id 列表。
- `GET /api/jobs/{id}`：返回状态（queued/downloading/finished/failed/expired）、进度、文件信息。
- `GET /api/jobs/{id}/events`：SSE 推送进度事件（可选，但建议做来达到“参考站一样丝滑”）。
- `GET /api/jobs/{id}/file`：下载成品文件（设置 `Content-Disposition`，移动端可直接保存）。
- （可选）`POST /api/info`：先探测并返回 formats（如果要做清晰度选择）。

### cookies 能力（默认关闭）
- 增加配置 `ENABLE_COOKIES=false`（默认）。
- 若开启：
  - 支持上传 `cookies.txt`（Netscape 格式）随 job 传入（仅用于该任务，落盘到 job 临时目录，完成/过期即删）。
  - 或支持 `cookiesfrombrowser`（**仅本地模式**，公网模式不建议）。

### 存储与清理（公网临时存储）
- 每个 job 一个临时目录：`/tmp/fvd/{job_id}/...`
- 清理策略：定时任务（如每 5 分钟）清理超过 TTL（如 1 小时）的任务目录与内存状态。
- 容量/滥用限制（不引入数据库也能做）：
  - 单 IP 并发 job 数限制、最大 URL 数、最大时长/文件大小（通过 yt-dlp info 预估 + 下载中断）。

## 代码组织（从零搭建最小可跑）
- `backend/app/main.py`：FastAPI 入口（路由、静态/模板挂载）
- `backend/app/jobs.py`：JobStore、状态机、TTL 清理
- `backend/app/ydl.py`：yt-dlp 封装（extract_info、download、progress_hooks、错误映射）
- `backend/app/settings.py`：配置（TTL、ENABLE_COOKIES、下载目录、限流参数）
- `backend/app/templates/*.html`：参考站风格页面（首页、任务页/队列）
- `backend/app/static/*`：Logo、插画风装饰、Tailwind 构建产物
- `backend/tests/*`：pytest（尽量不依赖真实下载）
- `docker/Dockerfile`（可选）：公网部署用

## 测试与验证（我会自主执行）
- **单元测试**：
  - URL 列表解析、队列创建、状态机流转、TTL 清理。
  - yt-dlp 封装用 mock（避免 CI 真下视频）。
- **集成验证（本地）**：
  - 用公开可下载的小视频链接跑一次全流程（创建→进度→成品下载）。
  - 批量 3 条链接：并发/排队表现、进度推送是否稳定。
- **手工验收脚本**：提供 5 步验收路径（你最终验收用）。

## 迭代路线（MVP 后）
- 清晰度/格式选择 UI（formats 列表→选择→下载）
- 字幕下载/翻译、视频总结（单独模块，避免污染 MVP）
- 付费能力（按日/按量/会员），以及配额与风控（需要数据库时再引入）
