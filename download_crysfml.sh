#!/bin/bash
# 下载 CrysFML EoS 模块的脚本

echo "=========================================="
echo "CrysFML EoS 模块下载脚本"
echo "=========================================="
echo ""

# 方法 1: 尝试从 GitLab 克隆
echo "方法 1: 从 GitLab 克隆 CrysFML2008..."
if command -v git &> /dev/null; then
    git clone https://gitlab.com/CrysFML/CrysFML2008.git crysfml_fortran 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✓ 成功克隆 CrysFML2008"
        echo "EoS 模块位置: crysfml_fortran/Src/CFML_EoS_Mod.f90"
        exit 0
    else
        echo "✗ GitLab 克隆失败，尝试其他方法..."
    fi
else
    echo "✗ Git 未安装"
fi

# 方法 2: 从 GitHub 镜像克隆
echo ""
echo "方法 2: 从 GitHub 克隆 CrysFML2008..."
if command -v git &> /dev/null; then
    git clone https://github.com/jrcrespoh/CrysFML2008.git crysfml_fortran 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✓ 成功克隆 CrysFML2008 (GitHub)"
        echo "EoS 模块位置: crysfml_fortran/Src/CFML_EoS_Mod.f90"
        exit 0
    else
        echo "✗ GitHub 克隆失败"
    fi
fi

# 方法 3: 直接下载文件
echo ""
echo "方法 3: 直接下载 CFML_EoS_Mod.f90..."
if command -v wget &> /dev/null; then
    mkdir -p crysfml_fortran/Src
    wget -O crysfml_fortran/Src/CFML_EoS_Mod.f90 \
        https://gitlab.com/CrysFML/CrysFML2008/-/raw/master/Src/CFML_EoS_Mod.f90 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✓ 成功下载 CFML_EoS_Mod.f90"
        echo "文件位置: crysfml_fortran/Src/CFML_EoS_Mod.f90"
        exit 0
    else
        echo "✗ wget 下载失败"
    fi
elif command -v curl &> /dev/null; then
    mkdir -p crysfml_fortran/Src
    curl -o crysfml_fortran/Src/CFML_EoS_Mod.f90 \
        https://gitlab.com/CrysFML/CrysFML2008/-/raw/master/Src/CFML_EoS_Mod.f90 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✓ 成功下载 CFML_EoS_Mod.f90"
        echo "文件位置: crysfml_fortran/Src/CFML_EoS_Mod.f90"
        exit 0
    else
        echo "✗ curl 下载失败"
    fi
fi

echo ""
echo "=========================================="
echo "自动下载失败"
echo "=========================================="
echo ""
echo "请手动访问以下网址之一下载 CrysFML:"
echo ""
echo "1. GitLab (官方):"
echo "   https://gitlab.com/CrysFML/CrysFML2008"
echo ""
echo "2. GitHub (镜像):"
echo "   https://github.com/jrcrespoh/CrysFML2008"
echo ""
echo "3. EoS 模块直接链接:"
echo "   https://gitlab.com/CrysFML/CrysFML2008/-/blob/master/Src/CFML_EoS_Mod.f90"
echo ""
echo "=========================================="

exit 1
