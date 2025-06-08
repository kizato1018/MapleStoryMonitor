"""
Capture Package
畫面捕捉相關模組
"""

import sys
from .base_capture import BaseCaptureEngine, create_capture_engine
from utils.log import get_logger

logger = get_logger(__name__)

# 根據作業系統條件性導入捕捉引擎
if sys.platform == "win32":
    try:
        from .windows_capture import WindowsCaptureEngine
        WINDOWS_AVAILABLE = True
    except ImportError:
        WINDOWS_AVAILABLE = False
        logger.warning("警告: Windows捕捉引擎導入失敗")
else:
    WINDOWS_AVAILABLE = False

if sys.platform == "darwin":
    try:
        from .mac_capture import MacCaptureEngine
        MAC_AVAILABLE = True
    except ImportError:
        MAC_AVAILABLE = False
        logger.warning("警告: Mac捕捉引擎導入失敗")
else:
    MAC_AVAILABLE = False

# 根據可用性決定導出的類別
__all__ = ['BaseCaptureEngine', 'create_capture_engine']

if WINDOWS_AVAILABLE:
    __all__.append('WindowsCaptureEngine')
if MAC_AVAILABLE:
    __all__.append('MacCaptureEngine')
