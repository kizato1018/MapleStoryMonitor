"""
Common Utilities Module
共用工具函數模組
"""

import threading
import time
from typing import Any, Callable, Optional
from utils.log import get_logger

logger = get_logger(__name__)


def safe_call(func: Callable, *args, **kwargs) -> Any:
    """
    安全調用函數，捕獲異常
    
    Args:
        func: 要調用的函數
        *args: 位置參數
        **kwargs: 關鍵字參數
    
    Returns:
        函數返回值，如果發生異常則返回None
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"安全調用錯誤 {func.__name__}: {e}")
        return None


def create_daemon_thread(target: Callable, *args, **kwargs) -> threading.Thread:
    """
    創建守護進程線程
    
    Args:
        target: 目標函數
        *args: 位置參數
        **kwargs: 關鍵字參數
    
    Returns:
        threading.Thread: 配置好的線程對象
    """
    thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    return thread


class PerformanceTimer:
    """性能計時器"""
    
    def __init__(self, name: str = "Timer"):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def start(self) -> None:
        """開始計時"""
        self.start_time = time.time()
    
    def stop(self) -> float:
        """
        停止計時
        
        Returns:
            float: 經過的時間（秒）
        """
        self.end_time = time.time()
        if self.start_time is None:
            return 0.0
        return self.end_time - self.start_time
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = self.stop()
        logger.debug(f"{self.name}: {elapsed:.4f}秒")


class FrequencyController:
    """頻率控制器"""
    
    def __init__(self, fps: float = 5.0):
        self.fps = fps
        self.last_time = 0.0
    
    def set_fps(self, fps: float) -> None:
        """設定FPS"""
        self.fps = max(0.1, fps)  # 最小0.1 FPS
    
    def wait(self) -> None:
        """等待到下一個幀時間"""
        if self.fps <= 0:
            return
        
        current_time = time.time()
        frame_time = 1.0 / self.fps
        elapsed = current_time - self.last_time
        
        if elapsed < frame_time:
            sleep_time = frame_time - elapsed
            time.sleep(sleep_time)
        
        self.last_time = time.time()
    
    def should_process(self) -> bool:
        """
        檢查是否應該處理下一幀
        
        Returns:
            bool: 是否應該處理
        """
        if self.fps <= 0:
            return True
        
        current_time = time.time()
        frame_time = 1.0 / self.fps
        elapsed = current_time - self.last_time
        
        if elapsed >= frame_time:
            self.last_time = current_time
            return True
        
        return False


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    將值限制在指定範圍內
    
    Args:
        value: 要限制的值
        min_val: 最小值
        max_val: 最大值
    
    Returns:
        float: 限制後的值
    """
    return max(min_val, min(value, max_val))


def format_size(size: int) -> str:
    """
    格式化檔案大小
    
    Args:
        size: 檔案大小（字節）
    
    Returns:
        str: 格式化後的大小字符串
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def validate_region(x: int, y: int, w: int, h: int, 
                   max_width: Optional[int] = None, 
                   max_height: Optional[int] = None) -> tuple:
    """
    驗證並修正區域座標
    
    Args:
        x, y: 區域左上角座標
        w, h: 區域寬度和高度
        max_width, max_height: 最大寬度和高度限制
    
    Returns:
        tuple: 修正後的 (x, y, w, h)
    """
    # 確保座標為非負數
    x = max(0, x)
    y = max(0, y)
    w = max(1, w)  # 寬度至少為1
    h = max(1, h)  # 高度至少為1
    
    # 應用最大尺寸限制
    if max_width is not None:
        if x + w > max_width:
            w = max_width - x
        w = max(1, w)
    
    if max_height is not None:
        if y + h > max_height:
            h = max_height - y
        h = max(1, h)
    
    return x, y, w, h
