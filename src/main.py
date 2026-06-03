"""
課題管理アプリ - 大学生向け
Flet を使ったデスクトップアプリです。
課題の登録・完了管理・フィルター・締切順ソートができます。
データは tasks.json に保存・読み込みされます。
"""

import json
import os
from datetime import datetime
import flet as ft

# データ保存先ファイル（アプリと同じディレクトリに作成されます）
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "tasks.json")

# 優先度の選択肢
PRIORITY_OPTIONS = ["高", "中", "低"]

# 優先度ごとの表示色
PRIORITY_COLORS = {
    "高": ft.Colors.RED_400,
    "中": ft.Colors.ORANGE_400,
    "低": ft.Colors.GREEN_400,
}


def load_tasks() -> list[dict]:
    """tasks.json からタスク一覧を読み込む。ファイルがなければ空リストを返す。"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_tasks(tasks: list[dict]) -> None:
    """タスク一覧を tasks.json に保存する。"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


class TaskItem(ft.Container):
    """1件の課題を表すウィジェット"""

    def __init__(self, task: dict, on_toggle, on_delete):
        super().__init__()
        self.task = task          # {"name", "subject", "deadline", "priority", "done"}
        self.on_toggle = on_toggle
        self.on_delete = on_delete

        # 締切の表示（過ぎていれば赤色）
        deadline_str = task.get("deadline", "")
        deadline_color = ft.Colors.BLACK
        if deadline_str:
            try:
                dl = datetime.strptime(deadline_str, "%Y-%m-%d")
                if not task["done"] and dl.date() < datetime.today().date():
                    deadline_color = ft.Colors.RED
            except ValueError:
                pass

        priority = task.get("priority", "中")

        self.padding = ft.padding.symmetric(horizontal=8, vertical=4)
        self.border = ft.border.all(1, ft.Colors.GREY_300)
        self.border_radius = 8
        self.margin = ft.margin.only(bottom=6)

        # 完了チェックボックス
        self.checkbox = ft.Checkbox(
            value=task["done"],
            on_change=self._toggle,
        )

        self.content = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                # 左側：チェックボックス＋課題情報
                ft.Row(
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self.checkbox,
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(
                                    task["name"],
                                    weight=ft.FontWeight.BOLD,
                                    # 完了済みなら薄くする
                                    color=ft.Colors.GREY_500 if task["done"] else ft.Colors.BLACK,
                                ),
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Text(f"📚 {task.get('subject', '')}", size=12),
                                        ft.Text(
                                            f"📅 {deadline_str}" if deadline_str else "📅 締切なし",
                                            size=12,
                                            color=deadline_color,
                                        ),
                                        ft.Container(
                                            content=ft.Text(
                                                priority, size=11, color=ft.Colors.WHITE
                                            ),
                                            bgcolor=PRIORITY_COLORS.get(priority, ft.Colors.GREY),
                                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                            border_radius=4,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                # 右側：削除ボタン
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.GREY_500,
                    tooltip="削除",
                    on_click=self._delete,
                ),
            ],
        )

    def _toggle(self, e):
        self.task["done"] = e.control.value
        self.on_toggle()

    def _delete(self, e):
        self.on_delete(self.task)


