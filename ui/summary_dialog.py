from PyQt6.QtWidgets import QDialog, QTextEdit, QVBoxLayout


class SummaryDialog(QDialog):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(780, 520)

        layout = QVBoxLayout(self)
        text_edit = QTextEdit(self)
        text_edit.setReadOnly(True)
        text_edit.setPlainText(content)
        layout.addWidget(text_edit)
