"""
Window Selection Widget Module
視窗選擇控制元件模組
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List, Tuple, Callable
import time

from capture.base_capture import BaseCaptureEngine, create_capture_engine
from utils.log import get_logger
from utils.common import FuzzySearchMatcher

logger = get_logger(__name__)


class WindowSelectionWidget:
    """視窗選擇控制元件"""
    
    def __init__(self, parent, capture_engine: BaseCaptureEngine = None, config_callback: Optional[Callable] = None):
        self.parent = parent
        self.config_callback = config_callback
        self.window_title_var = tk.StringVar(value="")
        self.selected_hwnd = None
        self.window_list = []
        self.is_expanded = False  # 視窗列表展開狀態
        self.filtered_indices = []  # 儲存搜尋結果的索引
        
        # 初始化模糊搜尋匹配器
        self.fuzzy_matcher = FuzzySearchMatcher(confidence_threshold=0.8)
        
        # 移除重複的捕捉引擎創建，將在需要時從外部獲取
        self.capture_engine = capture_engine
        
        if self.config_callback:
            self.window_title_var.trace('w', lambda *args: self.config_callback())
        
        self._create_widget()
    
    
    def _create_widget(self):
        """創建視窗選擇控制元件"""
        self.frame = ttk.LabelFrame(self.parent, text="視窗選擇設定", padding=10)
        
        # 視窗標題輸入和展開/收起按鈕
        title_frame = ttk.Frame(self.frame)
        title_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(title_frame, text="視窗標題:").pack(side=tk.LEFT, padx=(0, 5))
        
        # 先放置按鈕，確保其寬度固定且優先顯示
        self.toggle_button = ttk.Button(title_frame, text="展開列表", command=self._toggle_window_list, width=10)
        self.toggle_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 輸入框放在中間，會自動填充剩餘空間
        entry = ttk.Entry(title_frame, textvariable=self.window_title_var)
        entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        
        # 綁定Enter鍵事件到自動搜尋
        entry.bind('<Return>', lambda e: self._auto_search_from_entry())
        
        # 視窗列表（預設隱藏）
        self.list_frame = ttk.Frame(self.frame)
        
        self.window_listbox = tk.Listbox(self.list_frame, height=6)
        self.window_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.window_listbox.bind('<<ListboxSelect>>', self._on_window_select)
        
        # 狀態標籤
        self.status_label = ttk.Label(self.frame, text="請輸入視窗標題")
        self.status_label.pack(pady=5)
        
        # 初始化視窗列表但不顯示
        self._refresh_window_list()
    
    def _toggle_window_list(self):
        """展開/收起視窗列表"""
        if self.is_expanded:
            self.list_frame.pack_forget()
            self.toggle_button.config(text="展開列表")
            self.is_expanded = False
        else:
            self.list_frame.pack(fill=tk.X, pady=5)
            self.toggle_button.config(text="收起列表")
            self.is_expanded = True
            self._refresh_window_list()
    
    def _auto_search_from_entry(self):
        """從輸入框自動搜尋視窗（支援模糊搜尋）"""
        search_text = self.window_title_var.get().strip().lower()
        if not search_text:
            return
        
        # 如果列表未展開，先展開
        if not self.is_expanded:
            self._toggle_window_list()
        
        # 執行模糊搜尋並高亮匹配項
        self._fuzzy_search_and_highlight(search_text)
    
    def _fuzzy_search_and_highlight(self, search_text: str):
        """模糊搜尋並高亮匹配的視窗"""
        if not search_text:
            return
        
        # 清除之前的選擇
        self.window_listbox.selection_clear(0, tk.END)
        
        # 使用模糊搜尋匹配器找到匹配項
        matches = self.fuzzy_matcher.find_best_matches(
            search_text, 
            self.window_list,
            key_func=lambda x: x[1]  # 使用標題進行匹配
        )
        
        if matches:
            # 選擇第一個最佳匹配
            best_match_index = matches[0][0]
            self.window_listbox.selection_set(best_match_index)
            self.window_listbox.see(best_match_index)
            
            # 自動選擇第一個匹配項
            self._select_window_by_index(best_match_index)
            
            # 顯示匹配結果
            confidence = matches[0][1]
            if len(matches) == 1:
                self.status_label.config(text=f"找到匹配視窗並已選擇 (信心度: {confidence:.2f})")
            else:
                self.status_label.config(text=f"找到 {len(matches)} 個匹配視窗，已選擇最佳匹配 (信心度: {confidence:.2f})")
        else:
            self.status_label.config(text=f"未找到高信心度匹配 '{search_text}' 的視窗")
    
    def _refresh_window_list(self):
        """刷新視窗列表"""
        try:
            if not self.capture_engine:
                raise ValueError("捕捉引擎未設定")
                
            self.window_list = self.capture_engine.get_window_list()
            self.window_listbox.delete(0, tk.END)
            
            logger.info(f"獲取到 {len(self.window_list)} 個視窗")
            
            for hwnd, title in self.window_list:
                self.window_listbox.insert(tk.END, f"{title}")
                
        except Exception as e:
            logger.error(f"刷新視窗列表錯誤: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.config(text="獲取視窗列表失敗")
    
    def _search_windows(self):
        """搜尋視窗（保持完整列表，只高亮匹配項）"""
        search_text = self.window_title_var.get().strip().lower()
        if not search_text:
            return
        
        self._highlight_matching_windows(search_text)
    
    def _auto_search_and_select(self):
        """自動搜尋並選擇視窗（供載入配置時使用）"""
        search_text = self.window_title_var.get().strip().lower()
        if not search_text:
            self.status_label.config(text="視窗標題為空")
            return False, ""
        
        # 刷新視窗列表以獲取最新的視窗
        self._refresh_window_list()
        
        # 尋找匹配的視窗
        for i, (hwnd, title) in enumerate(self.window_list):
            if search_text in title.lower():
                self.selected_hwnd = hwnd
                self.window_title_var.set(title)
                self.status_label.config(text=f"自動選擇視窗: {title}")
                self.capture_engine.set_window(self.selected_hwnd)
                return True, title
        
        self.status_label.config(text=f"未找到包含 '{search_text}' 的視窗")
        return False, ""
    
    def _select_window_by_index(self, index: int):
        """根據索引選擇視窗"""
        if 0 <= index < len(self.window_list):
            hwnd, title = self.window_list[index]
            self.selected_hwnd = hwnd
            self.window_title_var.set(title)
            self.status_label.config(text=f"已選擇: {title}")
            logger.info(f"選擇視窗: hwnd={hwnd}, title={title}")
    
    def _on_window_select(self, event):
        """視窗選擇事件處理"""
        selection = self.window_listbox.curselection()
        if selection:
            index = selection[0]
            self._select_window_by_index(index)
            self.capture_engine.set_window(self.selected_hwnd)
    
    def pack(self, **kwargs):
        """打包元件"""
        self.frame.pack(**kwargs)
    
    def get_window_info(self) -> Optional[Dict[str, Any]]:
        """獲取當前選擇的視窗資訊"""
        if self.selected_hwnd and self.capture_engine:
            try:
                rect = self.capture_engine.get_window_rect(self.selected_hwnd)
                if rect:
                    # logger.debug(f"獲取視窗資訊成功: hwnd={self.selected_hwnd}, rect={rect}")
                    return {
                        'hwnd': self.selected_hwnd,
                        'rect': rect,
                        'title': self.window_title_var.get()
                    }
                else:
                    logger.warning(f"無法獲取視窗矩形: hwnd={self.selected_hwnd}")
            except Exception as e:
                logger.error(f"獲取視窗資訊錯誤: {e}")
        return None
    
    def set_window_title(self, title: str):
        """設定視窗標題"""
        self.window_title_var.set(title)
