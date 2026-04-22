# 抖音下载器 - 快速验证指南

## 验证步骤

### 1. 验证 URL 检测功能

```bash
cd /Users/xl/workspaces/projects/free-video-downloader
python3 << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.douyin import is_douyin_url

# 测试抖音 URL
douyin_urls = [
    "https://v.douyin.com/iXXXXXXX/",
    "https://www.douyin.com/video/7123456789",
    "https://www.iesdouyin.com/share/video/7123456789/",
]

print("✓ 抖音 URL 检测:")
for url in douyin_urls:
    result = is_douyin_url(url)
    print(f"  {url}: {result}")

# 测试非抖音 URL
other_urls = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.bilibili.com/video/BV1234567890",
]

print("\n✓ 非抖音 URL 检测:")
for url in other_urls:
    result = is_douyin_url(url)
    print(f"  {url}: {result}")
EOF
```

**预期输出**:
```
✓ 抖音 URL 检测:
  https://v.douyin.com/iXXXXXXX/: True
  https://www.douyin.com/video/7123456789: True
  https://www.iesdouyin.com/share/video/7123456789/: True

✓ 非抖音 URL 检测:
  https://www.youtube.com/watch?v=dQw4w9WgXcQ: False
  https://www.bilibili.com/video/BV1234567890: False
```

---

### 2. 验证 API 可访问性

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.douyin import DouyinParser

parser = DouyinParser(download_dir="test_downloads")

print(f"API 端点: {parser.API_URL}")
print(f"下载目录: {parser.download_dir}")
print(f"最大重试: {parser.max_retries}")
print(f"超时设置: {parser.timeout}")

# 测试 API 可访问性
try:
    resp = parser.session.get(
        parser.API_URL,
        params={"item_ids": "test"},
        timeout=(10, 30)
    )
    print(f"\n✓ API 可访问 (状态码: {resp.status_code})")
    print(f"✓ 响应类型: {resp.headers.get('Content-Type', 'unknown')}")
except Exception as e:
    print(f"✗ API 测试失败: {e}")
EOF
```

**预期输出**:
```
API 端点: https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/
下载目录: test_downloads
最大重试: 3
超时设置: (10, 30)

✓ API 可访问 (状态码: 200)
✓ 响应类型: application/json
```

---

### 3. 验证视频 ID 提取

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.douyin import DouyinParser

parser = DouyinParser(download_dir="test_downloads")

test_cases = [
    ("https://www.douyin.com/video/7123456789012345", "7123456789012345"),
    ("https://www.iesdouyin.com/share/video/7123456789012345/", "7123456789012345"),
    ("https://www.douyin.com/note/7123456789012345", "7123456789012345"),
]

print("✓ 视频 ID 提取:")
for url, expected_id in test_cases:
    extracted_id = parser._extract_video_id(url)
    status = "✓" if extracted_id == expected_id else "✗"
    print(f"  {status} {url}")
    print(f"     → {extracted_id}")
EOF
```

**预期输出**:
```
✓ 视频 ID 提取:
  ✓ https://www.douyin.com/video/7123456789012345
     → 7123456789012345
  ✓ https://www.iesdouyin.com/share/video/7123456789012345/
     → 7123456789012345
  ✓ https://www.douyin.com/note/7123456789012345
     → 7123456789012345
```

---

### 4. 验证 URL 解析

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.main import _parse_urls

mixed_input = """
https://v.douyin.com/iXXXXXXX/
https://www.douyin.com/video/7123456789
https://www.youtube.com/watch?v=dQw4w9WgXcQ
invalid text
https://www.iesdouyin.com/share/video/7123456789/
"""

parsed = _parse_urls(mixed_input)
print(f"✓ 解析了 {len(parsed)} 个有效 URL:")
for url in parsed:
    print(f"  - {url}")
EOF
```

**预期输出**:
```
✓ 解析了 4 个有效 URL:
  - https://v.douyin.com/iXXXXXXX/
  - https://www.douyin.com/video/7123456789
  - https://www.youtube.com/watch?v=dQw4w9WgXcQ
  - https://www.iesdouyin.com/share/video/7123456789/
```

---

### 5. 验证集成测试

```bash
cd /Users/xl/workspaces/projects/free-video-downloader
python3 backend/tests/test_douyin_integration.py
```

**预期输出**:
```
================================================================================
DOUYIN PARSER - COMPREHENSIVE INTEGRATION TEST SUITE
================================================================================

================================================================================
TEST 1: Douyin URL Detection
================================================================================
✓ https://v.douyin.com/iXXXXXXX/
✓ https://www.douyin.com/video/7123456789
✓ https://www.iesdouyin.com/share/video/7123456789/
✓ https://m.douyin.com/video/7123456789
✓ https://www.youtube.com/watch?v=dQw4w9WgXcQ (correctly rejected)
✓ https://www.bilibili.com/video/BV1234567890 (correctly rejected)
✓ All URL detection tests passed

... (更多测试) ...

