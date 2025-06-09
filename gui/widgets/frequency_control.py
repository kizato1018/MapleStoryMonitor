"""
Frequency Control Widget Module
頻率控制元件模組
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable


class FrequencyControlWidget:
    """頻率控制元件"""
    
    def __init__(self, parent, config_callback: Optional[Callable] = None):
        self.parent = parent
        self.config_callback = config_callback
        self.frequency_var = tk.StringVar(value="5.0")
        
        if self.config_callback:
            self.frequency_var.trace_add('write''w', lambda *args: self.config_callback())
        
        self._create_widget()
    
    def _create_widget(self):
        """創建頻率控制元件"""
        self.frame = ttk.LabelFrame(self.parent, text="擷取設定", padding=10)
        
        input_frame = ttk.Frame(self.frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="擷取頻率 (FPS):").grid(row=0, column=0, padx=5, sticky='w')
        ttk.Entry(input_frame, textvariable=self.frequency_var, width=10).grid(row=0, column=1, padx=5)
        
        self.freq_label = ttk.Label(self.frame, text="")
        self.freq_label.pack(anchor=tk.W, pady=(5, 0))
        
        self.frequency_var.trace_add('write''w', self._update_freq_label)
        self._update_freq_label()
    
    def _update_freq_label(self, *args):
        """更新頻率標籤"""
        try:
            fps = float(self.frequency_var.get())
            interval = 1.0 / fps if fps > 0 else 0
            self.freq_label.config(text=f"當前頻率: {fps:.1f} FPS (間隔: {interval:.3f}秒)")
        except ValueError:
            self.freq_label.config(text="請輸入有效的數值")
    
    def pack(self, **kwargs):
        """打包元件"""
        self.frame.pack(**kwargs)
    
    def get_frequency(self) -> float:
        """獲取頻率值"""
        try:
            return float(self.frequency_var.get())
        except ValueError:
            return 5.0
    
    def set_frequency(self, fps: float):
        """設定頻率值"""
        self.frequency_var.set(str(fps))
