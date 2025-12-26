"""
请求统计模块
追踪正常请求、回退请求和各种指标
"""
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RequestRecord:
    """单次请求记录"""
    timestamp: float
    is_fallback: bool


class RequestStats:
    """请求统计器"""
    
    def __init__(self, window_seconds: int = 60):
        """
        初始化统计器
        
        Args:
            window_seconds: 统计窗口大小（秒），用于计算 RPM
        """
        self.window_seconds = window_seconds
        self._records: Deque[RequestRecord] = deque()
        self._lock = threading.Lock()
        
        # 总计数器
        self._total_normal = 0
        self._total_fallback = 0
        
        # 启动时间
        self._start_time = time.time()
    
    def record_request(self, is_fallback: bool) -> None:
        """
        记录一次请求
        
        Args:
            is_fallback: 是否是回退请求
        """
        now = time.time()
        record = RequestRecord(timestamp=now, is_fallback=is_fallback)
        
        with self._lock:
            self._records.append(record)
            
            if is_fallback:
                self._total_fallback += 1
                logger.debug(f"记录回退请求，总回退数: {self._total_fallback}")
            else:
                self._total_normal += 1
                logger.debug(f"记录正常请求，总正常数: {self._total_normal}")
            
            # 清理过期记录
            self._cleanup_old_records(now)
    
    def _cleanup_old_records(self, now: float) -> None:
        """清理超出窗口的旧记录"""
        cutoff = now - self.window_seconds
        while self._records and self._records[0].timestamp < cutoff:
            self._records.popleft()
    
    def get_stats(self) -> dict:
        """
        获取当前统计数据
        
        Returns:
            统计数据字典
        """
        now = time.time()
        
        with self._lock:
            self._cleanup_old_records(now)
            
            # 计算窗口内的请求数
            window_normal = sum(1 for r in self._records if not r.is_fallback)
            window_fallback = sum(1 for r in self._records if r.is_fallback)
            window_total = len(self._records)
            
            # 计算 RPM（每分钟请求数）
            # 基于窗口时间计算
            rpm_normal = window_normal * (60 / self.window_seconds)
            rpm_fallback = window_fallback * (60 / self.window_seconds)
            rpm_total = window_total * (60 / self.window_seconds)
            
            # 计算回退率
            total_requests = self._total_normal + self._total_fallback
            fallback_rate = (self._total_fallback / total_requests * 100) if total_requests > 0 else 0
            
            # 窗口内的回退率
            window_fallback_rate = (window_fallback / window_total * 100) if window_total > 0 else 0
            
            # 运行时间
            uptime_seconds = now - self._start_time
            
            return {
                "total_requests": total_requests,
                "total_normal": self._total_normal,
                "total_fallback": self._total_fallback,
                "fallback_rate": round(fallback_rate, 2),
                "window_seconds": self.window_seconds,
                "window_normal": window_normal,
                "window_fallback": window_fallback,
                "window_total": window_total,
                "window_fallback_rate": round(window_fallback_rate, 2),
                "rpm_normal": round(rpm_normal, 2),
                "rpm_fallback": round(rpm_fallback, 2),
                "rpm_total": round(rpm_total, 2),
                "uptime_seconds": round(uptime_seconds, 0),
                "uptime_formatted": self._format_uptime(uptime_seconds)
            }
    
    def _format_uptime(self, seconds: float) -> str:
        """格式化运行时间"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


# 全局统计实例
_stats_instance: Optional[RequestStats] = None


def get_stats() -> RequestStats:
    """获取统计器单例实例"""
    global _stats_instance
    if _stats_instance is None:
        _stats_instance = RequestStats()
    return _stats_instance
