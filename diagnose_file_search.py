#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件查找诊断工具 - 帮助诊断为什么只找到1个文件
"""

import os
import glob
import sys

def diagnose(input_pattern):
    """诊断文件查找问题"""
    print("="*80)
    print("文件查找诊断工具")
    print("="*80)
    print(f"\n输入路径: {input_pattern}")
    print(f"类型: {type(input_pattern)}")
    print(f"长度: {len(input_pattern)}")
    print(f"repr: {repr(input_pattern)}")
    
    # 检查路径状态
    print(f"\n路径检查:")
    print(f"  os.path.exists: {os.path.exists(input_pattern)}")
    print(f"  os.path.isdir: {os.path.isdir(input_pattern)}")
    print(f"  os.path.isfile: {os.path.isfile(input_pattern)}")
    print(f"  os.path.abspath: {os.path.abspath(input_pattern)}")
    
    # Method 1
    print(f"\n{'='*80}")
    print(f"Method 1: glob.glob(input_pattern, recursive=True)")
    print(f"{'='*80}")
    result1 = sorted(glob.glob(input_pattern, recursive=True))
    print(f"原始结果数: {len(result1)}")
    if result1:
        print(f"原始结果:")
        for i, f in enumerate(result1[:10], 1):
            print(f"  {i}. {f}")
            print(f"     - Is file: {os.path.isfile(f)}")
            print(f"     - Ends with .h5: {f.endswith('.h5')}")
        if len(result1) > 10:
            print(f"  ... 还有 {len(result1)-10} 个")
    
    # 过滤
    filtered1 = [f for f in result1 if f.endswith('.h5') and os.path.isfile(f)]
    print(f"\n过滤后（只保留.h5文件）: {len(filtered1)}")
    if filtered1:
        for i, f in enumerate(filtered1[:5], 1):
            print(f"  {i}. {f}")
    
    # Method 2
    print(f"\n{'='*80}")
    print(f"Method 2: 检测目录并递归搜索")
    print(f"{'='*80}")
    
    if os.path.isdir(input_pattern):
        print(f"✓ 检测到是目录")
        pattern2 = os.path.join(input_pattern, '**', '*.h5')
        print(f"使用pattern: {pattern2}")
        result2 = sorted(glob.glob(pattern2, recursive=True))
        print(f"找到: {len(result2)} 个文件")
        if result2:
            print(f"示例文件:")
            for i, f in enumerate(result2[:10], 1):
                print(f"  {i}. {f}")
            if len(result2) > 10:
                print(f"  ... 还有 {len(result2)-10} 个")
    else:
        print(f"✗ 不是目录，跳过Method 2")
    
    # 尝试列出目录内容
    print(f"\n{'='*80}")
    print(f"尝试列出目录内容")
    print(f"{'='*80}")
    
    check_path = input_pattern
    if os.path.isfile(input_pattern):
        check_path = os.path.dirname(input_pattern)
        print(f"输入是文件，检查父目录: {check_path}")
    
    if os.path.isdir(check_path):
        print(f"列出目录内容: {check_path}")
        try:
            # 直接列出
            items = os.listdir(check_path)
            h5_files = [f for f in items if f.endswith('.h5')]
            print(f"\n直接子文件 (.h5): {len(h5_files)}")
            for f in h5_files[:10]:
                full_path = os.path.join(check_path, f)
                print(f"  - {f} (size: {os.path.getsize(full_path)} bytes)")
            
            # 递归遍历
            print(f"\n递归遍历所有子目录:")
            all_h5 = []
            for root, dirs, files in os.walk(check_path):
                h5_in_dir = [f for f in files if f.endswith('.h5')]
                if h5_in_dir:
                    print(f"  {root}: {len(h5_in_dir)} 个 .h5 文件")
                    all_h5.extend([os.path.join(root, f) for f in h5_in_dir])
            
            print(f"\n总共找到: {len(all_h5)} 个 .h5 文件")
            if all_h5:
                print(f"前5个:")
                for f in all_h5[:5]:
                    print(f"  - {f}")
        except Exception as e:
            print(f"错误: {e}")
    else:
        print(f"路径不存在或不是目录: {check_path}")
    
    # 总结
    print(f"\n{'='*80}")
    print(f"诊断总结")
    print(f"{'='*80}")
    print(f"如果上面显示找到了多个文件，但GUI只显示1个，")
    print(f"请提供GUI的完整Console日志。")
    print(f"\n可能的原因:")
    print(f"  1. 路径格式问题（反斜杠转义）")
    print(f"  2. GUI传递的路径与这里测试的不同")
    print(f"  3. 代码版本没有更新（需要重启GUI）")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_pattern = sys.argv[1]
    else:
        print("请输入要检查的路径：")
        input_pattern = input().strip()
    
    diagnose(input_pattern)
