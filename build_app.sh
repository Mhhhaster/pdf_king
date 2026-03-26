#!/bin/bash
# PDFKing 一键打包脚本
# 将 Python 应用打包为 macOS .app

set -e

echo "🔨 PDFKing 打包开始..."

# 确保在项目目录
cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

echo "📦 激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install -r requirements.txt

# 生成图标
echo "🎨 生成应用图标..."
python3 create_icon.py

# 打包
echo "📦 使用 PyInstaller 打包..."
pyinstaller --noconfirm \
    --windowed \
    --name "PDFKing" \
    --icon "icon.icns" \
    --add-data "icon.icns:." \
    --osx-bundle-identifier "com.pdfking.app" \
    --hidden-import "PyQt6" \
    --hidden-import "fitz" \
    --hidden-import "PIL" \
    pdfking.py

echo ""
echo "✅ 打包完成！"
echo "📍 应用位置: dist/PDFKing.app"
echo ""
echo "你可以将 dist/PDFKing.app 拖到 /Applications 目录使用"
echo "或直接双击运行"
