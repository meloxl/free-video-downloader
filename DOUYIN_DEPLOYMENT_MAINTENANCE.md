# 抖音下载器 - 部署与维护指南

## 部署前检查清单

### 代码检查
- [x] [`backend/app/douyin.py`](backend/app/douyin.py) - DouyinParser 实现完整
- [x] [`backend/app/ydl.py`](backend/app/ydl.py) - 集成 Douyin 检测和路由
- [x] [`backend/app/main.py`](backend/app/main.py) - URL 验证集成
- [x] [`backend/tests/test_douyin_integration.py`](backend/tests/test_douyin_integration.py) - 测试套件完整

### 依赖检查
- [x] `requests` - 已在 requirements.txt 中
- [x] 所有标准库依赖可用
- [x] 无新增外部依赖

### 功能检查
- [x] URL 检测正常
- [x] API 可访问
- [x] 视频 ID 提取正确
- [x] 错误处理完整
- [x] 降级机制就绪

### 安全检查
- [x] 无硬编码凭证
- [x] 无用户数据收集
- [x] 输入验证完整
- [x] 异常处理安全

---

## 部署步骤

### 1. 代码部署

```bash
# 1.1 更新代码
cd /Users/xl/workspaces/projects/free-video-downloader
git add backend/app/douyin.py backend/app/ydl.py backend/app/main.py
git add backend/tests/test_douyin_integration.py
git commit -m "feat: integrate DouyinParser for public API-based video downloads"

# 1.2 验证部署
python3 backend/tests/test_douyin_integration.py
```

### 2. 环境配置

```bash
# 2.1 确保依赖已安装
pip install -r backend/requirements.txt

# 2.2 验证 requests 库
python3 -c "import requests; print(f'requests {requests.__version__}')"
```

### 3. 应用启动

```bash
# 3.1 启动应用
cd /Users/xl/workspaces/projects/free-video-downloader
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 3.2 验证应用运行
curl http://localhost:8000/
```

### 4. 功能验证

```bash
# 4.1 测试 Douyin URL 下载
curl -X POST http://localhost:8000/api/jobs \
  -F "urls=https://v.douyin.com/iXXXXXXX/"

# 4.2 检查任务状态
curl http://localhost:8000/api/jobs/{job_id}

# 4.3 下载文件
curl http://localhost:8000/api/jobs/{job_id}/file -o video.mp4
```

---

## 监控与日志

### 日志配置

```python
# backend/app/douyin.py 中已配置
import logging
logger = logging.getLogger("douyin")

# 启用日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 关键日志点

| 位置 | 日志 | 说明 |
|------|------|------|
| `_fetch_item_info()` | "公开API获取失败" | API 失败，准备降级 |
| `_fetch_via_api()` | "API 返回空数据" | 视频不存在或已删除 |
| `_fetch_via_share_page()` | "无法从分享页提取数据" | 分享页解析失败 |
| `_download_file()` | "文件下载失败" | 下载异常 |

### 监控指标

```python
# 建议监控的指标
metrics = {
    "total_downloads": 0,           # 总下载数
    "successful_downloads": 0,      # 成功下载数
    "failed_downloads": 0,          # 失败下载数
    "api_success_rate": 0.0,        # API 成功率
    "average_download_time": 0.0,   # 平均下载时间
    "average_file_size": 0.0,       # 平均文件大小
}
```

---

## 故障排查

### 问题 1: "Fresh cookies (not necessarily logged in) are needed"

**症状**: 下载失败，错误信息包含 "Fresh cookies"

**原因**: yt-dlp 的 Douyin 提取器被调用

**解决步骤**:
1. 检查 `is_douyin_url()` 是否正确识别 URL
2. 检查 `download_url()` 中的路由逻辑
3. 查看日志确认是否进入 `_download_douyin()`

**验证**:
```bash
python3 << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.douyin import is_douyin_url
from app.ydl import download_url

