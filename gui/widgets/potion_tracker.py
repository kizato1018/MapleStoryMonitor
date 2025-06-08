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
        super().__init__(parent_frame, "藥水追蹤", timer)
    
    def _create_content(self):
        """創建藥水追蹤內容"""
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # 成本設定
        cost_frame = ttk.Frame(content_frame)
        cost_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(cost_frame, text="單價:").pack(side=tk.LEFT)
        self.cost_var = tk.StringVar(value="0")
        cost_entry = ttk.Entry(cost_frame, textvariable=self.cost_var, width=10)
        cost_entry.pack(side=tk.LEFT, padx=2)
        cost_entry.bind('<Return>', self._on_cost_changed)
        cost_entry.bind('<FocusOut>', self._on_cost_changed)
        
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
    
    def _on_cost_changed(self, event=None):
        """成本設定改變時的處理"""
        if self.manager:
            try:
                cost = float(self.cost_var.get())
                self.manager.set_unit_cost(cost)
                logger.info(f"藥水單價已設定為: {cost}")
            except ValueError:
                logger.warning("無效的成本值")
    
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
            potion_10min_data, total_used_data = self.manager.get_potion_per_10min_data()
            
            if potion_10min_data is not None:
                self.labels["potion_10min"].config(text=f"10分鐘使用量: {potion_10min_data:,}")
            else:
                self.labels["potion_10min"].config(text="10分鐘使用量: 計算中...")
            
            if total_used_data is not None:
                self.labels["total_used"].config(text=f"總累計使用量: {total_used_data:,}")
            else:
                self.labels["total_used"].config(text="總累計使用量: 計算中...")
            
            # 成本數據
            cost_10min_data, total_cost_data = self.manager.get_cost_per_10min_data()
            
            if cost_10min_data is not None:
                self.labels["cost_10min"].config(text=f"10分鐘成本: {cost_10min_data:,.0f}")
            else:
                self.labels["cost_10min"].config(text="10分鐘成本: 計算中...")
            
            if total_cost_data is not None:
                self.labels["total_cost"].config(text=f"總累計成本: {total_cost_data:,.0f}")
            else:
                self.labels["total_cost"].config(text="總累計成本: 計算中...")
                
        except Exception as e:
            logger.error(f"更新藥水顯示時發生錯誤: {e}")
