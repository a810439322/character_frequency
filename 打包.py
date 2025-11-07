# -*- coding: utf-8 -*-
# author: 虎码新手2群-也无风雨也无晴
"""
打包脚本 - 将字频统计.py打包成exe
使用方法：
1. 确保已安装 pyinstaller: pip install pyinstaller
2. 运行此脚本: python 打包.py
"""

import os
import subprocess
import sys

def build_exe():
    print("=" * 60)
    print("字频统计工具 - 打包脚本")
    print("=" * 60)

    # 检查必要文件
    required_files = ['字频统计.py', 'dict_simple.txt', '前1500.txt']
    db_module_files = ['db_uploader.py', 'db_config.yaml', 'db_config.yaml.template', 'create_table.sql']

    for file in required_files:
        if not os.path.exists(file):
            print(f"错误：找不到 {file}")
            return False

    # 检查数据库模块文件
    db_available = all(os.path.exists(f) for f in db_module_files)
    if db_available:
        print("✓ 检测到数据库上传模块（含真实配置、模板和SQL）")
        print("  - 将打包真实配置到exe中作为默认配置")
        print("  - 首次运行会生成模板文件供用户参考")
    else:
        print("⚠ 未检测到完整数据库模块，将不包含数据库功能")
        missing = [f for f in db_module_files if not os.path.exists(f)]
        if missing:
            print(f"   缺少文件: {', '.join(missing)}")

    print("\n✓ 必要文件检查通过")

    # 检查pyinstaller
    try:
        import PyInstaller
        print("✓ PyInstaller 已安装")
    except ImportError:
        print("\n错误：未安装 PyInstaller")
        print("请运行: pip install pyinstaller")
        return False

    # 打包命令
    print("\n开始打包...")
    cmd = [
        'pyinstaller',
        '--onefile',                    # 打包成单个exe
        '--console',                    # 显示控制台窗口（必须，因为需要用户交互）
        '--add-data', 'dict_simple.txt;.',  # 将dict_simple.txt打包进去
        '--add-data', '前1500.txt;.',       # 将前1500.txt打包进去
        '--name', '字频统计工具',        # exe名称
        '--clean',                      # 清理临时文件
        '字频统计.py'
    ]

    # 如果数据库模块存在，也打包进去
    if db_available:
        cmd.insert(-1, '--add-data')
        cmd.insert(-1, 'db_uploader.py;.')
        cmd.insert(-1, '--add-data')
        cmd.insert(-1, 'db_config.yaml;.')           # 打包真实配置（开发者自己用）
        cmd.insert(-1, '--add-data')
        cmd.insert(-1, 'db_config.yaml.template;.')  # 打包模板（生成给用户参考）
        cmd.insert(-1, '--add-data')
        cmd.insert(-1, 'create_table.sql;.')         # 打包SQL文件
        cmd.insert(-1, '--hidden-import')
        cmd.insert(-1, 'pymysql')
        cmd.insert(-1, '--hidden-import')
        cmd.insert(-1, 'yaml')
        print("  ✓ 已添加数据库模块（真实配置 + 模板 + SQL）")
        print("  💡 工作原理：")
        print("     - 你自己运行：直接使用打包的真实配置")
        print("     - 分发给别人：会生成模板供他们参考配置")

    # Windows下路径分隔符不同
    if sys.platform == 'win32':
        # 替换所有路径分隔符为Windows格式
        for i in range(len(cmd)):
            if '--add-data' in cmd[i-1] if i > 0 else False:
                if ':' in cmd[i]:
                    cmd[i] = cmd[i].replace(':', ';')
    else:
        # Unix/Linux下使用冒号
        cmd[4] = 'dict_simple.txt:.'
        cmd[6] = '前1500.txt:.'
        if db_available:
            # 找到数据库文件的位置并修改
            for i in range(len(cmd)):
                if ';' in cmd[i]:
                    cmd[i] = cmd[i].replace(';', ':')

    print(f"执行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✓ 打包成功！")
        print("=" * 60)
        print("生成的文件位于: dist/字频统计工具.exe")
        print("\n使用说明：")
        print("1. 将 字频统计工具.exe 放到包含txt文件的目录")
        print("2. 双击运行，选择要统计的txt文件")
        print("3. 统计结果会生成在同一目录下")

        if db_available:
            print("\n数据库功能说明：")
            print("1. 你自己运行：")
            print("   - exe会使用打包的真实配置，直接连接你的数据库")
            print("2. 分发给别人时：")
            print("   - 首次运行会在exe目录生成 db_config.yaml.template 和 create_table.sql")
            print("   - 他们需要参考模板创建自己的 db_config.yaml")
            print("   - 程序会自动检测配置有效性并启用数据库功能")
            print("\n⚠ 安全提示：")
            print("  - 真实配置已安全打包在exe内部，外部看不到")
            print("  - 用户看到的只是模板文件（占位符）")

        return True
    except subprocess.CalledProcessError as e:
        print(f"\n打包失败: {e}")
        return False
    except Exception as e:
        print(f"\n发生错误: {e}")
        return False

if __name__ == '__main__':
    success = build_exe()

    if success:
        # 询问是否清理临时文件
        response = input("\n是否清理临时文件？(y/n): ").lower()
        if response == 'y':
            import shutil
            for folder in ['build', '__pycache__']:
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                    print(f"已清理: {folder}")
            if os.path.exists('字频统计工具.spec'):
                os.remove('字频统计工具.spec')
                print("已清理: 字频统计工具.spec")

    input("\n按回车键退出...")
