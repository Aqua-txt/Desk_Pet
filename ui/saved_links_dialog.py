from functools import partial

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class SavedLinksDialog(QDialog):
    def __init__(self, link_store, parent=None):
        super().__init__(parent)
        self.link_store = link_store
        self.setWindowTitle("已保存链接")
        self.resize(760, 420)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(8)

        self.tip_label = QLabel("点击链接可直接打开抖音视频，右侧可删除该记录。", self)
        self.main_layout.addWidget(self.tip_label)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)

        self.container = QWidget()
        self.rows_layout = QVBoxLayout(self.container)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.rows_layout.setSpacing(6)
        self.scroll_area.setWidget(self.container)

        self.refresh_links()

    def refresh_links(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        records = self.link_store.get_links()
        if not records:
            self.rows_layout.addWidget(QLabel("暂无已保存链接。", self))
            return

        for record in records:
            self.rows_layout.addWidget(self._build_row(record))

    def _build_row(self, record: dict) -> QWidget:
        row = QWidget(self)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        record_index = record["index"]
        url = record["url"]
        display_text = record.get("display_text", url)
        created_at = record.get("created_at", "")
        button_text = display_text if len(display_text) <= 72 else f"{display_text[:72]}..."
        if created_at:
            button_text = f"{button_text}  ({created_at})"

        open_button = QPushButton(button_text, row)
        open_button.setToolTip(f"{display_text}\n{url}")
        open_button.setStyleSheet("text-align: left; padding: 6px;")
        open_button.clicked.connect(partial(self.open_link, url))

        delete_button = QPushButton("删除", row)
        delete_button.setFixedWidth(72)
        delete_button.clicked.connect(partial(self.delete_link, record_index))

        row_layout.addWidget(open_button, 1)
        row_layout.addWidget(delete_button, 0)
        return row

    def open_link(self, url: str):
        normalized = self.link_store.extract_douyin_url(url)
        if not normalized:
            QMessageBox.warning(self, "打开失败", "链接无法打开，请检查链接格式。")
            return

        ok = QDesktopServices.openUrl(QUrl(normalized))
        if not ok:
            QMessageBox.warning(self, "打开失败", "链接无法打开，请检查链接格式。")

    def delete_link(self, index: int):
        ok = self.link_store.delete_link(index)
        if not ok:
            QMessageBox.warning(self, "删除失败", "该链接不存在或已被删除。")
            return
        self.refresh_links()