url = "https://v.douyin.com/iXXXXXXX/"
print(f"is_douyin_url: {is_douyin_url(url)}")
print(f"Should use DouyinParser: {is_douyin_url(url)}")
EOF
```

### 问题 2: "Failed to parse JSON"

**症状**: API 返回无效 JSON

**原因**: 
- 网络连接问题
- API 端点不可访问
- 视频 ID 无效

**解决步骤**:
1. 检查网络连接
2. 测试 API 端点可访问性
3. 验证视频 ID 格式

**验证**:
```bash
python3 << 'EOF'
import sys
sys.path.insert(0, 'backend')
from app.douyin import DouyinParser

parser = DouyinParser()
try:
    resp = parser.session.get(
        parser.API_URL,
        params={"item_ids": "7123456789012345"},
        timeout=(10, 30)
    )
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('Content-Type')}")
    print(f"Response: {resp.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
EOF
```

### 问题 3: "无法从链接中提取视频ID"

**症状**: URL 格式不支持

**原因**: URL 格式不在支持列表中

**解决步骤**:
1. 检查 URL 格式是否正确
2. 使用支持的 URL 格式
3. 如需支持新格式，修改 `_extract_video_id()`

**支持的格式**:
```
✓ https://v.douyin.com/iXXXXXXX/
✓ https://www.douyin.com/video/7123456789
✓ https://www.iesdouyin.com/share/video/7123456789/
✓ https://www.douyin.com/note/7123456789
✓ https://m.douyin.com/video/7123456789
```

### 问题 4: 下载速度慢

**症状**: 下载耗时过长

**原因**:
- 网络连接慢
- 抖音服务器响应慢
- 文件过大

**优化方案**:
1. 检查网络连接
2. 增加超时时间
3. 使用代理加速

**配置**:
```python
# 修改 backend/app/douyin.py
self.timeout = (15, 60)  # 增加超时时间
```

### 问题 5: 内存占用过高

**症状**: 下载大文件时内存占用过高

**原因**: 块大小设置过大

**优化方案**:
```python
# 修改 backend/app/douyin.py 中的 _download_file()
chunk_size = 32 * 1024  # 减小块大小到 32KB
```

---

## 性能优化

### 1. 连接池优化

```python
# 增加连接池大小
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=10,
    max_retries=Retry(total=3, backoff_factor=0.5)
)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

### 2. 并发优化

```python
# backend/app/main.py
executor = ThreadPoolExecutor(max_workers=8)  # 增加并发数
```

### 3. 缓存优化

```python
# 缓存视频元数据
from functools import lru_cache

@lru_cache(maxsize=1000)
def _fetch_item_info_cached(video_id: str):
    return self._fetch_item_info(video_id)
```

### 4. 磁盘优化

```python
# 定期清理过期文件
import os
import time

def cleanup_old_files(directory, days=7):
    now = time.time()
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            if os.stat(filepath).st_mtime < now - days * 86400:
                os.remove(filepath)
```

---

## 更新与维护

### 定期检查

**每周**:
- [ ] 检查错误日志
- [ ] 验证 API 可访问性
- [ ] 检查磁盘空间

**每月**:
- [ ] 运行完整测试套件
- [ ] 检查依赖更新
- [ ] 分析性能指标

**每季度**:
- [ ] 代码审查
- [ ] 安全审计
- [ ] 性能优化

### 版本更新

```bash
# 检查 requests 库更新
pip list --outdated

# 更新依赖
pip install --upgrade requests

# 运行测试确保兼容性
python3 backend/tests/test_douyin_integration.py
```

### 备份策略

```bash
# 备份配置和数据
tar -czf backup_$(date +%Y%m%d).tar.gz \
  backend/app/douyin.py \
  backend/app/ydl.py \
  backend/app/main.py \
  downloads/
```

---

## 扩展与定制

### 添加新的 URL 格式

