#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本文件编码批量转换器

功能：
1. 自动检测文件编码
2. 批量转换为目标编码（默认UTF-8）
3. 支持备份原文件
4. 显示详细转换信息
"""

import os
import shutil
import tkinter as tk
from tkinter import filedialog
from datetime import datetime

# ========== 配置区 ==========

# 是否备份原文件
BACKUP_ENABLED = True

# 备份文件夹名称
BACKUP_FOLDER = "编码转换备份"

# 支持检测的编码列表（按优先级排序）
ENCODING_LIST = [
    'utf-8',
    'utf-8-sig',
    'gbk',
    'gb2312',
    'gb18030',
    'big5',
    'ascii',
    'iso-8859-1'
]

# 支持的目标编码选项
TARGET_ENCODING_OPTIONS = {
    '1': ('utf-8', False, 'UTF-8 (推荐：通用标准，无BOM)'),
    '2': ('utf-8', True, 'UTF-8-BOM (Windows兼容性更好)'),
    '3': ('gbk', False, 'GBK (Windows简体中文)'),
    '4': ('gb18030', False, 'GB18030 (国标中文)'),
    '5': ('big5', False, 'Big5 (繁体中文)'),
}

# ========== 核心功能 ==========

def detect_encoding(file_path):
    """
    自动检测文件编码

    Args:
        file_path: 文件路径

    Returns:
        str: 检测到的编码名称，失败返回None
    """
    for encoding in ENCODING_LIST:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None


def backup_file(file_path, backup_folder):
    """
    备份原文件

    Args:
        file_path: 原文件路径
        backup_folder: 备份文件夹路径

    Returns:
        str: 备份文件路径
    """
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    filename = os.path.basename(file_path)
    backup_path = os.path.join(backup_folder, filename)

    # 如果备份文件已存在，添加时间戳
    if os.path.exists(backup_path):
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_folder, f"{name}_{timestamp}{ext}")

    shutil.copy2(file_path, backup_path)
    return backup_path


def convert_file_encoding(file_path, target_encoding, use_bom=False, backup_enabled=True):
    """
    转换单个文件的编码

    Args:
        file_path: 文件路径
        target_encoding: 目标编码
        use_bom: 是否使用BOM
        backup_enabled: 是否备份原文件

    Returns:
        dict: 转换结果信息
    """
    result = {
        'success': False,
        'file': os.path.basename(file_path),
        'original_encoding': None,
        'target_encoding': target_encoding,
        'message': ''
    }

    try:
        # 检测原始编码
        original_encoding = detect_encoding(file_path)
        if original_encoding is None:
            result['message'] = "无法识别文件编码"
            return result

        result['original_encoding'] = original_encoding

        # 如果已经是目标编码，跳过
        final_target = f"{target_encoding}-sig" if use_bom and target_encoding == 'utf-8' else target_encoding

        if original_encoding == final_target:
            result['success'] = True
            result['message'] = f"已经是 {final_target} 编码，无需转换"
            return result

        # 读取原文件内容
        with open(file_path, 'r', encoding=original_encoding) as f:
            content = f.read()

        # 备份原文件
        if backup_enabled:
            file_dir = os.path.dirname(file_path)
            backup_folder = os.path.join(file_dir, BACKUP_FOLDER)
            backup_path = backup_file(file_path, backup_folder)
            result['backup'] = backup_path

        # 写入新编码
        with open(file_path, 'w', encoding=final_target) as f:
            f.write(content)

        result['success'] = True
        result['message'] = f"{original_encoding} → {final_target}"
        return result

    except Exception as e:
        result['message'] = f"转换失败: {str(e)}"
        return result


def convert_batch(file_paths, target_encoding='utf-8', use_bom=False, backup_enabled=True):
    """
    批量转换文件编码

    Args:
        file_paths: 文件路径列表
        target_encoding: 目标编码
        use_bom: 是否使用BOM
        backup_enabled: 是否备份

    Returns:
        list: 转换结果列表
    """
    results = []
    total = len(file_paths)

    print(f"\n开始批量转换，共 {total} 个文件...")
    print(f"目标编码: {target_encoding}{'-sig' if use_bom else ''}")
    print(f"是否备份: {'是' if backup_enabled else '否'}")
    print("=" * 60)

    for i, file_path in enumerate(file_paths, 1):
        print(f"\n[{i}/{total}] {os.path.basename(file_path)}")

        result = convert_file_encoding(file_path, target_encoding, use_bom, backup_enabled)
        results.append(result)

        if result['success']:
            print(f"  ✓ {result['message']}")
            if 'backup' in result:
                print(f"  备份: {os.path.basename(result['backup'])}")
        else:
            print(f"  ✗ {result['message']}")

    return results


def generate_report(results, output_folder, target_encoding_desc):
    """
    生成转换报告

    Args:
        results: 转换结果列表
        output_folder: 输出文件夹
        target_encoding_desc: 目标编码描述
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_folder, f"编码转换报告_{timestamp}.txt")

    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("文本文件编码批量转换报告\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"转换时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总文件数: {len(results)}\n")
        f.write(f"成功: {success_count} | 失败: {fail_count}\n")
        f.write(f"目标编码: {target_encoding_desc}\n\n")

        f.write("【转换详情】\n\n")

        for i, result in enumerate(results, 1):
            status = "✓" if result['success'] else "✗"
            f.write(f"{i}. {status} {result['file']}\n")
            f.write(f"   原编码: {result['original_encoding'] or '未知'}\n")
            f.write(f"   结果: {result['message']}\n")
            if 'backup' in result:
                f.write(f"   备份: {os.path.basename(result['backup'])}\n")
            f.write("\n")

        f.write("=" * 60 + "\n")
        f.write("说明：\n")
        f.write("- UTF-8: 国际通用标准，推荐使用\n")
        f.write("- UTF-8-BOM: 带BOM标记的UTF-8，Windows兼容性好\n")
        f.write("- GBK: Windows中文简体编码\n")
        f.write("- 备份文件保存在原文件目录的'编码转换备份'文件夹中\n")

    return report_file


def select_target_encoding():
    """
    让用户选择目标编码

    Returns:
        tuple: (encoding, use_bom, description) 或 None
    """
    print("\n请选择目标编码：")
    print("-" * 60)
    for key in sorted(TARGET_ENCODING_OPTIONS.keys()):
        encoding, use_bom, desc = TARGET_ENCODING_OPTIONS[key]
        print(f"  {key}. {desc}")
    print("-" * 60)

    while True:
        choice = input("\n请输入选项编号 (1-5, 按q退出): ").strip()

        if choice.lower() == 'q':
            return None

        if choice in TARGET_ENCODING_OPTIONS:
            return TARGET_ENCODING_OPTIONS[choice]
        else:
            print("  ✗ 无效选项，请重新输入")


def main():
    """主程序"""
    print("=" * 60)
    print("文本文件编码批量转换器")
    print("=" * 60)
    print("\n通用推荐编码: UTF-8 (国际标准)")
    print("Windows兼容性更好: UTF-8-BOM (带BOM标记)")

    # 选择目标编码
    encoding_info = select_target_encoding()
    if encoding_info is None:
        print("已取消操作")
        return

    target_encoding, use_bom, encoding_desc = encoding_info
    print(f"\n已选择: {encoding_desc}")

    # 选择文件
    print("\n请选择要转换的文本文件...")
    root = tk.Tk()
    root.withdraw()

    file_paths = filedialog.askopenfilenames(
        title="选择文本文件（可多选）",
        filetypes=[
            ("文本文件", "*.txt"),
            ("所有文件", "*.*")
        ]
    )

    if not file_paths:
        print("未选择文件，程序退出")
        return

    # 确认配置
    print(f"\n当前配置:")
    print(f"  目标编码: {encoding_desc}")
    print(f"  是否备份: {'是' if BACKUP_ENABLED else '否'}")
    print(f"  备份位置: 原文件目录/{BACKUP_FOLDER}/")
    print(f"  文件数量: {len(file_paths)}")

    confirm = input("\n是否继续？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消操作")
        return

    # 批量转换
    results = convert_batch(file_paths, target_encoding, use_bom, BACKUP_ENABLED)

    # 生成报告
    output_folder = os.path.dirname(file_paths[0]) if file_paths else os.getcwd()
    report_file = generate_report(results, output_folder, encoding_desc)

    # 显示统计
    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count

    print("\n" + "=" * 60)
    print("转换完成！")
    print("=" * 60)
    print(f"  总文件数: {len(results)}")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  报告已保存: {os.path.basename(report_file)}")

    if BACKUP_ENABLED:
        backup_folder = os.path.join(output_folder, BACKUP_FOLDER)
        print(f"  备份位置: {backup_folder}")

    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
