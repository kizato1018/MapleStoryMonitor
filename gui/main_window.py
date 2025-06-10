"""
Main Window Module
主視窗模組
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Dict, Any
import os
import ctypes

from gui.widgets.window_selection import WindowSelectionWidget
from gui.widgets.frequency_control import FrequencyControlWidget
from gui.widgets.multi_tracker import MultiTrackerWidget
from gui.monitor_tab import GameMonitorTab
from gui.settings_tab import SettingsTab
from config.config_manager import ConfigManager
from ocr.ocr_engine import OCREngine
from module.hpmp_manager import HPMPManager
from module.exp_manager import EXPManager
from module.coin_manager import CoinManager
from module.potion_manager import TotalPotionManager
from utils.common import FrequencyController
from utils.log import get_logger
from capture.base_capture import create_capture_engine

logger = get_logger(__name__)


class GameMonitorMainWindow:
    """遊戲監控主視窗"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("遊戲狀態監控")
        
        # 配置管理器 - 移到前面以便載入視窗大小
        self.config_manager = ConfigManager()
        
        # 設定初始視窗大小（稍後會被配置覆蓋）
        self.root.geometry("0x0")
        self.root.withdraw()
        
        # 設定視窗圖標
        try:
            import platform
            if platform.system() == "Windows":
                myappid = 'mycompany.myapp.subapp.1.0'  # 任意唯一值
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "icon.ico")
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
                    logger.debug(f"成功設定視窗圖標: {icon_path}")
                else:
                    logger.warning(f"視窗圖標檔案不存在: {icon_path}")
            else:
                icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "icon.png")
                if os.path.exists(icon_path):
                    self.root.iconphoto(True, tk.Image("photo", file=icon_path)) # you may also want to try this.
                    logger.debug(f"成功設定視窗圖標: {icon_path}")
                else:
                    logger.warning(f"視窗圖標檔案不存在: {icon_path}")
            
        except Exception as e:
            logger.warning(f"設定視窗圖標失敗: {e}")
        
        # 設定最小視窗大小
        self.root.minsize(380, 350)  # 最小寬度350，最小高度500以確保內容不被遮擋
        
        # 數據管理器
        self.hpmp_manager = HPMPManager()
        self.exp_manager = EXPManager()
        self.coin_manager = CoinManager()
        self.potion_manager = TotalPotionManager()
        
        # 標記是否正在載入配置（防止觸發保存）
        self.is_loading_config = True
        # 共享的FPS變數
        self.fps_var = tk.StringVar(value="5.0")
        
        # 顯示選項變數
        self.show_status_var = tk.BooleanVar(value=True)
        self.show_tracker_var = tk.BooleanVar(value=True)
        self.window_pinned_var = tk.BooleanVar(value=False)
        self.window_transparency_var = tk.DoubleVar(value=1.0)  # 1.0 = 完全不透明, 0.0 = 完全透明
        self.auto_update_var = tk.BooleanVar(value=True)  # 新增自動更新變數
        
        
        # OCR引擎
        self.ocr_engine = OCREngine()
        self.ocr_frequency_controller = FrequencyController(2.0)  # OCR較低頻率
        # 監控標籤頁
        self.tabs = {}
        self.tabs_names = ["HP", "MP", "EXP", "楓幣", "藥水1", "藥水2", "藥水3", "藥水4", "藥水5", "藥水6", "藥水7", "藥水8"]
        self.tab_visibility_vars = {
            tab_name: tk.BooleanVar() for tab_name in self.tabs_names
        }
        # 設定標籤頁
        self.settings_tab = None
        self.settings_widget = None
        
        # 共享捕捉引擎管理器
        self.capture_manager = create_capture_engine()
        
        
        self._create_gui()
        self._init_ocr()
        # 載入配置移到GUI創建後
        self._load_config()
        # 配置載入完成後，啟用配置保存
        self.is_loading_config = False
        
        self._init_visibility()
        # 應用初始的分頁可見性設定
        self._apply_tab_visibility_changes()
        # 延遲自動選擇視窗，確保GUI完全初始化
        self._auto_select_window()
        # 啟動監控
        self._start_monitoring()
    
    def _create_gui(self):
        """創建GUI"""
        

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 先創建設定標籤頁，確保 shared_window_widget 先初始化
        self.setting_frame = ttk.Frame(self.notebook)
        self._create_setting_tab()

        # 創建總覽標籤頁
        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="總覽")
        self._create_overview_tab()
        
        # 創建所有監控標籤頁（初始都創建，稍後根據配置決定是否顯示）
        for tab_name in self.tabs_names:
            self._create_monitor_tab(tab_name)

        # 最後添加設定標籤頁到最右邊
        self.notebook.add(self.setting_frame, text="設定")

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_setting_tab(self):
        """創建設定標籤頁，使用SettingsTab類"""
        self.settings_tab = SettingsTab(self.setting_frame, self.capture_manager, self._save_config_if_ready)
        
        # 設定變數
        self.settings_tab.set_variables(
            self.fps_var,
            self.show_status_var,
            self.show_tracker_var,
            self.tab_visibility_vars,
            self.window_pinned_var,
            self.window_transparency_var,
            self.auto_update_var
        )
        
        # 設定回調函數
        self.settings_tab.set_callbacks(
            self._update_status_visibility,
            self._update_tracker_visibility,
            self._apply_tab_visibility_changes,
            self._update_window_pinning,
            self._update_window_transparency,
            self._update_auto_update
        )
        
        # 創建設定頁面內容
        self.settings_widget = self.settings_tab.create_tab()

    def _create_overview_tab(self):
        """創建總覽標籤頁"""
        # 標題
        title_label = tk.Label(
            self.overview_frame,
            text="遊戲狀態總覽",
            font=('Arial', 12, 'bold')
        )
        title_label.pack(pady=(5, 0))
        
        # 結果顯示框架
        self.results_frame = ttk.LabelFrame(self.overview_frame, text="當前狀態") 
        self.results_frame.pack(side=tk.TOP, fill=tk.X, expand=False, padx=20, pady=(0, 5))
        
        # 創建結果顯示標籤 - 改為動態創建
        self.overview_labels = {}
        self._create_status_labels()
        
        # OCR狀態顯示 - 移到results_frame外面，避免被銷毀
        self.ocr_status_frame = ttk.Frame(self.overview_frame)
        self.ocr_status_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(0, 5))
        
        tk.Label(self.ocr_status_frame, text="OCR狀態:", font=('Arial', 10)).pack(side=tk.LEFT, padx=(5, 0))
        self.ocr_status_label = tk.Label(
            self.ocr_status_frame,
            text="初始化中...",
            font=('Arial', 10),
        )
        self.ocr_status_label.pack(side=tk.LEFT, padx=(2, 0))
        
        # EXP計算器
        self.multi_tracker_frame = ttk.LabelFrame(self.overview_frame, text="多功能追蹤計算器")
        self.multi_tracker_frame.pack(side=tk.TOP, fill=tk.X, padx=20)
        
        self.multi_tracker = MultiTrackerWidget(self.multi_tracker_frame, 
                                                self.exp_manager, 
                                                self.coin_manager, 
                                                self.potion_manager)
        self.multi_tracker.pack(fill=tk.X)
        
        tk.Frame(self.overview_frame).pack(side=tk.TOP, fill=tk.BOTH, expand=True)  # 分隔線

    def _create_status_labels(self):
        """動態創建狀態標籤"""
        # 清除現有的標籤 - 只清除results_frame內的widget
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        self.overview_labels.clear()
        
        # 只為可見的分頁創建標籤
        for stat_name in self.tabs_names:
            if self.tab_visibility_vars[stat_name].get():
                stat_frame = ttk.Frame(self.results_frame)
                stat_frame.pack(fill=tk.X, pady=0)
                
                ttk.Label(stat_frame, text=f"{stat_name}:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(5, 5)) 
                
                # 設定顏色：HP 紅色, MP 藍色, EXP 黑色, 楓幣 金色, 藥水 綠色
                color = "black"
                if stat_name == "HP":
                    color = "red"
                elif stat_name == "MP":
                    color = "blue"
                elif stat_name == "楓幣":
                    color = "#DAA520"  # 金色
                elif "藥水" in stat_name:
                    color = "green"
                value_label = tk.Label(
                    stat_frame,
                    text="N/A",
                    font=('Arial', 10), 
                    fg=color,
                    width=18
                )
                value_label.pack(side=tk.LEFT, padx=(0, 0)) 
                
                self.overview_labels[stat_name] = value_label

    def _update_fps_label(self, *args):
        """更新全域FPS標籤"""
        if self.settings_tab:
            self.settings_tab._update_fps_label(*args)

    def _update_status_visibility(self):
        """更新狀態顯示的可見性"""
        if hasattr(self, 'results_frame'):
            if self.show_status_var.get():
                self.results_frame.pack(side=tk.TOP,fill=tk.X, expand=False, padx=20, before=self.multi_tracker_frame)
            else:
                self.results_frame.pack_forget()
        self._save_config_if_ready()
    
    def _update_tracker_visibility(self):
        """更新追蹤計算器的可見性"""
        if hasattr(self, 'multi_tracker_frame'):
            if self.show_tracker_var.get():
                self.multi_tracker_frame.pack(side=tk.TOP, fill=tk.X, padx=20)
            else:
                self.multi_tracker_frame.pack_forget()
        self._save_config_if_ready()
    
    def _update_window_pinning(self):
        """更新視窗釘選狀態"""
        try:
            is_pinned = self.window_pinned_var.get()
            self.root.attributes('-topmost', is_pinned)
            logger.info(f"視窗釘選狀態已更新: {'已釘選' if is_pinned else '已取消釘選'}")
        except Exception as e:
            logger.error(f"更新視窗釘選狀態時發生錯誤: {e}")
        self._save_config_if_ready()

    def _update_window_transparency(self):
        """更新視窗透明度"""
        try:
            transparency = self.window_transparency_var.get()
            # 確保透明度在有效範圍內 (0.1 到 1.0)
            transparency = max(0.1, min(1.0, transparency))
            self.root.attributes('-alpha', transparency)
            logger.info(f"視窗透明度已更新: {transparency:.1%}")
        except Exception as e:
            logger.error(f"更新視窗透明度時發生錯誤: {e}")
        self._save_config_if_ready()

    def _update_auto_update(self):
        try:
            auto_update = self.auto_update_var.get()
            self.config_manager.set_auto_update(auto_update)
            logger.info(f"自動更新狀態已更新: {'啟用' if auto_update else '禁用'}")
        except Exception as e:
            logger.error(f"更新自動更新狀態時發生錯誤: {e}")
        self._save_config_if_ready()
        

    def _init_visibility(self):
        self._update_status_visibility()
        self._update_tracker_visibility()
        self._update_window_pinning()
        self._update_window_transparency()

    def _apply_tab_visibility_changes(self):
        """應用分頁可見性變更"""
        # 儲存當前的 notebook 索引
        current_tab_name = None
        try:
            current_tab_name = self.notebook.tab(self.notebook.select(), "text")
        except:
            pass
        
        # 先移除所有監控分頁（保留總覽和設定）
        all_tabs = list(self.notebook.tabs())
        for tab_id in all_tabs:
            tab_text = self.notebook.tab(tab_id, "text")
            if tab_text in self.tabs_names:
                self.notebook.forget(tab_id)
        
        # 找到設定分頁的位置（應該是最後一個）
        setting_tab_index = None
        current_tabs = list(self.notebook.tabs())
        for i, tab_id in enumerate(current_tabs):
            if self.notebook.tab(tab_id, "text") == "設定":
                setting_tab_index = i
                break
        
        # 如果沒找到設定分頁，則插入到最後
        if setting_tab_index is None:
            setting_tab_index = len(current_tabs)
        
        # 根據選擇重新添加分頁（在設定分頁之前插入）
        insert_index = setting_tab_index
        
        for tab_name in self.tabs_names:
            if self.tab_visibility_vars[tab_name].get() and tab_name in self.tabs:
                # 使用 tab 對象的 frame 屬性（如果存在）或重新創建
                tab_obj = self.tabs[tab_name]
                if hasattr(tab_obj, 'frame'):
                    frame = tab_obj.frame
                else:
                    # 如果沒有 frame 屬性，嘗試獲取已創建的 frame
                    frame = getattr(tab_obj, '_frame', None)
                    if frame is None:
                        # 如果還是沒有，重新創建 frame
                        frame = tab_obj._create_tab()
                        tab_obj._frame = frame
                
                self.notebook.insert(insert_index, frame, text=tab_name)
                insert_index += 1
        
        # 嘗試恢復之前選中的分頁
        if current_tab_name is not None:
            try:
                # 找到具有相同名稱的分頁
                current_tabs = list(self.notebook.tabs())
                for i, tab_id in enumerate(current_tabs):
                    if self.notebook.tab(tab_id, "text") == current_tab_name:
                        self.notebook.select(i)
                        break
                else:
                    # 如果沒找到同名分頁，選擇第一個
                    if current_tabs:
                        self.notebook.select(0)
            except Exception as e:
                logger.warning(f"無法恢復選中的分頁: {current_tab_name}, 錯誤: {e}")
                # 如果失敗就選擇第一個分頁
                try:
                    self.notebook.select(0)
                except:
                    pass

        # 重新創建狀態標籤以匹配可見的分頁
        if hasattr(self, 'results_frame'):
            self._create_status_labels()
            
        for i in range(len(self.potion_manager)):
            potion_tab_name = f"藥水{i+1}"
            if potion_tab_name in self.tabs:
                potion_manager = self.potion_manager[i]
                potion_manager.enabled = self.tab_visibility_vars[potion_tab_name].get()

        self._save_config_if_ready()
    
    def _create_monitor_tab(self, tab_name: str):
        """創建監控標籤頁"""
        # 創建標籤頁，傳遞共享捕捉管理器
        tab = GameMonitorTab(
            self.notebook, 
            tab_name, 
            None,  # 暫時不綁定config_callback
            self.fps_var, 
            self.capture_manager,  # 傳遞共享捕捉管理器
            self.settings_widget.get_window_info
        )
        
        self.tabs[tab_name] = tab
        frame = tab._create_tab()
        
        # 增加藥水單價輸入到藥水標籤頁
        if "藥水" in tab_name:
            index = int(tab_name[-1]) - 1
            potion_manager = self.potion_manager[index]
            tab.add_potion_cost_input(potion_manager.set_unit_cost)
        
        # 儲存 frame 的引用到 tab 對象中，方便後續使用
        tab._frame = frame
        
        self.notebook.add(frame, text=tab_name)
        
        return tab
    
    def _init_ocr(self):
        """初始化OCR"""
        def update_status():
            status = self.ocr_engine.get_status()
            self.ocr_status_label.config(text=status)
            
            if status == "運行中":
                self.ocr_status_label.config(fg='green')
            elif status == "初始化中...":
                self.ocr_status_label.config(fg='orange')
            else:
                self.ocr_status_label.config(fg='red')
            
            # 每秒更新一次狀態
            self.root.after(1000, update_status)
        
        # 設定OCR結果回調
        self.ocr_engine.set_result_callback(self._update_ocr_result)
        
        # 初始化OCR引擎
        self.ocr_engine.initialize(self.tabs_names)
        
        # 開始狀態更新
        update_status()

    def _start_ocr_processing(self):
        """開始OCR處理"""
        def ocr_loop():
            while True:
                try:
                    if self.ocr_frequency_controller.should_process():
                        # 收集所有標籤頁的圖像
                        images_dict = {}
                        for tab_name, tab in self.tabs.items():
                            image = tab.get_latest_image()
                            if image:
                                images_dict[tab_name] = image
                        logger.debug(f"[OCR DEBUG] images_dict keys: {list(images_dict.keys())}")  # <--- debug

                        # 處理OCR
                        if images_dict:
                            logger.debug("[OCR DEBUG] 呼叫 process_images")
                            self.ocr_engine.process_images(images_dict)
                        else:
                            logger.debug("[OCR DEBUG] 沒有可用的圖像進行OCR")
                            pass
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"OCR處理錯誤: {e}")
                    time.sleep(1.0)
        threading.Thread(target=ocr_loop, daemon=True).start()

    def _update_ocr_result(self, tab_name: str, result: str):
        """更新OCR結果"""
        logger.debug(f"[OCR DEBUG] set_ocr_result({tab_name}, {result})")
        
        # 將辨識結果傳送到對應的管理器和多功能追蹤器
        if tab_name == "HP" or tab_name == "MP":
            # 獲取當前HP和MP值
            current_hp = self.tabs["HP"].get_ocr_result() if "HP" in self.tabs else "N/A"
            current_mp = self.tabs["MP"].get_ocr_result() if "MP" in self.tabs else "N/A"
            
            # 如果當前更新的是HP，使用新結果
            if tab_name == "HP":
                current_hp = result
            elif tab_name == "MP":
                current_mp = result
                
            # 更新HP/MP管理器
            self.hpmp_manager.update(current_hp, current_mp)
            
            # 獲取格式化的結果（附加百分比）
            hp_formatted = self.hpmp_manager.get_formatted_hp()
            mp_formatted = self.hpmp_manager.get_formatted_mp()
            
            # Debug parse 結果
            logger.debug(f"[PARSE DEBUG] HP parse: {hp_formatted}, MP parse: {mp_formatted}")
            
            # 更新對應標籤頁的結果（使用原始OCR結果）
            if tab_name == "HP" and "HP" in self.tabs:
                self.tabs["HP"].set_ocr_result(result)
            elif tab_name == "MP" and "MP" in self.tabs:
                self.tabs["MP"].set_ocr_result(result)
              # 更新總覽頁面（使用格式化結果）
            if "HP" in self.overview_labels:
                self.overview_labels["HP"].config(text=hp_formatted)
            if "MP" in self.overview_labels:
                self.overview_labels["MP"].config(text=mp_formatted)
                
        elif tab_name == "EXP":
            # 更新EXP管理器
            self.exp_manager.update(result)
            
            # 取得格式化EXP顯示 - 使用有效的經驗值
            exp_status = self.exp_manager.get_status()
            exp_formatted = None
            if exp_status:
                exp_val = exp_status.get("current_exp_value")
                exp_percent = exp_status.get("current_exp_percent")
                if exp_val is not None:
                    exp_val_str = f"{exp_val:,}"
                else:
                    exp_val_str = "N/A"
                if exp_percent is not None:
                    exp_formatted = f"{exp_val_str} [{exp_percent:.2f}%]"
                else:
                    exp_formatted = exp_val_str
                # Debug parse 結果
                logger.debug(f"[PARSE DEBUG] EXP parse: {exp_formatted}")
            else:
                exp_formatted = "N/A"
            
            # 更新對應標籤頁的結果
            if tab_name in self.tabs:
                self.tabs[tab_name].set_ocr_result(exp_formatted)
              # 更新總覽頁面（使用格式化的有效結果）
            if tab_name in self.overview_labels:
                self.overview_labels[tab_name].config(text=exp_formatted)
        elif tab_name == "楓幣":
            # 更新楓幣管理器
            self.coin_manager.update(result)
                
            # 更新對應標籤頁的結果
            if tab_name in self.tabs:
                self.tabs[tab_name].set_ocr_result(result)
            
            # 更新總覽頁面
            if tab_name in self.overview_labels:
                self.overview_labels[tab_name].config(text=result)
                
        elif "藥水" in tab_name:
            # 更新藥水管理器
            index = int(tab_name[-1]) - 1  # 假設標籤頁名稱為 "藥水1", "藥水2" 等
            potion_manager = self.potion_manager[index]
            potion_manager.update(result)
            potion_status = potion_manager.get_status()
            
            if potion_status:
                potion_value = potion_status.get("potion")
                if potion_value is not None:
                    potion_count = str(potion_value)
                else:
                    potion_count = "N/A"
                logger.debug(f"[PARSE DEBUG] {tab_name} parse: {potion_count}")
                
            # 更新對應標籤頁的結果（使用原始OCR結果）
            if tab_name in self.tabs:
                self.tabs[tab_name].set_ocr_result(result)
            
            # 更新總覽頁面
            if tab_name in self.overview_labels:
                self.overview_labels[tab_name].config(text=potion_count)
        
        else:
            # 其他標籤頁直接更新
            if tab_name in self.tabs:
                self.tabs[tab_name].set_ocr_result(result)
            
            # 更新總覽頁面
            if tab_name in self.overview_labels:
                self.overview_labels[tab_name].config(text=result)
    
    def _start_monitoring(self):
        """開始監控"""
        self.capture_manager.start_capture()
        for tab_name, tab in self.tabs.items():
            # 為每個標籤頁啟動捕捉和OCR處理
            tab.start_capture()
        self._start_ocr_processing()
    
    def _stop_monitoring(self):
        """停止監控"""
        self.capture_manager.stop_capture()
        for tab_name, tab in self.tabs.items():
            # 為每個標籤頁停止捕捉
            tab.stop_capture()
        
    
    def _load_config(self):
        """載入配置"""
        success = self.config_manager.load_config()
        if success:
            logger.info(f"成功載入配置檔案: {self.config_manager.config_file}")
            
            # 載入全域配置
            global_config = self.config_manager.get_global_config()
            
            # 載入視窗大小和位置配置
            window_size = self.config_manager.get_window_size()
            window_position = self.config_manager.get_window_position()
            self.root.geometry(f"{window_size['width']}x{window_size['height']}+{window_position['x']}+{window_position['y']}")
            self.root.update_idletasks()  # 確保視窗大小更新
            self.root.deiconify()
            logger.info(f"載入視窗大小: {window_size['width']}x{window_size['height']}")
            logger.info(f"載入視窗位置: {window_position['x']}, {window_position['y']}")
            
            # 處理FPS配置（支援舊格式）
            fps = global_config.get('fps', self.config_manager.config_data.get('global_fps', 5.0))
            self.fps_var.set(str(fps))
            # 立即更新所有tab的frequency_controller
            self._update_fps_label()
            self.auto_update_var.set(global_config.get('auto_update', True))
            
            # 載入顯示選項配置
            display_config = global_config.get('display_options', {})
            self.show_status_var.set(display_config.get('show_status', True))
            self.show_tracker_var.set(display_config.get('show_tracker', True))
            self.window_pinned_var.set(display_config.get('window_pinned', False))
            self.window_transparency_var.set(display_config.get('window_transparency', 1.0))
            
            # 載入分頁可見性配置
            tab_visibility = display_config.get('tab_visibility', {})
            for tab_name, var in self.tab_visibility_vars.items():
                var.set(tab_visibility.get(tab_name, True))
            
            # 設定視窗標題（支援舊格式）
            window_title = global_config.get('window_title', '')
            if not window_title:
                # 檢查舊格式的shared_window配置
                shared_window = self.config_manager.config_data.get('shared_window', {})
                window_title = shared_window.get('window_title', '')
            
            if self.settings_widget:
                self.settings_widget.set_window_title(window_title)
            
            # 載入各標籤頁配置（支援舊格式）
            for tab_name, tab in self.tabs.items():
                # 優先從tabs結構載入
                tab_config = self.config_manager.get_tab_config(tab_name)
                if not tab_config:
                    # 檢查根層級的舊格式配置
                    tab_config = self.config_manager.config_data.get(tab_name)
                
                if tab_config:
                    logger.info(f"載入 {tab_name} 配置: {tab_config}")
                    tab.load_config(tab_config)
                else:
                    logger.warning(f"未找到 {tab_name} 的配置")
            
            # 設定OCR允許字符列表
            allow_list = global_config.get('ocr_allow_list', '0123456789.[]/%')
            self.ocr_engine.set_allow_list(allow_list)
        
        # 配置載入完成後，啟用視窗大小變更監聽
        self.is_window_configure_bound = True
        
        # 配置載入完成後，綁定回調函數
        self._bind_config_callbacks()

    def _bind_config_callbacks(self):
        """綁定配置回調函數"""
        # 綁定FPS變數的回調
        self.fps_var.trace_add('write', lambda *args: self._save_config_if_ready())
        self.fps_var.trace_add('write', self._update_fps_label)
        
        # 綁定顯示選項變數的回調
        self.show_status_var.trace_add('write', lambda *args: self._save_config_if_ready())
        self.show_tracker_var.trace_add('write', lambda *args: self._save_config_if_ready())
        self.window_pinned_var.trace_add('write', lambda *args: self._save_config_if_ready())
        self.window_transparency_var.trace_add('write', lambda *args: self._save_config_if_ready())
        
        # 綁定分頁可見性變數的回調
        for var in self.tab_visibility_vars.values():
            var.trace_add('write', lambda *args: self._save_config_if_ready())
        
        # 綁定視窗選擇控件的回調
        if self.settings_widget:
            # 安全地設定callback，如果屬性不存在就創建
            if not hasattr(self.settings_widget, 'config_callback'):
                self.settings_widget.config_callback = None
            self.settings_widget.config_callback = self._save_config_if_ready
            
            # 綁定視窗標題變數
            if hasattr(self.settings_widget, 'window_title_var'):
                self.settings_widget.window_title_var.trace_add('write', lambda *args: self._save_config_if_ready())
        
        # 綁定設定標籤頁的回調
        if self.settings_tab:
            self.settings_tab.bind_callbacks()
        
        # 綁定各標籤頁的回調
        for tab in self.tabs.values():
            if hasattr(tab, 'config_callback'):
                tab.config_callback = self._save_config_if_ready
            # 為每個輸入框重新綁定trace
            if hasattr(tab, 'region_widget'):
                for var in [tab.region_widget.x_var, tab.region_widget.y_var, 
                           tab.region_widget.w_var, tab.region_widget.h_var]:
                    var.trace_add('write', lambda *args: self._save_config_if_ready())
                    
        # 綁定視窗大小和位置變更事件
        if hasattr(self, 'is_window_configure_bound'):
            if self.is_window_configure_bound:
                self.root.bind('<Configure>', self._on_window_configure)
                self.is_window_configure_bound = False
                logger.debug("已綁定視窗大小和位置變更事件")

    def _on_window_configure(self, event):
        """視窗配置變更事件處理（包括大小和位置）"""
        # 只處理主視窗的事件，忽略子控件的事件
        if event.widget == self.root:
            self._save_window_geometry()

    def _save_window_size(self):
        """儲存視窗大小"""
        try:
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            self.config_manager.set_window_size(width, height)
            logger.debug(f"儲存視窗大小: {width}x{height}")
            # 觸發完整配置保存
            self._save_config()
        except Exception as e:
            logger.error(f"儲存視窗大小失敗: {e}")

    def _save_window_geometry(self):
        """儲存視窗大小和位置"""
        try:
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            
            self.config_manager.set_window_size(width, height)
            self.config_manager.set_window_position(x, y)
            logger.debug(f"儲存視窗幾何: {width}x{height}+{x}+{y}")
            # 觸發完整配置保存
            self._save_config()
        except Exception as e:
            logger.error(f"儲存視窗幾何失敗: {e}")

    def _save_config(self):
        """儲存配置"""
        # 儲存全域配置
        try:
            fps = float(self.fps_var.get())
            self.config_manager.set_fps(fps)
        except ValueError:
            pass
        
        if self.settings_widget and hasattr(self.settings_widget, 'window_title_var'):
            window_title = self.settings_widget.window_title_var.get()
            self.config_manager.set_window_title(window_title)
        
        # 儲存顯示選項配置
        display_options = {
            'show_status': self.show_status_var.get(),
            'show_tracker': self.show_tracker_var.get(),
            'window_pinned': self.window_pinned_var.get(),
            'window_transparency': self.window_transparency_var.get(),
            'tab_visibility': {
                tab_name: var.get() 
                for tab_name, var in self.tab_visibility_vars.items()
            }
        }
        
        # 獲取現有的全域配置並更新
        global_config = self.config_manager.get_global_config()
        global_config['display_options'] = display_options
        
        # 儲存各標籤頁配置
        for tab_name, tab in self.tabs.items():
            if hasattr(tab, 'get_config'):
                tab_config = tab.get_config()
                if tab_config:
                    self.config_manager.set_tab_config(tab_name, tab_config)
        
        # 儲存到檔案
        self.config_manager.save_config()
    def _save_config_if_ready(self):
        """只有在配置載入完成後才保存配置"""
        if not self.is_loading_config:
            self._save_config()
    def _on_closing(self):
        """視窗關閉事件處理"""
        self._save_config()
        self._stop_monitoring()
        self.root.destroy()
    
    def _auto_select_window(self):
        """自動選擇目標視窗"""
        if self.settings_widget:
            window_title = self.settings_widget.window_title_var.get().strip()
            if window_title:
                success, window_title = self.settings_widget._auto_search_and_select()
                if success:
                    logger.info(f"成功自動選擇視窗: {window_title}")
                else:
                    logger.warning(f"未找到視窗: {window_title}")


    def run(self):
        """運行主程式"""
        self.root.mainloop()
