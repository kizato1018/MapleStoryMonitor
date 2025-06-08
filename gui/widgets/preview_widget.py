"""
Preview Widget Module
預覽元件模組
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from typing import Optional
from utils.log import get_logger


logger = get_logger(__name__)


class PreviewWidget:
    """預覽元件"""
    
    def __init__(self, parent):
        self.parent = parent
        self.preview_photo = None
        self._create_widget()
    
    def _create_widget(self):
        """創建預覽元件"""
        self.frame = ttk.LabelFrame(self.parent, text="即時預覽", padding=10)
        self.preview_label = tk.Label(
            self.frame, 
            text="等待擷取...", 
            bg="gray90", 
            width=40, 
            height=15,
            font=('Arial', 12)
        )
        self.preview_label.pack(fill=tk.BOTH, expand=True)
    
    def update_preview(self, image: Optional[Image.Image]):
        """
        更新預覽圖像
        
        Args:
            image: 要顯示的PIL圖像
        """
        if image is None:
            self.set_message("圖像為空")
            return
        
        try:
            preview_img = image.copy()
            label_width = self.preview_label.winfo_width()
            label_height = self.preview_label.winfo_height()
            
            # 計算縮放比例
            if label_width > 1 and label_height > 1:
                img_ratio = preview_img.width / preview_img.height
                label_ratio = label_width / label_height
                
                if img_ratio > label_ratio:
                    # 圖像比較寬，以寬度為準
                    new_width = min(label_width - 10, 400)
                    new_height = int(new_width / img_ratio)
                else:
                    # 圖像比較高，以高度為準
                    new_height = min(label_height - 10, 300)
                    new_width = int(new_height * img_ratio)
                
                # 確保尺寸合理
                new_width = max(1, new_width)
                new_height = max(1, new_height)
                
                preview_img = preview_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                # 如果無法獲取標籤尺寸，使用默認縮放
                preview_img.thumbnail((400, 300), Image.Resampling.LANCZOS)
            
            # 轉換為Tkinter可用的PhotoImage
            self.preview_photo = ImageTk.PhotoImage(preview_img)
            self.preview_label.config(image=self.preview_photo, text="")
            
        except Exception as e:
            logger.error(f"預覽更新錯誤: {e}")
            self.set_message(f"預覽錯誤: {str(e)}")
    
    def set_message(self, message: str):
        """
        設定顯示訊息
        
        Args:
            message: 要顯示的訊息
        """
        self.preview_label.config(image="", text=message)
        self.preview_photo = None
    
    def pack(self, **kwargs):
        """打包元件"""
        self.frame.pack(**kwargs)
