import sys
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
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QPixmap, QScreen
from services import DouyinSummaryPipeline
from storage import DouyinLinkStore, PetGrowthStore, SummaryStore
from ui import SavedLinksDialog
from web_sync_server import LocalWebServer

# 桌面宠物类
class DesktopPet(QMainWindow):
    PET_IMAGES_DIR = Path("Animations") / "Images"
    WEB_HOME_PAGE = Path("web") / "index.html"
    WEB_PASSION_CHECKIN = Path("web") / "passion-checkin.html"
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
        self.web_server = LocalWebServer(
            project_root=Path(__file__).resolve().parent,
            stats_provider=self.link_store.get_learning_stats,
        )
        self.web_server.start()

        self.pet_frames = self.load_pet_frames()
        self.current_pet_index = 0
        self.pet_pixmap = self.load_scaled_pet_image(self.current_level_config()["size"])
        self.init_window()
        self.move_to_bottom_right()

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
    def move_to_bottom_right(self, margin: int = 40):
        screen: QScreen = self.screen()
        screen_geo = screen.availableGeometry()
        pet_geo = self.geometry()
        x = screen_geo.right() - pet_geo.width() - margin
        y = screen_geo.bottom() - pet_geo.height() - margin
        self.move(x, y)

    def load_base_pet_image(self) -> QPixmap:
        pixmap = QPixmap(str(self.PET_IMAGE_PATH))
        if pixmap.isNull():
            raise FileNotFoundError(f"未找到桌宠图片: {self.PET_IMAGE_PATH}")
        return pixmap

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
        passion_action = QAction("热爱打卡 (+15起)", self)
        open_web_action = QAction("打开成长主页", self)
        add_link_action = QAction("输入抖音链接", self)
        view_links_action = QAction("查看已保存链接", self)
        exit_action = QAction("退出", self)

        passion_action.triggered.connect(lambda: self.open_web_page(self.WEB_PASSION_CHECKIN))
        open_web_action.triggered.connect(self.open_growth_web_page)
        add_link_action.triggered.connect(self.add_douyin_link)
        view_links_action.triggered.connect(self.show_saved_links)
        exit_action.triggered.connect(self.close)

        menu.addAction(passion_action)
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

    def add_passion_task(self):
        task_name, ok = QInputDialog.getText(self, "热爱打卡", "今天完成了什么热爱行动：")
        if not ok:
            return
        task_name = task_name.strip()
        if not task_name:
            QMessageBox.warning(self, "输入无效", "热爱行动不能为空。")
            return

        minutes, ok = QInputDialog.getInt(
            self,
            "投入时长",
            "本次投入分钟数：",
            value=30,
            min=10,
            max=600,
            step=10,
        )
        if not ok:
            return

        note, ok = QInputDialog.getText(self, "行动备注", "本次收获（可选）：")
        if not ok:
            return

        dynamic_bonus = min((minutes // 30) * 2, 10)
        exp_gain = 15 + dynamic_bonus
        self.growth_state["passion_tasks"].append(
            {
                "task_name": task_name,
                "minutes": minutes,
                "note": note.strip(),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.growth_state["passion_tasks"] = self.growth_state["passion_tasks"][-120:]
        result = self.apply_growth(exp_gain=exp_gain)
        QMessageBox.information(
            self,
            "打卡成功",
            self.build_growth_message(f"热爱行动已打卡，成长值 +{exp_gain}。", result),
        )

    def apply_growth(self, exp_gain: int) -> dict:
        level_before = self.current_level_config()["level"]
        penalty_applied, streak_bonus = self.update_streak_and_penalty()
        self.growth_state["exp"] = max(0, int(self.growth_state["exp"]) + exp_gain + streak_bonus)
        self.growth_store.save_state(self.growth_state)
        self.refresh_pet_appearance()
        self.move_to_bottom_right()

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
        current = self.current_level_config()
        next_level = self.next_level_config()
        corner_count = len(self.growth_state["corner_logs"])
        passion_count = len(self.growth_state["passion_tasks"])
        message_count = len(self.growth_state["future_messages"])
        latest_corner = self.growth_state["corner_logs"][-1]["corner_name"] if corner_count else "暂无"
        latest_passion = self.growth_state["passion_tasks"][-1]["task_name"] if passion_count else "暂无"

        lines = [
            f"当前等级：Lv{current['level']} · {current['title']}",
            f"经验值：{self.growth_state['exp']}",
            f"连续打卡：{self.growth_state['streak_days']} 天",
        ]
        if next_level:
            remaining = max(0, int(next_level["min_exp"]) - int(self.growth_state["exp"]))
            lines.append(f"距离 Lv{next_level['level']} 还差：{remaining} 经验值")
        else:
            lines.append("已达到最高等级，继续打卡可维持光芒状态。")

        lines.extend(
            [
                "",
                f"角落记录数：{corner_count}",
                f"热爱打卡数：{passion_count}",
                f"未来寄语数：{message_count}",
                "",
                f"最近角落：{latest_corner}",
                f"最近热爱：{latest_passion}",
            ]
        )
        dialog = SummaryDialog("樱小宠成长面板", "\n".join(lines), self)
        dialog.exec()

    def generate_future_message(self):
        current = self.current_level_config()
        latest_corner = self.growth_state["corner_logs"][-1]["corner_name"] if self.growth_state["corner_logs"] else "武大某个还没被点亮的角落"
        latest_passion = self.growth_state["passion_tasks"][-1]["task_name"] if self.growth_state["passion_tasks"] else "你真正热爱的事情"
        streak = int(self.growth_state["streak_days"])

        templates = [
            "三年后的你会记得今天在「{corner}」的观察，因为那是你把热爱「{passion}」变成长期行动的起点。",
            "未来的你想对现在说：继续在「{corner}」发现问题并行动，你在「{passion}」上的坚持会成为核心竞争力。",
            "如果把这份热爱坚持三年，你会在武汉大学留下自己的坐标：从「{corner}」出发，用「{passion}」影响更多人。",
            "三年后的你正在感谢今天的你：没有忽视「{corner}」，也没有放弃「{passion}」。",
        ]
        tail = (
            f"\n\n成长建议：保持连续打卡，当前已坚持 {streak} 天。"
            if streak
            else "\n\n成长建议：先从连续 3 天小目标开始。"
        )
        message = random.choice(templates).format(corner=latest_corner, passion=latest_passion) + tail

        self.growth_state["future_messages"].append(
            {
                "content": message,
                "level": current["level"],
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.growth_state["future_messages"] = self.growth_state["future_messages"][-50:]
        self.growth_store.save_state(self.growth_state)

        dialog = SummaryDialog("三年后的自己 · 寄语", message, self)
        dialog.exec()

    def open_web_page(self, page_path: Path):
        target_url = QUrl.fromLocalFile(str(page_path.resolve()))
        if self.web_server.running:
            target_url = QUrl(self.web_server.build_url(str(page_path)))
        elif not page_path.exists():
            target_url = QUrl(self.WEB_FALLBACK_URL)
        ok = QDesktopServices.openUrl(target_url)
        if not ok:
            QMessageBox.warning(self, "打开失败", f"无法打开网页：{target_url.toString()}")

    def open_growth_web_page(self):
        self.open_web_page(self.WEB_HOME_PAGE)

    def closeEvent(self, event):
        try:
            self.web_server.stop()
        finally:
            super().closeEvent(event)

# 主程序
if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec())
