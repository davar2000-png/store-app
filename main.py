# -*- coding: utf-8 -*-
"""نقطه شروع اجرای نرم‌افزار"""

import sys
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from services import session_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    app = QApplication(sys.argv)

    # لیست پنجره‌های باز نگه‌داشته می‌شود تا Garbage Collector آن‌ها را نبندد
    windows = []

    # وضعیت Session جاری این اجرای برنامه (Phase 13.1)
    session_state = {"session_id": None}
    heartbeat_timer = QTimer()
    heartbeat_timer.setInterval(60000)  # تقریباً هر ۶۰ ثانیه

    def do_heartbeat():
        session_id = session_state.get("session_id")
        if session_id is None:
            return
        try:
            session_service.heartbeat(session_id)
        except Exception:
            # Heartbeat هرگز نباید باعث Crash یا Freeze شدن برنامه شود
            logger.exception("خطا در ثبت Heartbeat برای Session %s", session_id)

    heartbeat_timer.timeout.connect(do_heartbeat)

    def close_current_session():
        session_id = session_state.get("session_id")
        if session_id is None:
            return
        try:
            session_service.close_session_cleanly(session_id)
        except Exception:
            # برنامه باید در هر صورت بتواند بسته شود
            logger.exception("خطا در بستن تمیز Session %s", session_id)
        finally:
            session_state["session_id"] = None
            heartbeat_timer.stop()

    def check_for_crashed_sessions(user_id):
        try:
            crashed_sessions = session_service.find_crashed_sessions(user_id)
        except Exception:
            logger.exception("خطا در بررسی Sessionهای قطع‌شده")
            return

        if not crashed_sessions:
            return

        QMessageBox.warning(
            None,
            "هشدار",
            "به نظر می‌رسد اجرای قبلی برنامه به‌طور غیرعادی بسته شده است "
            "(مثلاً قطع برق یا خطای غیرمنتظره).\n"
            "لطفاً اطلاعات اخیر خود را بررسی کنید."
        )

        for crashed in crashed_sessions:
            try:
                session_service.mark_as_crashed(crashed["ID"])
            except Exception:
                logger.exception(
                    "خطا در نهایی‌کردن وضعیت Session قطع‌شده %s",
                    crashed.get("ID")
                )

    def on_login_success(user):
        user_id = user["ID"]

        # ابتدا باید Sessionهای قطع‌شده‌ی اجراهای قبلی بررسی شوند؛
        # این کار باید قبل از start_session انجام شود، در غیر این
        # صورت Session تازه‌ساخته‌شده‌ی همین اجرا به‌اشتباه به‌عنوان
        # Crashed شناسایی می‌شود.
        check_for_crashed_sessions(user_id)

        try:
            session_state["session_id"] = session_service.start_session(user_id)
        except Exception:
            logger.exception("خطا در ایجاد Session جدید")
            session_state["session_id"] = None

        if session_state["session_id"] is not None:
            heartbeat_timer.start()

        main_win = MainWindow(user, session_id=session_state.get("session_id"))
        windows.append(main_win)
        main_win.show()

    login_win = LoginWindow(on_login_success)
    windows.append(login_win)
    login_win.show()

    app.aboutToQuit.connect(close_current_session)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
