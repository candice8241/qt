#!/bin/bash
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试 auto_fitting_module_v2.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. 检查语法..."
python3 -m py_compile /workspace/auto_fitting_module_v2.py 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ 语法检查通过"
else
    echo "   ❌ 语法错误"
    exit 1
fi
echo ""
echo "2. 统计信息..."
echo "   总行数: $(wc -l < /workspace/auto_fitting_module_v2.py)"
echo "   函数数: $(grep -c "^    def " /workspace/auto_fitting_module_v2.py)"
echo "   类数: $(grep -c "^class " /workspace/auto_fitting_module_v2.py)"
echo ""
echo "3. 核心功能检查..."
for func in "load_file" "auto_find_peaks" "fit_peaks" "subtract_background" "toggle_bg_selection" "batch_auto_fit"; do
    if grep -q "def $func" /workspace/auto_fitting_module_v2.py; then
        echo "   ✅ $func"
    else
        echo "   ❌ $func 缺失"
    fi
done
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ v2版本基本检查完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
