import sys
from datetime import date
import os
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QAction, QDesktopServices, QPixmap
from PyQt6.QtCore import Qt, QUrl, QUrlQuery
from services.doubao_summary_service import load_dotenv_file
from services import DouyinSummaryPipeline
from storage import DouyinLinkStore, PetGrowthStore, SummaryStore
from ui import SavedLinksDialog

# 桌面宠物类
class DesktopPet(QMainWindow):
    PET_IMAGES_DIR = Path("Animations") / "Images"
    WEB_HOME_PAGE = Path("web") / "index.html"
    WEB_GROWTH_PANEL_PAGE = Path("web") / "growth_panel.html"
    WEB_CORNER_LOG_PAGE = Path("web") / "corner_log.html"
    WEB_PASSION_CHECKIN_PAGE = Path("web") / "passion_checkin.html"
    WEB_FUTURE_MESSAGE_PAGE = Path("web") / "future_message.html"
    WEB_FALLBACK_URL = "https://www.wuhanuniversity.edu.cn/"
    LEVEL_CONFIGS = [
        {"level": 1, "title": "初来乍到", "min_exp": 0, "size": 118, "color": "#9FB3D9"},
        {"level": 2, "title": "有点期待", "min_exp": 30, "size": 128, "color": "#7DC2FF"},
        {"level": 3, "title": "热爱上头", "min_exp": 80, "size": 138, "color": "#77E1B2"},
        {"level": 4, "title": "角落守护者", "min_exp": 150, "size": 146, "color": "#FFD27D"},
        {"level": 5, "title": "未来引路人", "min_exp": 240, "size": 156, "color": "#FF9CB9"},
    ]

    def __init__(self):
        super().__init__()
        self.drag_pos = None
        self.press_pos = None
        self.link_store = DouyinLinkStore(Path("data") / "douyin_links.json")
        self.summary_store = SummaryStore(Path("data") / "video_summaries.json")
        self.growth_store = PetGrowthStore(Path("data") / "pet_growth.json")
        self.growth_state = self.growth_store.load_state()
        self.summary_pipeline = DouyinSummaryPipeline()

        self.pet_frames = self.load_pet_frames()
        self.current_pet_index = 0
        self.pet_pixmap = self.load_scaled_pet_image(self.current_level_config()["size"])
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.label.setStyleSheet("background: transparent; border: none;")
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 85);
                border-radius: 4px;
                background: rgba(20, 24, 35, 150);
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #66ccff, stop:1 #4f7bff
                );
            }
            """
        )
        self.level_label = QLabel(self)
        self.level_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.level_label.setStyleSheet(
            "color: #EAF0FF; font-size: 12px; font-weight: bold; background: transparent;"
        )

        self.panel = QWidget(self)
        self.panel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(4)
        panel_layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.progress_bar)
        panel_layout.addWidget(self.level_label, alignment=Qt.AlignmentFlag.AlignRight)
        self.setCentralWidget(self.panel)

        self.init_window()
        self.refresh_pet_appearance()
        self.refresh_learning_ui()

    def init_window(self):
        self.setWindowTitle("樱小宠")
        self.update_window_size()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def load_pet_frames(self) -> list[QPixmap]:
        frames: list[tuple[int, QPixmap]] = []
        for image_path in self.PET_IMAGES_DIR.glob("ComfyUI_*.png"):
            match = re.fullmatch(r"ComfyUI_(\d+)\.png", image_path.name)
            if not match:
                continue

            order = int(match.group(1))
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                continue
            frames.append((order, pixmap))

        if not frames:
            raise FileNotFoundError(
                f"未找到可用桌宠图片，请检查目录：{self.PET_IMAGES_DIR}（需要 ComfyUI_1.png 这类文件）"
            )

        frames.sort(key=lambda item: item[0])
        return [pixmap for _, pixmap in frames]

    def load_scaled_pet_image(self, size: int) -> QPixmap:
        base_pixmap = self.pet_frames[self.current_pet_index]
        return base_pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def refresh_pet_appearance(self):
        level = self.current_level_config()
        self.pet_pixmap = self.load_scaled_pet_image(level["size"])
        self.label.setPixmap(self.pet_pixmap)
        self.label.setFixedSize(self.pet_pixmap.size())
        self.update_window_size()
        self.setWindowTitle(f"樱小宠 Lv{level['level']} · {level['title']}")
        self.setToolTip(
            f"等级: Lv{level['level']} {level['title']}\n"
            f"经验值: {self.growth_state['exp']}\n"
            f"连续打卡: {self.growth_state['streak_days']} 天"
        )

    def update_window_size(self):
        width = max(self.pet_pixmap.width(), 180)
        height = self.pet_pixmap.height() + 8 + 4 + 18
        self.setFixedSize(width, height)

    def refresh_learning_ui(self):
        stats = self.link_store.get_learning_stats()
        self.progress_bar.setMaximum(int(stats["progress_total"]))
        self.progress_bar.setValue(int(stats["level_progress"]))
        self.level_label.setText(f"Lv.{stats['level']}  经验 {stats['exp']}")

    def current_level_config(self) -> dict:
        exp = int(self.growth_state.get("exp", 0))
        current = self.LEVEL_CONFIGS[0]
        for cfg in self.LEVEL_CONFIGS:
            if exp >= cfg["min_exp"]:
                current = cfg
            else:
                break
        return current

    def next_level_config(self) -> dict | None:
        current_level = self.current_level_config()["level"]
        for cfg in self.LEVEL_CONFIGS:
            if cfg["level"] == current_level + 1:
                return cfg
        return None

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.pos()
            self.press_pos = event.globalPosition().toPoint()
        elif event.button() == Qt.MouseButton.RightButton:
            self.drag_pos = None
            self.show_context_menu(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            release_pos = event.globalPosition().toPoint()
            if self.press_pos is not None and (release_pos - self.press_pos).manhattanLength() <= 4:
                self.switch_to_next_pet_image()
            self.drag_pos = None
            self.press_pos = None

    def switch_to_next_pet_image(self):
        self.current_pet_index = (self.current_pet_index + 1) % len(self.pet_frames)
        self.refresh_pet_appearance()

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        growth_panel_action = QAction("查看成长面板", self)
        corner_log_action = QAction("记录被忽视角落 (+10)", self)
        passion_action = QAction("热爱打卡 (+15起)", self)
        future_action = QAction("生成三年后寄语", self)
        open_web_action = QAction("打开成长主页", self)
        add_link_action = QAction("输入抖音链接", self)
        view_links_action = QAction("查看已保存链接", self)
        exit_action = QAction("退出", self)

        growth_panel_action.triggered.connect(self.show_growth_panel)
        corner_log_action.triggered.connect(self.add_corner_log)
        passion_action.triggered.connect(self.add_passion_task)
        future_action.triggered.connect(self.generate_future_message)
        open_web_action.triggered.connect(self.open_growth_web_page)
        add_link_action.triggered.connect(self.add_douyin_link)
        view_links_action.triggered.connect(self.show_saved_links)
        exit_action.triggered.connect(self.close)

        menu.addAction(growth_panel_action)
        menu.addAction(corner_log_action)
        menu.addAction(passion_action)
        menu.addAction(future_action)
        menu.addAction(open_web_action)
        menu.addSeparator()
        menu.addAction(add_link_action)
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

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.summary_pipeline.run(link)
            self.summary_store.add_summary(
                raw_input=result.raw_input,
                short_url=result.short_url,
                resolved_url=result.resolved_url,
                extracted_text=result.extracted_text,
                summary=result.summary,
            )
        except Exception as exc:
            QMessageBox.warning(self, "已保存链接", f"抖音链接已保存，但自动总结失败：{exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        QMessageBox.information(self, "保存成功", "抖音链接已保存，并已自动生成视频总结。")
        self.refresh_learning_ui()

    def show_saved_links(self):
        dialog = SavedLinksDialog(
            self.link_store,
            self.summary_store,
            self,
            on_learning_status_changed=self.refresh_learning_ui,
        )
        dialog.exec()

    def add_corner_log(self):
        self.open_local_web_page(self.WEB_CORNER_LOG_PAGE)

    def add_passion_task(self):
        self.open_local_web_page(self.WEB_PASSION_CHECKIN_PAGE)

    def apply_growth(self, exp_gain: int) -> dict:
        level_before = self.current_level_config()["level"]
        penalty_applied, streak_bonus = self.update_streak_and_penalty()
        self.growth_state["exp"] = max(0, int(self.growth_state["exp"]) + exp_gain + streak_bonus)
        self.growth_store.save_state(self.growth_state)
        self.refresh_pet_appearance()

        level_after = self.current_level_config()["level"]
        return {
            "penalty_applied": penalty_applied,
            "streak_bonus": streak_bonus,
            "leveled_up": level_after > level_before,
            "level_after": level_after,
        }

    def update_streak_and_penalty(self) -> tuple[bool, int]:
        today = date.today()
        last_active = str(self.growth_state.get("last_active_date", "") or "").strip()
        penalty_applied = False
        streak_bonus = 0

        if not last_active:
            self.growth_state["streak_days"] = 1
        else:
            try:
                last_day = date.fromisoformat(last_active)
            except ValueError:
                last_day = today

            day_diff = (today - last_day).days
            if day_diff <= 0:
                pass
            elif day_diff == 1:
                self.growth_state["streak_days"] = int(self.growth_state["streak_days"]) + 1
            else:
                self.growth_state["exp"] = max(0, int(self.growth_state["exp"]) - 5)
                self.growth_state["streak_days"] = 1
                penalty_applied = True

            if day_diff > 0 and int(self.growth_state["streak_days"]) % 3 == 0:
                streak_bonus = 5

        self.growth_state["last_active_date"] = today.isoformat()
        return penalty_applied, streak_bonus

    def build_growth_message(self, headline: str, result: dict) -> str:
        lines = [headline]
        if result["streak_bonus"] > 0:
            lines.append(f"连续打卡奖励 +{result['streak_bonus']}。")
        if result["penalty_applied"]:
            lines.append("检测到长时间未互动，已触发 -5 衰减后重新起步。")
        if result["leveled_up"]:
            current = self.current_level_config()
            lines.append(f"恭喜升级到 Lv{current['level']}：{current['title']}！")
        lines.append(
            f"当前状态：Lv{self.current_level_config()['level']}，经验值 {self.growth_state['exp']}，"
            f"连续 {self.growth_state['streak_days']} 天。"
        )
        return "\n".join(lines)

    def show_growth_panel(self):
        self.open_local_web_page(self.WEB_GROWTH_PANEL_PAGE)

    def generate_future_message(self):
        self.open_local_web_page(self.WEB_FUTURE_MESSAGE_PAGE)

    def open_local_web_page(self, local_page: Path):
        page = local_page.resolve()
        if not page.exists():
            QMessageBox.warning(self, "打开失败", f"未找到网页文件：{local_page}")
            return

        target_url = QUrl.fromLocalFile(str(page))
        ok = QDesktopServices.openUrl(target_url)
        if not ok:
            QMessageBox.warning(self, "打开失败", f"无法打开网页：{target_url.toString()}")

    def open_growth_web_page(self):
        local_page = self.WEB_HOME_PAGE.resolve()
        if local_page.exists():
            target_url = QUrl.fromLocalFile(str(local_page))
        else:
            target_url = QUrl(self.WEB_FALLBACK_URL)

        ok = QDesktopServices.openUrl(target_url)
        if not ok:
            QMessageBox.warning(self, "打开失败", f"无法打开网页：{target_url.toString()}")

# 主程序
if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec())
