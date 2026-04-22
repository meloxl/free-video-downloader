# 抖音视频下载问题 - 快速参考指南

## 问题症状
```
ERROR: Unsupported URL: https://www.douyin.com/user/...
```

## 根本原因
提供的链接是**用户主页链接**而非**视频链接**。yt-dlp 只支持直接的视频链接。

---

## 快速解决方案

### ✓ 使用正确的链接格式

| 格式 | 示例 | 状态 |
|------|------|------|
| 短链接 | `https://v.douyin.com/xxxxx/` | ✓ 支持 |
| 视频链接 | `https://www.douyin.com/video/1234567890` | ✓ 支持 |
| `/v/` 格式 | `https://www.douyin.com/v/1234567890` | ✓ 支持 |
| **用户主页** | `https://www.douyin.com/user/xxxxx` | **✗ 不支持** |

### 如何获取正确的链接

1. 打开抖音 App 或网页
2. 找到要下载的**单个视频**
3. 点击右下角"分享"按钮
4. 选择"复制链接"
5. 粘贴到应用中

---

## 代码改进（已实施）

### 1. 改进的错误提示 [`backend/app/main.py:78-85`](backend/app/main.py:78)
- 检测抖音 URL 错误
- 显示友好的中文提示
- 告诉用户正确的链接格式

### 2. 更新的 HTTP 头 [`backend/app/ydl.py:110-117`](backend/app/ydl.py:110)
- Referer 改为 `https://www.douyin.com`
- 添加 30 秒超时配置
- 提高抖音视频识别成功率

### 3. URL 验证逻辑 [`backend/app/main.py:65-80`](backend/app/main.py:65)
- 自动过滤不支持的抖音链接格式
- 保留其他平台的链接
- 提前发现问题

---

## 测试验证

所有改进已通过测试验证：

```
✓ 抖音短链接 - 接受
✓ 抖音视频链接 - 接受
✓ 抖音 /v/ 格式 - 接受
✓ 抖音用户主页 - 拒绝（正确）
✓ TikTok 视频链接 - 接受
✓ YouTube 链接 - 接受
✓ B站链接 - 接受
✓ 错误消息改进 - 有效
```

---

## 运行诊断

如果遇到其他问题，可以运行诊断脚本：

```bash
# 测试特定的抖音链接
python backend/tests/test_douyin_diagnostic.py "https://v.douyin.com/xxxxx/"

# 验证修复方案
python backend/tests/test_douyin_fix_verification.py
```

---

## 常见问题

**Q: 为什么用户主页链接不支持？**
A: 用户主页包含多个视频，需要爬虫模式。当前项目只支持单个视频下载。

**Q: 如何下载用户的所有视频？**
A: 需要使用专门的爬虫工具或启用高级功能。

**Q: 某些视频仍无法下载？**
A: 可能需要登录。启用 cookies 功能：
```bash
FVD_ENABLE_COOKIES=true
FVD_ADMIN_TOKEN=your_token
```

**Q: yt-dlp 版本是否需要更新？**
A: 当前版本 2026.02.04 已是最新。定期更新可获得最新网站支持。

---

## 文件清单

| 文件 | 说明 |
|------|------|
| [`DOUYIN_DIAGNOSTIC_REPORT.md`](DOUYIN_DIAGNOSTIC_REPORT.md) | 完整诊断报告 |
| [`backend/tests/test_douyin_diagnostic.py`](backend/tests/test_douyin_diagnostic.py) | 诊断脚本 |
| [`backend/tests/test_douyin_fix_verification.py`](backend/tests/test_douyin_fix_verification.py) | 验证脚本 |
| [`backend/app/main.py`](backend/app/main.py) | 改进的错误处理和 URL 验证 |
| [`backend/app/ydl.py`](backend/app/ydl.py) | 改进的 yt-dlp 配置 |

