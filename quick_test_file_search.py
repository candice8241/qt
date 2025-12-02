#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试文件查找功能 - 交互式版本
"""

import os
import glob
import sys

def test_file_search(input_pattern):
    """测试文件查找逻辑"""
    print(f"\n{'='*80}")
    print(f"测试输入: {input_pattern}")
    print(f"{'='*80}")
    
    h5_files = []
    
    print(f"🔍 Starting file search with input: {input_pattern}")
    print(f"   Input type: {type(input_pattern)}")
    print(f"   Is directory: {os.path.isdir(input_pattern)}")
    print(f"   Exists: {os.path.exists(input_pattern)}")
    
    # Method 1: Try the pattern as-is with recursive search
    print(f"\n📂 Method 1: Trying pattern as-is with recursive=True...")
    h5_files = sorted(glob.glob(input_pattern, recursive=True))
    # Filter out the directory itself and only keep .h5 files
    h5_files = [f for f in h5_files if f.endswith('.h5') and os.path.isfile(f)]
    print(f"   Result: Found {len(h5_files)} files")
    if h5_files:
        print(f"   ✓ Success! Sample files:")
        for f in h5_files[:5]:
            print(f"      - {f}")
        if len(h5_files) > 5:
            print(f"      ... and {len(h5_files) - 5} more files")
        return h5_files
    
    # Method 2: If no files and it's a directory path, search for **/*.h5 recursively
    if not h5_files and os.path.isdir(input_pattern):
        print(f"\n📂 Method 2: Directory detected, searching recursively for **/*.h5...")
        pattern = os.path.join(input_pattern, '**', '*.h5')
        print(f"   Pattern: {pattern}")
        h5_files = sorted(glob.glob(pattern, recursive=True))
        print(f"   Result: Found {len(h5_files)} files")
        if h5_files:
            print(f"   ✓ Success! Found {len(h5_files)} .h5 files in directory: {input_pattern}")
            print(f"   Sample files:")
            for f in h5_files[:5]:
                print(f"      - {f}")
            if len(h5_files) > 5:
                print(f"      ... and {len(h5_files) - 5} more files")
            return h5_files
    
    # Method 3: If pattern contains *.h5 but no **, try recursive search
    if not h5_files and '*.h5' in input_pattern and '**' not in input_pattern:
        print(f"\n📂 Method 3: Converting *.h5 pattern to recursive **/*.h5...")
        # Extract directory part
        if input_pattern.endswith('*.h5'):
            base_dir = input_pattern[:-len('*.h5')].rstrip('/\\')
            if not base_dir:
                base_dir = '.'
            recursive_pattern = os.path.join(base_dir, '**', '*.h5')
        else:
            recursive_pattern = input_pattern.replace('*.h5', '**/*.h5')
        print(f"   Pattern: {recursive_pattern}")
        h5_files = sorted(glob.glob(recursive_pattern, recursive=True))
        print(f"   Result: Found {len(h5_files)} files")
        if h5_files:
            print(f"   ✓ Success! Using recursive pattern")
            print(f"   Sample files:")
            for f in h5_files[:5]:
                print(f"      - {f}")
            if len(h5_files) > 5:
                print(f"      ... and {len(h5_files) - 5} more files")
            return h5_files
    
    # Method 4: Try as directory with recursive **/*.h5
    if not h5_files:
        print(f"\n📂 Method 4: Trying to interpret as directory with recursive search...")
        # Strip trailing wildcards if any
        clean_path = input_pattern.rstrip('/*')
        if os.path.isdir(clean_path):
            recursive_pattern = os.path.join(clean_path, '**', '*.h5')
            print(f"   Pattern: {recursive_pattern}")
            h5_files = sorted(glob.glob(recursive_pattern, recursive=True))
            print(f"   Result: Found {len(h5_files)} files")
            if h5_files:
                print(f"   ✓ Success! Found files in cleaned directory path")
                print(f"   Sample files:")
                for f in h5_files[:5]:
                    print(f"      - {f}")
                if len(h5_files) > 5:
                    print(f"      ... and {len(h5_files) - 5} more files")
                return h5_files
    
    # Method 5: Try parent directory if path looks like it might be incomplete
    if not h5_files and os.path.sep in input_pattern:
        print(f"\n📂 Method 5: Trying parent directory...")
        parent_dir = os.path.dirname(input_pattern)
        if parent_dir and os.path.isdir(parent_dir):
            recursive_pattern = os.path.join(parent_dir, '**', '*.h5')
            print(f"   Pattern: {recursive_pattern}")
            h5_files = sorted(glob.glob(recursive_pattern, recursive=True))
            print(f"   Result: Found {len(h5_files)} files")
            if h5_files:
                print(f"   ✓ Success! Found files in parent directory: {parent_dir}")
                print(f"   Sample files:")
                for f in h5_files[:5]:
                    print(f"      - {f}")
                if len(h5_files) > 5:
                    print(f"      ... and {len(h5_files) - 5} more files")
                return h5_files

    if not h5_files:
        print(f"\n⚠ ERROR: No matching .h5 files found!")
        print(f"  Input pattern: {input_pattern}")
        print(f"  Absolute path: {os.path.abspath(input_pattern)}")
        print(f"  Current directory: {os.getcwd()}")
        
        # List what's actually in the directory if it exists
        check_path = input_pattern
        if not os.path.exists(check_path):
            check_path = os.path.dirname(input_pattern)
        
        if check_path and os.path.isdir(check_path):
            print(f"\n  📋 Searching for .h5 files in: {check_path}")
            try:
                found_any = False
                for root, dirs, files in os.walk(check_path):
                    h5_in_dir = [f for f in files if f.endswith('.h5')]
                    if h5_in_dir:
                        found_any = True
                        print(f"    {root}: {len(h5_in_dir)} .h5 files")
                        for f in h5_in_dir[:3]:
                            print(f"      - {f}")
                        if len(h5_in_dir) > 3:
                            print(f"      ... and {len(h5_in_dir) - 3} more")
                if not found_any:
                    print(f"    ⚠ No .h5 files found in directory tree")
            except Exception as e:
                print(f"    Error listing directory: {e}")
    
    return h5_files


def interactive_mode():
    """交互式模式"""
    print("="*80)
    print("文件查找测试工具 - 交互式模式")
    print("="*80)
    print("\n请输入要搜索的路径（支持的格式）：")
    print("  1. 目录路径: /path/to/data")
    print("  2. 通配符: /path/to/data/*.h5")
    print("  3. 递归: /path/to/data/**/*.h5")
    print("  4. 相对路径: data 或 ./data")
    print("\n输入 'q' 退出\n")
    
    while True:
        try:
            user_input = input("请输入路径 > ").strip()
            
            if user_input.lower() == 'q':
                print("再见！")
                break
            
            if not user_input:
                print("⚠ 请输入有效路径\n")
                continue
            
            files = test_file_search(user_input)
            
            print(f"\n{'='*80}")
            print(f"✓ 搜索完成：找到 {len(files)} 个文件")
            print(f"{'='*80}\n")
            
        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 命令行模式
        input_pattern = sys.argv[1]
        files = test_file_search(input_pattern)
        print(f"\n{'='*80}")
        print(f"✓ Final result: Found {len(files)} files")
        print(f"{'='*80}")
    else:
        # 交互式模式
        interactive_mode()
