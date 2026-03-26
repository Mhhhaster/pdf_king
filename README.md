<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS-blue?style=flat-square&logo=apple" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.9+-green?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PyQt6-orange?style=flat-square" alt="PyQt6">
  <img src="https://img.shields.io/github/license/Mhhhaster/pdf_king?style=flat-square" alt="License">
</p>

# 👑 PDFKing

**一款优雅的 macOS 桌面 PDF 工具**，拖入即用，支持 PDF 转图片、页面截取和批量转换。

> 告别繁琐的在线工具和命令行操作，拖入 PDF 即可完成转换。

---

## ✨ 功能特性

### 🖼 PDF 转图片
- 将 PDF 每一页导出为高清 PNG 图片
- 支持 **DPI 分辨率调整**（72 ~ 600 DPI），满足不同场景需求
- 实时**缩略图预览**，可调整预览大小
- 点击缩略图可**放大查看**原始尺寸
- 输出文件名格式：`{PDF名称}_{页码}.png`

### 📄 PDF 页面截取
- 指定起始页和结束页，截取生成新的 PDF 文件
- 自动识别 PDF 总页数，防止超出范围
- 适合提取论文章节、合同关键页等场景

### 📁 批量转图片
- 选择文件夹，**一键转换**文件夹下所有 PDF 为图片
- 支持**递归扫描子文件夹**
- 自动为每个 PDF 创建同名子文件夹，整齐归类
- 显示扫描到的文件列表和总页数

### 🎨 设计特色
- 🌙 **暗色主题** — 精心调色的 Catppuccin 暗色风格
- 🖱 **拖拽操作** — 支持将 PDF 文件或文件夹直接拖入窗口
- ⚡ **多线程处理** — 后台线程执行转换，界面不会卡顿
- 📊 **进度反馈** — 实时进度条和状态提示

---

## 📸 界面预览

> 💡 运行应用后，拖入 PDF 即可看到简洁直观的操作界面。

---

## 🚀 快速开始

### 方式一：直接运行源码

```bash
# 1. 克隆仓库
git clone https://github.com/Mhhhaster/pdf_king.git
cd pdf_king

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动应用
python3 pdfking.py
```

### 方式二：打包为 macOS 应用

```bash
# 一键打包（自动创建虚拟环境、安装依赖、生成图标、打包）
chmod +x build_app.sh
./build_app.sh
```

打包完成后，应用位于 `dist/PDFKing.app`，可以直接双击运行或拖入 `/Applications` 目录。

### 方式三：生成 DMG 安装镜像

```bash
# 先完成打包，再生成 DMG
./build_app.sh
chmod +x create_dmg.sh
./create_dmg.sh
```

生成的 `dist/PDFKing.dmg` 可以直接分享给同事，双击打开后拖入 Applications 即可安装。

---

## 📦 项目结构

```
pdfking/
├── pdfking.py          # 主程序（GUI + PDF 处理逻辑）
├── requirements.txt    # Python 依赖
├── build_app.sh        # PyInstaller 一键打包脚本
├── create_icon.py      # 应用图标生成脚本
├── create_dmg.sh       # DMG 安装镜像生成脚本
└── LICENSE             # MIT 许可证
```

---

## 🛠 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| GUI 框架 | **PyQt6** | 跨平台桌面 GUI，原生 macOS 体验 |
| PDF 处理 | **PyMuPDF (fitz)** | 高性能 PDF 渲染与操作引擎 |
| 图像处理 | **Pillow** | 图标生成 |
| 应用打包 | **PyInstaller** | 打包为独立 macOS .app 应用 |

---

## 📋 系统要求

- **操作系统**：macOS 11.0 (Big Sur) 及以上
- **Python**：3.9+（仅源码运行需要）
- **芯片架构**：Apple Silicon (M1/M2/M3/M4) 和 Intel 均支持
  > ⚠️ 打包后的 .app 仅支持与打包机器相同的架构

---

## 🤝 分享给同事

| 方式 | 操作 | 适合场景 |
|------|------|----------|
| **发送 .app** | 将 `dist/PDFKing.app` 压缩为 zip 发送 | 快速分享，同架构 Mac |
| **发送 .dmg** | 运行 `create_dmg.sh` 生成安装镜像 | 正式分发，体验更好 |
| **分享源码** | 发送仓库链接，对方运行 `build_app.sh` | 跨架构，可自行打包 |

---

## 📝 使用指南

1. **拖入文件** — 将 PDF 拖入窗口中央区域，或点击按钮选择文件
2. **选择模式** — 在「转为图片」「截取页面」「批量转图片」三种模式间切换
3. **调整参数** — 设置 DPI、页码范围等参数
4. **开始导出** — 点击「开始导出」按钮，选择输出目录
5. **查看结果** — 导出完成后可直接在 Finder 中打开

---

## 📜 License

本项目基于 [MIT License](LICENSE) 开源。

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/Mhhhaster">Mhhhaster</a>
</p>
