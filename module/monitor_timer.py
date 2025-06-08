import time
from typing import Optional

class MonitorTimer:
    """負責處理監控時間相關邏輯"""
    
    def __init__(self):
        self.start_time = None
        self.is_tracking = False
        self.is_paused = False
        self.paused_time = 0  # 累計暫停的時間
        self.pause_start_time = None  # 暫停開始時間
        self.last_update_time = None

    def start_tracking(self):
        """開始追蹤時間"""
        current_time = time.time()
        self.start_time = current_time
        self.is_tracking = True
        self.is_paused = False
        self.paused_time = 0
        self.pause_start_time = None
        self.last_update_time = current_time

    def pause_tracking(self):
        """暫停追蹤時間"""
        if self.is_tracking and not self.is_paused:
            self.is_paused = True
            self.pause_start_time = time.time()

    def resume_tracking(self):
        """恢復追蹤時間"""
        if self.is_tracking and self.is_paused:
            self.is_paused = False
            if self.pause_start_time is not None:
                self.paused_time += time.time() - self.pause_start_time
                self.pause_start_time = None

    def stop_tracking(self):
        """停止追蹤時間"""
        self.is_tracking = False
        self.is_paused = False
        self.paused_time = 0
        self.pause_start_time = None

    def reset_tracking(self):
        """重置追蹤時間"""
        self.start_time = None
        self.is_tracking = False
        self.is_paused = False
        self.paused_time = 0
        self.pause_start_time = None
        self.last_update_time = None

    def get_elapsed_time(self) -> Optional[float]:
        """獲取已經過時間（秒），排除暫停時間"""
        if not self.is_tracking or self.start_time is None:
            return None
        
        current_time = time.time()
        total_paused = self.paused_time
        
        # 如果目前正在暫停，加上當前暫停時間
        if self.is_paused and self.pause_start_time is not None:
            total_paused += current_time - self.pause_start_time
        
        return current_time - self.start_time - total_paused

    def update_last_update_time(self):
        """更新最後更新時間"""
        if self.is_tracking and not self.is_paused:
            self.last_update_time = time.time()

    def get_status(self):
        """獲取計時器狀態"""
        return {
            "is_tracking": self.is_tracking,
            "is_paused": self.is_paused,
            "elapsed_time": self.get_elapsed_time(),
            "start_time": self.start_time,
            "last_update_time": self.last_update_time
        }

    def get_current_effective_time(self) -> Optional[float]:
        """獲取當前有效時間（基於計時器的時間基準，考慮暫停）"""
        if not self.is_tracking or self.start_time is None:
            return None
        
        elapsed = self.get_elapsed_time()
        if elapsed is None:
            return self.start_time
        
        # 返回基於起始時間加上有效經過時間的時間點
        return self.start_time + elapsed