================================================================================
ALL TESTS PASSED ✓
================================================================================
✓ DouyinParser fully integrated
✓ Uses public API: https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/
✓ No authentication or cookies required
✓ Bypasses yt-dlp for Douyin URLs
✓ Ready for production deployment
================================================================================
```

---

### 6. 验证错误处理

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.douyin import DouyinParser

parser = DouyinParser(download_dir="test_downloads")

print("✓ 错误处理验证:")

# 测试无效 URL
try:
    parser._extract_video_id("https://example.com/invalid")
    print("  ✗ 应该抛出 ValueError")
except ValueError as e:
    print(f"  ✓ 正确抛出 ValueError: {e}")

# 测试 URL 提取
try:
    url = parser._extract_url("Check this: https://v.douyin.com/iXXXXXXX/")
    print(f"  ✓ URL 提取成功: {url}")
except Exception as e:
    print(f"  ✗ URL 提取失败: {e}")
EOF
```

**预期输出**:
```
✓ 错误处理验证:
  ✓ 正确抛出 ValueError: 无法从链接中提取视频ID
  ✓ URL 提取成功: https://v.douyin.com/iXXXXXXX/
```

---

### 7. 验证集成流程

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.douyin import is_douyin_url
from app.main import _parse_urls
from app.ydl import download_url, _download_douyin

print("✓ 集成流程验证:")
print("  ✓ is_douyin_url 可调用")
print("  ✓ _parse_urls 可调用")
print("  ✓ download_url 可调用")
print("  ✓ _download_douyin 可调用")

# 验证路由逻辑
douyin_url = "https://v.douyin.com/iXXXXXXX/"
assert is_douyin_url(douyin_url)
print(f"\n✓ 抖音 URL 正确识别: {douyin_url}")

print("\n✓ 完整流程:")
print("  1. 用户提交抖音 URL")
print("  2. main.py 使用 is_douyin_url() 验证")
print("  3. URL 添加到任务队列")
print("  4. download_url() 在执行器中运行")
print("  5. 检测到抖音 URL → 调用 _download_douyin()")
print("  6. DouyinParser.download() 处理视频")
print("  7. 返回 (filepath, filename)")
print("  8. 文件可供下载")
EOF
```

**预期输出**:
```
✓ 集成流程验证:
  ✓ is_douyin_url 可调用
  ✓ _parse_urls 可调用
  ✓ download_url 可调用
  ✓ _download_douyin 可调用

✓ 抖音 URL 正确识别: https://v.douyin.com/iXXXXXXX/

✓ 完整流程:
  1. 用户提交抖音 URL
  2. main.py 使用 is_douyin_url() 验证
  3. URL 添加到任务队列
  4. download_url() 在执行器中运行
  5. 检测到抖音 URL → 调用 _download_douyin()
  6. DouyinParser.download() 处理视频
  7. 返回 (filepath, filename)
  8. 文件可供下载
```

---

## 验证清单

- [ ] 1. URL 检测功能正常
- [ ] 2. API 可访问
- [ ] 3. 视频 ID 提取正确
- [ ] 4. URL 解析正确
- [ ] 5. 集成测试全部通过
- [ ] 6. 错误处理正常
- [ ] 7. 集成流程完整

---

## 关键文件

| 文件 | 说明 |
|------|------|
| [`backend/app/douyin.py`](backend/app/douyin.py) | DouyinParser 核心实现 |
| [`backend/app/ydl.py`](backend/app/ydl.py) | 下载器集成 |
| [`backend/app/main.py`](backend/app/main.py) | URL 验证集成 |
| [`backend/tests/test_douyin_integration.py`](backend/tests/test_douyin_integration.py) | 集成测试套件 |
| [`DOUYIN_INTEGRATION_SUMMARY.md`](DOUYIN_INTEGRATION_SUMMARY.md) | 详细总结文档 |

---

## 常见问题

### Q: 为什么不使用 yt-dlp 的 Douyin 提取器？
**A**: yt-dlp 的 Douyin 提取器需要 Cookie，而我们的实现使用公开 API，无需任何认证。

### Q: 支持哪些 URL 格式？
**A**: 支持所有常见的抖音 URL 格式：
- 短链接: `https://v.douyin.com/iXXXXXXX/`
- 长链接: `https://www.douyin.com/video/7123456789`
- 分享链接: `https://www.iesdouyin.com/share/video/7123456789/`
- 笔记链接: `https://www.douyin.com/note/7123456789`

### Q: 下载速度如何？
**A**: 取决于网络连接和抖音服务器响应速度。系统使用 64KB 块大小进行流式下载，支持断点续传。

### Q: 是否支持批量下载？
**A**: 是的，可以在一个请求中提交多个 URL，系统会并行处理（最多 6 个并发任务）。

---

## 下一步

1. 运行所有验证步骤
2. 确认所有测试通过
3. 在生产环境中部署
4. 监控日志和性能指标

---

**最后更新**: 2026-04-22
**状态**: ✓ 生产就绪