```python
# 在 backend/app/douyin.py 的 _extract_video_id() 中添加

def _extract_video_id(self, url: str) -> str:
    # ... 现有逻辑 ...
    
    # 添加新格式
    for pattern in (
        r"/video/(\d{8,24})",
        r"/note/(\d{8,24})",
        r"/(\d{8,24})(?:/|$)",
        r"/new_format/(\d{8,24})",  # 新格式
    ):
        match = re.search(pattern, parsed.path)
        if match:
            return match.group(1)
```

### 添加新的媒体格式

```python
# 在 backend/app/douyin.py 的 _get_media_url() 中添加

def _get_media_url(self, item_info: dict, mode: str = "video") -> str:
    if mode == "video":
        # ... 现有逻辑 ...
    elif mode == "audio":
        # ... 现有逻辑 ...
    elif mode == "subtitle":
        # 添加字幕支持
        subtitles = item_info.get("subtitle", {})
        subtitle_urls = subtitles.get("url_list", [])
        if not subtitle_urls:
            raise ValueError("未找到字幕")
        return subtitle_urls[0]
    else:
        raise ValueError(f"不支持的模式: {mode}")
```

### 添加代理支持

```python
# 在 backend/app/douyin.py 的 __init__() 中添加

def __init__(self, download_dir: str = "downloads", proxy: str = None):
    self.download_dir = Path(download_dir)
    self.download_dir.mkdir(parents=True, exist_ok=True)
    self.session = requests.Session()
    
    if proxy:
        self.session.proxies = {
            "http": proxy,
            "https": proxy,
        }
    
    self.session.headers.update(DEFAULT_HEADERS)
    self.timeout = (10, 30)
    self.max_retries = 3
```

---

## 故障恢复

### 自动重启

```bash
# 使用 systemd 服务文件
# /etc/systemd/system/douyin-downloader.service

[Unit]
Description=Douyin Video Downloader
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/Users/xl/workspaces/projects/free-video-downloader
ExecStart=/usr/bin/python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 健康检查

```python
# 添加健康检查端点
@app.get("/health")
async def health_check():
    try:
        parser = DouyinParser()
        resp = parser.session.get(
            parser.API_URL,
            params={"item_ids": "test"},
            timeout=(5, 10)
        )
        return {
            "status": "healthy",
            "api_status": resp.status_code == 200
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

---

## 文档维护

### 文档更新清单

- [x] [`DOUYIN_INTEGRATION_SUMMARY.md`](DOUYIN_INTEGRATION_SUMMARY.md) - 集成总结
- [x] [`DOUYIN_VERIFICATION_GUIDE.md`](DOUYIN_VERIFICATION_GUIDE.md) - 验证指南
- [x] [`DOUYIN_TECHNICAL_ARCHITECTURE.md`](DOUYIN_TECHNICAL_ARCHITECTURE.md) - 技术架构
- [x] [`DOUYIN_DEPLOYMENT_MAINTENANCE.md`](DOUYIN_DEPLOYMENT_MAINTENANCE.md) - 部署维护 (本文件)

### 文档同步

```bash
# 定期更新文档
git add DOUYIN_*.md
git commit -m "docs: update Douyin documentation"
git push
```

---

## 支持与反馈

### 报告问题

如遇到问题，请提供以下信息：

1. **错误信息**: 完整的错误堆栈跟踪
2. **URL**: 导致问题的 URL
3. **日志**: 相关的应用日志
4. **环境**: Python 版本、操作系统等

### 功能请求

如需新功能，请说明：

1. **需求描述**: 详细的功能描述
2. **使用场景**: 实际应用场景
3. **优先级**: 功能优先级

---

## 总结

DouyinParser 已成功集成到项目中，提供了：

✓ **无缝集成**: 自动检测 Douyin URL 并使用专用下载器
✓ **无需认证**: 基于公开 API，无需 Cookie 或登录
✓ **高可靠性**: 完整的错误处理和降级机制
✓ **生产就绪**: 经过充分测试，可直接部署
✓ **易于维护**: 清晰的代码结构和完整的文档

系统现在可以处理抖音视频下载，同时保持对其他平台的支持。

---

**最后更新**: 2026-04-22
**版本**: 1.0
**状态**: ✓ 生产就绪
