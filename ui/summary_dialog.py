from PyQt6.QtWidgets import QDialog, QLabel, QTextEdit, QVBoxLayout, QWidget


class SummaryDialog(QDialog):
    def __init__(self, title: str, content: str, parent=None, meta_lines: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 560)
        self.setStyleSheet(
            """
            QDialog {
                background: transparent;
            }
            QWidget#Card {
                background: rgba(255, 244, 251, 244);
                border: 1px solid rgba(255, 188, 225, 185);
                border-radius: 18px;
            }
            QLabel#Title {
                color: #704A6A;
                font-size: 24px;
                font-weight: 700;
            }
            QLabel#Meta {
                color: #7F5B77;
                font-size: 13px;
                line-height: 1.5;
            }
            QTextEdit {
                background: rgba(255, 255, 255, 240);
                color: #4D3850;
                border: 1px solid rgba(255, 200, 227, 180);
                border-radius: 12px;
                padding: 10px;
                font-size: 15px;
                line-height: 1.65;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)

        card = QWidget(self)
        card.setObjectName("Card")
        root_layout.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel(title, self)
        title_label.setObjectName("Title")
        layout.addWidget(title_label)

        if meta_lines:
            meta_label = QLabel("\n".join(meta_lines), self)
            meta_label.setObjectName("Meta")
            meta_label.setWordWrap(True)
            layout.addWidget(meta_label)

        text_edit = QTextEdit(self)
        text_edit.setReadOnly(True)
        text_edit.setPlainText(content)
        text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(text_edit)
