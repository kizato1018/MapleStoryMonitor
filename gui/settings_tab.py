"""
Settings Tab Module
設定標籤頁模組
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable, Any
from utils.log import get_logger

logger = get_logger(__name__)


class SettingsTab:
    """設定標籤頁類"""
    
    def __init__(self, parent_frame, capture_manager, config_callback: Callable = None):
        self.parent_frame = parent_frame
        self.capture_manager = capture_manager
        self.config_callback = config_callback
        
        # 將從主視窗傳入的變數
        self.fps_var = None
        self.show_status_var = None
        self.show_tracker_var = None
        self.tab_visibility_vars = None
        self.shared_window_widget = None
        
        # GUI組件
        self.fps_label = None
        
    def set_variables(self, shared_fps_var, show_status_var, show_tracker_var, tab_visibility_vars):
        """設定從主視窗傳入的變數"""
        self.fps_var = shared_fps_var
        self.show_status_var = show_status_var
        self.show_tracker_var = show_tracker_var
        self.tab_visibility_vars = tab_visibility_vars
        
    def set_callbacks(self, update_status_visibility, update_tracker_visibility, apply_tab_visibility_changes):
        """設定回調函數"""
        self.update_status_visibility = update_status_visibility
        self.update_tracker_visibility = update_tracker_visibility
        self.apply_tab_visibility_changes = apply_tab_visibility_changes
        
    def create_tab(self):
        """創建設定標籤頁內容"""
        # 視窗選擇
        window_frame = ttk.LabelFrame(self.parent_frame, text="目標視窗選擇", padding=10)
        window_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 動態導入以避免循環導入
        from gui.widgets.window_selection import WindowSelectionWidget
        self.shared_window_widget = WindowSelectionWidget(window_frame, self.capture_manager, None)
        self.shared_window_widget.pack(fill=tk.X)

        # 全域FPS控制
        fps_frame = ttk.LabelFrame(self.parent_frame, text="全域設定", padding=10)
        fps_frame.pack(fill=tk.X, padx=20, pady=10)
        fps_control_frame = ttk.Frame(fps_frame)
        fps_control_frame.pack(fill=tk.X, pady=5)
        ttk.Label(fps_control_frame, text="擷取頻率 (FPS):").grid(row=0, column=0, padx=5, sticky='w')
        ttk.Entry(fps_control_frame, textvariable=self.fps_var, width=10).grid(row=0, column=1, padx=5)
        self.fps_label = ttk.Label(fps_frame, text="")
        self.fps_label.pack(anchor=tk.W, pady=(5, 0))
        self._update_fps_label()
        
        # 顯示選項設定
        display_frame = ttk.LabelFrame(self.parent_frame, text="顯示選項", padding=10)
        display_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Checkbutton(
            display_frame,
            text="顯示當前狀態",
            variable=self.show_status_var,
            command=self.update_status_visibility
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Checkbutton(
            display_frame,
            text="顯示追蹤計算器",
            variable=self.show_tracker_var,
            command=self.update_tracker_visibility
        ).pack(anchor=tk.W, pady=2)
        
        # 分頁顯示設定
        tabs_frame = ttk.LabelFrame(self.parent_frame, text="分頁顯示設定", padding=10)
        tabs_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(tabs_frame, text="選擇要顯示的分頁:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        tabs_checkboxes_frame = ttk.Frame(tabs_frame)
        tabs_checkboxes_frame.pack(fill=tk.X)
        
        # 根據視窗寬度自適應布局
        def update_layout():
            # 獲取frame的實際寬度
            tabs_checkboxes_frame.update_idletasks()
            frame_width = tabs_checkboxes_frame.winfo_width()
            
            # 估算每個checkbox的寬度（包含文字和padding）
            # 根據最長的標籤名稱估算
            max_text_length = max(len(tab_name) for tab_name in self.tab_visibility_vars.keys())
            checkbox_width = max_text_length * 8 + 50  # 8像素每字符 + 50像素padding
            
            # 計算可容納的列數，最少1列，最多6列
            if frame_width > 0:
                cols = max(1, min(6, frame_width // checkbox_width))
            else:
                cols = 3  # 默認值
            
            # 清除現有的checkbox
            for widget in tabs_checkboxes_frame.winfo_children():
                widget.destroy()
            
            # 重新創建checkbox
            for i, (tab_name, var) in enumerate(self.tab_visibility_vars.items()):
                row = i // cols
                col = i % cols
                ttk.Checkbutton(
                    tabs_checkboxes_frame,
                    text=tab_name,
                    variable=var,
                    command=self.apply_tab_visibility_changes
                ).grid(row=row, column=col, sticky='w', padx=10, pady=2)
        
        # 初始布局
        self.parent_frame.after(100, update_layout)  # 延遲執行以確保frame已經渲染
        
        # 綁定視窗大小變化事件
        self.parent_frame.bind('<Configure>', lambda e: update_layout())
        
        return self.shared_window_widget
    
    def _update_fps_label(self, *args):
        """更新全域FPS標籤"""
        if not self.fps_label or not self.fps_var:
            return
            
        try:
            fps = float(self.fps_var.get())
            interval = 1.0 / fps if fps > 0 else 0
            self.fps_label.config(text=f"當前頻率: {fps:.1f} FPS (間隔: {interval:.3f}秒)")
        except ValueError:
            self.fps_label.config(text="請輸入有效的數值")
    
    def bind_callbacks(self):
        """綁定回調函數"""
        if self.fps_var:
            self.fps_var.trace('w', self._update_fps_label)
    
    def get_window_widget(self):
        """獲取視窗選擇控件"""
        return self.shared_window_widget
