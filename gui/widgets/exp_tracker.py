"""
EXP Tracker Widget
經驗追蹤子元件
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from module.monitor_timer import MonitorTimer
from gui.widgets.base_tracker import TrackerSubWidget
from utils.log import get_logger

logger = get_logger(__name__)


class EXPTrackerWidget(TrackerSubWidget):
    """經驗追蹤子元件"""
    
    def __init__(self, parent_frame, timer: MonitorTimer):
        super().__init__(parent_frame, "經驗追蹤", timer)
    
    def _create_content(self):
        """創建經驗追蹤內容"""
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        self.labels["exp_10min"] = ttk.Label(content_frame, text="10分鐘經驗: 未啟用")
        self.labels["exp_10min"].pack(anchor=tk.W)
        
        self.labels["levelup_time"] = ttk.Label(content_frame, text="預估升級時間: 未啟用")
        self.labels["levelup_time"].pack(anchor=tk.W)
        
        self.labels["total_exp"] = ttk.Label(content_frame, text="總累計經驗: 未啟用")
        self.labels["total_exp"].pack(anchor=tk.W)
    
    def update_display(self):
        """更新經驗顯示"""
        if not self.is_enabled() or not self.manager:
            self.labels["exp_10min"].config(text="10分鐘經驗: 未啟用")
            self.labels["levelup_time"].config(text="預估升級時間: 未啟用")
            self.labels["total_exp"].config(text="總累計經驗: 未啟用")
            return
        
        try:
            status = self.manager.get_status()
            
            # 10分鐘經驗
            exp_10min_data = status.get("exp_10min_data")
            if exp_10min_data:
                exp_value = exp_10min_data.get("exp_value")
                exp_percent = exp_10min_data.get("exp_percent")
                display_text = self._format_exp_display(exp_value, exp_percent, "10分鐘經驗")
                self.labels["exp_10min"].config(text=display_text)
            else:
                self.labels["exp_10min"].config(text="10分鐘經驗: 計算中...")
            
            # 總累計經驗
            total_exp_data = status.get("total_exp_data")
            if total_exp_data:
                exp_value = total_exp_data.get("exp_value")
                exp_percent = total_exp_data.get("exp_percent")
                display_text = self._format_exp_display(exp_value, exp_percent, "總累計經驗")
                self.labels["total_exp"].config(text=display_text)
            else:
                self.labels["total_exp"].config(text="總累計經驗: 計算中...")
            
            # 預估升級時間
            estimated_levelup_data = status.get("estimated_levelup_data")
            if estimated_levelup_data:
                hours = estimated_levelup_data.get("hours", 0)
                minutes = estimated_levelup_data.get("minutes", 0)
                seconds = estimated_levelup_data.get("seconds", 0)
                display_text = self._format_time_display(hours, minutes, seconds)
                self.labels["levelup_time"].config(text=display_text)
            else:
                self.labels["levelup_time"].config(text="預估升級時間: 計算中...")
                
        except Exception as e:
            logger.error(f"更新經驗顯示時發生錯誤: {e}")
    
    def _format_exp_display(self, value: Optional[int], percent: Optional[float], prefix: str) -> str:
        """格式化經驗值顯示"""
        if value is not None and percent is not None:
            return f"{prefix}: {value:,} ({percent:.2f}%)"
        elif percent is not None:
            return f"{prefix}: N/A ({percent:.2f}%)"
        elif value is not None:
            return f"{prefix}: {value:,} (N/A%)"
        else:
            return f"{prefix}: 計算中..."

    def _format_time_display(self, hours: int, minutes: int, seconds: int) -> str:
        """格式化時間顯示"""
        if hours > 0:
            return f"預估升級時間: {hours}小時{minutes}分{seconds}秒"
        elif minutes > 0:
            return f"預估升級時間: {minutes}分{seconds}秒"
        else:
            return f"預估升級時間: {seconds}秒"
