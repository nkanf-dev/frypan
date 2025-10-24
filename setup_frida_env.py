#!/usr/bin/env python3

# Frida 环境配置脚本
# 作者: [您的名字]
# 日期: 2025-10-24

import sys
import subprocess
import os

# 定义颜色代码
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
NC = "\033[0m"  # No Color


def check_frida_installed():
    """检查 Frida 是否已安装"""
    try:
        import frida
        print(f"{GREEN}Frida 已安装: {frida.__version__}{NC}")
        return True
    except ImportError:
        print(f"{RED}Frida 未安装{NC}")
        return False


def list_frida_versions():
    """列出所有可用的 Frida 版本"""
    try:
        versions = subprocess.check_output([sys.executable, "-m", "pip", "index", "versions", "frida-tools"], text=True)
        print(f"{YELLOW}可用的 Frida 版本:{NC}")
        print(versions)
        return versions
    except subprocess.CalledProcessError as e:
        print(f"{RED}获取 Frida 版本失败: {e}{NC}")
        return None


def install_frida_version(version=None):
    """安装指定版本的 Frida 并下载对应版本的 fridaserver"""
    if version:
        print(f"{YELLOW}正在安装 Frida 版本: {version}{NC}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", f"frida-tools=={version}"])
            print(f"{GREEN}Frida {version} 安装成功{NC}")
            
            # 下载对应版本的 fridaserver
            print(f"{YELLOW}正在下载 fridaserver {version}...{NC}")
            import platform
            import requests
            import json

            os_type = platform.system().lower()
            arch = subprocess.check_output(["uname", "-m"], text=True).strip().lower()

            # 仅支持 arm64 架构
            if "arm" not in arch and "aarch64" not in arch:
                print(f"{RED}仅支持 arm64 架构的 Android 设备{NC}")
                sys.exit(1)

            # 获取 Frida 的发布信息
            try:
                response = requests.get("https://api.github.com/repos/frida/frida/releases")
                response.raise_for_status()
                releases = response.json()
            except Exception as e:
                print(f"{RED}获取 Frida 发布信息失败: {e}{NC}")
                sys.exit(1)

            # 查找指定版本的发布信息
            release = None
            for r in releases:
                if r["tag_name"] == version:
                    release = r
                    break

            if not release:
                print(f"{RED}未找到 Frida 版本: {version}{NC}")
                sys.exit(1)

            # 查找匹配的下载链接（仅匹配 arm64 的 Android 版本）
            download_url = None
            for asset in release["assets"]:
                asset_name = asset["name"].lower()
                if "frida-server" in asset_name and "android" in asset_name and "arm64" in asset_name:
                    download_url = asset["browser_download_url"]
                    break

            if not download_url:
                print(f"{RED}未找到匹配的 arm64 Android 版本{NC}")
                sys.exit(1)

            # 下载文件
            try:
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                with open(f"fridaserver-{version}.xz", "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"{GREEN}fridaserver {version} 下载完成{NC}")
            except Exception as e:
                print(f"{RED}下载失败: {e}{NC}")
                sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"{RED}操作失败: {e}{NC}")
            sys.exit(1)
    else:
        list_frida_versions()


def use_frida_version(version):
    """使用指定版本的 Frida"""
    print(f"{YELLOW}正在切换到 Frida 版本: {version}{NC}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", f"frida-tools=={version}"])
        print(f"{GREEN}已切换到 Frida {version}{NC}")
    except subprocess.CalledProcessError as e:
        print(f"{RED}切换 Frida 版本失败: {e}{NC}")
        sys.exit(1)


def list_installed_frida_versions():
    """列出已安装的 Frida 版本"""
    try:
        versions = subprocess.check_output([sys.executable, "-m", "pip", "list", "--format=freeze"], text=True)
        frida_versions = [line.split('==')[1] for line in versions.splitlines() if line.startswith("frida-tools==")]
        if frida_versions:
            print(f"{YELLOW}已安装的 Frida 版本:{NC}")
            for v in frida_versions:
                print(v)
        else:
            print(f"{RED}未安装任何 Frida 版本{NC}")
    except subprocess.CalledProcessError as e:
        print(f"{RED}获取已安装版本失败: {e}{NC}")


def show_help():
    """显示帮助信息"""
    print("使用说明:")
    print("  ./setup_frida_env.py [选项]")
    print("选项:")
    print("  -h, --help     显示帮助信息")
    print("  -v, --version  显示脚本版本")
    print("  -c, --check    检查 Frida 是否安装")
    print("  -i, --install      安装或更新 Frida (可指定版本)")
    print("  -u, --use          使用指定版本的 Frida")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    option = sys.argv[1]
    if option in ("-h", "--help"):
        show_help()
    elif option in ("-v", "--version"):
        print("Frida 环境配置脚本 v1.0")
    elif option in ("-c", "--check"):
        check_frida_installed()
    elif option in ("-i", "--install"):
        version = sys.argv[2] if len(sys.argv) > 2 else None
        install_frida_version(version)
    elif option in ("-u", "--use"):
        if len(sys.argv) < 3:
            print(f"{RED}请指定要使用的 Frida 版本{NC}")
            sys.exit(1)
        use_frida_version(sys.argv[2])
    elif option in ("-l", "--list"):
        list_installed_frida_versions()
    else:
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()