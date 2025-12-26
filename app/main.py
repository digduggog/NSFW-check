"""
FastAPI 主应用
API 中间件入口
"""
import logging
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.config import SERVER_PORT, MIDDLEWARE_API_KEY, validate_config
from app.proxy import get_proxy
from app.stats import get_stats

logger = logging.getLogger(__name__)

# API Key 验证
security = HTTPBearer(auto_error=False)


async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    验证 API Key
    如果配置了 MIDDLEWARE_API_KEY，则必须提供正确的 Key
    如果未配置，则跳过验证
    """
    if not MIDDLEWARE_API_KEY:
        # 未配置 API Key，跳过验证
        return None
    
    if not credentials:
        logger.warning("请求缺少 Authorization 头")
        raise HTTPException(status_code=401, detail="Missing API key")
    
    if credentials.credentials != MIDDLEWARE_API_KEY:
        logger.warning("API Key 验证失败")
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return credentials.credentials


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时验证配置
    validate_config()
    if MIDDLEWARE_API_KEY:
        logger.info("中间件 API Key 验证已启用")
    else:
        logger.warning("中间件 API Key 未配置，所有请求将被放行")
    
    # 启动 WebUI 仪表板（在后台线程）
    from app.webui import run_webui, WEBUI_PORT
    webui_thread = threading.Thread(target=run_webui, daemon=True)
    webui_thread.start()
    logger.info(f"WebUI 仪表板已启动在端口 {WEBUI_PORT}")
    
    logger.info("内容审查中间件已启动")
    
    yield
    
    # 关闭时清理资源
    proxy = get_proxy()
    await proxy.close()
    logger.info("内容审查中间件已关闭")


app = FastAPI(
    title="Content Filter Middleware",
    description="API 中间件，优先请求正常上游，响应为空时自动回退到备用上游",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """健康检查端点（无需鉴权）"""
    return {"status": "healthy"}


@app.get("/v1/models")
async def list_models(request: Request, _: str = Depends(verify_api_key)):
    """获取模型列表（透传上游）"""
    proxy = get_proxy()
    
    headers = dict(request.headers)
    response = await proxy.forward_models_request(headers)
    
    return JSONResponse(
        content=response.json(),
        status_code=response.status_code
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, _: str = Depends(verify_api_key)):
    """
    聊天补全接口
    始终先请求正常上游，如果返回为空则回退到备用上游
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"解析请求体失败: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # 获取代理
    proxy = get_proxy()
    
    # 获取原始请求头
    headers = {k.lower(): v for k, v in request.headers.items()}
    
    # 判断是否为流式请求
    is_stream = body.get("stream", False)
    
    # 获取统计器
    stats = get_stats()
    
    if is_stream:
        # 流式响应：使用带回退的流式方法
        logger.info("处理流式请求，先尝试正常上游")
        
        async def stream_with_stats():
            """包装流式响应，记录统计数据"""
            is_fallback = False
            async for chunk in proxy.forward_stream_with_fallback(body, headers):
                # 检测是否发生了回退（通过日志或标记）
                yield chunk
            # 流结束后记录统计（通过 proxy 的回退标记）
            stats.record_request(proxy.last_stream_was_fallback)
        
        return StreamingResponse(
            stream_with_stats(),
            media_type="text/event-stream"
        )
    else:
        # 非流式响应：先请求正常上游
        logger.info("处理非流式请求，先尝试正常上游")
        response, response_json, is_empty = await proxy.forward_request(body, False, headers)
        
        if is_empty:
            # 正常上游返回为空，回退到备用上游
            logger.warning("正常上游响应为空，回退到备用上游")
            response, response_json, _ = await proxy.forward_request(body, True, headers)
            stats.record_request(is_fallback=True)
        else:
            stats.record_request(is_fallback=False)
        
        return JSONResponse(
            content=response_json,
            status_code=response.status_code
        )


@app.post("/reload")
async def reload_config(_: str = Depends(verify_api_key)):
    """
    重新加载配置（模型映射）
    """
    proxy = get_proxy()
    proxy.reload_model_mapping()
    
    logger.info("配置已手动重新加载")
    return {"status": "reloaded"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=SERVER_PORT,
        log_level="info"
    )
