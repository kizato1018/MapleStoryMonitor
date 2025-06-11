"""
Windows Capture Module
Windows平台捕捉實現
"""

import time
import ctypes
import sys
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image
import subprocess
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
            self.scale_factor = self.get_display_scale_factor()
            self.is_initialized = True
            logger.debug(f"Windows捕捉資源初始化成功: {w}x{h}")
            return True
            
        except Exception as e:
            logger.error(f"Windows捕捉資源初始化失敗: {e}")
            self.cleanup_resources()
            return False
    
    def capture_window(self) -> Optional[Image.Image]:
        """捕捉完整視窗畫面"""
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

            # 取得視窗大小與座標
            left, top, right, bottom = self.get_window_rect(hwnd)
            window_width = right - left
            window_height = bottom - top

            # 直接捕捉整個視窗內容
            hdcTemp = hdcMem.CreateCompatibleDC()
            hbmTemp = win32ui.CreateBitmap()
            hbmTemp.CreateCompatibleBitmap(hdcMem, window_width, window_height)
            hdcTemp.SelectObject(hbmTemp)

            result = self.user32.PrintWindow(hwnd, hdcTemp.GetSafeHdc(), 2)  # PW_RENDERFULLCONTENT

            if result:
                # 直接將整個視窗內容轉為PIL Image
                bmpinfo = hbmTemp.GetInfo()
                bmpstr = hbmTemp.GetBitmapBits(True)
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
                )
            else:
                # 回退到 BitBlt 畫面
                hdcTemp.BitBlt((0, 0), (window_width, window_height), hdcMem, (0, 0), win32con.SRCCOPY)
                bmpinfo = hbmTemp.GetInfo()
                bmpstr = hbmTemp.GetBitmapBits(True)
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
                )

            # 清理臨時資源
            win32gui.DeleteObject(hbmTemp.GetHandle())
            hdcTemp.DeleteDC()

            return img
        except Exception as e:
            logger.error(f"Windows捕捉完整畫面錯誤: {e}")
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
                # 獲取視窗矩形區域
                left, top, right, bottom = win32gui.GetWindowRect(window_handle)
                left = int(left * self.scale_factor)
                top = int(top * self.scale_factor)
                right = int(right * self.scale_factor)
                bottom = int(bottom * self.scale_factor)
                return (left, top, right, bottom)
        except Exception as e:
            logger.error(f"獲取視窗矩形錯誤: {e}")
        return None

    @staticmethod
    def get_display_scale_factor() -> float:
        """獲取顯示縮放因子（靜態方法，可被外部調用）"""
        try:
            result = subprocess.run(
                ['pythonw', 'utils/get_scalor_factor.py'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                scale_factor = float(result.stdout.strip())
                logger.info(f"從 subprocess 獲取 Windows 縮放因子: {scale_factor}")
                return scale_factor
            else:
                logger.warning(f"subprocess 獲取縮放因子失敗: {result.stderr}")
                return 1.0
        except Exception as e:
            logger.error(f"獲取 Windows 縮放因子錯誤: {e}")
            return 1.0