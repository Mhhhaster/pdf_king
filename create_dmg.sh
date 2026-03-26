#!/bin/bash
# 生成 PDFKing.dmg 安装镜像
set -e

cd "$(dirname "$0")"

APP_NAME="PDFKing"
DMG_NAME="${APP_NAME}.dmg"
DIST_DIR="dist"
APP_PATH="${DIST_DIR}/${APP_NAME}.app"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ 未找到 ${APP_PATH}，请先运行 build_app.sh 打包"
    exit 1
fi

# 清理旧文件
rm -f "${DIST_DIR}/${DMG_NAME}"

echo "📦 正在创建 DMG 安装镜像..."

# 创建临时目录
TMP_DMG_DIR=$(mktemp -d)
cp -R "$APP_PATH" "${TMP_DMG_DIR}/"

# 创建 Applications 快捷方式
ln -s /Applications "${TMP_DMG_DIR}/Applications"

# 生成 DMG
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$TMP_DMG_DIR" \
    -ov -format UDZO \
    "${DIST_DIR}/${DMG_NAME}"

# 清理
rm -rf "$TMP_DMG_DIR"

echo ""
echo "✅ DMG 已生成: ${DIST_DIR}/${DMG_NAME}"
echo "📍 $(du -sh ${DIST_DIR}/${DMG_NAME} | cut -f1) 大小"
echo ""
echo "分享给同事后，双击 DMG → 将 PDFKing 拖到 Applications 即可"
