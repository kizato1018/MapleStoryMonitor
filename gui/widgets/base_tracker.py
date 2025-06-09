"""
Base Tracker Widget
追蹤子元件基類
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from module.monitor_timer import MonitorTimer
from utils.log import get_logger

logger = get_logger(__name__)


class TrackerSubWidget:
    """追蹤子元件基類"""
    
    def __init__(self, parent_frame, title: str, timer: MonitorTimer):
        self.parent_frame = parent_frame
        self.title = title
        self.timer = timer
        self.enabled = tk.BooleanVar(value=True)
        self.manager = None
        
        self.main_frame = None
        self.checkbox = None
        self.labels = {}
        
        self._create_widget()
    
    def _create_widget(self):
        """創建子元件UI"""
        self.main_frame = ttk.LabelFrame(self.parent_frame, text=self.title)
        
        # 設定最小寬度
        self.main_frame.configure(width=150)
        self.main_frame.grid_propagate(False)  # 防止自動縮小
        
        # 啟用checkbox
        self.checkbox = ttk.Checkbutton(
            self.main_frame, 
            text="啟用", 
            variable=self.enabled,
            command=self._on_enable_changed
        )
        self.checkbox.pack(anchor=tk.W, padx=5, pady=2)
        
        # 子類別實作具體內容
        self._create_content()
    
    def _create_content(self):
        """子類別實作具體內容 - 需要被重寫"""
        pass
    
    def _on_enable_changed(self):
        """啟用狀態改變時的處理"""
        if self.enabled.get():
            logger.info(f"{self.title} 已啟用")
        else:
            logger.info(f"{self.title} 已停用")
    
    def is_enabled(self) -> bool:
        """檢查是否啟用"""
        return self.enabled.get()
    
    def set_manager(self, manager):
        """設定管理器"""
        self.manager = manager
    
    def update_display(self):
        """更新顯示 - 需要被重寫"""
        pass
    
    def pack(self, **kwargs):
        """打包元件"""
        if self.main_frame:
            self.main_frame.pack(**kwargs)
