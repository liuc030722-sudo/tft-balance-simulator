"""Locate the Windows-configured desktop without assuming a drive."""

import os
from pathlib import Path
import winreg


def locate_desktop() -> Path:
    # User Shell Folders 保存重定向后的配置；展开环境变量后使用 pathlib 验证。
    registry_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
        configured, _ = winreg.QueryValueEx(key, "Desktop")
    desktop = Path(os.path.expandvars(configured))
    if not desktop.is_absolute() or not desktop.is_dir():
        raise RuntimeError("Configured desktop is unavailable; ask for path confirmation.")
    return desktop


if __name__ == "__main__":
    # 仅在本地显示路径，不将用户名或路径写入可提交的配置。
    print(locate_desktop())
