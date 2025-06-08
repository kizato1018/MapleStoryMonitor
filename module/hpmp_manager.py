import re
from typing import Optional, Tuple

class HPMPManager:
    """負責處理HP/MP相關邏輯"""

    def __init__(self):
        self.hp = None
        self.mp = None
        self.hp_max = None
        self.mp_max = None
        self.hp_percentage = None
        self.mp_percentage = None

    def update(self, hp_value: str, mp_value: str):
        """更新HP/MP值並計算百分比"""
        self.hp = hp_value
        self.mp = mp_value
        
        # 解析HP值和百分比
        hp_current, hp_max, hp_percent = self._parse_hp_mp_value(hp_value)
        if hp_current is not None and hp_max is not None:
            self.hp_max = hp_max
            self.hp_percentage = hp_percent if hp_percent is not None else (hp_current / hp_max * 100 if hp_max > 0 else 0)
        
        # 解析MP值和百分比
        mp_current, mp_max, mp_percent = self._parse_hp_mp_value(mp_value)
        if mp_current is not None and mp_max is not None:
            self.mp_max = mp_max
            self.mp_percentage = mp_percent if mp_percent is not None else (mp_current / mp_max * 100 if mp_max > 0 else 0)

    def _parse_hp_mp_value(self, value: str) -> Tuple[Optional[int], Optional[int], Optional[float]]:
        """
        解析HP/MP值，支援格式：[current_value/max_value]
        - "1234/5678" -> 返回 (1234, 5678, None)
        - "1234/5678 [50%]" -> 返回 (1234, 5678, 50.0)
        - "1234" -> 返回 (1234, None, None)
        """
        if not value or value == "N/A":
            return None, None, None

        try:
            value = value.replace(" ", "")
            # 百分比
            percent_match = re.search(r'\[(\d+\.?\d*)%\]', value)
            percentage = float(percent_match.group(1)) if percent_match else None
            # 移除百分比
            value_without_percent = re.sub(r'\[\d+\.?\d*%\]', '', value)
            # 格式：[current/max] 或 current/max
            match = re.match(r'\[?(\d+)/(\d+)\]?', value_without_percent)
            if match:
                current = int(match.group(1))
                maximum = int(match.group(2))
                return current, maximum, percentage
            # 備援：只支援純數字
            current_match = re.match(r'\[?(\d+)\]?', value_without_percent)
            if current_match:
                current = int(current_match.group(1))
                return current, None, percentage
        except (ValueError, AttributeError):
            pass
        return None, None, None

    def get_formatted_hp(self) -> str:
        """獲取格式化的HP值（current/max [percent%]）"""
        if self.hp is None or self.hp == "N/A":
            return "N/A"

        if self.hp_max is not None and self.hp_percentage is not None:
            # 只顯示 current/max [percent%]
            hp_str = f"{str(self.hp).replace('[','').replace(']','')}"
            # 只取 current/max
            hp_main = hp_str.split()[0] if ' ' in hp_str else hp_str
            return f"{hp_main} [{self.hp_percentage:.1f}%]"
        return str(self.hp).replace('[','').replace(']','')

    def get_formatted_mp(self) -> str:
        """獲取格式化的MP值（current/max [percent%]）"""
        if self.mp is None or self.mp == "N/A":
            return "N/A"

        if self.mp_max is not None and self.mp_percentage is not None:
            mp_str = f"{str(self.mp).replace('[','').replace(']','')}"
            mp_main = mp_str.split()[0] if ' ' in mp_str else mp_str
            return f"{mp_main} [{self.mp_percentage:.1f}%]"
        return str(self.mp).replace('[','').replace(']','')

    def get_status(self):
        return {
            "HP": self.hp,
            "MP": self.mp,
            "HP_formatted": self.get_formatted_hp(),
            "MP_formatted": self.get_formatted_mp(),
            "HP_percentage": self.hp_percentage,
            "MP_percentage": self.mp_percentage
        }
