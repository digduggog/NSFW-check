"""
请求统计模块
追踪正常请求、回退请求和各种指标
支持每日统计和数据持久化
"""
import time
import threading
import json
import os
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional, Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# 数据文件路径
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
STATS_FILE = os.path.join(DATA_DIR, "stats_data.json")


@dataclass
class RequestRecord:
    """单次请求记录"""
    timestamp: float
    is_fallback: bool


@dataclass
class HourlyStats:
    """小时统计"""
    total: int = 0
    normal: int = 0
    fallback: int = 0


@dataclass
class DailyStats:
    """每日统计"""
    date: str
    total_requests: int = 0
    total_normal: int = 0
    total_fallback: int = 0
    hourly_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "total_requests": self.total_requests,
            "total_normal": self.total_normal,
            "total_fallback": self.total_fallback,
            "fallback_rate": round(self.total_fallback / self.total_requests * 100, 2) if self.total_requests > 0 else 0,
            "hourly_stats": self.hourly_stats
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DailyStats':
        return cls(
            date=data["date"],
            total_requests=data.get("total_requests", 0),
            total_normal=data.get("total_normal", 0),
            total_fallback=data.get("total_fallback", 0),
            hourly_stats=data.get("hourly_stats", {})
        )


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
        
        # 每日统计
        self._daily_stats: Dict[str, DailyStats] = {}
        
        # 启动时间
        self._start_time = time.time()
        
        # 上次保存时间
        self._last_save_time = time.time()
        self._save_interval = 60  # 每60秒保存一次
        
        # 加载历史数据
        self._load_data()
    
    def _get_today(self) -> str:
        """获取今天的日期字符串"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def _get_current_hour(self) -> str:
        """获取当前小时"""
        return datetime.now().strftime("%H")
    
    def _ensure_daily_stats(self, date: str) -> DailyStats:
        """确保指定日期的统计对象存在"""
        if date not in self._daily_stats:
            self._daily_stats[date] = DailyStats(date=date)
        return self._daily_stats[date]
    
    def _load_data(self) -> None:
        """从文件加载历史数据"""
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 加载每日统计
                for date_str, daily_data in data.get("daily_stats", {}).items():
                    self._daily_stats[date_str] = DailyStats.from_dict(daily_data)
                
                # 加载总计数器（从今天的数据恢复）
                today = self._get_today()
                if today in self._daily_stats:
                    today_stats = self._daily_stats[today]
                    self._total_normal = today_stats.total_normal
                    self._total_fallback = today_stats.total_fallback
                
                logger.info(f"已加载历史统计数据，共 {len(self._daily_stats)} 天")
        except Exception as e:
            logger.warning(f"加载统计数据失败: {e}")
    
    def _save_data(self, force: bool = False) -> None:
        """保存数据到文件"""
        now = time.time()
        if not force and now - self._last_save_time < self._save_interval:
            return
        
        self._last_save_time = now
        
        try:
            # 确保目录存在
            os.makedirs(DATA_DIR, exist_ok=True)
            
            # 只保留最近30天的数据
            cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            filtered_stats = {
                date: stats.to_dict() 
                for date, stats in self._daily_stats.items() 
                if date >= cutoff_date
            }
            
            data = {
                "daily_stats": filtered_stats,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug("统计数据已保存")
        except Exception as e:
            logger.warning(f"保存统计数据失败: {e}")
    
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
            
            # 更新总计数器
            if is_fallback:
                self._total_fallback += 1
                logger.debug(f"记录回退请求，总回退数: {self._total_fallback}")
            else:
                self._total_normal += 1
                logger.debug(f"记录正常请求，总正常数: {self._total_normal}")
            
            # 更新每日统计
            today = self._get_today()
            hour = self._get_current_hour()
            daily_stats = self._ensure_daily_stats(today)
            
            daily_stats.total_requests += 1
            if is_fallback:
                daily_stats.total_fallback += 1
            else:
                daily_stats.total_normal += 1
            
            # 更新小时统计
            if hour not in daily_stats.hourly_stats:
                daily_stats.hourly_stats[hour] = {"total": 0, "normal": 0, "fallback": 0}
            daily_stats.hourly_stats[hour]["total"] += 1
            if is_fallback:
                daily_stats.hourly_stats[hour]["fallback"] += 1
            else:
                daily_stats.hourly_stats[hour]["normal"] += 1
            
            # 清理过期记录
            self._cleanup_old_records(now)
            
            # 尝试保存数据
            self._save_data()
    
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
    
    def get_daily_stats(self, date: str) -> Optional[dict]:
        """
        获取指定日期的统计数据
        
        Args:
            date: 日期字符串，格式 YYYY-MM-DD
            
        Returns:
            当天的统计数据，如果不存在返回 None
        """
        with self._lock:
            if date in self._daily_stats:
                return self._daily_stats[date].to_dict()
            return None
    
    def get_recent_days_stats(self, days: int = 30) -> List[dict]:
        """
        获取近N天的统计概览
        
        Args:
            days: 天数
            
        Returns:
            统计数据列表，按日期降序排列
        """
        with self._lock:
            result = []
            today = datetime.now()
            
            for i in range(days):
                date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                if date in self._daily_stats:
                    result.append(self._daily_stats[date].to_dict())
                else:
                    # 没有数据的日期也返回，方便前端展示
                    result.append({
                        "date": date,
                        "total_requests": 0,
                        "total_normal": 0,
                        "total_fallback": 0,
                        "fallback_rate": 0,
                        "hourly_stats": {}
                    })
            
            return result
    
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
