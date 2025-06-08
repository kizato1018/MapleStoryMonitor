"""
Coin Tracker Widget
楓幣追蹤子元件
"""

import tkinter as tk
from tkinter import ttk
from module.monitor_timer import MonitorTimer
from gui.widgets.base_tracker import TrackerSubWidget
from utils.log import get_logger

logger = get_logger(__name__)


class CoinTrackerWidget(TrackerSubWidget):
    """楓幣追蹤子元件"""
    
    def __init__(self, parent_frame, timer: MonitorTimer):
        super().__init__(parent_frame, "楓幣追蹤", timer)
    
    def _create_content(self):
        """創建楓幣追蹤內容"""
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        self.labels["coin_10min"] = ttk.Label(content_frame, text="10分鐘楓幣: 未啟用")
        self.labels["coin_10min"].pack(anchor=tk.W)
        
        self.labels["total_coin"] = ttk.Label(content_frame, text="總累計楓幣: 未啟用")
        self.labels["total_coin"].pack(anchor=tk.W)
    
    def update_display(self):
        """更新楓幣顯示"""
        if not self.is_enabled() or not self.manager:
            self.labels["coin_10min"].config(text="10分鐘楓幣: 未啟用")
            self.labels["total_coin"].config(text="總累計楓幣: 未啟用")
            return
        
        try:
            coin_10min_data, total_coin_data = self.manager.get_coin_per_10min_data()
            
            if coin_10min_data is not None:
                self.labels["coin_10min"].config(text=f"10分鐘楓幣: {coin_10min_data:,}")
            else:
                self.labels["coin_10min"].config(text="10分鐘楓幣: 計算中...")
            
            if total_coin_data is not None:
                self.labels["total_coin"].config(text=f"總累計楓幣: {total_coin_data:,}")
            else:
                self.labels["total_coin"].config(text="總累計楓幣: 計算中...")
                
        except Exception as e:
            logger.error(f"更新楓幣顯示時發生錯誤: {e}")
