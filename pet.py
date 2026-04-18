import sys
import random
from datetime import date, datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsColorizeEffect,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QPixmap, QScreen
from services import DouyinSummaryPipeline
from storage import DouyinLinkStore, PetGrowthStore, SummaryStore
from ui import SavedLinksDialog, SummaryDialog

# 桌面宠物类
class DesktopPet(QMainWindow):
    PET_IMAGE_PATH = Path("Animations") / "Images" / "ComfyUI_00094_.png"
    WEB_HOME_PAGE = Path("web") / "index.html"
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
        self.link_store = DouyinLinkStore(Path("data") / "douyin_links.json")
        self.summary_store = SummaryStore(Path("data") / "video_summaries.json")
        self.growth_store = PetGrowthStore(Path("data") / "pet_growth.json")
        self.growth_state = self.growth_store.load_state()
        self.summary_pipeline = DouyinSummaryPipeline()

        self.base_pet_pixmap = self.load_base_pet_image()
        self.pet_pixmap = self.load_scaled_pet_image(self.current_level_config()["size"])
        self.init_window()
        self.move_to_bottom_right()

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setCentralWidget(self.label)

        self.color_effect = QGraphicsColorizeEffect(self.label)
        self.label.setGraphicsEffect(self.color_effect)
        self.refresh_pet_appearance()

    def init_window(self):
        self.setWindowTitle("樱小宠")
        self.setFixedSize(self.pet_pixmap.size())
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

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
        return self.base_pet_pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def refresh_pet_appearance(self):
        level = self.current_level_config()
        self.pet_pixmap = self.load_scaled_pet_image(level["size"])
        self.label.setPixmap(self.pet_pixmap)
        self.setFixedSize(self.pet_pixmap.size())
        self.color_effect.setColor(QColor(level["color"]))
        self.color_effect.setStrength(0.25 + (level["level"] - 1) * 0.08)
        self.setWindowTitle(f"樱小宠 Lv{level['level']} · {level['title']}")
        self.setToolTip(
            f"等级: Lv{level['level']} {level['title']}\n"
            f"经验值: {self.growth_state['exp']}\n"
            f"连续打卡: {self.growth_state['streak_days']} 天"
        )

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
        elif event.button() == Qt.MouseButton.RightButton:
            self.drag_pos = None
            self.show_context_menu(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = None

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        growth_panel_action = QAction("查看成长面板", self)
        corner_log_action = QAction("记录被忽视角落 (+10)", self)
        passion_action = QAction("热爱打卡 (+15起)", self)
        future_action = QAction("生成三年后寄语", self)
        open_web_action = QAction("打开成长主页", self)
        add_link_action = QAction("输入抖音链接", self)
        summarize_action = QAction("生成视频总结", self)
        view_links_action = QAction("查看已保存链接", self)
        exit_action = QAction("退出", self)

        growth_panel_action.triggered.connect(self.show_growth_panel)
        corner_log_action.triggered.connect(self.add_corner_log)
        passion_action.triggered.connect(self.add_passion_task)
        future_action.triggered.connect(self.generate_future_message)
        open_web_action.triggered.connect(self.open_growth_web_page)
        add_link_action.triggered.connect(self.add_douyin_link)
        summarize_action.triggered.connect(self.generate_video_summary)
        view_links_action.triggered.connect(self.show_saved_links)
        exit_action.triggered.connect(self.close)

        menu.addAction(growth_panel_action)
        menu.addAction(corner_log_action)
        menu.addAction(passion_action)
        menu.addAction(future_action)
        menu.addAction(open_web_action)
        menu.addSeparator()
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

    def add_corner_log(self):
        corner_name, ok = QInputDialog.getText(self, "记录角落", "角落名称（例如：老教学楼侧门小路）：")
        if not ok:
            return
        corner_name = corner_name.strip()
        if not corner_name:
            QMessageBox.warning(self, "输入无效", "角落名称不能为空。")
            return

        categories = ["设施问题", "人文故事", "安静学习点", "情绪治愈地", "其他"]
        category, ok = QInputDialog.getItem(self, "角落分类", "请选择分类：", categories, 0, False)
        if not ok:
            return

        feeling, ok = QInputDialog.getText(self, "补充描述", "你想对这个角落说什么（可选）：")
        if not ok:
            return

        self.growth_state["corner_logs"].append(
            {
                "corner_name": corner_name,
                "category": category,
                "feeling": feeling.strip(),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.growth_state["corner_logs"] = self.growth_state["corner_logs"][-80:]
        result = self.apply_growth(exp_gain=10)
        QMessageBox.information(
            self,
            "记录完成",
            self.build_growth_message("已记录你的角落观察，成长值 +10。", result),
        )

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
