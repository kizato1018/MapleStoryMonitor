"""
Multi-Tracker Calculator Widget
多功能追蹤計算器主元件
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from module.exp_manager import EXPManager
from module.coin_manager import CoinManager
from module.potion_manager import PotionManager
from module.monitor_timer import MonitorTimer
from gui.widgets.exp_tracker import EXPTrackerWidget
from gui.widgets.coin_tracker import CoinTrackerWidget
from gui.widgets.potion_tracker import PotionTrackerWidget
from utils.log import get_logger

logger = get_logger(__name__)


class MultiTrackerWidget:
    """多功能追蹤計算器主元件"""
    
    def __init__(self, parent, exp_manager: Optional[EXPManager] = None, coin_manager: Optional[CoinManager] = None, potion_manager: Optional[PotionManager] = None):
        self.parent = parent
        self.timer = MonitorTimer()  # 共用計時器
        
        # 管理器實例
        self.exp_manager = exp_manager if exp_manager else EXPManager()
        self.coin_manager = coin_manager if coin_manager else CoinManager()
        self.potion_manager = potion_manager if potion_manager else PotionManager()
        
        # 將共用計時器設定給各管理器
        self.exp_manager.timer = self.timer
        self.coin_manager.timer = self.timer
        self.potion_manager.timer = self.timer
        
        # UI 元件
        self.main_frame = None
        self.start_button = None
        self.time_label = None
        
        # 子元件
        self.exp_widget = None
        self.coin_widget = None
        self.potion_widget = None
        
        # 防止重複更新布局
        self.layout_updating = False
        self.last_width = None
        
        self._create_widget()
    
    def _create_widget(self):
        """創建主元件UI"""
        self.main_frame = ttk.Frame(self.parent)
        
        # 控制按鈕區域
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_frame, text="重置", command=self._reset_tracking).pack(side=tk.LEFT, padx=5)
        self.start_button = ttk.Button(control_frame, text="開始", command=self._toggle_tracking)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 子元件容器
        self.trackers_frame = ttk.Frame(self.main_frame)
        self.trackers_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 經過時間顯示區域（最下面靠右）
        time_frame = ttk.Frame(self.main_frame)
        time_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.time_label = tk.Label(time_frame, text="經過時間: 00:00:00", fg="black")
        self.time_label.pack(side=tk.RIGHT, padx=5)
        
        # 創建子元件
        self.exp_widget = EXPTrackerWidget(self.trackers_frame, self.timer)
        self.exp_widget.set_manager(self.exp_manager)
        
        self.coin_widget = CoinTrackerWidget(self.trackers_frame, self.timer)
        self.coin_widget.set_manager(self.coin_manager)
        
        self.potion_widget = PotionTrackerWidget(self.trackers_frame, self.timer)
        self.potion_widget.set_manager(self.potion_manager)
        
        # 初始布局
        self._update_layout()
        
        # 綁定視窗大小變化事件
        self._bind_resize_event()
        
        # 開始更新顯示
        self._update_display()
    
    def _bind_resize_event(self):
        """綁定視窗大小變化事件"""
        def on_configure(event):
            # 只處理來自頂層視窗的事件
            if event.widget == self.main_frame.winfo_toplevel():
                self.main_frame.after_idle(self._check_and_update_layout)
        
        self.main_frame.winfo_toplevel().bind('<Configure>', on_configure, add='+')
    
    def _check_and_update_layout(self):
        """檢查並更新布局"""
        if self.layout_updating:
            return
            
        try:
            self.main_frame.update_idletasks()
            window_width = self.main_frame.winfo_toplevel().winfo_width()
        except:
            window_width = 500
        
        # 如果寬度變化不大，不需要重新布局
        if self.last_width is not None and abs(window_width - self.last_width) < 50:
            return
        
        self._update_layout()
    
    def _update_layout(self):
        """更新布局"""
        if self.layout_updating:
            return
            
        self.layout_updating = True
        
        try:
            self.trackers_frame.update_idletasks()
            frame_width = self.trackers_frame.winfo_width()
            
            # 計算每個widget最小寬度（150 + padding）
            widget_min_width = 160  # 150 + 10 padding
            
            # 決定排列方式
            if frame_width < widget_min_width * 2:
                # 單列排列
                self._arrange_single_column()
            elif frame_width < widget_min_width * 3:
                # 雙列排列
                self._arrange_double_column()
            else:
                # 三列排列
                self._arrange_triple_column()
            
            self.last_width = frame_width
            
        except Exception as e:
            logger.error(f"布局更新錯誤: {e}")
        finally:
            self.layout_updating = False
    
    def _arrange_single_column(self):
        """單列排列"""
        # 清除現有grid配置
        for widget in [self.exp_widget, self.coin_widget, self.potion_widget]:
            widget.main_frame.grid_forget()
        
        # 重新配置grid
        self.trackers_frame.grid_columnconfigure(0, weight=1)
        for i in range(1, 3):
            self.trackers_frame.grid_columnconfigure(i, weight=0)
        
        for i in range(3):
            self.trackers_frame.grid_rowconfigure(i, weight=1)
        
        # 排列元件
        self.exp_widget.main_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        self.coin_widget.main_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        self.potion_widget.main_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=2)
    
    def _arrange_double_column(self):
        """雙列排列"""
        # 清除現有grid配置
        for widget in [self.exp_widget, self.coin_widget, self.potion_widget]:
            widget.main_frame.grid_forget()
        
        # 重新配置grid
        for i in range(2):
            self.trackers_frame.grid_columnconfigure(i, weight=1)
        self.trackers_frame.grid_columnconfigure(2, weight=0)
        
        for i in range(2):
            self.trackers_frame.grid_rowconfigure(i, weight=1)
        self.trackers_frame.grid_rowconfigure(2, weight=0)
        
        # 排列元件
        self.exp_widget.main_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.coin_widget.main_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.potion_widget.main_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
    
    def _arrange_triple_column(self):
        """三列排列"""
        # 清除現有grid配置
        for widget in [self.exp_widget, self.coin_widget, self.potion_widget]:
            widget.main_frame.grid_forget()
        
        # 重新配置grid
        for i in range(3):
            self.trackers_frame.grid_columnconfigure(i, weight=1)
        self.trackers_frame.grid_rowconfigure(0, weight=1)
        for i in range(1, 3):
            self.trackers_frame.grid_rowconfigure(i, weight=0)
        
        # 排列元件
        self.exp_widget.main_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.coin_widget.main_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.potion_widget.main_frame.grid(row=0, column=2, sticky="nsew", padx=2, pady=2)

    def _toggle_tracking(self):
        """切換追蹤狀態"""
        if not self.timer.is_tracking:
            self._start_tracking()
        elif self.timer.is_paused:
            self._resume_tracking()
        else:
            self._pause_tracking()
    
    def _start_tracking(self):
        """開始追蹤"""
        # 啟動共用計時器
        self.timer.start_tracking()
        
        # 啟動各個已啟用的管理器
        if self.exp_widget.is_enabled():
            self.exp_manager.start_tracking()
        if self.coin_widget.is_enabled():
            self.coin_manager.start_tracking()
        if self.potion_widget.is_enabled():
            self.potion_manager.start_tracking()
        
        self.start_button.config(text="暫停")
        logger.info("多功能追蹤已開始")
    
    def _pause_tracking(self):
        """暫停追蹤"""
        self.timer.pause_tracking()
        
        if self.exp_widget.is_enabled():
            self.exp_manager.pause_tracking()
        if self.coin_widget.is_enabled():
            self.coin_manager.pause_tracking()
        if self.potion_widget.is_enabled():
            self.potion_manager.pause_tracking()
        
        self.start_button.config(text="開始")
        logger.info("多功能追蹤已暫停")
    
    def _resume_tracking(self):
        """恢復追蹤"""
        self.timer.resume_tracking()
        
        if self.exp_widget.is_enabled():
            self.exp_manager.resume_tracking()
        if self.coin_widget.is_enabled():
            self.coin_manager.resume_tracking()
        if self.potion_widget.is_enabled():
            self.potion_manager.resume_tracking()
        
        self.start_button.config(text="暫停")
        logger.info("多功能追蹤已恢復")
    
    def _reset_tracking(self):
        """重置追蹤"""
        self.timer.reset_tracking()
        self.exp_manager.reset_tracking()
        self.coin_manager.reset_tracking()
        self.potion_manager.reset_tracking()
        
        self.start_button.config(text="開始")
        logger.info("多功能追蹤已重置")
    
    def _update_display(self):
        """更新顯示內容"""
        try:
            # 更新按鈕文字和時間標籤顏色
            if not self.timer.is_tracking:
                self.start_button.config(text="開始")
                self.time_label.config(fg="black")  # 停止：黑色
            elif self.timer.is_paused:
                self.start_button.config(text="開始")
                self.time_label.config(fg="red")    # 暫停：紅色
            else:
                self.start_button.config(text="暫停")
                self.time_label.config(fg="green")  # 啟動：綠色
            
            # 更新經過時間顯示
            elapsed_time = self.timer.get_elapsed_time()
            if elapsed_time is not None:
                hours = int(elapsed_time // 3600)
                minutes = int((elapsed_time % 3600) // 60)
                seconds = int(elapsed_time % 60)
                time_str = f"經過時間: {hours:02d}:{minutes:02d}:{seconds:02d}"
                self.time_label.config(text=time_str)
            else:
                self.time_label.config(text="經過時間: 00:00:00")
            
            # 更新各子元件顯示
            self.exp_widget.update_display()
            self.coin_widget.update_display()
            self.potion_widget.update_display()
                
        except Exception as e:
            logger.error(f"更新顯示時發生錯誤: {e}")
        
        # 每秒更新一次
        self.parent.after(1000, self._update_display)
    
    def update_exp(self, exp_value: str):
        """更新經驗值"""
        if self.exp_widget.is_enabled():
            self.exp_manager.update(exp_value)
    
    def update_coin(self, coin_value: str):
        """更新楓幣值"""
        if self.coin_widget.is_enabled():
            self.coin_manager.update(coin_value)
    
    def update_potion(self, potion_value: str):
        """更新藥水值"""
        if self.potion_widget.is_enabled():
            self.potion_manager.update(potion_value)
    
    def pack(self, **kwargs):
        """打包主元件"""
        if self.main_frame:
            self.main_frame.pack(**kwargs)
    
    def destroy(self):
        """銷毀元件"""
        if self.main_frame:
            self.main_frame.destroy()
