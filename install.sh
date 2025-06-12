#!/bin/bash
# filepath: d:\Program\Others\python\MapleStoryMonitor\install.sh

echo "================================================"
echo "   MapleStory Monitor 自動安裝腳本 (macOS)"
echo "================================================"
echo

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 錯誤處理函數
error_exit() {
    echo -e "${RED}[錯誤] $1${NC}"
    echo "安裝失敗，請檢查錯誤訊息"
    exit 1
}

# 成功訊息函數
success_msg() {
    echo -e "${GREEN}[成功] $1${NC}"
}

# 資訊訊息函數
info_msg() {
    echo -e "${BLUE}[資訊] $1${NC}"
}

# 警告訊息函數
warn_msg() {
    echo -e "${YELLOW}[警告] $1${NC}"
}

# 檢查 Python 3
info_msg "[1/6] 檢查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        error_exit "未找到 Python，請先安裝 Python 3.8 或更新版本
下載網址: https://www.python.org/downloads/"
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

PYTHON_VERSION=$($PYTHON_CMD --version)
success_msg "已找到 $PYTHON_VERSION"

# 檢查 Python 版本是否符合要求
PYTHON_VERSION_NUM=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

# 檢查版本：主版本號必須是3，次版本號必須>=8
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    error_exit "Python 版本過舊 ($PYTHON_VERSION_NUM)，需要 Python 3.8 或更新版本"
fi

# 檢查 pip
info_msg "[2/6] 檢查 pip..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    error_exit "pip 未正確安裝"
fi
success_msg "pip 檢查完成"

# 清理舊的虛擬環境
info_msg "[3/6] 清理舊環境..."
if [ -d "venv" ]; then
    echo
    warn_msg "偵測到舊的虛擬環境！"
    echo
    echo "選擇操作："
    echo "  1. 重新安裝 - 刪除舊環境並重新建立 (建議)"
    echo "  2. 保留現有環境 - 跳過虛擬環境建立"
    echo "  3. 取消安裝"
    echo
    printf "請輸入選擇 (1/2/3): "
    read choice
    
    case $choice in
        1)
            echo
            info_msg "正在刪除舊的虛擬環境..."
            
            # 嘗試正常刪除
            rm -rf venv
            
            # 等待檔案系統同步
            sleep 1
            
            # 檢查是否還存在
            if [ -d "venv" ]; then
                warn_msg "無法完全清理舊環境，嘗試強制清理..."
                sudo rm -rf venv 2>/dev/null || {
                    error_exit "無法清理舊環境，請手動刪除 venv 資料夾後重新執行"
                }
            fi
            success_msg "舊環境清理完成"
            ;;
        2)
            echo
            info_msg "保留現有虛擬環境，跳到依賴套件安裝..."
            # 檢查現有環境是否完整
            if [ ! -f "venv/bin/python" ]; then
                error_exit "現有虛擬環境不完整，請選擇重新安裝"
            fi
            # 跳到安裝套件部分
            skip_venv_creation=true
            ;;
        3)
            echo
            info_msg "安裝已取消"
            exit 0
            ;;
        *)
            echo
            warn_msg "無效的選擇，預設進行重新安裝..."
            rm -rf venv
            ;;
    esac
else
    success_msg "未發現舊環境"
fi

# 創建虛擬環境
if [ "$skip_venv_creation" != "true" ]; then
    info_msg "[4/6] 創建虛擬環境..."
    $PYTHON_CMD -m venv venv || error_exit "創建虛擬環境失敗
可能的解決方案：
1. 確保有足夠的磁碟空間
2. 檢查目錄權限
3. 嘗試使用 sudo 執行"

    # 等待檔案系統同步
    sleep 2
    success_msg "虛擬環境創建成功"

    # 檢查虛擬環境是否正常
    info_msg "[5/6] 檢查虛擬環境..."
    if [ ! -f "venv/bin/python" ]; then
        error_exit "虛擬環境建立不完整，請檢查錯誤訊息或重新執行"
    fi

    # 啟動虛擬環境並升級 pip
    info_msg "[6/6] 啟動虛擬環境並升級 pip..."
    source venv/bin/activate || error_exit "啟動虛擬環境失敗"
    python -m pip install --upgrade pip || warn_msg "升級 pip 失敗，但將繼續安裝"
else
    info_msg "[4-6/6] 跳過虛擬環境創建，使用現有環境..."
    source venv/bin/activate || error_exit "啟動現有虛擬環境失敗"
fi

# 安裝依賴套件
info_msg "[7/8] 安裝依賴套件..."
echo "這可能需要幾分鐘時間，請耐心等待..."

# 檢查 requirements.txt 是否存在
if [ ! -f "requirements.txt" ]; then
    error_exit "找不到 requirements.txt 檔案"
fi

python -m pip install -r requirements.txt || error_exit "安裝依賴套件失敗
請檢查網路連線或嘗試手動安裝"

# 創建啟動腳本
info_msg "[8/8] 創建啟動腳本..."
cat > "MapleStory Monitor.command" << 'EOF'
#!/bin/bash
# MapleStory Monitor 啟動腳本

# 獲取腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
SCRIPT_PATH="$(pwd)/venv/bin/python3 $(pwd)/main.py"

osascript -e "do shell script \"$SCRIPT_PATH > /dev/null 2>&1 &\""
EOF

# 設定執行權限
chmod +x "MapleStory Monitor.command"

echo
echo "================================================"
echo "           🎉 安裝完成！ 🎉"
echo "================================================"
echo
echo "使用方法："
echo "  • 在終端機中執行: ./MapleStory Monitor.command"
echo "  • 或雙擊 MapleStory Monitor.command 檔案（當程式啟動以後，啟動的終端機可以關閉）"
echo
echo "注意事項："
echo "  • 請確保 MapleStory 遊戲已啟動"
echo "  • 首次使用需要設定視窗選擇和監控區域"
echo "  • 可能需要允許應用程式擷取螢幕畫面的權限"
echo "  • 如遇問題請查看 Log 資料夾中的記錄檔"
echo
