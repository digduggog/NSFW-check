"""
配置管理模块
从环境变量和配置文件加载所有配置项
"""
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 服务配置
SERVER_PORT = int(os.getenv("SERVER_PORT", "8003"))
MIDDLEWARE_API_KEY = os.getenv("MIDDLEWARE_API_KEY", "")

# 上游配置
UPSTREAM_NORMAL = os.getenv("UPSTREAM_NORMAL", "")
UPSTREAM_FALLBACK = os.getenv("UPSTREAM_FALLBACK", "")
UPSTREAM_NORMAL_KEY = os.getenv("UPSTREAM_NORMAL_KEY", "")
UPSTREAM_FALLBACK_KEY = os.getenv("UPSTREAM_FALLBACK_KEY", "")

# 模型映射文件路径
MODEL_MAPPING_FILE = os.getenv("MODEL_MAPPING_FILE", "model_mapping.json")


def load_model_mapping() -> dict:
    """加载模型名称映射配置"""
    mapping_path = Path(MODEL_MAPPING_FILE)
    if not mapping_path.exists():
        logger.warning(f"模型映射文件不存在: {MODEL_MAPPING_FILE}")
        return {}
    
    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
            logger.info(f"已加载模型映射配置，共 {len(mapping)} 个模型")
            return mapping
    except json.JSONDecodeError as e:
        logger.error(f"模型映射文件格式错误: {e}")
        return {}
    except Exception as e:
        logger.error(f"加载模型映射文件失败: {e}")
        return {}


def get_mapped_model(original_model: str, is_fallback: bool, mapping: dict) -> str:
    """
    获取映射后的模型名称
    
    Args:
        original_model: 原始模型名称
        is_fallback: 是否使用备用上游
        mapping: 模型映射配置
    
    Returns:
        映射后的模型名称，如果没有映射则返回原名
    """
    if original_model not in mapping:
        return original_model
    
    model_config = mapping[original_model]
    target_key = "fallback" if is_fallback else "normal"
    
    return model_config.get(target_key, original_model)


# 验证必要配置
def validate_config():
    """验证必要的配置项是否已设置"""
    errors = []
    
    if not UPSTREAM_NORMAL:
        errors.append("UPSTREAM_NORMAL 未配置")
    if not UPSTREAM_FALLBACK:
        errors.append("UPSTREAM_FALLBACK 未配置")
    
    if errors:
        for error in errors:
            logger.error(error)
        raise ValueError("配置验证失败: " + ", ".join(errors))
    
    logger.info("配置验证通过")
    logger.info(f"正常上游: {UPSTREAM_NORMAL}")
    logger.info(f"备用上游: {UPSTREAM_FALLBACK}")
    logger.info(f"服务端口: {SERVER_PORT}")
