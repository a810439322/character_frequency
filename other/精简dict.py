#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
精简dict.yaml，只保留首字，去除重复
"""

def simplify_dict():
    seen = set()
    result = []

    with open('../dict.yaml', 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if parts:
                char = parts[0]
                if char and char not in seen:
                    seen.add(char)
                    result.append(char)

    # 保存到新文件
    with open('../dict_simple.txt', 'w', encoding='utf-8') as f:
        for char in result:
            f.write(char + '\n')

    print(f"精简完成！")
    print(f"原始行数: {len(seen)} + 重复项")
    print(f"去重后字数: {len(result)}")
    print(f"已保存到: dict_simple.txt")

if __name__ == '__main__':
    simplify_dict()
