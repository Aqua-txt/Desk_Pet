from functools import partial

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from ui.summary_dialog import SummaryDialog
from ui.theme import AnimatedButton


class SavedLinksDialog(QDialog):
    def __init__(self, link_store, summary_store, parent=None, on_learning_status_changed=None):
        super().__init__(parent)
        self.link_store = link_store
        self.summary_store = summary_store
        self.on_learning_status_changed = on_learning_status_changed
        self.setWindowTitle("已保存链接")
        self.resize(760, 420)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(
            """
            QDialog {
                background: transparent;
            }
            QWidget#Card {
                background-color: rgba(255, 241, 250, 238);
                border: 1px solid rgba(255, 182, 222, 180);
                border-radius: 18px;
            }
            QLabel {
                color: #6F4A67;
                font-size: 14px;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QWidget#RowCard {
                background: rgba(255, 255, 255, 210);
                border: 1px solid rgba(255, 196, 229, 170);
                border-radius: 12px;
            }
            """
        )

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        self.card = QWidget(self)
        self.card.setObjectName("Card")
        outer_layout.addWidget(self.card)

        self.main_layout = QVBoxLayout(self.card)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(10)

        self.tip_label = QLabel(
            "点击链接可打开抖音；可切换已学习状态；点击“总结视频内容”可查看已生成总结。",
            self,
        )
        self.main_layout.addWidget(self.tip_label)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        row.setObjectName("RowCard")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 8, 8, 8)
        row_layout.setSpacing(8)

        record_index = record["index"]
        url = record["url"]
        display_text = record.get("display_text", url)
        learned = bool(record.get("learned", False))
        created_at = record.get("created_at", "")
        button_text = display_text if len(display_text) <= 24 else f"{display_text[:24]}..."
        if created_at:
            short_date = created_at[:10]
            button_text = f"{button_text}  ({short_date})"

        open_button = AnimatedButton(button_text, role="soft", parent=row)
        open_button.setToolTip(f"{display_text}\n{url}")
        open_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        open_button.setMinimumWidth(220)
        open_button.setMaximumWidth(340)
        open_button.clicked.connect(partial(self.open_link, url))

        summary_button = AnimatedButton("总结视频内容", role="soft", parent=row)
        summary_button.setFixedWidth(112)
        summary_button.clicked.connect(partial(self.show_summary, url))

        learn_button_text = "已学习" if learned else "未学习"
        learn_button_role = "soft" if learned else "primary"
        learn_button = AnimatedButton(learn_button_text, role=learn_button_role, parent=row)
        learn_button.setFixedWidth(82)
        learn_button.clicked.connect(partial(self.toggle_learned, record_index, learned))

        delete_button = AnimatedButton("删除", role="danger", parent=row)
        delete_button.setFixedWidth(66)
        delete_button.setStyleSheet(
            delete_button.styleSheet()
            + "QPushButton {text-align: center; padding: 8px 0px;}"
        )
        delete_button.clicked.connect(partial(self.delete_link, record_index))

        row_layout.addWidget(open_button, 1)
        row_layout.addWidget(learn_button, 0)
        row_layout.addWidget(summary_button, 0)
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
        if callable(self.on_learning_status_changed):
            self.on_learning_status_changed()
        self.refresh_links()

    def toggle_learned(self, index: int, current: bool):
        ok = self.link_store.set_learned(index, not current)
        if not ok:
            QMessageBox.warning(self, "更新失败", "学习状态更新失败，请稍后重试。")
            return
        if callable(self.on_learning_status_changed):
            self.on_learning_status_changed()
        self.refresh_links()

    def show_summary(self, url: str):
        normalized = self.link_store.extract_douyin_url(url)
        if not normalized:
            QMessageBox.warning(self, "查看失败", "该链接无效，无法读取总结。")
            return

        record = self.summary_store.get_summary_by_short_url(normalized)
        if not record:
            QMessageBox.information(self, "暂无总结", "该视频暂未生成总结，请重新保存该链接后再试。")
            return

        summary_content = str(record.get("summary", "")).strip()
        if not summary_content:
            QMessageBox.information(self, "暂无总结", "该视频总结内容为空。")
            return

        summary_time = record.get("updated_at") or record.get("created_at", "未知时间")
        dialog = SummaryDialog(
            "视频总结",
            summary_content,
            self,
            meta_lines=[
                f"链接：{normalized}",
                f"更新时间：{summary_time}",
            ],
        )
        dialog.exec()
