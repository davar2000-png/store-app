# -*- coding: utf-8 -*-
"""نقطه شروع اجرای نرم‌افزار"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # لیست پنجره‌های باز نگه‌داشته می‌شود تا Garbage Collector آن‌ها را نبندد
    windows = []

    def on_login_success(user):
        main_win = MainWindow(user)
        windows.append(main_win)
        main_win.show()

    login_win = LoginWindow(on_login_success)
    windows.append(login_win)
    login_win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
