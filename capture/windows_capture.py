"""
Windows Capture Module
Windows平台捕捉實現
"""

import time
import ctypes
import sys
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image
from utils.log import get_logger

logger = get_logger(__name__)

# 只在Windows平台導入win32相關模組
if sys.platform == "win32":
    try:
        import win32gui
        import win32ui
        import win32con
        import win32api
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        logger.warning("警告: Windows平台需要安裝pywin32: pip install pywin32")
else:
    WIN32_AVAILABLE = False

from .base_capture import BaseCaptureEngine


class WindowsCaptureEngine(BaseCaptureEngine):
    """Windows平台捕捉引擎"""
    
    def __init__(self):
        super().__init__()
        if not WIN32_AVAILABLE:
            logger.warning("警告: Windows捕捉引擎僅在Windows平台可用")
            return
        self.user32 = ctypes.windll.user32
    
    def initialize_resources(self, window_handle: int, region: Dict[str, int]) -> bool:
        """初始化Windows捕捉資源"""
        if not WIN32_AVAILABLE:
            return False
        
        try:
            if not self.is_window_valid(window_handle):
                return False
            
            # 檢查視窗是否被最小化
            if win32gui.IsIconic(window_handle):
                win32gui.ShowWindow(window_handle, win32con.SW_RESTORE)
                time.sleep(0.1)
            
            x, y, w, h = region['x'], region['y'], region['w'], region['h']
            
            # 獲取視窗設備上下文
            hdcSrc = win32gui.GetWindowDC(window_handle)
            hdcMem = win32ui.CreateDCFromHandle(hdcSrc)
            hdcBitmap = hdcMem.CreateCompatibleDC()
            
            # 創建位圖
            hbm = win32ui.CreateBitmap()
            hbm.CreateCompatibleBitmap(hdcMem, w, h)
            hdcBitmap.SelectObject(hbm)
            
            self.current_resources = {
                'hwnd': window_handle,
                'hdcSrc': hdcSrc,
                'hdcMem': hdcMem,
                'hdcBitmap': hdcBitmap,
                'hbm': hbm,
                'region': region
            }
            
            self.is_initialized = True
            logger.debug(f"Windows捕捉資源初始化成功: {w}x{h}")
            return True
            
        except Exception as e:
            logger.error(f"Windows捕捉資源初始化失敗: {e}")
            self.cleanup_resources()
            return False
    
    def capture_region(self) -> Optional[Image.Image]:
        """捕捉指定區域"""
        if not WIN32_AVAILABLE:
            return None
        
        if not self.is_initialized or not self.current_resources:
            return None
        
        try:
            resources = self.current_resources
            hwnd = resources['hwnd']
            hdcBitmap = resources['hdcBitmap']
            hdcMem = resources['hdcMem']
            hbm = resources['hbm']
            region = resources['region']
            
            # 確保視窗仍然存在
            if not self.is_window_valid(hwnd):
                return None
            
            x, y, w, h = region['x'], region['y'], region['w'], region['h']
            
            # 獲取視窗大小
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            window_width = right - left
            window_height = bottom - top
            
            # 創建臨時位圖來存放整個視窗
            hdcTemp = hdcMem.CreateCompatibleDC()
            hbmTemp = win32ui.CreateBitmap()
            hbmTemp.CreateCompatibleBitmap(hdcMem, window_width, window_height)
            hdcTemp.SelectObject(hbmTemp)
            
            # 使用PrintWindow擷取整個視窗
            result = self.user32.PrintWindow(hwnd, hdcTemp.GetSafeHdc(), 2)  # PW_RENDERFULLCONTENT
            
            if result:
                # 從整個視窗中複製指定區域到目標位圖
                hdcBitmap.BitBlt((0, 0), (w, h), hdcTemp, (x, y), win32con.SRCCOPY)
            else:
                # 回退到直接BitBlt方法
                hdcBitmap.BitBlt((0, 0), (w, h), hdcMem, (x, y), win32con.SRCCOPY)
            
            # 清理臨時資源
            win32gui.DeleteObject(hbmTemp.GetHandle())
            hdcTemp.DeleteDC()
            
            # 獲取位圖數據
            bmpinfo = hbm.GetInfo()
            bmpstr = hbm.GetBitmapBits(True)
            
            # 轉換為PIL Image
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            return img
            
        except Exception as e:
            logger.error(f"Windows捕捉錯誤: {e}")
            return None
    
    def cleanup_resources(self) -> None:
        """清理Windows捕捉資源"""
        if not WIN32_AVAILABLE:
            return
        
        if self.current_resources:
            try:
                resources = self.current_resources
                if 'hbm' in resources:
                    win32gui.DeleteObject(resources['hbm'].GetHandle())
                if 'hdcBitmap' in resources:
                    resources['hdcBitmap'].DeleteDC()
                if 'hdcMem' in resources:
                    resources['hdcMem'].DeleteDC()
                if 'hdcSrc' in resources and 'hwnd' in resources:
                    win32gui.ReleaseDC(resources['hwnd'], resources['hdcSrc'])
                logger.debug("Windows捕捉資源已清理")
            except Exception as e:
                logger.error(f"清理Windows捕捉資源錯誤: {e}")
            finally:
                self.current_resources = None
                self.is_initialized = False
    
    def is_window_valid(self, window_handle: int) -> bool:
        """檢查Windows視窗是否有效"""
        if not WIN32_AVAILABLE:
            return False
        
        try:
            return win32gui.IsWindow(window_handle)
        except:
            return False
    
    def get_window_list(self) -> List[Tuple[int, str]]:
        """獲取Windows系統視窗列表"""
        if not WIN32_AVAILABLE:
            return []
        
        window_list = []
        
        def enum_callback(hwnd, window_list):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if window_text.strip():
                    window_list.append((hwnd, window_text))
            return True
        
        try:
            win32gui.EnumWindows(enum_callback, window_list)
        except Exception as e:
            logger.error(f"獲取視窗列表錯誤: {e}")
        
        return window_list
    
    def get_window_rect(self, window_handle: int) -> Optional[Tuple[int, int, int, int]]:
        """獲取Windows視窗矩形區域"""
        if not WIN32_AVAILABLE:
            return None
        
        try:
            if self.is_window_valid(window_handle):
                return win32gui.GetWindowRect(window_handle)
        except Exception as e:
            logger.error(f"獲取視窗矩形錯誤: {e}")
        return None
