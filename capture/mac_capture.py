import sys
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image

from utils.log import get_logger
logger = get_logger(__name__)

# 根據平台條件導入
PYOBJC_AVAILABLE = False
if sys.platform == "darwin":
    try:
        from Cocoa import NSApplication, NSWorkspace
        from Quartz import (
            CGWindowListCopyWindowInfo, CGWindowListCreateImage,
            CGRectMake, CGRectNull, kCGWindowListOptionOnScreenOnly,
            kCGWindowListExcludeDesktopElements, kCGWindowImageDefault,
            kCGNullWindowID, CGDataProviderCopyData, CGImageGetDataProvider,
            CGImageGetWidth, CGImageGetHeight, kCGWindowImageBoundsIgnoreFraming,
            CGImageGetBytesPerRow, kCGWindowListOptionIncludingWindow
        )
        PYOBJC_AVAILABLE = True
    except ImportError as e:
        logger.warning("警告: PyObjC未安裝，請執行: pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz")
        logger.error(f"錯誤: {e}")

from .base_capture import BaseCaptureEngine

class MacCaptureEngine(BaseCaptureEngine):
    def __init__(self):
        super().__init__()
        if not PYOBJC_AVAILABLE:
            logger.warning("警告: Mac捕捉引擎僅在Mac平台可用且需要PyObjC支援")
            return
        self.window_id = None
        self.capture_rect = None
        self._init_count = 0

    def initialize_resources(self, window_handle: Any, region: Dict[str, int]) -> bool:
        if not PYOBJC_AVAILABLE:
            return False

        self._init_count += 1

        if (self.is_initialized and
            self.window_id == window_handle and
            self.current_resources and
            self._same_region(region)):
            return True

        if self.is_initialized:
            self.cleanup_resources()

        try:
            self.window_id = window_handle
            x = region.get('x', 0)
            y = region.get('y', 0)
            w = region.get('w', region.get('width', 800))
            h = region.get('h', region.get('height', 600))
            self.capture_rect = CGRectMake(x, y, w, h)

            if window_handle and not self.is_window_valid(window_handle):
                logger.warning(f"警告: 視窗ID {window_handle} 可能無效")

            self.current_resources = {
                'window_id': self.window_id,
                'rect': self.capture_rect,
                'region': region.copy()
            }
            self.is_initialized = True
            return True

        except Exception as e:
            logger.error(f"Mac捕捉資源初始化失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _same_region(self, new_region: Dict[str, int]) -> bool:
        old_region = self.current_resources.get('region') if self.current_resources else None
        if not old_region:
            return False
        return (old_region.get('x') == new_region.get('x') and
                old_region.get('y') == new_region.get('y') and
                old_region.get('w') == new_region.get('w') and
                old_region.get('h') == new_region.get('h'))

    def capture_window(self) -> Optional[Image.Image]:
        if not PYOBJC_AVAILABLE or not self.is_initialized:
            return None
        try:
            if self.window_id:
                # 取得視窗資訊
                window_info = self._get_window_info(self.window_id)
                if not window_info:
                    logger.warning("無法獲取視窗資訊")
                    return None
                bounds = window_info.get('kCGWindowBounds')
                if not bounds:
                    logger.warning("無法獲取視窗邊界")
                    return None
                x = int(bounds['X'])
                y = int(bounds['Y'])
                w = int(bounds['Width'])
                h = int(bounds['Height'])

                # 直接抓整個視窗
                image_ref = CGWindowListCreateImage(
                    CGRectMake(x, y, w, h),
                    kCGWindowListOptionIncludingWindow,
                    self.window_id,
                    kCGWindowImageBoundsIgnoreFraming
                )
                if not image_ref:
                    logger.warning("CGWindowListCreateImage 回傳 None")
                    return None
                pil_img = self._cgimage_to_pil(image_ref)
                if pil_img is None:
                    logger.warning("CGImage 轉 PIL 失敗")
                    return None
                return pil_img
            # else:
                # # ...原本的螢幕區域擷取...
                # print("沒有指定視窗ID，使用螢幕區域擷取")
                # image_ref = CGWindowListCreateImage(
                #     self.capture_rect,
                #     kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
                #     kCGNullWindowID,
                #     kCGWindowImageDefault
                # )
                # if not image_ref:
                #     return None
                # return self._cgimage_to_pil(image_ref)
        except Exception as e:
            logger.error(f"Mac區域捕捉錯誤: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_window_info(self, window_id: Any) -> Optional[Dict]:
        try:
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionIncludingWindow,
                window_id
            )
            for window_info in window_list:
                if window_info.get('kCGWindowNumber') == window_id:
                    return window_info
            return None
        except Exception as e:
            logger.error(f"獲取視窗資訊錯誤: {e}")
            return None

    def _cgimage_to_pil(self, cgimage_ref) -> Optional[Image.Image]:
        try:
            width = CGImageGetWidth(cgimage_ref)
            height = CGImageGetHeight(cgimage_ref)
            bytes_per_row = CGImageGetBytesPerRow(cgimage_ref)

            data_provider = CGImageGetDataProvider(cgimage_ref)
            if not data_provider:
                return None

            data = CGDataProviderCopyData(data_provider)
            if not data:
                return None

            image_data = bytes(data)
            expected_length = height * bytes_per_row
            if len(image_data) < expected_length:
                return None

            try:
                image = Image.frombytes('RGBA', (width, height), image_data, 'raw', 'BGRA', bytes_per_row, 1)
            except:
                try:
                    image = Image.frombytes('RGB', (width, height), image_data, 'raw', 'BGR', bytes_per_row, 1)
                except:
                    return None

            if image.mode == 'RGBA':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1])
                return rgb_image

            return image.convert('RGB')

        except Exception as e:
            logger.error(f"CGImage轉換錯誤: {e}")
            import traceback
            traceback.print_exc()
            return None

    def cleanup_resources(self) -> None:
        self.window_id = None
        self.capture_rect = None
        self.current_resources = None
        self.is_initialized = False

    def is_window_valid(self, window_handle: Any) -> bool:
        if not PYOBJC_AVAILABLE:
            return False

        try:
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
                kCGNullWindowID
            )
            return any(win.get('kCGWindowNumber') == window_handle for win in window_list)
        except:
            return False

    def get_window_list(self) -> List[Tuple[Any, str]]:
        if not PYOBJC_AVAILABLE:
            return []

        try:
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
                kCGNullWindowID
            )
            windows = []
            for win in window_list:
                window_id = win.get('kCGWindowNumber')
                window_name = win.get('kCGWindowName', '')
                owner_name = win.get('kCGWindowOwnerName', '')
                display_name = f"{owner_name} - {window_name}" if owner_name and window_name else owner_name or window_name or f"視窗 {window_id}"
                if window_id and display_name.strip():
                    windows.append((window_id, display_name))
            return windows
        except:
            return []

    def get_window_rect(self, window_handle: Any) -> Optional[Tuple[int, int, int, int]]:
        if not PYOBJC_AVAILABLE:
            return None
        try:
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
                kCGNullWindowID
            )
            for win in window_list:
                if win.get('kCGWindowNumber') == window_handle:
                    bounds = win.get('kCGWindowBounds')
                    if bounds:
                        # 獲取邏輯座標
                        logical_x = int(bounds['X'])
                        logical_y = int(bounds['Y'])
                        logical_width = int(bounds['Width'])
                        logical_height = int(bounds['Height'])
                        
                        # 獲取顯示縮放因子
                        scale_factor = self.get_display_scale_factor()
                        logger.debug(f"顯示縮放因子: {scale_factor}")
                        logger.debug(f"邏輯尺寸: {logical_width}x{logical_height}")
                        
                        # 轉換為實際像素座標
                        actual_x = int(logical_x * scale_factor)
                        actual_y = int(logical_y * scale_factor)
                        actual_width = int(logical_width * scale_factor)
                        actual_height = int(logical_height * scale_factor)
                        
                        logger.debug(f"實際像素尺寸: {actual_width}x{actual_height}")
                        
                        return (actual_x, actual_y, actual_x + actual_width, actual_y + actual_height)
            return None
        except Exception as e:
            logger.error(f"獲取視窗矩形錯誤: {e}")
            return None
    
    @staticmethod
    def get_display_scale_factor() -> float:
        """獲取顯示縮放因子（靜態方法，可被外部調用）"""
        if not PYOBJC_AVAILABLE:
            return 1.0

        try:
            from Cocoa import NSScreen
            main_screen = NSScreen.mainScreen()
            if main_screen:
                backing_scale_factor = main_screen.backingScaleFactor()
                return float(backing_scale_factor)
            return 1.0
        except Exception as e:
            logger.warning(f"無法獲取顯示縮放因子: {e}")
            # 嘗試另一種方法
            try:
                import subprocess
                result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                      capture_output=True, text=True)
                if 'Retina' in result.stdout:
                    return 2.0  # 大多數 Retina 顯示器
                return 1.0
            except:
                return 2.0  # 預設為 2.0，因為大多數現代 Mac 都是 Retina
