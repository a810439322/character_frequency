#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雨天跟打器难度算法 - Python实现
基于ytgdq项目的DifficultyDict.cs算法

算法说明：
1. 使用10级字符字典（0.txt-9.txt），共5321个常用字
2. 每级对应固定权重：1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 9.0
3. 计算公式：难度 = Σ(字符权重) / 文本长度
4. 特殊字符：空白=1.0, 标点=1.0, 未知汉字=12.0
5. 百分制换算：百分制 = min(100, (原始难度 / 6.0) * 100)
"""

import os
import tkinter as tk
from tkinter import filedialog
from collections import Counter

# ========== 配置区 ==========

# 字典文件路径（ytgdq项目的字典文件）
DICT_BASE_PATH = r"E:\nas同步\打字\SynologyDrive\雨天跟打器\ytgdq\TyDll\Resources\DIC"

# 10级字典对应的权重（与ytgdq保持一致）
LEVEL_WEIGHTS = {
    0: 1.25,   # 最常用
    1: 1.5,
    2: 1.75,
    3: 2.0,
    4: 2.5,
    5: 3.0,
    6: 4.0,
    7: 5.0,
    8: 7.0,
    9: 9.0     # 罕见字
}

# 特殊字符权重
WHITESPACE_WEIGHT = 1.0
PUNCTUATION_WEIGHT = 1.0
UNKNOWN_WEIGHT = 12.0

# 标点符号集合（与ytgdq保持一致）
SYMBOL_CHARS = r"""abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!！`~@#$￥%^…&*()（）-_—=+[]{}'''""\、|·;；:：,，.。<>《》?？/"""

# 难度等级划分（与ytgdq的DiffText方法保持一致）
DIFFICULTY_LEVELS = [
    (0.00, "无"),
    (1.50, "轻松"),
    (1.88, "容易"),
    (2.25, "一般"),
    (2.80, "稍难"),
    (3.50, "困难"),
    (4.20, "超难"),
    (5.40, "极难"),
    (float('inf'), "地狱")
]

# 输出文件夹
OUTPUT_FOLDER = "雨天难度结果"

# 百分制换算参数
MAX_DIFFICULTY_REF = 6.0  # 参考最大难度（地狱级对应100分）
# 换算公式：百分制 = min(100, (原始难度 / MAX_DIFFICULTY_REF) * 100)

# ========== 核心功能 ==========

def load_difficulty_dict():
    """
    加载10级字符字典，构建字符->权重映射

    Returns:
        dict: {字符: 权重}
    """
    char_weights = {}

    for level in range(10):
        dict_file = os.path.join(DICT_BASE_PATH, f"{level}.txt")

        if not os.path.exists(dict_file):
            print(f"⚠ 警告：字典文件不存在: {dict_file}")
            continue

        try:
            with open(dict_file, 'r', encoding='utf-8-sig') as f:
                content = f.read().strip()
                weight = LEVEL_WEIGHTS[level]

                for char in content:
                    if char and not char.isspace():
                        char_weights[char] = weight

                print(f"✓ 加载字典 {level}.txt: {len(content)} 个字符, 权重={weight}")

        except Exception as e:
            print(f"✗ 读取字典文件 {dict_file} 失败: {e}")

    print(f"\n字典加载完成，共 {len(char_weights)} 个字符")
    return char_weights


def calculate_difficulty(text, char_weights):
    """
    计算文本难度（ytgdq算法）

    Args:
        text: 待分析文本
        char_weights: 字符权重字典

    Returns:
        tuple: (难度分数, 详细统计)
    """
    if not text:
        return 0.0, {}

    total_weight = 0.0
    total_chars = len(text)

    # 统计各类字符数量
    stats = {
        'whitespace': 0,      # 空白字符
        'punctuation': 0,     # 标点符号
        'known': 0,           # 已知汉字
        'unknown': 0,         # 未知汉字
        'level_dist': {i: 0 for i in range(10)}  # 各等级分布
    }

    for char in text:
        if char.isspace():
            # 空白字符
            total_weight += WHITESPACE_WEIGHT
            stats['whitespace'] += 1

        elif char in char_weights:
            # 已知汉字
            weight = char_weights[char]
            total_weight += weight
            stats['known'] += 1

            # 统计等级分布
            for level, level_weight in LEVEL_WEIGHTS.items():
                if weight == level_weight:
                    stats['level_dist'][level] += 1
                    break

        elif char in SYMBOL_CHARS:
            # 标点符号
            total_weight += PUNCTUATION_WEIGHT
            stats['punctuation'] += 1

        else:
            # 未知汉字
            total_weight += UNKNOWN_WEIGHT
            stats['unknown'] += 1

    # 计算平均难度
    difficulty = total_weight / total_chars if total_chars > 0 else 0.0

    stats['total_chars'] = total_chars
    stats['total_weight'] = total_weight
    stats['difficulty'] = difficulty

    return difficulty, stats


def get_difficulty_text(difficulty):
    """
    根据难度分数获取难度等级文字

    Args:
        difficulty: 难度分数

    Returns:
        str: 难度等级
    """
    if difficulty == 0:
        return "无"

    for threshold, level_text in DIFFICULTY_LEVELS:
        if difficulty <= threshold:
            return level_text

    return "地狱"


def convert_to_percentage(difficulty):
    """
    将原始难度转换为百分制分数

    Args:
        difficulty: 原始难度分数

    Returns:
        float: 百分制分数 (0-100)
    """
    if difficulty <= 0:
        return 0.0

    percentage = (difficulty / MAX_DIFFICULTY_REF) * 100
    return min(100.0, percentage)


def ensure_output_folder():
    """确保输出文件夹存在"""
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"创建输出文件夹: {OUTPUT_FOLDER}")
    return OUTPUT_FOLDER


def analyze_file(file_path, char_weights):
    """
    分析单个文件

    Args:
        file_path: 文件路径
        char_weights: 字符权重字典

    Returns:
        bool: 是否成功
    """
    try:
        # 读取文件（尝试多种编码）
        text = None
        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                print(f"  使用编码: {encoding}")
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if text is None:
            print(f"\n✗ 无法识别文件编码，请确保文件是文本格式")
            return False

        print(f"\n{'='*60}")
        print(f"分析文件: {os.path.basename(file_path)}")
        print(f"{'='*60}")

        # 计算难度
        difficulty, stats = calculate_difficulty(text, char_weights)
        difficulty_text = get_difficulty_text(difficulty)
        difficulty_percentage = convert_to_percentage(difficulty)

        # 准备输出
        output_folder = ensure_output_folder()
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(output_folder, f"{base_name}_雨天难度_{difficulty:.2f}[{difficulty_percentage:.1f}分].txt")

        # 生成报告
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"雨天跟打器难度分析报告\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"文件名: {os.path.basename(file_path)}\n")
            f.write(f"文本长度: {stats['total_chars']} 字符\n\n")

            f.write("【难度评分】\n")
            f.write(f"  原始难度: {difficulty:.2f} ({difficulty_text})\n")
            f.write(f"  百分制: {difficulty_percentage:.1f} 分\n")
            f.write(f"  换算说明: 以 {MAX_DIFFICULTY_REF:.1f} 为满分参考点\n\n")

            f.write("【算法说明】\n")
            f.write(f"  - 算法来源: ytgdq (雨天跟打器)\n")
            f.write(f"  - 计算公式: Σ(字符权重) / 文本长度\n")
            f.write(f"  - 总权重: {stats['total_weight']:.2f}\n")
            f.write(f"  - 平均值: {difficulty:.4f}\n\n")

            f.write("【字符统计】\n")
            f.write(f"  总字符数: {stats['total_chars']}\n")
            f.write(f"  ├─ 已知汉字: {stats['known']} ({stats['known']/stats['total_chars']*100:.1f}%)\n")
            f.write(f"  ├─ 未知汉字: {stats['unknown']} ({stats['unknown']/stats['total_chars']*100:.1f}%) [权重={UNKNOWN_WEIGHT}]\n")
            f.write(f"  ├─ 标点符号: {stats['punctuation']} ({stats['punctuation']/stats['total_chars']*100:.1f}%) [权重={PUNCTUATION_WEIGHT}]\n")
            f.write(f"  └─ 空白字符: {stats['whitespace']} ({stats['whitespace']/stats['total_chars']*100:.1f}%) [权重={WHITESPACE_WEIGHT}]\n\n")

            f.write("【难度等级分布】\n")
            f.write(f"  字典共10级，权重1.25-9.0，覆盖5321个常用字\n\n")

            for level in range(10):
                count = stats['level_dist'][level]
                weight = LEVEL_WEIGHTS[level]
                if count > 0:
                    pct = count / stats['total_chars'] * 100
                    f.write(f"  等级 {level} [权重={weight:.2f}]: {count} 字符 ({pct:.1f}%)\n")

            f.write("\n【难度等级标准】\n")
            f.write("  0.00         → 无\n")
            f.write("  0.01 - 1.50  → 轻松\n")
            f.write("  1.51 - 1.88  → 容易\n")
            f.write("  1.89 - 2.25  → 一般\n")
            f.write("  2.26 - 2.80  → 稍难\n")
            f.write("  2.81 - 3.50  → 困难\n")
            f.write("  3.51 - 4.20  → 超难\n")
            f.write("  4.21 - 5.40  → 极难\n")
            f.write("  5.41+        → 地狱\n")

        print(f"\n✓ 分析完成！")
        print(f"  原始难度: {difficulty:.2f} ({difficulty_text})")
        print(f"  百分制: {difficulty_percentage:.1f} 分")
        print(f"  报告已保存: {output_file}")

        return True

    except Exception as e:
        print(f"\n✗ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主程序"""
    print("=" * 60)
    print("雨天跟打器难度算法 - Python实现")
    print("=" * 60)
    print("\n基于ytgdq项目的DifficultyDict.cs算法")
    print("使用10级字符字典，权重1.25-9.0，未知字=12.0")
    print("同时提供原始难度和百分制分数对照\n")

    # 加载字典
    print("正在加载字符字典...")
    char_weights = load_difficulty_dict()

    if not char_weights:
        print("\n✗ 错误：字典加载失败，请检查字典文件路径！")
        input("\n按回车键退出...")
        return

    # 选择文件
    print("\n请选择要分析的文本文件...")
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

    # 批量分析
    success_count = 0
    for file_path in file_paths:
        if analyze_file(file_path, char_weights):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"批量分析完成: {success_count}/{len(file_paths)} 个文件成功")
    print(f"{'='*60}")

    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
