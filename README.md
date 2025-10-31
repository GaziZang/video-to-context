# 视频转文字系统

基于 **yt-dlp + FFmpeg + OpenAI Whisper** 的开源视频转文字服务，支持异步处理、多平台视频和 **现代化 Web 界面**。

## 🚀 功能特性

- 🌐 **现代化 Web 界面**: 无需命令行，浏览器直接操作 ⭐ 新增
- ✅ **实时进度跟踪**: 任务状态自动更新，进度条可视化 ⭐ 新增
- ✅ **在线查看结果**: 网页直接显示转换文本，支持复制和下载 ⭐ 新增
- ✅ **多平台支持**: YouTube、B站、TikTok、优酷等30+视频平台
- ✅ **高精度识别**: 基于 OpenAI Whisper，支持99种语言
- ✅ **异步处理**: 使用 Celery + Redis 实现高并发异步任务队列
- ✅ **多种输出格式**: 纯文本(txt) 或 带时间戳的字幕(srt)
- ✅ **模型选择**: 支持 tiny/base/small/medium/large 多种模型规模
- ✅ **容器化部署**: Docker Compose 一键启动
- ✅ **RESTful API**: FastAPI 自动生成交互式文档
- ✅ **监控界面**: Flower 实时监控任务状态

## 📸 界面预览

### Web 前端界面
访问 `http://localhost:8000` 即可使用完整的 Web 界面：

**主要功能：**
- 📝 简洁的任务提交表单
- 🎯 实时进度显示和状态更新
- 📊 自动轮询任务处理进度
- 💾 一键复制文本或下载文件
- 📱 响应式设计，支持移动端
- 🎨 现代化 UI 设计

## 📋 系统要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 内存
- 至少 10GB 磁盘空间（用于存储 Whisper 模型）

## 🛠️ 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/GaziZang/video-to-context.git
cd video-to-context
```

### 2. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f
```

## 🌐 访问 Web 界面

启动成功后，访问以下地址确认服务运行：

- **🎨 Web 前端界面**: http://localhost:8000 ⭐ **主要入口**
- **📚 API 文档**: http://localhost:8000/docs
- **🏥 健康检查**: http://localhost:8000/health
- **📊 Flower 监控**: http://localhost:5555

## 📖 使用指南

### 方式一：Web 界面（推荐）

1. 访问 http://localhost:8000
2. 在表单中输入视频链接
3. 选择输出格式和模型大小
4. 点击"开始转换"
5. 实时查看处理进度
6. 完成后在线查看结果或下载文件

**Web 界面功能：**
- 📝 可视化任务提交
- ⏱️ 实时进度显示（下载→处理音频→识别）
- 📊 任务状态自动更新
- 👀 在线预览转换结果
- 📋 一键复制文本到剪贴板
- 💾 下载 TXT 或 SRT 文件
- 🔄 快速开始新任务

### 方式二：API 调用

#### 提交转换任务

```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "output_format": "txt",
    "language": "en",
    "model_size": "small"
  }'
```

**响应示例**:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "created_at": "2025-10-30T12:00:00",
  "message": "任务已提交,正在处理中"
}
```

#### 查询任务状态

```bash
curl -X GET "http://localhost:8000/api/tasks/{task_id}"
```

**完成响应**:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "progress": "处理完成",
  "result": {
    "format": "txt",
    "text": "这是转录的文本内容...",
    "language": "zh",
    "duration": 180.5
  },
  "created_at": "2025-10-30T12:00:00",
  "updated_at": "2025-10-30T12:03:45"
}
```

## 🎯 参数说明

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `video_url` | string | ✅ | - | 视频链接地址 |
| `output_format` | string | ❌ | txt | 输出格式: txt 或 srt |
| `language` | string | ❌ | auto | 语言代码(如 zh, en)，不指定则自动检测 |
| `model_size` | string | ❌ | small | 模型大小: tiny/base/small/medium/large |

### Whisper 模型对比

| 模型 | 内存占用 | 相对速度 | 相对精度 | 适用场景 |
|------|----------|----------|----------|----------|
| **tiny** | ~1 GB | 最快 | 较低 | 快速原型验证 |
| **base** | ~1 GB | 很快 | 低 | 清晰语音、少噪音 |
| **small** | ~2 GB | 中等 | 中等 | ⭐ 推荐: 平衡之选 |
| **medium** | ~5 GB | 较慢 | 高 | 高精度需求 |
| **large** | ~10 GB | 最慢 | 最高 | 专业用途、复杂音频 |

## 🔧 配置说明

### 环境变量

在 `.env` 文件中配置（参考 `.env.example`）：

```bash
REDIS_HOST=redis
REDIS_PORT=6379
DEFAULT_MODEL_SIZE=small
WHISPER_DEVICE=cpu
MAX_FILE_SIZE=500M
```

## 📊 监控和维护

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f web
docker-compose logs -f celery_worker
```

### 重启服务

```bash
docker-compose restart
```

## 🐛 故障排除

### Web 界面无法访问

```bash
# 检查服务状态
docker-compose ps

# 查看 web 服务日志
docker-compose logs web

# 重启 web 服务
docker-compose restart web
```

### 任务一直处于 "处理中"

```bash
# 查看 worker 日志
docker-compose logs celery_worker

# 重启 worker
docker-compose restart celery_worker
```

### 视频下载失败

```bash
# 更新 yt-dlp
docker-compose exec celery_worker yt-dlp -U
```

## 🔐 安全建议

1. **URL 验证**: 已内置基本的 URL 安全检查
2. **文件大小限制**: yt-dlp 限制最大 500MB
3. **任务超时**: 设置了 1 小时超时保护
4. **定期清理**: Redis 任务数据 24 小时自动过期

## 📝 开发说明

### 项目结构

```
.
├── main.py              # FastAPI 应用主文件
├── celery_tasks.py      # Celery 任务定义
├── config.py           # 配置管理
├── index.html          # Web 前端界面
├── requirements.txt     # Python 依赖
├── Dockerfile           # Docker 镜像配置
├── docker-compose.yml   # Docker 编排配置
└── README.md            # 项目文档
```

## 📄 许可证

本项目使用 MIT 许可证

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

## 📞 联系方式

如有问题请提交 Issue 到 GitHub。

---

**注意**: 请确保遵守视频平台的服务条款，仅用于个人学习和合法用途。
