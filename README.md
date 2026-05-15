## Free Video Downloader

基于 `yt-dlp` 的轻量“万能视频下载”Web 应用（FastAPI）。

### 功能（MVP）

- **单链接 / 批量下载**：支持一次提交多条 URL 队列下载
- **实时进度**：SSE 推送下载进度（前端实时更新）
- **临时存储**：公网部署默认临时保留并自动清理
- **cookies（默认关闭）**：管理员开关开启后，可为单次任务上传 `cookies.txt`

### 快速开始（本地）

1. 安装依赖

```bash
# 推荐使用 conda（mac 默认）
conda activate base

# 确保 python 版本可用（建议 >=3.10；当前代码兼容 3.9+）
python --version

pip install -r backend/requirements.txt
```

1. 启动服务

```bash
uvicorn backend.app.main:app --reload --port 8000
```

1. 打开页面

- `http://127.0.0.1:8000`

### 文档沉淀

- 需求分析：`docs/需求分析.md`
- 方案设计：`docs/方案设计.md`

### 环境变量

- **`FVD_DEMO_MODE`**: `true/false`，默认 `false`；为演示/CI 提供“无外网也能跑通”的下载占位模式
- **`FVD_ENABLE_COOKIES`**: `true/false`，默认 `false`
- **`FVD_ADMIN_TOKEN`**: 开启 cookies 时需要的管理员 Token（请求头 `X-Admin-Token`）
- **`FVD_TTL_SECONDS`**: 临时文件保留时长，默认 3600
- **`FVD_MAX_URLS_PER_REQUEST`**: 单次最多 URL 数，默认 20
- **`FVD_MAX_ACTIVE_JOBS_PER_IP`**: 单 IP 同时进行任务数，默认 3

<br />

export FVD\_DEEPSEEK\_API\_KEY="sk-1d2ba4d0f53a4ce792c5fb05d0936e0c"

export FVD\_DEEPSEEK\_BASE\_URL="<https://api.deepseek.com>"

export FVD\_DEEPSEEK\_MODEL="deepseek-chat"

python -m uvicorn backend.app.main:app --reload

<br />

### 免责声明

请尊重版权与平台规则，仅用于学习研究。下载需要登录/会员的内容有封号风险；本项目默认关闭 cookies 功能。
