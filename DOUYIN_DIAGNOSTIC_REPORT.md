# 抖音视频下载问题诊断报告

## 问题概述

**错误信息**: `Unsupported URL: https://www.douyin.com/user/...`

**根本原因**: 提供的链接是**用户主页链接**，而不是**视频链接**。yt-dlp 的抖音提取器只支持直接的视频链接，不支持用户主页或其他页面类型。

---

## 诊断结果

### 1. 环境信息
- **yt-dlp 版本**: 2026.02.04 ✓ (最新版本，满足要求 >=2025.1.1)
- **Python 版本**: 3.13.2
- **操作系统**: macOS
- **网络**: 正常（通过代理连接）

### 2. 错误分析

```
ERROR: Unsupported URL: https://www.douyin.com/user/MS4wLjABAAAAvZsQGToYZGFzSJgL5w-8LQ9VC3oziORrGo7js4nrPGWJquop_jMGMZTezeCq2Ipz?from_tab_name=main&modal_id=7581084899554281829
```

**问题类型**: URL 格式不支持

**原因分析**:
- 该 URL 是抖音**用户主页**链接（`/user/` 路径）
- yt-dlp 的抖音提取器只支持**视频链接**（`/video/` 路径）
- 用户主页包含多个视频，需要特殊处理（爬虫模式）

---

## 支持的 URL 格式

### ✓ 支持的格式

| 格式 | 示例 | 说明 |
|------|------|------|
| 短链接 | `https://v.douyin.com/xxxxx/` | 最常见的分享格式 |
| 视频链接 | `https://www.douyin.com/video/1234567890` | 完整视频页面 |
| 短视频链接 | `https://www.douyin.com/v/1234567890` | 另一种视频格式 |

### ✗ 不支持的格式

| 格式 | 示例 | 原因 |
|------|------|------|
| 用户主页 | `https://www.douyin.com/user/xxxxx` | 需要爬虫模式 |
| 话题页面 | `https://www.douyin.com/discover` | 需要爬虫模式 |
| 搜索结果 | `https://www.douyin.com/search` | 需要爬虫模式 |

---

## 解决方案

### 方案 1: 使用正确的视频链接（推荐）

**步骤**:
1. 打开抖音 App 或网页
2. 找到要下载的**单个视频**
3. 点击"分享"按钮
4. 复制短链接（`https://v.douyin.com/...`）或完整链接
5. 在应用中粘贴该链接

**示例**:
```
✓ 正确: https://v.douyin.com/xxxxx/
✓ 正确: https://www.douyin.com/video/1234567890
✗ 错误: https://www.douyin.com/user/xxxxx
```

### 方案 2: 启用 Cookies（针对受限视频）

某些视频可能需要登录才能访问。启用 cookies 功能：

1. 在 `.env` 文件中设置:
```bash
FVD_ENABLE_COOKIES=true
FVD_ADMIN_TOKEN=your_secret_token
```

2. 导出浏览器 cookies 为 `cookies.txt`

3. 上传 cookies 文件进行下载

### 方案 3: 更新 yt-dlp（如果仍有问题）

```bash
pip install --upgrade yt-dlp
```

当前版本 2026.02.04 已是最新，但定期更新可获得最新的网站支持。

---

## 代码修改建议

### 1. 改进错误提示 [`backend/app/main.py`](backend/app/main.py:78-81)

在 [`_human_error`](backend/app/main.py:78) 函数中添加更友好的错误消息：

```python
def _human_error(e: Exception) -> str:
    s = str(e) or e.__class__.__name__
    
    # 针对抖音 URL 的特殊处理
    if "Unsupported URL" in s and "douyin.com" in s:
        return "不支持的抖音链接格式。请使用视频链接（如 https://v.douyin.com/... 或 https://www.douyin.com/video/...）"
    
    return s[:1200]
```

### 2. 改进 yt-dlp 配置 [`backend/app/ydl.py`](backend/app/ydl.py:99-114)

添加抖音特定的配置选项：

```python
ydl_opts: dict[str, Any] = {
    "format": "bestvideo+bestaudio/best",
    "outtmpl": outtmpl,
    "progress_hooks": [on_progress],
    "noplaylist": True,
    "retries": 10,
    "fragment_retries": 10,
    "concurrent_fragment_downloads": 8,
    "quiet": False,
    "no_warnings": False,
    "ignoreerrors": False,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com"  # 改为抖音
    },
    # 抖音特定配置
    "socket_timeout": 30,
    "extractor_args": {
        "douyin": {
            "api_hostname": "api.douyin.com",
        }
    }
}
```

### 3. 添加 URL 验证 [`backend/app/main.py`](backend/app/main.py:65-75)

在 [`_parse_urls`](backend/app/main.py:65) 中添加验证逻辑：

```python
def _parse_urls(raw: str) -> list[str]:
    urls: list[str] = []
    for part in raw.replace("\r", "\n").split("\n"):
        s = part.strip()
        if not s:
            continue
        if len(s) > 2000:
            continue
        if s.startswith("http://") or s.startswith("https://"):
            # 抖音 URL 验证
            if "douyin.com" in s or "tiktok.com" in s:
                # 检查是否是视频链接
                if "/video/" in s or "/v/" in s or "v.douyin.com" in s or "v.tiktok.com" in s:
                    urls.append(s)
                # 其他格式会被过滤，返回友好错误
            else:
                urls.append(s)
    return urls
```

---

## 测试验证

### 测试脚本位置
[`backend/tests/test_douyin_diagnostic.py`](backend/tests/test_douyin_diagnostic.py)

### 运行测试

```bash
# 测试有效的视频链接
python backend/tests/test_douyin_diagnostic.py "https://v.douyin.com/xxxxx/"

# 测试完整视频链接
python backend/tests/test_douyin_diagnostic.py "https://www.douyin.com/video/1234567890"
```

---

## 常见问题

### Q: 为什么用户主页链接不支持？
A: 用户主页包含多个视频，需要爬虫模式逐个提取。yt-dlp 的抖音提取器目前只支持单个视频链接。

### Q: 如何下载用户的所有视频？
A: 需要使用专门的爬虫工具或启用高级功能。当前项目不支持此功能。

### Q: 为什么某些视频无法下载？
A: 可能原因：
- 视频已被删除
- 需要登录（启用 cookies）
- 地域限制
- 视频被设为私密

### Q: 如何获取正确的视频链接？
A: 
1. 打开抖音 App
2. 找到要下载的视频
3. 点击右下角"分享"
4. 选择"复制链接"
5. 粘贴到应用中

---

## 总结

| 项目 | 状态 | 说明 |
|------|------|------|
| yt-dlp 版本 | ✓ 正常 | 2026.02.04 是最新版本 |
| 网络连接 | ✓ 正常 | 可以连接到抖音服务器 |
| 代码配置 | ✓ 正常 | 配置正确 |
| **用户输入** | **✗ 错误** | **提供的是用户主页链接，不是视频链接** |

**建议**: 请提供正确格式的**视频链接**（如 `https://v.douyin.com/...` 或 `https://www.douyin.com/video/...`）进行测试。

