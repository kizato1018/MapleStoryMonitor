def get_version() -> str:
    """獲取當前程式版本"""
    with open("version.txt", "r") as file:
        version = file.read().strip()
    return version