"""
Potion Tracker Widget
藥水追蹤子元件
"""

import tkinter as tk
from tkinter import ttk
from module.monitor_timer import MonitorTimer
from gui.widgets.base_tracker import TrackerSubWidget
from utils.log import get_logger

logger = get_logger(__name__)


class PotionTrackerWidget(TrackerSubWidget):
    """藥水追蹤子元件"""
    
    def __init__(self, parent_frame, timer: MonitorTimer):
        self.is_total = tk.BooleanVar(value=True)
        super().__init__(parent_frame, "藥水追蹤", timer)
    
    def _create_content(self):
        """創建藥水追蹤內容"""
        self.total_checkbox = ttk.Checkbutton(
            self.checkbox_frame, 
            text="總計", 
            variable=self.is_total,
            command=self.update_display
        )
        self.total_checkbox.pack(side=tk.LEFT, padx=5, pady=2)
        
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # 使用量顯示
        self.labels["potion_10min"] = ttk.Label(content_frame, text="10分鐘使用量: 未啟用")
        self.labels["potion_10min"].pack(anchor=tk.W)
        
        self.labels["total_used"] = ttk.Label(content_frame, text="總累計使用量: 未啟用")
        self.labels["total_used"].pack(anchor=tk.W)
        
        # 成本顯示
        self.labels["cost_10min"] = ttk.Label(content_frame, text="10分鐘成本: 未啟用")
        self.labels["cost_10min"].pack(anchor=tk.W)
        
        self.labels["total_cost"] = ttk.Label(content_frame, text="總累計成本: 未啟用")
        self.labels["total_cost"].pack(anchor=tk.W)
    
    
    def update_display(self):
        """更新藥水顯示"""
        if not self.is_enabled() or not self.manager:
            self.labels["potion_10min"].config(text="10分鐘使用量: 未啟用")
            self.labels["total_used"].config(text="總累計使用量: 未啟用")
            self.labels["cost_10min"].config(text="10分鐘成本: 未啟用")
            self.labels["total_cost"].config(text="總累計成本: 未啟用")
            return
        
        try:
            # 使用量數據
            if self.is_total.get():
                potion_10min_data, total_used_data = self.manager.get_potion_per_10min_total_data()
                potion_10min_text = f"{potion_10min_data:,}" if potion_10min_data is not None else "計算中..."
                total_used_text = f"{total_used_data:,}" if total_used_data is not None else "計算中..."
            else:
                potion_10min_data, total_used_data = self.manager.get_potion_per_10min_data()
                potion_10min_text = ""
                total_used_text = ""
                for i in range(len(potion_10min_data)):
                    potion_10min_text += f"[{potion_10min_data[i]:,}] " if potion_10min_data[i] is not None else "[0]"
                    total_used_text += f"[{total_used_data[i]:,}] " if total_used_data[i] is not None else "[0]"
            
            self.labels["potion_10min"].config(text=f"10分鐘使用量: {potion_10min_text}")
            self.labels["total_used"].config(text=f"總累計使用量: {total_used_text}")
            
            # 成本數據
            if self.is_total.get():
                cost_10min_data, total_cost_data = self.manager.get_cost_per_10min_total_data()
                cost_10min_text = f"{cost_10min_data:,}" if cost_10min_data is not None else "計算中..."
                total_cost_text = f"{total_cost_data:,}" if total_cost_data is not None else "計算中..."
            else:
                cost_10min_data, total_cost_data = self.manager.get_cost_per_10min_data()
                cost_10min_text = ""
                total_cost_text = ""
                for i in range(len(cost_10min_data)):
                    cost_10min_text += f"[{cost_10min_data[i]:,}] " if cost_10min_data[i] is not None else "[0]"
                    total_cost_text += f"[{total_cost_data[i]:,}] " if total_cost_data[i] is not None else "[0]"
            
            self.labels["cost_10min"].config(text=f"10分鐘成本: {cost_10min_text}")
            self.labels["total_cost"].config(text=f"總累計成本: {total_cost_text}")
            
        except Exception as e:
            logger.error(f"更新藥水顯示時發生錯誤: {e}")
