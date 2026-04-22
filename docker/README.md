## Docker 部署（公网）

### 构建

```bash
docker build -f docker/Dockerfile -t free-video-downloader:latest .
```

### 运行

```bash
docker run --rm -p 8000:8000 \
  -e FVD_TTL_SECONDS=3600 \
  -e FVD_MAX_URLS_PER_REQUEST=20 \
  -e FVD_MAX_ACTIVE_JOBS_PER_IP=3 \
  free-video-downloader:latest
```

### cookies（默认关闭）
如需开启（不建议公网默认开启）：

```bash
docker run --rm -p 8000:8000 \
  -e FVD_ENABLE_COOKIES=true \
  -e FVD_ADMIN_TOKEN=change-me \
  free-video-downloader:latest
```

调用时携带请求头 `X-Admin-Token: change-me`，并上传 `cookies.txt`。

