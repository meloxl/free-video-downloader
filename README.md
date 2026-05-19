## Free Video Downloader（万能视频下载器）

基于 **yt-dlp** 的轻量 Web 应用：批量下载、实时进度、AI 视频总结、**Stripe Pro 订阅**。

### 功能概览

| 模块 | 能力 |
|------|------|
| **下载** | 单链接 / 批量队列；SSE 实时进度；临时存储 + 自动清理 |
| **平台** | yt-dlp 通用解析；抖音链接专项支持 |
| **AI 总结** | B 站字幕优先 → ASR 回退 → DeepSeek 结构化总结；模板 `learning` / `course` |
| **导出** | Markdown、Word、字幕 `.txt` |
| **Pro 会员** | Stripe USD 月付/年付；更高并发；**全平台** AI 总结 |
| **安全** | cookies 默认关闭；管理员 Token 控制；Webhook 验签 + 幂等 |

### 快速开始（本地）

```bash
conda activate base   # 或你的 Python 环境
python --version      # 建议 >= 3.10

pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

浏览器打开：**http://127.0.0.1:8000**

### 文档

- 需求分析：`docs/需求分析.md`
- 方案设计（API / 架构 / 配置）：`docs/方案设计.md`

### 环境变量

#### 下载与限流

| 变量 | 默认 | 说明 |
|------|------|------|
| `FVD_DEMO_MODE` | `false` | `true` = 无外网演示下载 |
| `FVD_ENABLE_COOKIES` | `false` | 是否允许上传 cookies |
| `FVD_ADMIN_TOKEN` | — | cookies 所需管理员 Token（头 `X-Admin-Token`） |
| `FVD_TTL_SECONDS` | `3600` | 任务文件保留秒数 |
| `FVD_MAX_URLS_PER_REQUEST` | `20` | 单次最多 URL 数 |
| `FVD_MAX_ACTIVE_JOBS_PER_IP` | `3` | 免费用户同时下载数 |

#### AI 总结（启用时需 DeepSeek Key）

| 变量 | 默认 | 说明 |
|------|------|------|
| `FVD_ENABLE_AI_SUMMARY` | `true` | 总开关 |
| `FVD_SUMMARY_ONLY_BILIBILI` | `true` | 免费用户仅 B 站总结 |
| `FVD_DEEPSEEK_API_KEY` | — | **必填**（非 Demo 模式） |
| `FVD_DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 地址 |
| `FVD_DEEPSEEK_MODEL` | `deepseek-chat` | 模型名 |
| `FVD_MAX_SUMMARY_WORKERS` | `2` | 总结阶段并发 |

#### Stripe Pro 订阅

| 变量 | 说明 |
|------|------|
| `FVD_PUBLIC_BASE_URL` | 站点根 URL，默认 `http://localhost:8000` |
| `FVD_STRIPE_SECRET_KEY` | 服务端密钥 `sk_test_...`（**勿用** `pk_` _publishable key） |
| `FVD_STRIPE_WEBHOOK_SECRET` | Webhook 签名 `whsec_...` |
| `FVD_STRIPE_PRICE_MONTHLY` | 月付 Price ID：`price_...` |
| `FVD_STRIPE_PRICE_YEARLY` | 年付 Price ID：`price_...` |
| `FVD_PRO_MAX_ACTIVE_JOBS_PER_IP` | Pro 并发，默认 `10` |
| `FVD_STRIPE_DEMO_MODE` | `true` = 不调 Stripe，本地模拟开通 |
| `FVD_BILLING_DB_PATH` | 账单 SQLite，默认 `/tmp/fvd/billing.db` |

#### 示例：本地完整配置

```bash
# AI 总结
export FVD_DEEPSEEK_API_KEY="sk-your-deepseek-key"
export FVD_DEEPSEEK_BASE_URL="https://api.deepseek.com"
export FVD_DEEPSEEK_MODEL="deepseek-chat"

# Stripe（Test Mode）
export FVD_PUBLIC_BASE_URL="http://localhost:8000"
export FVD_STRIPE_SECRET_KEY="sk_test_xxxxxxxx"
export FVD_STRIPE_PRICE_MONTHLY="price_xxxxxxxx"   # 注意是 price_ 不是 prod_
export FVD_STRIPE_PRICE_YEARLY="price_xxxxxxxx"
export FVD_STRIPE_WEBHOOK_SECRET="whsec_xxxxxxxx"  # 来自 stripe listen

python -m uvicorn backend.app.main:app --reload --port 8000
```

另开终端转发 Webhook：

```bash
stripe listen --forward-to http://127.0.0.1:8000/api/stripe/webhook
```

测试卡：`4242 4242 4242 4242`（任意未来日期与 CVC）。

### 测试

```bash
python -m pytest backend/tests/test_jobs_api.py backend/tests/test_billing.py -q
```

### 免责声明

请尊重版权与平台规则，仅用于学习研究。下载登录/会员内容有封号风险；本项目**默认关闭** cookies。Stripe 当前为 **Test Mode** 技术对接，未上 Live。
