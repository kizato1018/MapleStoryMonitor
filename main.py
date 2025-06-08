"""
Main Entry Point
遊戲監控主程式入口
"""

import sys
import os

# 添加當前目錄到Python路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from gui.main_window import GameMonitorMainWindow
from utils.log import get_logger

logger = get_logger(__name__)


def main():
    """主函數"""
    try:
        logger.info("啟動遊戲監控程式...")
        app = GameMonitorMainWindow()
        app.run()
    except KeyboardInterrupt:
        logger.info("\n程式被用戶中斷")
    except Exception as e:
        logger.error(f"程式運行錯誤: {e}", exc_info=True)
    finally:
        logger.info("程式結束")


if __name__ == "__main__":
    main()
