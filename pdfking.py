#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDFKing - macOS PDF 工具
功能：
1. PDF 转图片（支持分辨率调整、预览）
2. PDF 页面截取（指定页码范围导出新 PDF）
"""

import sys
import os
import fitz  # PyMuPDF
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QSpinBox, QComboBox,
    QScrollArea, QGridLayout, QStackedWidget, QSlider,
    QFrame, QSizePolicy, QProgressBar, QMessageBox, QGroupBox,
    QCheckBox
)
from PyQt6.QtCore import (
    Qt, QMimeData, QThread, pyqtSignal, QSize, QTimer
)
from PyQt6.QtGui import (
    QPixmap, QImage, QDragEnterEvent, QDropEvent,
    QFont, QColor, QPalette, QIcon, QPainter
)


# ──────────────────────────────────────────────
#  工作线程
# ──────────────────────────────────────────────
class PdfToImageWorker(QThread):
    """PDF 转图片后台线程"""
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(str)       # output_dir
    error = pyqtSignal(str)

    def __init__(self, pdf_path, output_dir, dpi, page_indices=None):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.dpi = dpi
        self.page_indices = page_indices  # None = 全部

    def run(self):
        try:
            doc = fitz.open(self.pdf_path)
            pdf_name = Path(self.pdf_path).stem
            pages = self.page_indices if self.page_indices else range(len(doc))
            total = len(pages) if isinstance(pages, list) else len(list(pages))

            for idx, page_num in enumerate(pages):
                page = doc.load_page(page_num)
                zoom = self.dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                output_path = os.path.join(
                    self.output_dir,
                    f"{pdf_name}_{page_num + 1}.png"
                )
                pix.save(output_path)
                self.progress.emit(idx + 1, total)

            doc.close()
            self.finished.emit(self.output_dir)
        except Exception as e:
            self.error.emit(str(e))


class BatchPdfToImageWorker(QThread):
    """批量 PDF 转图片后台线程"""
    progress = pyqtSignal(int, int, str)  # current, total, current_file_name
    finished = pyqtSignal(str, int, int)  # output_dir, file_count, total_images
    error = pyqtSignal(str)

    def __init__(self, pdf_paths, output_dir, dpi):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.output_dir = output_dir
        self.dpi = dpi

    def run(self):
        try:
            # 计算总页数
            total_pages = 0
            file_pages = []
            for pdf_path in self.pdf_paths:
                doc = fitz.open(pdf_path)
                pages = len(doc)
                file_pages.append(pages)
                total_pages += pages
                doc.close()

            processed = 0
            total_images = 0

            for file_idx, pdf_path in enumerate(self.pdf_paths):
                doc = fitz.open(pdf_path)
                pdf_name = Path(pdf_path).stem

                # 为每个 PDF 创建子文件夹
                pdf_output_dir = os.path.join(self.output_dir, pdf_name)
                os.makedirs(pdf_output_dir, exist_ok=True)

                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    zoom = self.dpi / 72.0
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, alpha=False)

                    output_path = os.path.join(
                        pdf_output_dir,
                        f"{pdf_name}_{page_num + 1}.png"
                    )
                    pix.save(output_path)
                    processed += 1
                    total_images += 1
                    self.progress.emit(
                        processed, total_pages,
                        f"{pdf_name} ({page_num + 1}/{len(doc)})"
                    )

                doc.close()

            self.finished.emit(self.output_dir, len(self.pdf_paths), total_images)
        except Exception as e:
            self.error.emit(str(e))


class PdfExtractWorker(QThread):
    """PDF 页面截取后台线程"""
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, pdf_path, output_path, start_page, end_page):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_path = output_path
        self.start_page = start_page
        self.end_page = end_page

    def run(self):
        try:
            doc = fitz.open(self.pdf_path)
            new_doc = fitz.open()
            total = self.end_page - self.start_page + 1

            for idx, page_num in enumerate(range(self.start_page - 1, self.end_page)):
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                self.progress.emit(idx + 1, total)

            new_doc.save(self.output_path)
            new_doc.close()
            doc.close()
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────────────────────────
#  可点击的缩略图 Label
# ──────────────────────────────────────────────
class ClickableLabel(QLabel):
    """点击可放大预览的缩略图"""
    def __init__(self, pixmap_full, page_num, parent=None):
        super().__init__(parent)
        self.pixmap_full = pixmap_full
        self.page_num = page_num
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"第 {page_num} 页 — 点击放大预览")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_preview()

    def _show_preview(self):
        dialog = QWidget(self.window(), Qt.WindowType.Window)
        dialog.setWindowTitle(f"预览 — 第 {self.page_num} 页")
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        layout = QVBoxLayout(dialog)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        label = QLabel()

        screen = QApplication.primaryScreen()
        if screen:
            screen_size = screen.availableSize()
            max_w = int(screen_size.width() * 0.8)
            max_h = int(screen_size.height() * 0.8)
        else:
            max_w, max_h = 1200, 800

        scaled = self.pixmap_full.scaled(
            max_w, max_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        label.setPixmap(scaled)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(label)
        layout.addWidget(scroll)

        dialog.resize(min(scaled.width() + 40, max_w), min(scaled.height() + 40, max_h))
        dialog.show()


# ──────────────────────────────────────────────
#  拖拽区域
# ──────────────────────────────────────────────
class DropZone(QLabel):
    """拖拽 PDF 文件 / 文件夹区域"""
    file_dropped = pyqtSignal(str)
    folder_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(180)
        self._set_default_style()
        self._update_text()

    def _set_default_style(self):
        self.setStyleSheet("""
            QLabel {
                border: 3px dashed #555;
                border-radius: 16px;
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-size: 16px;
                padding: 30px;
            }
        """)

    def _update_text(self, filename=None, is_folder=False):
        if filename:
            if is_folder:
                self.setText(f"📁 已加载文件夹: {filename}\n\n拖入新文件或文件夹可替换")
            else:
                self.setText(f"📄 已加载: {filename}\n\n拖入新文件或文件夹可替换")
        else:
            self.setText("📁 将 PDF 文件或文件夹拖入此处\n\n或点击下方按钮选择")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            # 接受 PDF 文件或文件夹
            for u in urls:
                path = u.toLocalFile()
                if path.lower().endswith('.pdf') or os.path.isdir(path):
                    event.acceptProposedAction()
                    self.setStyleSheet("""
                        QLabel {
                            border: 3px dashed #89b4fa;
                            border-radius: 16px;
                            background-color: #2a2a3e;
                            color: #89b4fa;
                            font-size: 16px;
                            padding: 30px;
                        }
                    """)
                    break

    def dragLeaveEvent(self, event):
        self._set_default_style()

    def dropEvent(self, event: QDropEvent):
        self._set_default_style()
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isdir(file_path):
                self._update_text(os.path.basename(file_path), is_folder=True)
                self.folder_dropped.emit(file_path)
                return
            elif file_path.lower().endswith('.pdf'):
                self._update_text(os.path.basename(file_path))
                self.file_dropped.emit(file_path)
                return


# ──────────────────────────────────────────────
#  主窗口
# ──────────────────────────────────────────────
class PDFKingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pdf_path = None
        self.pdf_doc = None
        self.total_pages = 0
        self.preview_pixmaps = []   # 缓存全尺寸 pixmap
        self.worker = None
        self.batch_folder = None     # 批量模式选择的文件夹
        self.batch_pdf_list = []     # 批量模式扫描到的 PDF 列表

        self.setWindowTitle("PDFKing")
        self.setMinimumSize(900, 700)
        self.resize(1100, 800)
        self._apply_dark_theme()
        self._build_ui()

    # ─── 暗色主题 ────────────────────────────
    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #181825;
            }
            QWidget {
                background-color: #181825;
                color: #cdd6f4;
                font-family: "PingFang SC", "SF Pro", "Helvetica Neue", sans-serif;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 14px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #89b4fa;
            }
            QPushButton:pressed {
                background-color: #585b70;
            }
            QPushButton:disabled {
                background-color: #1e1e2e;
                color: #585b70;
                border-color: #313244;
            }
            QPushButton#primaryBtn {
                background-color: #89b4fa;
                color: #1e1e2e;
                font-weight: bold;
                border: none;
            }
            QPushButton#primaryBtn:hover {
                background-color: #b4d0fb;
            }
            QPushButton#primaryBtn:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
            QPushButton#dangerBtn {
                background-color: #f38ba8;
                color: #1e1e2e;
                font-weight: bold;
                border: none;
            }
            QPushButton#dangerBtn:hover {
                background-color: #f5a0b8;
            }
            QGroupBox {
                border: 1px solid #313244;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #89b4fa;
            }
            QSpinBox, QComboBox {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px 8px;
                color: #cdd6f4;
                min-height: 28px;
                font-size: 14px;
            }
            QSpinBox:focus, QComboBox:focus {
                border-color: #89b4fa;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #313244;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                height: 16px;
                margin: -5px 0;
                background: #89b4fa;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #89b4fa;
                border-radius: 3px;
            }
            QProgressBar {
                background-color: #313244;
                border: none;
                border-radius: 6px;
                text-align: center;
                color: #cdd6f4;
                min-height: 22px;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 6px;
            }
            QScrollArea {
                border: none;
                background-color: #181825;
            }
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: bold;
                color: #cdd6f4;
                padding: 4px 0;
            }
            QLabel#statusLabel {
                color: #a6adc8;
                font-size: 13px;
            }
        """)

    # ─── 构建界面 ────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # 标题
        title = QLabel("PDFKing")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #89b4fa; padding: 0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("拖入 PDF → 转图片 / 截取页面 / 批量转换")
        subtitle.setStyleSheet("font-size: 14px; color: #6c7086; padding: 0; margin-bottom: 4px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # 拖拽区
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._on_file_loaded)
        self.drop_zone.folder_dropped.connect(self._on_folder_loaded)
        main_layout.addWidget(self.drop_zone)

        # 选择文件 / 文件夹按钮
        btn_row = QHBoxLayout()
        self.btn_browse = QPushButton("📂  选择 PDF 文件")
        self.btn_browse.clicked.connect(self._browse_file)
        self.btn_browse_folder = QPushButton("📁  选择文件夹（批量）")
        self.btn_browse_folder.clicked.connect(self._browse_folder)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_browse)
        btn_row.addWidget(self.btn_browse_folder)
        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        # PDF 信息
        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("statusLabel")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.lbl_info)

        # ─── 操作面板（两栏） ─────────────────
        self.panel = QWidget()
        self.panel.setVisible(False)
        panel_layout = QHBoxLayout(self.panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(16)

        # 左栏：模式 + 参数
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        #   模式选择
        mode_group = QGroupBox("操作模式")
        mode_layout = QVBoxLayout(mode_group)
        mode_btn_row = QHBoxLayout()

        self.btn_mode_img = QPushButton("🖼  转为图片")
        self.btn_mode_img.setCheckable(True)
        self.btn_mode_img.setChecked(True)
        self.btn_mode_img.clicked.connect(lambda: self._switch_mode(0))

        self.btn_mode_pdf = QPushButton("📄  截取页面")
        self.btn_mode_pdf.setCheckable(True)
        self.btn_mode_pdf.clicked.connect(lambda: self._switch_mode(1))

        self.btn_mode_batch = QPushButton("📁  批量转图片")
        self.btn_mode_batch.setCheckable(True)
        self.btn_mode_batch.clicked.connect(lambda: self._switch_mode(2))

        mode_btn_row.addWidget(self.btn_mode_img)
        mode_btn_row.addWidget(self.btn_mode_pdf)
        mode_btn_row.addWidget(self.btn_mode_batch)
        mode_layout.addLayout(mode_btn_row)
        left_layout.addWidget(mode_group)

        #   参数 stack
        self.param_stack = QStackedWidget()

        # --- 图片参数 ---
        img_params = QWidget()
        img_layout = QVBoxLayout(img_params)
        img_layout.setContentsMargins(0, 8, 0, 0)

        # DPI
        dpi_group = QGroupBox("分辨率 (DPI)")
        dpi_layout = QVBoxLayout(dpi_group)
        dpi_row = QHBoxLayout()
        self.dpi_slider = QSlider(Qt.Orientation.Horizontal)
        self.dpi_slider.setRange(72, 600)
        self.dpi_slider.setValue(150)
        self.dpi_slider.setTickInterval(50)
        self.dpi_slider.valueChanged.connect(self._on_dpi_changed)
        self.lbl_dpi = QLabel("150 DPI")
        self.lbl_dpi.setMinimumWidth(70)
        dpi_row.addWidget(self.dpi_slider)
        dpi_row.addWidget(self.lbl_dpi)
        dpi_layout.addLayout(dpi_row)

        presets_row = QHBoxLayout()
        for dpi_val in [72, 150, 300, 600]:
            b = QPushButton(f"{dpi_val}")
            b.setFixedWidth(56)
            b.clicked.connect(lambda checked, v=dpi_val: self.dpi_slider.setValue(v))
            presets_row.addWidget(b)
        presets_row.addStretch()
        dpi_layout.addLayout(presets_row)

        img_layout.addWidget(dpi_group)

        # 预览尺寸
        preview_group = QGroupBox("缩略图预览大小")
        preview_layout = QHBoxLayout(preview_group)
        self.preview_slider = QSlider(Qt.Orientation.Horizontal)
        self.preview_slider.setRange(80, 400)
        self.preview_slider.setValue(180)
        self.preview_slider.valueChanged.connect(self._on_preview_size_changed)
        self.lbl_preview_size = QLabel("180 px")
        self.lbl_preview_size.setMinimumWidth(60)
        preview_layout.addWidget(self.preview_slider)
        preview_layout.addWidget(self.lbl_preview_size)
        img_layout.addWidget(preview_group)

        self.param_stack.addWidget(img_params)

        # --- PDF 截取参数 ---
        pdf_params = QWidget()
        pdf_layout = QVBoxLayout(pdf_params)
        pdf_layout.setContentsMargins(0, 8, 0, 0)

        range_group = QGroupBox("页码范围")
        range_layout = QVBoxLayout(range_group)
        range_row = QHBoxLayout()

        range_row.addWidget(QLabel("从第"))
        self.spin_start = QSpinBox()
        self.spin_start.setMinimum(1)
        self.spin_start.setMaximum(1)
        self.spin_start.setValue(1)
        range_row.addWidget(self.spin_start)

        range_row.addWidget(QLabel("页  到第"))
        self.spin_end = QSpinBox()
        self.spin_end.setMinimum(1)
        self.spin_end.setMaximum(1)
        self.spin_end.setValue(1)
        range_row.addWidget(self.spin_end)
        range_row.addWidget(QLabel("页"))
        range_row.addStretch()

        range_layout.addLayout(range_row)

        self.lbl_page_hint = QLabel("")
        self.lbl_page_hint.setStyleSheet("color: #a6adc8; font-size: 12px;")
        range_layout.addWidget(self.lbl_page_hint)

        pdf_layout.addWidget(range_group)
        pdf_layout.addStretch()
        self.param_stack.addWidget(pdf_params)

        # --- 批量转图片参数 ---
        batch_params = QWidget()
        batch_layout = QVBoxLayout(batch_params)
        batch_layout.setContentsMargins(0, 8, 0, 0)

        # 文件夹信息
        folder_group = QGroupBox("文件夹")
        folder_layout = QVBoxLayout(folder_group)

        self.lbl_batch_folder = QLabel("未选择文件夹")
        self.lbl_batch_folder.setStyleSheet("color: #a6adc8; font-size: 13px;")
        self.lbl_batch_folder.setWordWrap(True)
        folder_layout.addWidget(self.lbl_batch_folder)

        self.btn_change_folder = QPushButton("📁  更换文件夹")
        self.btn_change_folder.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.btn_change_folder)

        self.chk_recursive = QCheckBox("包含子文件夹中的 PDF")
        self.chk_recursive.setChecked(True)
        self.chk_recursive.setStyleSheet("QCheckBox { font-size: 13px; }")
        self.chk_recursive.stateChanged.connect(self._rescan_folder)
        folder_layout.addWidget(self.chk_recursive)

        batch_layout.addWidget(folder_group)

        # 文件列表
        file_list_group = QGroupBox("扫描到的 PDF 文件")
        file_list_layout = QVBoxLayout(file_list_group)

        self.lbl_batch_count = QLabel("0 个文件")
        self.lbl_batch_count.setStyleSheet("color: #a6e3a1; font-size: 13px; font-weight: bold;")
        file_list_layout.addWidget(self.lbl_batch_count)

        self.batch_file_scroll = QScrollArea()
        self.batch_file_scroll.setWidgetResizable(True)
        self.batch_file_scroll.setMaximumHeight(150)
        self.batch_file_scroll.setStyleSheet("""
            QScrollArea { background-color: #1e1e2e; border-radius: 6px; border: 1px solid #313244; }
        """)
        self.batch_file_list_widget = QLabel("")
        self.batch_file_list_widget.setStyleSheet("font-size: 12px; color: #a6adc8; padding: 8px; background: transparent;")
        self.batch_file_list_widget.setWordWrap(True)
        self.batch_file_list_widget.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.batch_file_scroll.setWidget(self.batch_file_list_widget)
        file_list_layout.addWidget(self.batch_file_scroll)

        batch_layout.addWidget(file_list_group)

        # 批量 DPI
        batch_dpi_group = QGroupBox("分辨率 (DPI)")
        batch_dpi_layout = QVBoxLayout(batch_dpi_group)
        batch_dpi_row = QHBoxLayout()
        self.batch_dpi_slider = QSlider(Qt.Orientation.Horizontal)
        self.batch_dpi_slider.setRange(72, 600)
        self.batch_dpi_slider.setValue(150)
        self.batch_dpi_slider.valueChanged.connect(self._on_batch_dpi_changed)
        self.lbl_batch_dpi = QLabel("150 DPI")
        self.lbl_batch_dpi.setMinimumWidth(70)
        batch_dpi_row.addWidget(self.batch_dpi_slider)
        batch_dpi_row.addWidget(self.lbl_batch_dpi)
        batch_dpi_layout.addLayout(batch_dpi_row)

        batch_presets_row = QHBoxLayout()
        for dpi_val in [72, 150, 300, 600]:
            b = QPushButton(f"{dpi_val}")
            b.setFixedWidth(56)
            b.clicked.connect(lambda checked, v=dpi_val: self.batch_dpi_slider.setValue(v))
            batch_presets_row.addWidget(b)
        batch_presets_row.addStretch()
        batch_dpi_layout.addLayout(batch_presets_row)

        batch_layout.addWidget(batch_dpi_group)
        batch_layout.addStretch()
        self.param_stack.addWidget(batch_params)

        left_layout.addWidget(self.param_stack)

        # 执行按钮
        self.btn_execute = QPushButton("🚀  开始导出")
        self.btn_execute.setObjectName("primaryBtn")
        self.btn_execute.setMinimumHeight(44)
        self.btn_execute.clicked.connect(self._execute)
        left_layout.addWidget(self.btn_execute)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.lbl_status)

        left_layout.addStretch()
        left_panel.setFixedWidth(360)

        # 右栏：预览区
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_title = QLabel("页面预览")
        preview_title.setObjectName("sectionTitle")
        right_layout.addWidget(preview_title)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background-color: #1e1e2e; border-radius: 10px; }
        """)

        self.preview_container = QWidget()
        self.preview_grid = QGridLayout(self.preview_container)
        self.preview_grid.setSpacing(12)
        self.preview_grid.setContentsMargins(12, 12, 12, 12)
        self.scroll_area.setWidget(self.preview_container)
        right_layout.addWidget(self.scroll_area)

        panel_layout.addWidget(left_panel)
        panel_layout.addWidget(right_panel, 1)
        main_layout.addWidget(self.panel, 1)

    # ─── 文件加载 ────────────────────────────
    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 PDF 文件", "", "PDF 文件 (*.pdf)"
        )
        if path:
            self.drop_zone._update_text(os.path.basename(path))
            self._on_file_loaded(path)

    def _on_file_loaded(self, path):
        if self.pdf_doc:
            self.pdf_doc.close()

        self.pdf_path = path
        self.pdf_doc = fitz.open(path)
        self.total_pages = len(self.pdf_doc)

        file_size = os.path.getsize(path)
        size_str = (
            f"{file_size / 1024 / 1024:.1f} MB"
            if file_size > 1024 * 1024
            else f"{file_size / 1024:.1f} KB"
        )
        self.lbl_info.setText(
            f"📄 {os.path.basename(path)}  ·  {self.total_pages} 页  ·  {size_str}"
        )

        # 更新页码范围
        self.spin_start.setMaximum(self.total_pages)
        self.spin_end.setMaximum(self.total_pages)
        self.spin_end.setValue(self.total_pages)
        self.lbl_page_hint.setText(f"共 {self.total_pages} 页")

        self.panel.setVisible(True)
        self.lbl_status.setText("")
        self.progress_bar.setVisible(False)

        # 生成预览
        self._generate_previews()

    def _generate_previews(self):
        """生成所有页面的缩略图"""
        self.preview_pixmaps.clear()
        # 清空网格
        while self.preview_grid.count():
            item = self.preview_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.pdf_doc:
            return

        preview_dpi = 100  # 预览用的基础 DPI
        thumb_size = self.preview_slider.value()

        cols = max(1, (self.scroll_area.width() - 40) // (thumb_size + 20))

        for i in range(self.total_pages):
            page = self.pdf_doc.load_page(i)
            zoom = preview_dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            img = QImage(
                pix.samples, pix.width, pix.height,
                pix.stride, QImage.Format.Format_RGB888
            )
            full_pixmap = QPixmap.fromImage(img)
            self.preview_pixmaps.append(full_pixmap)

            thumb = full_pixmap.scaled(
                thumb_size, thumb_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(4, 4, 4, 4)
            container_layout.setSpacing(4)

            lbl = ClickableLabel(full_pixmap, i + 1)
            lbl.setPixmap(thumb)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("""
                QLabel {
                    border: 1px solid #313244;
                    border-radius: 6px;
                    padding: 4px;
                    background-color: #1e1e2e;
                }
                QLabel:hover {
                    border-color: #89b4fa;
                }
            """)
            container_layout.addWidget(lbl)

            page_label = QLabel(f"第 {i + 1} 页")
            page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            page_label.setStyleSheet("font-size: 11px; color: #6c7086; border: none; background: transparent;")
            container_layout.addWidget(page_label)

            row, col = divmod(i, cols)
            self.preview_grid.addWidget(container, row, col)

    # ─── 模式切换 ────────────────────────────
    def _switch_mode(self, mode_index):
        self.param_stack.setCurrentIndex(mode_index)
        self.btn_mode_img.setChecked(mode_index == 0)
        self.btn_mode_pdf.setChecked(mode_index == 1)
        self.btn_mode_batch.setChecked(mode_index == 2)

        # 更新按钮样式
        active_style = """
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 14px;
                min-height: 32px;
            }
        """
        inactive_style = """
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 14px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #89b4fa;
            }
        """
        self.btn_mode_img.setStyleSheet(active_style if mode_index == 0 else inactive_style)
        self.btn_mode_pdf.setStyleSheet(active_style if mode_index == 1 else inactive_style)
        self.btn_mode_batch.setStyleSheet(active_style if mode_index == 2 else inactive_style)

        if mode_index == 0:
            self.btn_execute.setText("🚀  开始导出图片")
        elif mode_index == 1:
            self.btn_execute.setText("🚀  开始截取 PDF")
        else:
            self.btn_execute.setText("🚀  开始批量转换")

    # ─── 参数变化 ────────────────────────────
    def _on_batch_dpi_changed(self, value):
        self.lbl_batch_dpi.setText(f"{value} DPI")

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择包含 PDF 的文件夹", str(Path.home() / "Desktop")
        )
        if folder:
            self.drop_zone._update_text(os.path.basename(folder), is_folder=True)
            self._on_folder_loaded(folder)

    def _on_folder_loaded(self, folder_path):
        """加载文件夹，扫描 PDF 文件"""
        self.batch_folder = folder_path
        self._switch_mode(2)
        self.panel.setVisible(True)
        self.lbl_batch_folder.setText(f"📁 {folder_path}")
        self._rescan_folder()

    def _rescan_folder(self):
        """重新扫描文件夹中的 PDF 文件"""
        if not self.batch_folder:
            return

        self.batch_pdf_list.clear()
        recursive = self.chk_recursive.isChecked()

        if recursive:
            for root, dirs, files in os.walk(self.batch_folder):
                for f in sorted(files):
                    if f.lower().endswith('.pdf'):
                        self.batch_pdf_list.append(os.path.join(root, f))
        else:
            for f in sorted(os.listdir(self.batch_folder)):
                full_path = os.path.join(self.batch_folder, f)
                if os.path.isfile(full_path) and f.lower().endswith('.pdf'):
                    self.batch_pdf_list.append(full_path)

        count = len(self.batch_pdf_list)
        self.lbl_batch_count.setText(f"{count} 个 PDF 文件")

        # 计算总页数
        total_pages = 0
        file_info_lines = []
        for pdf_path in self.batch_pdf_list:
            try:
                doc = fitz.open(pdf_path)
                pages = len(doc)
                total_pages += pages
                doc.close()
                rel_path = os.path.relpath(pdf_path, self.batch_folder)
                file_info_lines.append(f"📄 {rel_path}  ({pages} 页)")
            except Exception:
                rel_path = os.path.relpath(pdf_path, self.batch_folder)
                file_info_lines.append(f"⚠️ {rel_path}  (无法读取)")

        if file_info_lines:
            self.batch_file_list_widget.setText("\n".join(file_info_lines))
            self.lbl_batch_count.setText(f"{count} 个 PDF 文件，共 {total_pages} 页")
        else:
            self.batch_file_list_widget.setText("未找到 PDF 文件")

        self.lbl_info.setText(
            f"📁 {os.path.basename(self.batch_folder)}  ·  {count} 个 PDF  ·  共 {total_pages} 页"
        )

        # 清空预览区（批量模式不展示预览）
        while self.preview_grid.count():
            item = self.preview_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.preview_pixmaps.clear()

        # 在预览区域显示提示
        hint_label = QLabel(f"📁 批量模式\n\n已扫描到 {count} 个 PDF 文件\n共 {total_pages} 页将被转换为图片\n\n每个 PDF 将在输出目录中\n创建同名子文件夹")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("font-size: 15px; color: #6c7086; padding: 40px; border: none; background: transparent;")
        self.preview_grid.addWidget(hint_label, 0, 0)

    def _on_dpi_changed(self, value):
        self.lbl_dpi.setText(f"{value} DPI")

    def _on_preview_size_changed(self, value):
        self.lbl_preview_size.setText(f"{value} px")
        self._refresh_thumbnails(value)

    def _refresh_thumbnails(self, thumb_size):
        """仅更新缩略图尺寸，不重新渲染"""
        cols = max(1, (self.scroll_area.width() - 40) // (thumb_size + 20))

        widgets = []
        while self.preview_grid.count():
            item = self.preview_grid.takeAt(0)
            w = item.widget()
            if w:
                widgets.append(w)

        for idx, container in enumerate(widgets):
            # 找到 ClickableLabel
            layout = container.layout()
            if layout and layout.count() > 0:
                lbl_widget = layout.itemAt(0).widget()
                if isinstance(lbl_widget, ClickableLabel) and idx < len(self.preview_pixmaps):
                    thumb = self.preview_pixmaps[idx].scaled(
                        thumb_size, thumb_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    lbl_widget.setPixmap(thumb)

            row, col = divmod(idx, cols)
            self.preview_grid.addWidget(container, row, col)

    # ─── 执行导出 ────────────────────────────
    def _execute(self):
        mode = self.param_stack.currentIndex()

        if mode == 0:
            # 转图片（单文件）
            if not self.pdf_path:
                QMessageBox.warning(self, "提示", "请先加载一个 PDF 文件")
                return

            output_dir = QFileDialog.getExistingDirectory(
                self, "选择图片保存目录", str(Path.home() / "Desktop")
            )
            if not output_dir:
                return

            dpi = self.dpi_slider.value()
            self.btn_execute.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.lbl_status.setText("正在导出图片...")

            self.worker = PdfToImageWorker(self.pdf_path, output_dir, dpi)
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(self._on_img_finished)
            self.worker.error.connect(self._on_error)
            self.worker.start()

        elif mode == 1:
            # 截取 PDF
            if not self.pdf_path:
                QMessageBox.warning(self, "提示", "请先加载一个 PDF 文件")
                return

            start = self.spin_start.value()
            end = self.spin_end.value()
            if start > end:
                QMessageBox.warning(self, "提示", "起始页码不能大于结束页码")
                return

            pdf_name = Path(self.pdf_path).stem
            default_name = f"{pdf_name}_p{start}-{end}.pdf"
            output_path, _ = QFileDialog.getSaveFileName(
                self, "保存截取的 PDF",
                str(Path.home() / "Desktop" / default_name),
                "PDF 文件 (*.pdf)"
            )
            if not output_path:
                return

            self.btn_execute.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.lbl_status.setText("正在截取页面...")

            self.worker = PdfExtractWorker(self.pdf_path, output_path, start, end)
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(self._on_pdf_finished)
            self.worker.error.connect(self._on_error)
            self.worker.start()

        elif mode == 2:
            # 批量转图片
            if not self.batch_pdf_list:
                QMessageBox.warning(self, "提示", "未找到 PDF 文件，请先选择包含 PDF 的文件夹")
                return

            output_dir = QFileDialog.getExistingDirectory(
                self, "选择图片保存目录", str(Path.home() / "Desktop")
            )
            if not output_dir:
                return

            dpi = self.batch_dpi_slider.value()
            self.btn_execute.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.lbl_status.setText("正在批量转换...")

            self.worker = BatchPdfToImageWorker(self.batch_pdf_list, output_dir, dpi)
            self.worker.progress.connect(self._on_batch_progress)
            self.worker.finished.connect(self._on_batch_finished)
            self.worker.error.connect(self._on_error)
            self.worker.start()

    def _on_progress(self, current, total):
        pct = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"处理中... {current}/{total}")

    def _on_img_finished(self, output_dir):
        self.btn_execute.setEnabled(True)
        self.progress_bar.setValue(100)
        self.lbl_status.setText(f"✅ 图片已导出到: {output_dir}")

        reply = QMessageBox.question(
            self, "导出完成",
            f"图片已成功导出到:\n{output_dir}\n\n是否在 Finder 中打开？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            os.system(f'open "{output_dir}"')

    def _on_batch_progress(self, current, total, current_file):
        pct = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"批量转换中... {current}/{total}  —  {current_file}")

    def _on_batch_finished(self, output_dir, file_count, total_images):
        self.btn_execute.setEnabled(True)
        self.progress_bar.setValue(100)
        self.lbl_status.setText(
            f"✅ 批量转换完成！{file_count} 个 PDF → {total_images} 张图片"
        )

        reply = QMessageBox.question(
            self, "批量转换完成",
            f"已将 {file_count} 个 PDF 文件转换为 {total_images} 张图片\n\n"
            f"保存目录: {output_dir}\n"
            f"（每个 PDF 在独立子文件夹中）\n\n是否在 Finder 中打开？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            os.system(f'open "{output_dir}"')

    def _on_pdf_finished(self, output_path):
        self.btn_execute.setEnabled(True)
        self.progress_bar.setValue(100)
        self.lbl_status.setText(f"✅ PDF 已保存: {output_path}")

        reply = QMessageBox.question(
            self, "截取完成",
            f"PDF 已成功保存到:\n{output_path}\n\n是否在 Finder 中打开？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            os.system(f'open -R "{output_path}"')

    def _on_error(self, msg):
        self.btn_execute.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(f"❌ 错误: {msg}")
        QMessageBox.critical(self, "错误", f"处理失败:\n{msg}")

    def closeEvent(self, event):
        if self.pdf_doc:
            self.pdf_doc.close()
        super().closeEvent(event)


# ──────────────────────────────────────────────
#  入口
# ──────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PDFKing")

    # macOS 特殊处理：接受 Finder 拖入的文件
    if sys.platform == 'darwin':
        app.setStyle('Fusion')

    window = PDFKingWindow()
    window.show()

    # 如果从命令行传入了 PDF 文件路径
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path) and path.lower().endswith('.pdf'):
            window._on_file_loaded(path)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
