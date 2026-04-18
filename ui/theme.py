from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QVariantAnimation
from PyQt6.QtWidgets import QApplication, QPushButton


def apply_global_theme(app: QApplication) -> None:
    app.setStyleSheet(
        """
        QMenu {
            background-color: rgba(20, 24, 40, 230);
            color: #EAF1FF;
            border: 1px solid rgba(112, 135, 214, 140);
            border-radius: 10px;
            padding: 6px;
        }
        QMenu::item {
            padding: 8px 18px;
            border-radius: 8px;
            margin: 2px 4px;
        }
        QMenu::item:selected {
            background-color: rgba(90, 120, 220, 170);
        }
        QMessageBox {
            background-color: rgba(16, 20, 34, 245);
        }
        QMessageBox QLabel {
            color: #F3F6FF;
        }
        QInputDialog {
            background-color: rgba(16, 20, 34, 245);
        }
        QInputDialog QLabel {
            color: #F3F6FF;
        }
        QInputDialog QLineEdit {
            border: 1px solid rgba(120, 145, 230, 150);
            border-radius: 8px;
            padding: 8px 10px;
            background: rgba(25, 31, 52, 230);
            color: #EEF2FF;
            selection-background-color: rgba(97, 131, 255, 170);
        }
        """
    )


class AnimatedButton(QPushButton):
    ROLE_STYLES = {
        "primary": {
            "normal_bg": "rgba(72, 104, 210, 170)",
            "hover_bg": "rgba(93, 127, 245, 220)",
            "normal_border": "rgba(139, 164, 255, 180)",
            "hover_border": "rgba(172, 191, 255, 230)",
        },
        "danger": {
            "normal_bg": "rgba(180, 68, 86, 165)",
            "hover_bg": "rgba(222, 89, 112, 215)",
            "normal_border": "rgba(255, 163, 175, 180)",
            "hover_border": "rgba(255, 196, 205, 230)",
        },
        "soft": {
            "normal_bg": "rgba(36, 44, 72, 210)",
            "hover_bg": "rgba(58, 70, 112, 230)",
            "normal_border": "rgba(116, 138, 220, 150)",
            "hover_border": "rgba(158, 178, 255, 205)",
        },
    }

    def __init__(self, text: str, role: str = "primary", parent=None):
        super().__init__(text, parent)
        self.role = role if role in self.ROLE_STYLES else "primary"
        self.setCursor(self.cursor().shape().PointingHandCursor)
        self.setMinimumHeight(38)

        self._is_hovered = False
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation.valueChanged.connect(self._apply_progress_style)
        self._apply_progress_style(0.0)

    def enterEvent(self, event):
        self._start_hover_animation(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._start_hover_animation(False)
        super().leaveEvent(event)

    def _start_hover_animation(self, hovered: bool):
        if self._is_hovered == hovered:
            return
        self._is_hovered = hovered
        self._animation.stop()
        self._animation.setStartValue(1.0 if not hovered else 0.0)
        self._animation.setEndValue(1.0 if hovered else 0.0)
        self._animation.start()

    def _apply_progress_style(self, progress):
        value = float(progress)
        style = self.ROLE_STYLES[self.role]
        bg = style["hover_bg"] if value >= 0.5 else style["normal_bg"]
        border = style["hover_border"] if value >= 0.5 else style["normal_border"]
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
                color: #F8FBFF;
                font-weight: 600;
                text-align: left;
                padding: 8px 12px;
            }}
            QPushButton:pressed {{
                background-color: rgba(50, 71, 145, 230);
            }}
            """
        )
