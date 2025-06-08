"""
Region Selection Widget Module
區域選擇控制元件模組
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, Callable
import time

from utils.common import validate_region
from utils.log import get_logger

logger = get_logger(__name__)

class RegionSelectionWidget:
    """區域選擇控制元件"""
    
    def __init__(self, parent, config_callback: Optional[Callable] = None):
        self.parent = parent
        self.config_callback = config_callback
        self.x_var = tk.StringVar(value="0")
        self.y_var = tk.StringVar(value="0")
        self.w_var = tk.StringVar(value="100")
        self.h_var = tk.StringVar(value="30")
        
        # 不在初始化時綁定trace，等待外部調用
        self._create_widget()
    
    def bind_config_callback(self):
        """綁定配置回調函數（在配置載入後調用）"""
        if self.config_callback:
            for var in [self.x_var, self.y_var, self.w_var, self.h_var]:
                var.trace('w', lambda *args: self.config_callback())
        
    def _create_widget(self):
        """創建區域選擇控制元件"""
        self.frame = ttk.LabelFrame(self.parent, text="擷取區域設定", padding=10)
        
        coord_frame = ttk.Frame(self.frame)
        coord_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(coord_frame, text="X:").grid(row=0, column=0, padx=5)
        ttk.Entry(coord_frame, textvariable=self.x_var, width=8).grid(row=0, column=1, padx=5)
        ttk.Label(coord_frame, text="Y:").grid(row=0, column=2, padx=5)
        ttk.Entry(coord_frame, textvariable=self.y_var, width=8).grid(row=0, column=3, padx=5)
        ttk.Label(coord_frame, text="W:").grid(row=1, column=0, padx=5)
        ttk.Entry(coord_frame, textvariable=self.w_var, width=8).grid(row=1, column=1, padx=5)
        ttk.Label(coord_frame, text="H:").grid(row=1, column=2, padx=5)
        ttk.Entry(coord_frame, textvariable=self.h_var, width=8).grid(row=1, column=3, padx=5)
        
        # 按鈕區域
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="滑鼠選取區域", command=self._start_mouse_selection).pack(side=tk.LEFT, padx=5)
        
        # 初始化選取相關變數
        self.selection_window = None
        self.selection_canvas = None
        self.rect_id = None
        self.start_x = 0
        self.start_y = 0

    
    def set_target_window_callback(self, callback: Callable):
        """設定獲取目標視窗的回調函數"""
        self.get_target_window = callback
    
    def _start_mouse_selection(self):
        """開始滑鼠選取區域"""
        # 獲取目標視窗
        if hasattr(self, 'get_target_window') and self.get_target_window:
            window_info = self.get_target_window()
            if not window_info:
                messagebox.showwarning("警告", "請先選擇目標視窗")
                return
            self.target_hwnd = window_info['hwnd']
            self.target_rect = window_info['rect']
        else:
            messagebox.showwarning("警告", "無法獲取目標視窗")
            return
        
        # 創建透明選取視窗
        try:
            # 嘗試將目標視窗置前
            try:
                import platform
                if platform.system() == 'Windows':
                    # Windows 版本
                    import win32gui
                    win32gui.SetForegroundWindow(self.target_hwnd)
                    time.sleep(0.1)
                elif platform.system() == 'Darwin':
                    # macOS 版本
                    try:
                        from Cocoa import NSWorkspace, NSRunningApplication
                        from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionIncludingWindow
                        
                        # 獲取視窗資訊以找到對應的應用程式
                        window_list = CGWindowListCopyWindowInfo(
                            kCGWindowListOptionIncludingWindow,
                            self.target_hwnd
                        )
                        
                        for window_info in window_list:
                            if window_info.get('kCGWindowNumber') == self.target_hwnd:
                                owner_pid = window_info.get('kCGWindowOwnerPID')
                                if owner_pid:
                                    # 透過 PID 獲取應用程式並置前
                                    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(owner_pid)
                                    if app:
                                        app.activateWithOptions_(0)  # NSApplicationActivateIgnoringOtherApps
                                        time.sleep(0.1)
                                        logger.debug(f"成功將應用程式置前 (PID: {owner_pid})")
                                        break
                                break
                    except Exception as mac_error:
                        logger.warning(f"macOS 視窗置前失敗: {mac_error}")
            except Exception as e:
                logger.warning(f"視窗置前失敗: {e}")
                pass  # 跨平台兼容
            
            # 創建透明選取視窗
            self._create_transparent_selection_window()
            
        except Exception as e:
            messagebox.showerror("錯誤", f"開始區域選取失敗: {e}")
    
    def _create_transparent_selection_window(self):
        """創建透明選取視窗"""
        try:
            # 檢測平台並獲取縮放因子
            import platform
            self.is_macos = platform.system() == 'Darwin'
            
            # 獲取 macOS 的縮放因子
            if self.is_macos:
                try:
                    from capture.mac_capture import MacCaptureEngine
                    self.scale_factor = MacCaptureEngine.get_display_scale_factor()
                    logger.debug(f"macOS 縮放因子: {self.scale_factor}")
                except:
                    self.scale_factor = 2.0  # 預設值
                    logger.warning("無法獲取縮放因子，使用預設值 2.0")
            else:
                self.scale_factor = 1.0
            
            self.selection_window = tk.Toplevel(self.parent)
            self.selection_window.title("選取擷取區域")
            self.selection_window.attributes('-topmost', True)
            
            if self.is_macos:  # macOS
                # 獲取螢幕尺寸
                screen_width = self.selection_window.winfo_screenwidth()
                screen_height = self.selection_window.winfo_screenheight()
                
                # 在 macOS 上不使用 overrideredirect，改用其他方式
                self.selection_window.overrideredirect(True)
                self.selection_window.geometry(f"{screen_width}x{screen_height}+0+0")

            else:
                # 其他系統使用原來的 fullscreen
                self.selection_window.attributes('-fullscreen', True)
            
            self.selection_window.attributes('-alpha', 0.3)  # 半透明
            self.selection_window.configure(bg='black', cursor="cross")
            
            # 創建畫布覆蓋整個螢幕
            self.selection_canvas = tk.Canvas(
                self.selection_window,
                cursor="cross",
                highlightthickness=0,
                bg='black'
            )
            self.selection_canvas.pack(fill=tk.BOTH, expand=True)
            
            # 初始化矩形ID
            self.rect_id = None
            
            # 繪製目標視窗邊框（需要考慮縮放因子）
            if hasattr(self, 'target_rect') and self.target_rect:
                left, top, right, bottom = self.target_rect
                
                # 在 macOS 上，目標視窗座標已經是實際像素座標，但畫布是邏輯座標
                if self.is_macos:
                    # 將實際像素座標轉換為邏輯座標用於畫布顯示
                    canvas_left = left / self.scale_factor
                    canvas_top = top / self.scale_factor
                    canvas_right = right / self.scale_factor
                    canvas_bottom = bottom / self.scale_factor
                else:
                    canvas_left, canvas_top, canvas_right, canvas_bottom = left, top, right, bottom
                
                # 繪製目標視窗區域為較亮的顏色
                self.selection_canvas.create_rectangle(
                    canvas_left, canvas_top, canvas_right, canvas_bottom,
                    outline="green", width=3, fill="gray30"
                )
                
                # 顯示視窗提示
                self.selection_canvas.create_text(
                    canvas_left + 10, max(10, canvas_top - 30),
                    text="目標視窗 - 請在此區域內選取",
                    fill="green",
                    font=("Arial", 14, "bold"),
                    anchor=tk.NW
                )
            
            # 綁定滑鼠事件
            self.selection_canvas.bind("<Button-1>", self._on_mouse_down)
            self.selection_canvas.bind("<B1-Motion>", self._on_mouse_drag)
            self.selection_canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
            
            # 綁定鍵盤事件 - 同時綁定到視窗和畫布
            self.selection_window.bind("<Escape>", self._cancel_selection)
            self.selection_window.bind("<Return>", self._confirm_selection)
            self.selection_canvas.bind("<Escape>", self._cancel_selection)
            self.selection_canvas.bind("<Return>", self._confirm_selection)
            
            # 確保視窗能接收鍵盤事件
            self.selection_window.focus_force()
            self.selection_canvas.focus_set()
            
            # 在 macOS 上額外處理焦點
            if self.is_macos:
                self.selection_window.after(100, self._ensure_focus)
            
            # 添加說明文字
            self.selection_canvas.create_text(
                50, 50,
                text="拖拽選取區域（相對於綠色目標視窗），按Enter確認，按ESC取消\n在 macOS 上，如果按鍵無效，請點擊畫布後再試",
                fill="white",
                font=("Arial", 16, "bold"),
                anchor=tk.NW,
                width=600
            )
            
        except Exception as e:
            logger.error(f"創建選取視窗錯誤: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("錯誤", f"無法創建選取視窗: {e}")
    
    def _ensure_focus(self):
        """確保視窗獲得焦點（macOS 專用）"""
        try:
            self.selection_window.lift()
            self.selection_window.focus_force()
            self.selection_canvas.focus_set()
            # 讓視窗可以接收所有事件
            self.selection_canvas.bind("<Key>", self._on_key_press)
            logger.debug("macOS 焦點設定完成")
        except Exception as e:
            logger.warning(f"設定焦點失敗: {e}")
    
    def _on_key_press(self, event):
        """處理鍵盤按鍵"""
        try:
            logger.debug(f"按鍵事件: {event.keysym}")
            if event.keysym == 'Escape':
                self._cancel_selection()
            elif event.keysym == 'Return':
                self._confirm_selection()
        except Exception as e:
            logger.error(f"按鍵處理錯誤: {e}")

    def _on_mouse_down(self, event):
        """滑鼠按下"""
        try:
            self.start_x = event.x
            self.start_y = event.y
            
            # 在 macOS 上，滑鼠點擊時重新設定焦點
            if self.is_macos:
                self.selection_canvas.focus_set()
            
            # 清除之前的矩形
            if self.rect_id:
                self.selection_canvas.delete(self.rect_id)
                self.rect_id = None
        except Exception as e:
            logger.error(f"滑鼠按下錯誤: {e}")
    
    def _on_mouse_drag(self, event):
        """滑鼠拖拽"""
        try:
            if self.rect_id:
                self.selection_canvas.delete(self.rect_id)
            
            # 繪製選取矩形
            self.rect_id = self.selection_canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline="red", width=2, fill="red", stipple="gray50"
            )
            
            # 計算螢幕座標（考慮縮放因子）
            if self.is_macos:
                # 將畫布座標轉換為實際螢幕像素座標
                screen_start_x = self.start_x * self.scale_factor
                screen_start_y = self.start_y * self.scale_factor
                screen_event_x = event.x * self.scale_factor
                screen_event_y = event.y * self.scale_factor
            else:
                screen_start_x = self.start_x
                screen_start_y = self.start_y
                screen_event_x = event.x
                screen_event_y = event.y
            
            # 計算相對於目標視窗的座標
            if hasattr(self, 'target_rect') and self.target_rect:
                window_left, window_top, window_right, window_bottom = self.target_rect
                
                # 轉換為相對座標
                rel_x1 = min(screen_start_x, screen_event_x) - window_left
                rel_y1 = min(screen_start_y, screen_event_y) - window_top
                rel_x2 = max(screen_start_x, screen_event_x) - window_left
                rel_y2 = max(screen_start_y, screen_event_y) - window_top
                
                # 驗證並修正座標
                window_width = window_right - window_left
                window_height = window_bottom - window_top
                rel_x1, rel_y1, w, h = validate_region(
                    int(rel_x1), int(rel_y1), int(rel_x2 - rel_x1), int(rel_y2 - rel_y1),
                    window_width, window_height
                )
                
                coord_text = f"相對座標 X:{rel_x1}, Y:{rel_y1}, W:{w}, H:{h}"
                if self.is_macos:
                    coord_text += f"\n縮放因子: {self.scale_factor}"
            else:
                # 如果沒有目標視窗，使用絕對座標
                x1, y1 = min(screen_start_x, screen_event_x), min(screen_start_y, screen_event_y)
                x2, y2 = max(screen_start_x, screen_event_x), max(screen_start_y, event.y)
                w, h = int(x2 - x1), int(y2 - y1)
                coord_text = f"絕對座標 X:{int(x1)}, Y:{int(y1)}, W:{w}, H:{h}"
            
            # 移除之前的座標文字
            self.selection_canvas.delete("coord_text")
            
            # 添加新的座標文字
            text_x = event.x + 10
            text_y = event.y - 30
            
            # 確保文字不會超出螢幕
            canvas_width = self.selection_canvas.winfo_width()
            canvas_height = self.selection_canvas.winfo_height()
            
            if text_x > canvas_width - 200:
                text_x = event.x - 200
            if text_y < 20:
                text_y = event.y + 20
            
            self.selection_canvas.create_text(
                text_x, text_y,
                text=coord_text,
                fill="red",
                font=("Arial", 10, "bold"),
                tags="coord_text",
                anchor=tk.NW,
                width=200
            )
        except Exception as e:
            logger.error(f"滑鼠拖拽錯誤: {e}")

    def _on_mouse_up(self, event):
        """滑鼠釋放"""
        self._confirm_selection(event)
    
    def _confirm_selection(self, event=None):
        """確認選取"""
        try:
            if self.rect_id and self.selection_canvas:
                coords = self.selection_canvas.coords(self.rect_id)
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    
                    # 轉換為螢幕座標（考慮縮放因子）
                    if self.is_macos:
                        screen_x1 = min(x1, x2) * self.scale_factor
                        screen_y1 = min(y1, y2) * self.scale_factor
                        screen_x2 = max(x1, x2) * self.scale_factor
                        screen_y2 = max(y1, y2) * self.scale_factor
                    else:
                        screen_x1 = min(x1, x2)
                        screen_y1 = min(y1, y2)
                        screen_x2 = max(x1, x2)
                        screen_y2 = max(y1, y2)
                    
                    # 計算相對於目標視窗的座標
                    if hasattr(self, 'target_rect') and self.target_rect:
                        window_left, window_top, window_right, window_bottom = self.target_rect
                        # 轉換為相對座標
                        rel_x = int(screen_x1 - window_left)
                        rel_y = int(screen_y1 - window_top)
                        w = int(screen_x2 - screen_x1)
                        h = int(screen_y2 - screen_y1)
                        # 驗證並修正座標
                        window_width = window_right - window_left
                        window_height = window_bottom - window_top
                        rel_x, rel_y, w, h = validate_region(rel_x, rel_y, w, h, window_width, window_height)
                        # 設定區域
                        self.set_region(rel_x, rel_y, w, h)
                        logger.debug(f"設定區域: x={rel_x}, y={rel_y}, w={w}, h={h}")
                        # 關閉選取視窗
                        self._close_selection_window()
                    else:
                        # 沒有目標視窗時使用絕對座標
                        x = int(screen_x1)
                        y = int(screen_y1)
                        w = int(screen_x2 - screen_x1)
                        h = int(screen_y2 - screen_y1)
                        self.set_region(x, y, w, h)
                        logger.debug(f"設定區域: x={x}, y={y}, w={w}, h={h}")
                        self._close_selection_window()
            else:
                messagebox.showwarning("警告", "請先選取一個區域")
        except Exception as e:
            logger.error(f"確認選取錯誤: {e}")
            self._close_selection_window()

    def _cancel_selection(self, event=None):
        """取消選取"""
        self._close_selection_window()
    
    def _close_selection_window(self):
        """關閉選取視窗"""
        try:
            if self.selection_window:
                self.selection_window.destroy()
            self.selection_window = None
            self.selection_canvas = None
            self.rect_id = None
        except Exception as e:
            logger.error(f"關閉選取視窗錯誤: {e}")
    
    def pack(self, **kwargs):
        """打包元件"""
        self.frame.pack(**kwargs)
    
    def get_region(self) -> Optional[Dict[str, int]]:
        """獲取區域配置"""
        try:
            return {
                'x': int(self.x_var.get()),
                'y': int(self.y_var.get()),
                'w': int(self.w_var.get()),
                'h': int(self.h_var.get())
            }
        except ValueError:
            return None
    
    def set_region(self, x: int, y: int, w: int, h: int):
        """設定區域配置"""
        self.x_var.set(str(x))
        self.y_var.set(str(y))
        self.w_var.set(str(w))
        self.h_var.set(str(h))
