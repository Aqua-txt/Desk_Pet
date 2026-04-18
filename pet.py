import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
)
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtCore import Qt
from services import DouyinSummaryPipeline
from storage import DouyinLinkStore, SummaryStore
from ui import SavedLinksDialog, SummaryDialog

# 桌面宠物类
class DesktopPet(QMainWindow):
    PET_IMAGE_PATH = Path("Animations") / "Images" / "ComfyUI_00094_.png"
    PET_SIZE = 128

    def __init__(self):
        super().__init__()
        # 拖动偏移量，按下左键时记录，松开时清空
        self.drag_pos = None
        # 加载桌宠形象
        self.pet_pixmap = self.load_pet_image()
        # 初始化窗口
        self.init_window()
        # 初始化链接存储
        self.link_store = DouyinLinkStore(Path("data") / "douyin_links.json")
        self.summary_store = SummaryStore(Path("data") / "video_summaries.json")
        self.summary_pipeline = DouyinSummaryPipeline()
        # 只创建一次标签，后续仅更新图片
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 让主窗口统一处理鼠标事件，避免被 QLabel 抢占
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setCentralWidget(self.label)
        # 显示桌宠形象
        self.show_pet_image()

    # 配置窗口：无边框、透明、置顶、固定大小
    def init_window(self):
        self.setWindowTitle("桌面宠物")
        # 窗口大小（宠物图片尺寸）
        self.setFixedSize(self.pet_pixmap.size())
        # 核心设置：无边框 + 窗口置顶 + 透明背景
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |  # 去掉标题栏边框
            Qt.WindowType.WindowStaysOnTopHint   # 始终悬浮在桌面最上层
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 透明背景

    def load_pet_image(self) -> QPixmap:
        pixmap = QPixmap(str(self.PET_IMAGE_PATH))
        if pixmap.isNull():
            raise FileNotFoundError(f"未找到桌宠图片: {self.PET_IMAGE_PATH}")
        return pixmap.scaled(
            self.PET_SIZE,
            self.PET_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    # 显示桌宠形象
    def show_pet_image(self):
        self.label.setPixmap(self.pet_pixmap)

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 记录拖动起始位置
            self.drag_pos = event.globalPosition().toPoint() - self.pos()
        elif event.button() == Qt.MouseButton.RightButton:
            self.drag_pos = None
            self.show_context_menu(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = None

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        add_link_action = QAction("输入抖音链接", self)
        summarize_action = QAction("生成视频总结", self)
        view_links_action = QAction("查看已保存链接", self)
        exit_action = QAction("退出", self)

        add_link_action.triggered.connect(self.add_douyin_link)
        summarize_action.triggered.connect(self.generate_video_summary)
        view_links_action.triggered.connect(self.show_saved_links)
        exit_action.triggered.connect(self.close)

        menu.addAction(add_link_action)
        menu.addAction(summarize_action)
        menu.addAction(view_links_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        menu.exec(global_pos)

    def add_douyin_link(self):
        link, ok = QInputDialog.getText(self, "添加抖音链接", "请输入抖音视频链接：")
        if not ok:
            return

        normalized = self.link_store.extract_douyin_url(link)
        if not normalized:
            QMessageBox.warning(self, "输入无效", "请输入有效的抖音链接。")
            return

        self.link_store.save_link(link)
        QMessageBox.information(self, "保存成功", "抖音链接已保存。")

    def show_saved_links(self):
        dialog = SavedLinksDialog(self.link_store, self)
        dialog.exec()

    def generate_video_summary(self):
        raw_input, ok = QInputDialog.getText(
            self,
            "生成视频总结",
            "请输入抖音分享文案或链接：",
        )
        if not ok:
            return

        if not raw_input.strip():
            QMessageBox.warning(self, "输入无效", "输入不能为空。")
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.summary_pipeline.run(raw_input)
        except Exception as exc:
            QMessageBox.warning(self, "总结失败", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.link_store.save_link(raw_input)
        self.summary_store.add_summary(
            raw_input=result.raw_input,
            short_url=result.short_url,
            resolved_url=result.resolved_url,
            extracted_text=result.extracted_text,
            summary=result.summary,
        )

        dialog = SummaryDialog("视频总结结果", result.summary, self)
        dialog.exec()

# 主程序
if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec())
