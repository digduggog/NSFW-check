# Content Filter Middleware

一个 API 中间件，用于内容过滤和请求路由。优先请求正常上游，当响应为空时自动回退到备用上游。

## 功能特性

- 🔄 **智能回退**：正常上游响应为空时自动切换到备用上游
- 📊 **实时统计**：WebUI 仪表板展示请求统计和 RPM
- 🔑 **API 鉴权**：可选的中间件 API Key 验证
- 🗺️ **模型映射**：支持为不同上游配置不同的模型名称
- 🐳 **Docker 部署**：开箱即用的 Docker Compose 配置

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/digduggog/NSFW-check.git
cd NSFW-check
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置上游地址和 API Key
```

### 3. Docker 部署

```bash
docker-compose up -d
```

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|-------|
| `SERVER_PORT` | API 服务端口 | 8003 |
| `WEBUI_PORT` | WebUI 仪表板端口 | 8004 |
| `MIDDLEWARE_API_KEY` | 中间件 API Key（留空则不验证） | - |
| `UPSTREAM_NORMAL` | 正常上游地址 | - |
| `UPSTREAM_NORMAL_KEY` | 正常上游 API Key | - |
| `UPSTREAM_FALLBACK` | 备用上游地址 | - |
| `UPSTREAM_FALLBACK_KEY` | 备用上游 API Key | - |
| `MODEL_MAPPING_FILE` | 模型映射配置文件 | model_mapping.json |

## API 端点

- `POST /v1/chat/completions` - 聊天补全接口
- `GET /v1/models` - 获取模型列表
- `GET /health` - 健康检查
- `POST /reload` - 重新加载配置

## WebUI 仪表板

访问8004端口查看实时请求统计仪表板。

## 许可证

MIT License
