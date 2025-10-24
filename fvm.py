#!/usr/bin/env python3

import sys
import subprocess
import requests
import json

def check_frida_installed():
    try:
        frida = __import__("frida")
        print(f"Frida 已安装: {frida.__version__}")
        return True
    except ImportError:
        print(f"Frida 未安装")
        return False


def list_frida_versions():
    try:
        versions = subprocess.check_output([sys.executable, "-m", "pip", "index", "versions", "frida"], text=True)
        print(f"Available Frida versions:")
        print(versions)
        return versions
    except subprocess.CalledProcessError as e:
        print(f"Failed to get Frida versions: {e}")
        return None


def install_frida_version(version=None):
    if version:
        print(f"Installing frida: {version}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", f"frida=={version}"])
            print(f"Frida {version} installed successfully")
            print(f"Downloading fridaserver {version}...")
            try:
                response = requests.get("https://api.github.com/repos/frida/frida/releases")
                response.raise_for_status()
                releases = response.json()
            except Exception as e:
                print(f"Failed to get frida release information: {e}")
                sys.exit(1)

            release = next(r for r in releases if r["tag_name"] == version)

            if not release:
                print(f"Failed to find frida release: {version}")
                sys.exit(1)
            download_url = release["assets"][0]["browser_download_url"]

            try:
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                with open(f"fridaserver-{version}.xz", "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        print(".", end="")
                print(f"fridaserver {version} has downloaded successfully")
            except Exception as e:
                print(f"Failed to download fridaserver: {e}")
                sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"Failed: {e}")
            sys.exit(1)
    else:
        list_frida_versions()


def use_frida_version(version):
    print(f"Switching frida version: {version}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", f"frida=={version}"])
        print(f"Switched to Frida {version}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to switch Frida version: {e}")
        sys.exit(1)

    print(f"Switching frida-server version: {version}")


def list_installed_frida_versions():
    """列出已安装的 Frida 版本"""
    try:
        versions = subprocess.check_output([sys.executable, "-m", "pip", "list", "--format=freeze"], text=True)
        frida_versions = [line.split('==')[1] for line in versions.splitlines() if line.startswith("frida==")]
        if frida_versions:
            print(f"已安装的 Frida 版本:")
            for v in frida_versions:
                print(v)
        else:
            print(f"未安装任何 Frida 版本")
    except subprocess.CalledProcessError as e:
        print(f"获取已安装版本失败: {e}")


def show_help():
    """显示帮助信息"""
    print("使用说明:")
    print("  ./fvm.py [选项]")
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
            print(f"请指定要使用的 Frida 版本")
            sys.exit(1)
        use_frida_version(sys.argv[2])
    elif option in ("-l", "--list"):
        list_installed_frida_versions()
    else:
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()