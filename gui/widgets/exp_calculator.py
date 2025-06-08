"""
EXP Calculator Widget
經驗計算器元件
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
import time

class EXPCalculatorWidget:
    """經驗計算器元件"""
    
    def __init__(self, parent, exp_manager=None):
        self.parent = parent
        self.exp_manager = exp_manager
        self.update_callback: Optional[Callable] = None
        
        # UI 元件
        self.start_button = None
        self.exp_10min_label = None
        self.total_exp_label = None
        self.time_label = None
        self.levelup_time_label = None
        
        self._create_widget()
    
    def _create_widget(self):
        """創建經驗計算器控制元件"""
        # 控制按鈕區域
        control_frame = ttk.Frame(self.parent)
        control_frame.pack(fill=tk.X, pady=5)
        
        # 將按鈕移到左邊
        ttk.Button(control_frame, text="重置", command=self._reset_tracking).pack(side=tk.LEFT, padx=5)
        self.start_button = ttk.Button(control_frame, text="開始", command=self._toggle_tracking)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 結果顯示區域
        result_frame = ttk.Frame(self.parent)
        result_frame.pack(fill=tk.X, pady=5)
        
        # 10分鐘經驗顯示
        self.exp_10min_label = ttk.Label(result_frame, text="10分鐘經驗: 未開始追蹤")
        self.exp_10min_label.pack(anchor=tk.W)
        
        # 預估升級時間顯示
        self.levelup_time_label = ttk.Label(result_frame, text="預估升級時間: 未開始追蹤")
        self.levelup_time_label.pack(anchor=tk.W)
        
        # 空行分隔
        ttk.Label(result_frame, text="").pack(anchor=tk.W)
        
        # 總累計經驗顯示
        self.total_exp_label = ttk.Label(result_frame, text="總累計經驗: 未開始追蹤")
        self.total_exp_label.pack(anchor=tk.W)
        

        # 經過時間顯示
        self.time_label = ttk.Label(result_frame, text="經過時間: 00:00:00")
        self.time_label.pack(anchor=tk.W)
        
        # 開始更新顯示
        self._update_display()
    
    def _toggle_tracking(self):
        """切換追蹤狀態"""
        if not self.exp_manager.is_tracking:
            self._start_tracking()
        elif self.exp_manager.is_paused:
            self._resume_tracking()
        else:
            self._pause_tracking()
    
    def _start_tracking(self):
        """開始追蹤經驗"""
        self.exp_manager.start_tracking()
        self.start_button.config(text="暫停")
    
    def _pause_tracking(self):
        """暫停追蹤經驗"""
        self.exp_manager.pause_tracking()
        self.start_button.config(text="開始")
    
    def _resume_tracking(self):
        """恢復追蹤經驗"""
        self.exp_manager.resume_tracking()
        self.start_button.config(text="暫停")
    
    def _reset_tracking(self):
        """重置追蹤"""
        self.exp_manager.reset_tracking()
        self.start_button.config(text="開始")
    
    def _format_exp_display(self, value: Optional[int], percent: Optional[float], prefix: str) -> str:
        """格式化經驗值顯示"""
        if value is not None and percent is not None:
            return f"{prefix}:{value:,} ({percent:.2f}%)"
        elif percent is not None:
            return f"{prefix}:N/A ({percent:.2f}%)"
        elif value is not None:
            return f"{prefix}:{value:,} (N/A%)"
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

    def _update_display(self):
        """更新顯示內容"""
        try:
            status = self.exp_manager.get_status()
            
            # 更新按鈕文字
            if not status["is_tracking"]:
                self.start_button.config(text="開始")
            elif status["is_paused"]:
                self.start_button.config(text="開始")
            else:
                self.start_button.config(text="暫停")
            
            # 更新經驗顯示（使用數據格式化）
            exp_10min_data = status.get("exp_10min_data")
            if exp_10min_data:
                exp_10min_value, exp_10min_percent = exp_10min_data
                exp_10min_text = self._format_exp_display(exp_10min_value, exp_10min_percent, "10分鐘經驗")
                self.exp_10min_label.config(text=exp_10min_text)
            else:
                self.exp_10min_label.config(text="10分鐘經驗: 未開始追蹤" if not status["is_tracking"] else "10分鐘經驗: 計算中...")
            
            total_exp_data = status.get("total_exp_data")
            if total_exp_data:
                total_exp_value, total_exp_percent = total_exp_data
                total_exp_text = self._format_exp_display(total_exp_value, total_exp_percent, "總累計經驗")
                self.total_exp_label.config(text=total_exp_text)
            else:
                self.total_exp_label.config(text="總累計經驗: 未開始追蹤" if not status["is_tracking"] else "總累計經驗: 計算中...")
            
            # 更新時間顯示
            elapsed_time = status.get("elapsed_time")
            if elapsed_time is not None:
                hours = int(elapsed_time // 3600)
                minutes = int((elapsed_time % 3600) // 60)
                seconds = int(elapsed_time % 60)
                time_str = f"經過時間: {hours:02d}:{minutes:02d}:{seconds:02d}"
                self.time_label.config(text=time_str)
            else:
                self.time_label.config(text="經過時間: 00:00:00")
            
            # 更新預估升級時間顯示（使用數據格式化）
            estimated_levelup_data = status.get("estimated_levelup_data")
            if estimated_levelup_data:
                hours, minutes, seconds = estimated_levelup_data
                levelup_text = self._format_time_display(hours, minutes, seconds)
                self.levelup_time_label.config(text=levelup_text)
            else:
                self.levelup_time_label.config(text="預估升級時間: 未開始追蹤" if not status["is_tracking"] else "預估升級時間: 數據不足")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
        
        # 每秒更新一次
        self.parent.after(1000, self._update_display)
    
    def set_exp_manager(self, exp_manager):
        """設定經驗管理器"""
        self.exp_manager = exp_manager
    
    def set_update_callback(self, callback: Callable):
        """設定更新回調函數"""
        self.update_callback = callback
    
    def pack(self, **kwargs):
        """包裝元件到父容器"""
        pass  # 元件已經在 _create_widget 中直接打包到 parent
    
    def destroy(self):
        """銷毀元件"""
        if self.main_frame:
            self.main_frame.destroy()