class AssignmentApp(ft.Column):
    """課題管理アプリ本体"""

    def build(self):
        # --- データ読み込み ---
        self.task_data: list[dict] = load_tasks()

        # --- 入力フォーム ---
        self.input_name = ft.TextField(label="課題名", expand=True)
        self.input_subject = ft.TextField(label="科目名", width=160)
        self.input_deadline = ft.TextField(
            label="締切日（例：2025-06-30）", width=200, hint_text="YYYY-MM-DD"
        )
        self.input_priority = ft.Dropdown(
            label="優先度",
            width=100,
            value="中",
            options=[ft.dropdown.Option(p) for p in PRIORITY_OPTIONS],
        )

        # --- フィルタータブ ---
        self.filter_tabs = ft.Tabs(
            selected_index=0,
            on_change=lambda e: self._refresh(),
            tabs=[
                ft.Tab(label="すべて"),
                ft.Tab(label="未完了"),
                ft.Tab(label="完了済み"),
            ],
        )

        # --- ソートボタン ---
        self.sort_btn = ft.TextButton(
            "締切が近い順に並び替え",
            icon=ft.Icons.SORT,
            on_click=self._sort_by_deadline,
        )

        # --- タスク一覧表示エリア ---
        self.task_list = ft.Column(spacing=0)

        # --- 件数表示 ---
        self.count_text = ft.Text("")

        self.width = 680
        self.spacing = 12
        self.controls = [
            # タイトル
            ft.Row(
                [ft.Text("📝 課題管理アプリ", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),

            # 入力フォーム（課題名）
            ft.Row(controls=[self.input_name]),

            # 入力フォーム（科目・締切・優先度）
            ft.Row(
                controls=[self.input_subject, self.input_deadline, self.input_priority],
                wrap=True,
            ),

            # 追加ボタン
            ft.Row(
                controls=[
                    ft.ElevatedButton(
                        "課題を追加",
                        icon=ft.Icons.ADD,
                        on_click=self._add_task,
                    )
                ],
            ),

            ft.Divider(),

            # フィルター＋ソート
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[self.filter_tabs, self.sort_btn],
            ),

            # 件数
            self.count_text,

            # タスク一覧
            self.task_list,
        ]

        # 初回表示
        self._refresh()

    # ------------------------------------------------------------------ #
    #  内部メソッド
    # ------------------------------------------------------------------ #

    def _add_task(self, e):
        """フォームの値で新しい課題を追加する"""
        name = self.input_name.value.strip()
        if not name:
            # 課題名が空なら何もしない
            self.input_name.error_text = "課題名を入力してください"
            self.input_name.update()
            return

        # 締切日のフォーマットチェック
        deadline = self.input_deadline.value.strip()
        if deadline:
            try:
                datetime.strptime(deadline, "%Y-%m-%d")
            except ValueError:
                self.input_deadline.error_text = "YYYY-MM-DD 形式で入力してください"
                self.input_deadline.update()
                return
        self.input_deadline.error_text = None

        # 新規タスクを追加
        self.task_data.append({
            "name": name,
            "subject": self.input_subject.value.strip(),
            "deadline": deadline,
            "priority": self.input_priority.value or "中",
            "done": False,
        })

        save_tasks(self.task_data)

        # フォームをリセット
        self.input_name.value = ""
        self.input_name.error_text = None
        self.input_subject.value = ""
        self.input_deadline.value = ""
        self.input_priority.value = "中"

        self._refresh()

    def _delete_task(self, task: dict):
        """指定したタスクを削除する"""
        self.task_data = [t for t in self.task_data if t is not task]
        save_tasks(self.task_data)
        self._refresh()

    def _on_toggle(self):
        """完了状態が変わったときに保存・再描画する"""
        save_tasks(self.task_data)
        self._refresh()

    def _sort_by_deadline(self, e):
        """締切日が近い順に並び替える（締切なしは末尾）"""
        def key(t):
            dl = t.get("deadline", "")
            return dl if dl else "9999-99-99"

        self.task_data.sort(key=key)
        save_tasks(self.task_data)
        self._refresh()

    def _refresh(self):
        """フィルターに合わせてタスク一覧を再描画する"""
        idx = self.filter_tabs.selected_index
        # 0:すべて  1:未完了  2:完了済み
        filtered = [
            t for t in self.task_data
            if idx == 0
            or (idx == 1 and not t["done"])
            or (idx == 2 and t["done"])
        ]

        self.task_list.controls = [
            TaskItem(t, self._on_toggle, self._delete_task)
            for t in filtered
        ]

        # 件数を更新
        total = len(self.task_data)
        done = sum(1 for t in self.task_data if t["done"])
        self.count_text.value = f"全 {total} 件 ／ 完了 {done} 件 ／ 未完了 {total - done} 件"

        self.update()


def main(page: ft.Page):
    page.title = "課題管理アプリ"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.add(ft.SafeArea(content=AssignmentApp()))


if __name__ == "__main__":
    ft.app(target=main)
