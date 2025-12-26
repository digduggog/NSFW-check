"""
代理请求处理模块
负责将请求转发到上游服务
"""
import json
import logging
from typing import AsyncGenerator, Optional
import httpx
from app.config import (
    UPSTREAM_NORMAL, UPSTREAM_FALLBACK,
    UPSTREAM_NORMAL_KEY, UPSTREAM_FALLBACK_KEY,
    load_model_mapping, get_mapped_model
)

logger = logging.getLogger(__name__)

# HTTP 客户端超时配置
TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=300.0,  # 流式响应可能需要较长时间
    write=10.0,
    pool=10.0
)


class UpstreamProxy:
    """上游代理处理器"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.model_mapping = load_model_mapping()
        self._mapping_last_check = 0
        self.last_stream_was_fallback = False  # 追踪最后一次流式请求是否使用了回退
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
    
    def reload_model_mapping(self):
        """重新加载模型映射配置"""
        self.model_mapping = load_model_mapping()
    
    def _get_upstream_config(self, use_fallback: bool) -> tuple:
        """
        获取上游配置
        
        Returns:
            (上游地址, API Key)
        """
        if use_fallback:
            return UPSTREAM_FALLBACK, UPSTREAM_FALLBACK_KEY
        return UPSTREAM_NORMAL, UPSTREAM_NORMAL_KEY
    
    def _prepare_request(
        self,
        request_body: dict,
        use_fallback: bool,
        original_headers: dict
    ) -> tuple:
        """
        准备转发请求
        
        Returns:
            (目标URL, 请求头, 请求体)
        """
        upstream_url, api_key = self._get_upstream_config(use_fallback)
        
        # 映射模型名称
        original_model = request_body.get("model", "")
        mapped_model = get_mapped_model(original_model, use_fallback, self.model_mapping)
        
        if mapped_model != original_model:
            logger.info(f"模型映射: {original_model} -> {mapped_model}")
            request_body = request_body.copy()
            request_body["model"] = mapped_model
        
        # 构建目标 URL
        target_url = f"{upstream_url.rstrip('/')}/v1/chat/completions"
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else original_headers.get("authorization", "")
        }
        
        # 保留部分原始请求头
        for key in ["user-agent", "x-request-id"]:
            if key in original_headers:
                headers[key] = original_headers[key]
        
        return target_url, headers, request_body
    
    async def forward_request(
        self,
        request_body: dict,
        use_fallback: bool,
        original_headers: dict
    ) -> tuple:
        """
        转发非流式请求
        
        Returns:
            (上游响应, 响应内容JSON, 是否为空响应)
        """
        target_url, headers, body = self._prepare_request(
            request_body, use_fallback, original_headers
        )
        
        upstream_type = "备用" if use_fallback else "正常"
        logger.info(f"转发请求到{upstream_type}上游: {target_url}")
        
        response = await self.client.post(
            target_url,
            json=body,
            headers=headers
        )
        
        logger.info(f"上游响应状态码: {response.status_code}")
        
        # 解析响应内容
        try:
            response_json = response.json()
        except Exception:
            response_json = {"error": response.text}
        
        # 检查响应是否为空
        is_empty = self._is_empty_response(response_json, response.status_code)
        
        return response, response_json, is_empty
    
    def _is_empty_response(self, response_json: dict, status_code: int) -> bool:
        """
        检查响应是否为空
        
        Args:
            response_json: 响应 JSON
            status_code: HTTP 状态码
        
        Returns:
            True 如果响应被认为是空的
        """
        # 非 200 状态码视为需要回退
        if status_code != 200:
            logger.info(f"响应状态码 {status_code}，视为空响应")
            return True
        
        # 检查 choices 是否为空
        choices = response_json.get("choices", [])
        if not choices:
            logger.info("响应 choices 为空")
            return True
        
        # 检查第一个 choice 的 content 是否为空
        first_choice = choices[0] if choices else {}
        message = first_choice.get("message", {})
        content = message.get("content", "")
        
        if not content or content.strip() == "":
            logger.info("响应内容为空")
            return True
        
        return False
    
    async def forward_stream(
        self,
        request_body: dict,
        use_fallback: bool,
        original_headers: dict
    ) -> AsyncGenerator[bytes, None]:
        """
        转发流式请求
        
        Yields:
            流式响应数据块
        """
        target_url, headers, body = self._prepare_request(
            request_body, use_fallback, original_headers
        )
        
        upstream_type = "备用" if use_fallback else "正常"
        logger.info(f"转发流式请求到{upstream_type}上游: {target_url}")
        
        async with self.client.stream(
            "POST",
            target_url,
            json=body,
            headers=headers
        ) as response:
            logger.info(f"上游流式响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                # 如果上游返回错误，读取完整错误信息并返回
                error_content = await response.aread()
                logger.error(f"上游错误响应: {error_content.decode('utf-8', errors='ignore')}")
                yield error_content
                return
            
            async for chunk in response.aiter_bytes():
                yield chunk
    
    async def forward_stream_with_fallback(
        self,
        request_body: dict,
        original_headers: dict
    ) -> AsyncGenerator[bytes, None]:
        """
        转发流式请求，带回退功能
        先请求正常上游，如果响应为空则转向备用上游
        
        Yields:
            流式响应数据块
        """
        # 先尝试正常上游（需要收集完整响应来判断是否为空）
        target_url, headers, body = self._prepare_request(
            request_body, False, original_headers
        )
        
        logger.info(f"转发流式请求到正常上游: {target_url}")
        
        collected_chunks = []
        collected_content = ""
        need_fallback = False
        
        async with self.client.stream(
            "POST",
            target_url,
            json=body,
            headers=headers
        ) as response:
            logger.info(f"正常上游流式响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                # 如果上游返回错误，需要回退
                error_content = await response.aread()
                logger.warning(f"正常上游返回错误，准备回退到备用上游")
                need_fallback = True
            else:
                # 收集所有响应块
                async for chunk in response.aiter_bytes():
                    collected_chunks.append(chunk)
                    # 尝试从 SSE 数据中提取内容
                    try:
                        chunk_str = chunk.decode('utf-8', errors='ignore')
                        for line in chunk_str.split('\n'):
                            if line.startswith('data: ') and line != 'data: [DONE]':
                                data = json.loads(line[6:])
                                choices = data.get('choices', [])
                                if choices:
                                    delta = choices[0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        collected_content += content
                    except Exception:
                        pass
                
                # 检查收集的内容是否为空
                if not collected_content.strip():
                    logger.warning(f"正常上游响应内容为空，准备回退到备用上游")
                    need_fallback = True
        
        if need_fallback:
            # 回退到备用上游
            self.last_stream_was_fallback = True
            logger.info("执行回退：转发流式请求到备用上游")
            async for chunk in self.forward_stream(request_body, True, original_headers):
                yield chunk
        else:
            # 返回已收集的正常上游响应
            self.last_stream_was_fallback = False
            logger.info("正常上游响应有效，返回收集的响应")
            for chunk in collected_chunks:
                yield chunk
    
    async def forward_models_request(
        self,
        original_headers: dict,
        use_fallback: bool = False
    ) -> httpx.Response:
        """
        转发模型列表请求
        
        Returns:
            上游响应
        """
        upstream_url, api_key = self._get_upstream_config(use_fallback)
        target_url = f"{upstream_url.rstrip('/')}/v1/models"
        
        headers = {
            "Authorization": f"Bearer {api_key}" if api_key else original_headers.get("authorization", "")
        }
        
        logger.info(f"转发模型列表请求: {target_url}")
        
        response = await self.client.get(target_url, headers=headers)
        return response


# 全局代理实例
proxy_instance: Optional[UpstreamProxy] = None


def get_proxy() -> UpstreamProxy:
    """获取代理单例实例"""
    global proxy_instance
    if proxy_instance is None:
        proxy_instance = UpstreamProxy()
    return proxy_instance
