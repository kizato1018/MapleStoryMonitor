"""
OCR Engine Module
光學字符識別引擎模組
"""

import os
import warnings
import threading
import time
from typing import Optional, Dict, List, Callable, Tuple
from PIL import Image
import numpy as np
import cv2
import sys
import traceback
from utils.log import get_logger

logger = get_logger(__name__)

DEBUG = True

class OCREngine:
    """OCR處理引擎"""
    
    def __init__(self, root):
        self.root = root
        self.ocr_reader = None
        self.is_initialized = False
        self.is_running = False
        self.ocr_thread = None
        self.last_ocr_time = 0
        self.ocr_interval = 0.1  # OCR處理最小間隔（秒）
        self.tabs_order = None
        
        # 回調函數：當OCR結果更新時調用
        self.result_callback: Optional[Callable[[str, str], None]] = None
    
    def initialize(self, tabs_order: Optional[List[str]] = None) -> None:
        """初始化OCR引擎（異步）"""
        if self.is_initialized or self.ocr_reader is not None:
            logger.info("OCR引擎已初始化，跳過重複初始化")
            return
        def init_thread():
            try:
                self.tabs_order = tabs_order
                import easyocr
                warnings.filterwarnings("ignore", message="'pin_memory' argument is set as true but no accelerator is found")
                logger.info("正在初始化OCR引擎...")
                self.ocr_reader = easyocr.Reader(['en'], gpu=False)
                self.is_initialized = True
                logger.info("OCR引擎初始化完成")
                self.is_running = True
            except ImportError:
                logger.error("錯誤: 未安裝easyocr。請執行: pip install easyocr")
            except Exception as e:
                logger.error(f"OCR引擎初始化失敗: {e}")
        
        threading.Thread(target=init_thread, daemon=True).start()
    
    def set_result_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        設定結果回調函數
        
        Args:
            callback: 回調函數，參數為(tab_name, result)
        """
        self.result_callback = lambda tab_name, result: self.root.after(0, callback(tab_name, result))
    
    
    def process_images(self, images_dict: Dict[str, Image.Image], tab_enabled_vars) -> None:
        """
        處理多個圖像的OCR - 合併圖像後進行單次OCR
        
        Args:
            images_dict: 圖像字典 {tab_name: image}
        """
        if not self.is_initialized or not self.ocr_reader:
            return
        
        current_time = time.time()
        if current_time - self.last_ocr_time < self.ocr_interval:
            return
        
        try:
            status_images = {}
            potions_images = {}
            for tab_name, image in images_dict.items():
                if DEBUG:
                    os.makedirs('tmp', exist_ok=True)
                    image.save(f'tmp/{tab_name}.png')
                if tab_name == 'HP' or tab_name == 'MP' or tab_name == 'EXP':
                    status_images[tab_name] = image
                elif '藥水' in tab_name:
                    potions_images[tab_name] = image
                else:
                    self._process_image(tab_name, image)
            # 處理狀態欄部分
            hp_enabled = tab_enabled_vars['HP'].get()
            mp_enabled = tab_enabled_vars['MP'].get()
            exp_enabled = tab_enabled_vars['EXP'].get()
            if status_images:
                self._process_status_part(status_images, hp_enabled, mp_enabled, exp_enabled)
            # 處理藥水欄部分
            potions_enabled = [tab_enabled_vars[f'藥水{i+1}'].get() for i in range(8)]
            if potions_images:
                self._process_potion_part(potions_images, potions_enabled)
            self.last_ocr_time = current_time
        except Exception as e:
            logger.error(f"處理圖像時發生錯誤: {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback_details = traceback.extract_tb(exc_traceback)
            
            # 顯示每一層 traceback
            for tb in traceback_details:
                logger.error(f"檔案: {tb.filename}, 行數: {tb.lineno}, 函式: {tb.name}")
                logger.error(f"  程式碼: {tb.line}")



    
    def _process_status_part(self, images: Dict[str, Image.Image], hp_enabled: bool, mp_enabled: bool, exp_enabled: bool) -> None:
        """
        處理狀態欄部分的OCR
        Args:
            images: 狀態欄圖像
            hp_enabled: 是否啟用HP狀態
            mp_enabled: 是否啟用MP狀態
            exp_enabled: 是否啟用SP狀態
        """
        if all((not hp_enabled, not mp_enabled, not exp_enabled)):
            logger.debug("狀態欄部分未啟用，跳過處理")
            return
        
        tab_order = ['HP', 'MP', 'EXP']
        process_images = []
        for tab_name in tab_order:
            image = images.get(tab_name)
            if image is not None:
                process_images.append((tab_name, self._preprocess_status_image(np.array(image))))

        

        merged_image, tab_positions = self._merge_images(process_images)
        if DEBUG:
            os.makedirs('tmp', exist_ok=True)
            save_image = cv2.cvtColor(merged_image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(f'tmp/merged_status.png', save_image)
        allowlist = '0123456789[]./%'
        results = self.ocr_reader.readtext(merged_image, allowlist=allowlist)
        if not results:
            logger.warning("狀態欄OCR結果為空")
            return
        
        # 計算每個OCR結果的中心座標，並根據位置分配到對應的狀態欄
        tab_results = {tab_name: [] for tab_name in tab_order}
        
        for result in results:
            try:
                # 檢查結果格式
                if len(result) < 2:
                    continue
                
                bbox = result[0]
                text = result[1]
                confidence = result[2] if len(result) > 2 else 1.0
                
                # 計算bbox中心點
                center_y = sum(point[1] for point in bbox) / len(bbox)
                
                # 根據中心點位置分配到對應的狀態欄
                for tab_name, (x, y, w, h) in tab_positions.items():
                    if y <= center_y <= y + h:
                        tab_results[tab_name].append(text.strip())
                        break
            except Exception as e:
                logger.debug(f"處理OCR結果時發生錯誤: {e}")
                continue
        
        enable_list = [hp_enabled, mp_enabled, exp_enabled]
        # 將結果回調
        for i, tab_name in enumerate(tab_order):
            if enable_list[i] and tab_results[tab_name]:
                result_text = ' '.join(tab_results[tab_name])
                logger.info(f"{tab_name} OCR結果: {result_text}")
                if self.result_callback:
                    self.result_callback(tab_name, result_text)
            elif enable_list[i]:
                logger.warning(f"{tab_name} OCR結果為空")
                if self.result_callback:
                    self.result_callback(tab_name, '無法辨識')
        
        return
    
    def _process_potion_part(self, images: Dict[str, Image.Image], potions_enabled: List[bool]) -> None:
        """
        處理藥水欄部分的OCR
        Args:
            images: 藥水欄圖像
            potions_enabled: 藥水欄啟用狀態列表
        """
        if not any(potions_enabled):
            logger.debug("藥水欄部分未啟用，跳過處理")
            return
        
        tab_order = [f'藥水{i+1}' for i in range(8)]
        process_images = []
        for tab_name in tab_order:
            image = images.get(tab_name)
            if image is not None:
                process_images.append((tab_name, self._preprocess_potion_image(np.array(image))))

        
        merged_image, tab_postionts = self._merge_images(process_images)
        if DEBUG:
            os.makedirs('tmp', exist_ok=True)
            cv2.imwrite(f'tmp/merged_potions.png', merged_image)
        allowlist = '0123456789'
        results = self.ocr_reader.readtext(merged_image, allowlist=allowlist, detail=1, low_text=0.5, text_threshold=0.8, link_threshold=0.7)
        if not results:
            logger.warning("藥水欄OCR結果為空")
            return
        
        # 計算每個OCR結果的中心座標，並根據位置分配到對應的藥水欄
        tab_results = {tab_name: [] for tab_name in tab_order}
        for result in results:
            try:
                # 檢查結果格式
                if len(result) < 2:
                    continue
                
                bbox = result[0]
                text = result[1]
                confidence = result[2] if len(result) > 2 else 1.0
                
                # 檢查置信度
                if confidence < 0.5:
                    continue
                
                # 檢查 bbox 格式
                if not isinstance(bbox, list) or len(bbox) < 4:
                    continue
                
                # 計算bbox中心點
                center_x = sum(point[0] for point in bbox) / len(bbox)
                center_y = sum(point[1] for point in bbox) / len(bbox)
                
                # 根據中心點位置分配到對應的藥水欄
                for tab_name, (x, y, w, h) in tab_postionts.items():
                    if x <= center_x <= x + w and y <= center_y <= y + h:
                        tab_results[tab_name].append(text.strip())
                        break
            except Exception as e:
                logger.debug(f"處理OCR結果時發生錯誤: {e}")
                continue
        
        # 將結果回調
        for i, tab_name in enumerate(tab_order):
            if potions_enabled[i] and tab_results[tab_name]:
                result_text = ' '.join(tab_results[tab_name])
                logger.info(f"{tab_name} OCR結果: {result_text}")
                if self.result_callback:
                    self.result_callback(tab_name, result_text)
            elif potions_enabled[i]:
                logger.warning(f"{tab_name} OCR結果為空")
                if self.result_callback:
                    self.result_callback(tab_name, '無法辨識')

        return

    def _process_image(self, tab_name: str, image: Image.Image) -> None:
        """
        處理單個圖像的OCR
        Args:
            tab_name: 圖像所屬的分頁名稱
            image: 要處理的圖像
        """
        try:
            allowlist = '0123456789,./%[]'
            results = self.ocr_reader.readtext(np.array(image), allowlist=allowlist, detail=0)
            
            if not results:
                logger.warning(f"{tab_name} OCR結果為空")
                if self.result_callback:
                    self.result_callback(tab_name, '無法辨識')
                return
            
            # 安全地獲取第一個結果
            text = str(results[0]).strip() if len(results) > 0 else '無法辨識'
            logger.info(f"{tab_name} OCR結果: {text}")
            
            if self.result_callback:
                self.result_callback(tab_name, text)
                
        except Exception as e:
            logger.error(f"處理單個圖像 {tab_name} 時發生錯誤: {e}")
            if self.result_callback:
                self.result_callback(tab_name, 'OCR錯誤')

    def _preprocess_status_image(self, image: np.ndarray) -> np.ndarray:
        """
        預處理狀態欄圖像
        Args:
            image: 狀態欄圖像
        Returns:
            np.ndarray: 預處理後的圖像
        """
        # output = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # h, w = output.shape[:2]
        # scale = min(200 / ((w + h) / 2), 3.5)
        # output = cv2.resize(output, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        return image      
        
    def _preprocess_potion_image(self, image: np.ndarray) -> np.ndarray:
        """
        預處理藥水欄圖像
        Args:
            image: 藥水欄圖像
        Returns:
            np.ndarray: 預處理後的圖像
        """
        img = image.copy()
        h, w = img.shape[:2]
        avg_size = (w + h) / 2
        scale = min(200 / avg_size, 3.5)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        h, w = img.shape[:2]
        top, bottom, left, right = (0.6, 0.0, 0.0, 0.12)  # 預設裁切比例
        img = img[int(h * top):int(h * (1-bottom)), int(w * left):int(w * (1-right))]
        

        # 轉換為 HSV 色彩空間
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # 取得 S（彩度）通道
        saturation = hsv[:, :, 1]

        # 設定彩度門檻（例如 100）
        threshold = 100

        # 建立遮罩：彩度超過門檻的位置
        mask1 = saturation > threshold

        # 將彩度高的像素設為黑色 (0,0,0)
        output = img.copy()
        output[mask1] = [0, 0, 0]
        
        
        # 建立遮罩（需比原圖大2）
        output = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
        
        #進行手動2質化
        output = cv2.adaptiveThreshold(
            output, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY, 15, 2
        )
        kernel = np.ones((3,3), np.uint8) if min(img.shape[0], img.shape[1]) > 100 else np.ones((2,2), np.uint8)
        output = cv2.morphologyEx(output, cv2.MORPH_CLOSE, kernel , iterations=1)
            
        h, w = output.shape
        mask = np.zeros((h + 2, w + 2), np.uint8)

        # 複製原圖作為填色目標
        floodfilled = output.copy()

        # 對四個邊緣進行 floodFill，尋找相連的黑色 (0)
        threshold = 255
        for x in range(w):
            if floodfilled[0, x] >= threshold:
                cv2.floodFill(floodfilled, mask, (x, 0), 0)
            if floodfilled[h - 1, x] >= threshold:
                cv2.floodFill(floodfilled, mask, (x, h - 1), 0)
        for y in range(h):
            if floodfilled[y, 0] >= threshold:
                cv2.floodFill(floodfilled, mask, (0, y), 0)
            if floodfilled[y, w - 1] >= threshold:
                cv2.floodFill(floodfilled, mask, (w - 1, y), 0)

        # floodfilled 中原本與邊界連通的黑色已變為白色 (255)
        # 其餘區域保留原樣
        output = floodfilled
        kernel = np.ones((4,4), np.uint8) if min(img.shape[0], img.shape[1]) > 100 else np.ones((3,3), np.uint8)
        output = cv2.morphologyEx(output, cv2.MORPH_OPEN, kernel , iterations=1)

        
        # 對前景做 connected component analysis
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(output, connectivity=8)
        
        min_area = img.shape[0] * img.shape[1] * 0.02
        min_height = img.shape[0] * 0.55
        max_width = img.shape[1] * 0.25

        # 四等分點
        width = img.shape[1]
        quarters = [width * i / 4 for i in range(1, 4)]
        quarter_margin = w * 0.01
    
        for i in range(1, num_labels):  # 跳過 index 0：背景
            area = stats[i, cv2.CC_STAT_AREA]
            height = stats[i, cv2.CC_STAT_HEIGHT]
            width_ = stats[i, cv2.CC_STAT_WIDTH]
            mid_x = stats[i, cv2.CC_STAT_LEFT] + width_ / 2

            # 條件 1：太小
            too_small = area < min_area
            too_short = height < min_height
            too_wide = width_ > max_width

            # 條件 2：avg_x 落在四等分點
            near_quarter = any(abs(mid_x - q) < quarter_margin for q in quarters)

            if too_small or too_short or too_wide or near_quarter:
                output[labels == i] = 0  # 填為黑色（背景）
        
        return output

    def _merge_images(self, images_with_tab: List[Tuple[str,np.ndarray]]) -> Tuple[np.ndarray, Dict[str, Tuple[int, int, int, int]]]:
        """合併多個圖像為一個大圖像，並返回每個圖像的位置
        Args:
            images: 圖像列表 [np.ndarray, ...]"""
        if not images_with_tab:
            return np.array([])
        
        # 過濾出非None的圖像
        valid_images = [(tab_name, img) for tab_name, img in images_with_tab if img is not None]
        if not valid_images:
            return np.array([]), {}

        # 計算合併後的圖像尺寸
        max_width = max(img.shape[1] for _, img in valid_images)
        total_height = sum(img.shape[0] for _, img in valid_images)

        # 創建空白的合併圖像
        if len(valid_images[0][1].shape) == 3:  # 彩色圖像
            merged = np.zeros((total_height, max_width, 3), dtype=np.uint8)
        else:  # 灰度圖像
            merged = np.zeros((total_height, max_width), dtype=np.uint8)

        # 記錄每個圖像在合併圖像中的位置
        tab_positions = {}
        current_y = 0

        for tab_name, img in valid_images:
            h, w = img.shape[:2]
            
            # 將圖像放置到合併圖像中
            if len(img.shape) == 3:  # 彩色圖像
                merged[current_y:current_y + h, :w] = img
            else:  # 灰度圖像
                merged[current_y:current_y + h, :w] = img
            
            # 記錄位置 (x, y, width, height)
            tab_positions[tab_name] = (0, current_y, w, h)
            current_y += h

        return merged, tab_positions
        
    
    def get_status(self) -> str:
        """獲取OCR引擎狀態"""
        if not self.is_initialized:
            return "初始化中..."
        elif self.is_running:
            return "運行中"
        else:
            return "已停止"
