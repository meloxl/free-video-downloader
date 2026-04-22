# Bilibili 视频下载 403 错误修复

## 问题描述
Bilibili 视频下载返回 HTTP 403 Forbidden 错误，导致下载失败。

## 根本原因
Bilibili 的反爬虫机制对请求头进行了严格验证。原代码中的 HTTP 请求头配置不适合 Bilibili：
- `Referer` 被设置为 `https://www.douyin.com`（抖音域名）
- 缺少必要的请求头如 `Origin`、`Accept-Language` 等
- User-Agent 使用的是 macOS 标识，不够通用

## 解决方案
修改 [`backend/app/ydl.py:99-127`](backend/app/ydl.py:99) 中的 HTTP 请求头配置：

### 关键改动
1. **动态 Referer 设置**：根据 URL 源自动选择正确的 Referer
   - Bilibili URL → `https://www.bilibili.com/`
   - 其他 URL → `https://www.douyin.com`（保持向后兼容）

2. **增强的请求头**：添加更完整的 HTTP 请求头
   - `Origin`: 与 Referer 对应的源
   - `Accept`: 标准的 HTML 接受类型
   - `Accept-Language`: 中文优先
   - `Accept-Encoding`: 支持压缩
   - `DNT`: 隐私保护标志
   - `Connection`: keep-alive
   - `Upgrade-Insecure-Requests`: 安全升级

3. **更通用的 User-Agent**：使用 Windows 标识而非 macOS
   - 从：`Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...`
   - 到：`Mozilla/5.0 (Windows NT 10.0; Win64; x64)...`

## 测试结果
✓ Bilibili 视频下载成功
✓ YouTube 视频下载仍正常工作
✓ 所有现有单元测试通过
✓ 向后兼容性保持

## 验证命令
```bash
# 测试 Bilibili 下载
python3 -c "
from backend.app.ydl import download_url
import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    output_path, display_name = download_url(
        url='https://www.bilibili.com/video/BV1dW4tz9E5M/?vd_source=8861a1451f98abce9448199c9c55348d',
        job_dir=tmpdir,
        on_progress=lambda d: None,
        cookies_path=None
    )
    print(f'✓ Success: {display_name}')
"

# 运行单元测试
pytest backend/tests/test_jobs_api.py -v
```

## 影响范围
- 修改文件：`backend/app/ydl.py`
- 修改行数：29 行（99-127）
- 向后兼容：✓ 是
- 破坏性改动：✗ 否
