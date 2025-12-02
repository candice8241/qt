#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试subprocess集成脚本
模拟powder_module.py的subprocess调用
"""

import subprocess
import sys
import os

def test_subprocess_integration(input_pattern):
    """测试subprocess调用batch_integration"""
    
    print("="*80)
    print("测试Subprocess集成")
    print("="*80)
    print(f"输入路径: {input_pattern}")
    print(f"工作目录: {os.getcwd()}")
    print(f"Python: {sys.executable}")
    
    # 创建测试脚本（简化版）
    def escape(s):
        return s.replace('\\', '\\\\').replace('"', '\\"') if s else ""
    
    script = f'''
import sys
import os
import glob

print("=== Subprocess Started ===", flush=True)
print(f"Working directory: {{os.getcwd()}}", flush=True)
print(f"Python: {{sys.executable}}", flush=True)

sys.path.insert(0, "{escape(os.path.dirname(os.path.abspath(__file__)))}")

input_pattern = "{escape(input_pattern)}"
print(f"Input pattern: {{input_pattern}}", flush=True)
print(f"Pattern repr: {{repr(input_pattern)}}", flush=True)
print(f"Exists: {{os.path.exists(input_pattern)}}", flush=True)
print(f"Is directory: {{os.path.isdir(input_pattern)}}", flush=True)

# Test file search
print("\\n--- Testing file search ---", flush=True)

# Method 1
h5_files = sorted(glob.glob(input_pattern, recursive=True))
print(f"Method 1 raw results: {{len(h5_files)}} items", flush=True)
if h5_files:
    print(f"  First item: {{h5_files[0]}}", flush=True)
    print(f"  Is file: {{os.path.isfile(h5_files[0])}}", flush=True)
    print(f"  Ends with .h5: {{h5_files[0].endswith('.h5')}}", flush=True)

h5_files = [f for f in h5_files if f.endswith('.h5') and os.path.isfile(f)]
print(f"Method 1 filtered: {{len(h5_files)}} files", flush=True)

# Method 2
if not h5_files and os.path.isdir(input_pattern):
    print("\\nMethod 2: Directory detected", flush=True)
    pattern = os.path.join(input_pattern, '**', '*.h5')
    print(f"  Pattern: {{pattern}}", flush=True)
    h5_files = sorted(glob.glob(pattern, recursive=True))
    print(f"  Found: {{len(h5_files)}} files", flush=True)
    if h5_files:
        print(f"  Sample: {{h5_files[:3]}}", flush=True)

print(f"\\n=== Final Result: {{len(h5_files)}} files ===", flush=True)

# Try to import batch_integration
try:
    print("\\n--- Testing batch_integration import ---", flush=True)
    from batch_integration import BatchIntegrator
    print("✓ BatchIntegrator imported successfully", flush=True)
except Exception as e:
    print(f"✗ Failed to import: {{e}}", flush=True)
'''
    
    print("\n生成的脚本:")
    print("-"*80)
    print(script)
    print("-"*80)
    
    print("\n执行subprocess...")
    print("="*80)
    
    try:
        process = subprocess.Popen(
            [sys.executable, '-c', script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        stdout, stderr = process.communicate(timeout=10)
        
        print("\n=== STDOUT ===")
        print(stdout)
        
        if stderr:
            print("\n=== STDERR ===")
            print(stderr)
        
        print(f"\n=== 返回码: {process.returncode} ===")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        print("请输入测试路径:")
        test_path = input().strip()
    
    test_subprocess_integration(test_path)
