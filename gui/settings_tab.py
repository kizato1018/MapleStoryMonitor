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
        self.window_pinned_var = None
        self.window_transparency_var = None
        self.tab_visibility_vars = None
        self.shared_window_widget = None
        
        # GUI組件
        self.fps_label = None
        self.transparency_label = None
        
    def set_variables(self, shared_fps_var, show_status_var, show_tracker_var, tab_visibility_vars, window_pinned_var=None, window_transparency_var=None):
        """設定從主視窗傳入的變數"""
        self.fps_var = shared_fps_var
        self.show_status_var = show_status_var
        self.show_tracker_var = show_tracker_var
        self.tab_visibility_vars = tab_visibility_vars
        self.window_pinned_var = window_pinned_var
        self.window_transparency_var = window_transparency_var
        
    def set_callbacks(self, update_status_visibility, update_tracker_visibility, apply_tab_visibility_changes, update_window_pinning=None, update_window_transparency=None):
        """設定回調函數"""
        self.update_status_visibility = update_status_visibility
        self.update_tracker_visibility = update_tracker_visibility
        self.apply_tab_visibility_changes = apply_tab_visibility_changes
        self.update_window_pinning = update_window_pinning
        self.update_window_transparency = update_window_transparency

    def create_tab(self):
        """創建設定標籤頁內容"""
        # 視窗選擇
        window_frame = ttk.LabelFrame(self.parent_frame, text="目標視窗選擇", padding=5)
        window_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 動態導入以避免循環導入
        from gui.widgets.window_selection import WindowSelectionWidget
        self.shared_window_widget = WindowSelectionWidget(window_frame, self.capture_manager, None)
        self.shared_window_widget.pack(fill=tk.X)

        # 全域FPS控制
        fps_frame = ttk.LabelFrame(self.parent_frame, text="全域設定", padding=5)
        fps_frame.pack(fill=tk.X, padx=10, pady=5)
        fps_control_frame = ttk.Frame(fps_frame)
        fps_control_frame.pack(fill=tk.X, pady=2)
        ttk.Label(fps_control_frame, text="擷取頻率 (FPS):").grid(row=0, column=0, padx=2, sticky='w')
        ttk.Entry(fps_control_frame, textvariable=self.fps_var, width=10).grid(row=0, column=1, padx=2)
        self.fps_label = ttk.Label(fps_frame, text="", font=('Arial', 11))
        self.fps_label.pack(anchor=tk.W, pady=(2, 0))
        self._update_fps_label()
        
        # 顯示選項設定
        display_frame = ttk.LabelFrame(self.parent_frame, text="顯示選項", padding=5)
        display_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(
            display_frame,
            text="顯示當前狀態",
            variable=self.show_status_var,
            command=self.update_status_visibility
        ).pack(anchor=tk.W, pady=1)
        
        ttk.Checkbutton(
            display_frame,
            text="顯示追蹤計算器",
            variable=self.show_tracker_var,
            command=self.update_tracker_visibility
        ).pack(anchor=tk.W, pady=1)
        
        if self.window_pinned_var and self.update_window_pinning:
            ttk.Checkbutton(
                display_frame,
                text="釘選視窗到最前方",
                variable=self.window_pinned_var,
                command=self.update_window_pinning
            ).pack(anchor=tk.W, pady=1)
        
        # 視窗透明度控制
        if self.window_transparency_var and self.update_window_transparency:
            transparency_frame = ttk.Frame(display_frame)
            transparency_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(transparency_frame, text="視窗透明度:").pack(side=tk.LEFT, padx=(0, 5))
            
            transparency_scale = ttk.Scale(
                transparency_frame,
                from_=0.2,
                to=1.0,
                orient=tk.HORIZONTAL,
                variable=self.window_transparency_var,
                command=lambda x: self.update_window_transparency()
            )
            transparency_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            
            self.transparency_label = ttk.Label(transparency_frame, text="", font=('Arial', 9))
            self.transparency_label.pack(side=tk.LEFT)
            self._update_transparency_label()
        
        # 分頁顯示設定
        tabs_frame = ttk.LabelFrame(self.parent_frame, text="分頁顯示設定", padding=5)
        tabs_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(tabs_frame, text="選擇要顯示的分頁:", font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(0, 3))
        
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
            checkbox_width = max_text_length * 8 + 40  # 減少padding
            
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
                ).grid(row=row, column=col, sticky='w', padx=5, pady=1)
        
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
            self.fps_label.config(text=f"當前: {fps:.1f} FPS (間隔: {interval:.3f}秒)")
        except ValueError:
            self.fps_label.config(text="請輸入有效的數值")
    
    def _update_transparency_label(self, *args):
        """更新透明度標籤"""
        if not self.transparency_label or not self.window_transparency_var:
            return
            
        try:
            transparency = self.window_transparency_var.get()
            percentage = transparency * 100
            self.transparency_label.config(text=f"{percentage:.0f}%")
        except ValueError:
            self.transparency_label.config(text="N/A")

    def bind_callbacks(self):
        """綁定回調函數"""
        if self.fps_var:
            self.fps_var.trace_add('write', self._update_fps_label)
        if self.window_transparency_var:
            self.window_transparency_var.trace_add('write', self._update_transparency_label)
    
    def get_window_widget(self):
        """獲取視窗選擇控件"""
        return self.shared_window_widget
