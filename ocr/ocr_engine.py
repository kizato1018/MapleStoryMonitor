"""
OCR Engine Module
光學字符識別引擎模組
"""

import warnings
import threading
import time
from typing import Optional, Dict, List, Callable, Tuple
from PIL import Image
import numpy as np
import cv2
from utils.log import get_logger

logger = get_logger(__name__)

class OCREngine:
    """OCR處理引擎"""
    
    def __init__(self, root, allow_list: str = "0123456789.[]/%"):
        self.root = root
        self.allow_list = allow_list
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
    
    
    def process_images(self, images_dict: Dict[str, Image.Image]) -> None:
        """
        處理多個圖像的OCR - 合併圖像後進行單次OCR
        
        Args:
            images_dict: 圖像字典 {tab_name: image}
        """
        # logger.debug(f"[OCR DEBUG] process_images called, images: {list(images_dict.keys())}")  # <--- debug
        logger.debug(f"[OCR DEBUG] process_images called, images: {list(images_dict.keys())}")  # <--- debug
        if not self.is_initialized or not self.ocr_reader:
            return
        
        current_time = time.time()
        if current_time - self.last_ocr_time < self.ocr_interval:
            return

        try:
            # 過濾有效圖像
            potion_images = {}
            status_images = {}
            for name, img in images_dict.items():
                if isinstance(img, Image.Image):
                    if '藥水' in name:
                        potion_images[name] = img
                    else:
                        status_images[name] = img
            if not status_images and not potion_images:
                return
            
            # 處理藥水圖像
            for tab_name, image in potion_images.items():
                # Image.Image.save(image, f"tmp/{tab_name}.png")  # 保存圖像以便調試
                # new_image = Image.open(f"tmp/{tab_name}.png")
                result = self._process_potion_image(image, tab_name)
                if self.result_callback:
                    self.result_callback(tab_name, result)
            


            if len(status_images) == 1:
                # 單個圖像直接處理
                tab_name, image = next(iter(status_images.items()))
                result = self._process_single_image(image)
                if self.result_callback:
                    self.result_callback(tab_name, result)
            else:
                # 多個圖像合併處理
                merged_image, tab_positions = self._merge_images(status_images)
                merged_results = self._process_merged_image(merged_image, tab_positions)
                
                # 分配結果給各個標籤
                for tab_name, result in merged_results.items():
                    # 如果結果為"無法識別"，則嘗試單獨處理該圖像
                    if result == "無法識別":
                        result = self._process_single_image(status_images[tab_name])
                    
                    if self.result_callback:
                        self.result_callback(tab_name, result)
                    
            
            self.last_ocr_time = current_time
            
        except Exception as e:
            logger.debug(f"批量OCR處理錯誤: {e}")
            

    def _potions_preprocess_image(self, image):
        try:
            img = np.array(image)
            scale = max(min(80 / img.shape[0], 1), 3)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            # 轉換為 HSV 色彩空間
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # 取得 S（彩度）通道
            saturation = hsv[:, :, 1]

            # 設定彩度門檻（例如 100）
            threshold = 85

            # 建立遮罩：彩度超過門檻的位置
            mask1 = saturation > threshold

            # 將彩度高的像素設為黑色 (0,0,0)
            output = img.copy()
            output[mask1] = [0, 0, 0]
            
            
            # 建立遮罩（需比原圖大2）
            output = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
            
            #進行手動2質化
            _, output = cv2.threshold(output, 80, 255, cv2.THRESH_BINARY)
                
            h, w = output.shape
            mask = np.zeros((h + 2, w + 2), np.uint8)

            # 複製原圖作為填色目標
            floodfilled = output.copy()

            # 對四個邊緣進行 floodFill，尋找相連的黑色 (0)
            threshold = 255
            to = 0
            for x in range(w):
                if floodfilled[0, x] == threshold:
                    cv2.floodFill(floodfilled, mask, (x, 0), to)
                if floodfilled[h - 1, x] == threshold:
                    cv2.floodFill(floodfilled, mask, (x, h - 1), to)
            for y in range(h):
                if floodfilled[y, 0] == threshold:
                    cv2.floodFill(floodfilled, mask, (0, y), to)
                if floodfilled[y, w - 1] == threshold:
                    cv2.floodFill(floodfilled, mask, (w - 1, y), to)

            # floodfilled 中原本與邊界連通的黑色已變為白色 (255)
            # 其餘區域保留原樣
            output = floodfilled
            # output = cv2.bitwise_not(output)
            output = cv2.morphologyEx(output, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)

            
        except Exception as e:
            logger.debug(f"圖像預處理錯誤: {e}")
            output = image

        return output

    def _potions_postprocess_result(self, result: str) -> str:
        """
        處理藥水OCR結果的後處理
        
        Args:
            result: OCR識別結果
        
        Returns:
            str: 處理後的結果
        """
        if not result:
            return (None, "無法識別", 0.0)
        
        # 找到最左下角的結果
        # 結果格式: (bbox, text, confidence)
        # bbox格式: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        
        best_result = None
        max_y = -1
        min_x = float('inf')
        
        for bbox, text, confidence in result:
            # 計算左下角的座標 (最小x值和最大y值)
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            
            left_x = min(x_coords)
            bottom_y = max(y_coords)
            
            # 優先選擇最下方的，如果y座標相同則選擇最左邊的
            if bottom_y > max_y or (bottom_y == max_y and left_x < min_x):
                max_y = bottom_y
                min_x = left_x
                best_result = (bbox, text, confidence)
        
        return best_result if best_result else (None, "無法識別", 0.0)

    def _process_potion_image(self, image: Image.Image, name) -> str:
        """
        處理藥水圖像的OCR
        
        Args:
            image: 要處理的圖像
        
        Returns:
            str: OCR識別結果
        """
        try:
            if not self.ocr_reader:
                return "OCR未初始化"
            # 將PIL圖像轉換為numpy數組
            image = self._potions_preprocess_image(image)
            # Image.fromarray(image).save(f"tmp/{name}_2.png")  # 保存圖像以便調試
            result = self.ocr_reader.readtext(
                image,
                allowlist=self.allow_list,
                paragraph=False,
                text_threshold=0.6,
                link_threshold=0.5,
                low_text=0.6,
                detail=1
            )
            bbox, text, confidence = self._potions_postprocess_result(result)

            return text

        except Exception as e:
            logger.debug(f"藥水圖像OCR處理錯誤: {e}")
            import traceback
            traceback.print_exc()
            return "OCR錯誤"
    
    def _process_single_image(self, image: Image.Image) -> str:
        """
        處理單個圖像的OCR
        
        Args:
            image: 要處理的圖像
        
        Returns:
            str: OCR識別結果
        """
        try:
            if not self.ocr_reader:
                return "OCR未初始化"

            # 將PIL圖像轉換為numpy數組
            import numpy as np
            img_array = np.array(image)

            # 若圖片為單通道，轉成3通道
            if len(img_array.shape) == 2:
                img_array = np.stack([img_array]*3, axis=-1)

            # 使用EasyOCR進行識別
            results = self.ocr_reader.readtext(
                img_array,
                allowlist=self.allow_list,
                paragraph=False,
                width_ths=0.7,
                height_ths=0.7
            )

            # 提取識別的文本
            if results:
                results.sort(key=lambda x: x[2], reverse=True)
                best_result = results[0]
                text = best_result[1].strip()
                confidence = best_result[2]
                if confidence > 0.5:
                    return text

            return "無法識別"

        except Exception as e:
            logger.debug(f"單個圖像OCR處理錯誤: {e}")
            import traceback
            traceback.print_exc()
            return "OCR錯誤"
    
    def _merge_images(self, images_dict: Dict[str, Image.Image]) -> Tuple[Image.Image, Dict[str, Tuple[int, int, int, int]]]:
        """
        合併多個圖像為一張圖像（參考原始game_monitor的方式）
        
        Args:
            images_dict: 圖像字典
            
        Returns:
            Tuple[Image.Image, Dict]: (合併後的圖像, 各標籤的位置信息)
        """
        # 按固定順序處理圖像（參考原始代碼）
        images_list = []
        tab_names = []
        
        # 計算合併後的尺寸
        max_width = 0
        total_height = 0
        
        for tab_name in self.tabs_order:
            if tab_name in images_dict:
                image = images_dict[tab_name]
                images_list.append(image)
                tab_names.append(tab_name)
                max_width = max(max_width, image.width)
                total_height += image.height
            else:
                # 如果某個標籤沒有圖像，創建空白區域
                dummy_image = Image.new('RGB', (100, 30), color=(0, 0, 0))
                images_list.append(dummy_image)
                tab_names.append(tab_name)
                max_width = max(max_width, 100)
                total_height += 30
        
        # 創建黑色背景的合併圖像
        merged_image = Image.new('RGB', (max_width, total_height), color=(0, 0, 0))
        
        # 記錄每個標籤的位置
        tab_positions = {}
        current_y = 0
        
        for tab_name, image in zip(tab_names, images_list):
            # 將圖像貼到合併圖像上
            merged_image.paste(image, (0, current_y))
            
            # 記錄位置信息 (x1, y1, x2, y2)
            tab_positions[tab_name] = (0, current_y, image.width, current_y + image.height)
            current_y += image.height
        
        return merged_image, tab_positions
    
    def _process_merged_image(self, image: Image.Image, tab_positions: Dict[str, Tuple[int, int, int, int]]) -> Dict[str, str]:
        """
        處理合併圖像的OCR並根據座標分配結果
        
        Args:
            image: 合併後的圖像
            tab_positions: 各標籤的位置信息 {tab_name: (x1, y1, x2, y2)}
        
        Returns:
            Dict[str, str]: 各標籤的OCR結果
        """
        try:
            if not self.ocr_reader:
                return {name: "OCR未初始化" for name in tab_positions.keys()}
            
            # 將PIL圖像轉換為numpy數組
            import numpy as np
            import cv2

            
            img_array = np.array(image)
            
            # 轉換為灰階（參考原始game_monitor的做法）
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # 使用EasyOCR進行識別
            results = self.ocr_reader.readtext(
                img_array,
                allowlist=self.allow_list,
                paragraph=False,
                width_ths=0.7,
                height_ths=0.7
            )
            
            # 根據座標將結果分配給各個標籤
            tab_results = {tab_name: [] for tab_name in tab_positions.keys()}
            
            # 處理EasyOCR結果（參考原始game_monitor的處理方式）
            for result in results:
                try:
                    # EasyOCR返回格式: (bbox, text, confidence)
                    if len(result) == 3:
                        bbox, text, confidence = result
                    elif len(result) == 2:
                        bbox, text = result
                        confidence = 1.0  # 假設置信度為1.0
                    else:
                        continue
                    
                    if confidence < 0.5:
                        continue
                    
                    # 計算文字的中心位置
                    if isinstance(bbox, list) and len(bbox) >= 4:
                        # bbox格式: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        center_x = sum(point[0] for point in bbox) / len(bbox)
                        center_y = sum(point[1] for point in bbox) / len(bbox)
                    else:
                        continue
                    
                    # 判斷文字屬於哪個標籤區域
                    for tab_name, (x1, y1, x2, y2) in tab_positions.items():
                        if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                            tab_results[tab_name].append(text.strip())
                            break
                
                except Exception as e:
                    logger.debug(f"處理OCR結果項目錯誤: {e}")
                    continue
            
            # 合併每個標籤的結果
            final_results = {}
            for tab_name in tab_positions.keys():
                if tab_results[tab_name]:
                    final_results[tab_name] = " ".join(tab_results[tab_name])
                else:
                    final_results[tab_name] = "無法識別"
            
            return final_results
            
        except Exception as e:
            logger.debug(f"合併圖像OCR處理錯誤: {e}")
            return {name: "OCR錯誤" for name in tab_positions.keys()}
    
    def _distribute_merged_result(self, merged_result: str, tab_positions: Dict[str, Tuple[int, int, int, int]], tab_names: List[str]) -> None:
        """
        將合併OCR結果分配給各個標籤
        
        Args:
            merged_result: 合併圖像的OCR結果
            tab_positions: 各標籤的位置信息
            tab_names: 標籤名稱列表
        """
        try:
            if not self.result_callback:
                return
            
            # 簡單策略：如果有多個標籤，嘗試按行分割結果
            if len(tab_names) == 1:
                self.result_callback(tab_names[0], merged_result)
            else:
                # 按換行符分割結果
                lines = merged_result.split('\n') if '\n' in merged_result else [merged_result]
                
                # 如果行數匹配標籤數，按順序分配
                if len(lines) == len(tab_names):
                    for tab_name, line in zip(tab_names, lines):
                        self.result_callback(tab_name, line.strip())
                else:
                    # 否則給每個標籤相同的結果
                    for tab_name in tab_names:
                        self.result_callback(tab_name, merged_result)
                        
        except Exception as e:
            logger.debug(f"分配OCR結果錯誤: {e}")
            # 發生錯誤時，給所有標籤相同的結果
            for tab_name in tab_names:
                if self.result_callback:
                    self.result_callback(tab_name, merged_result)
    
    def set_allow_list(self, allow_list: str) -> None:
        """設定允許的字符列表"""
        self.allow_list = allow_list
    
    def get_status(self) -> str:
        """獲取OCR引擎狀態"""
        if not self.is_initialized:
            return "初始化中..."
        elif self.is_running:
            return "運行中"
        else:
            return "已停止"
