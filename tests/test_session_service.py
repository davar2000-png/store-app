# -*- coding: utf-8 -*-

import services.session_service as session_service
from tests._fake_database import FakeDatabase


def setup_function():
    FakeDatabase.reset()
    session_service.Database = FakeDatabase


def test_start_session_creates_active_session():
    session_id = session_service.start_session(10)

    assert session_id == 1
    assert FakeDatabase.sessions[0]["UserRef"] == 10
    assert FakeDatabase.sessions[0]["CloseStatus"] == "ACTIVE"


def test_heartbeat_updates_session():
    session_id = session_service.start_session(10)

    FakeDatabase.sessions[0]["LastHeartbeat"] = "OLD"
    session_service.heartbeat(session_id)

    assert FakeDatabase.sessions[0]["LastHeartbeat"] == "NOW"


def test_mark_autosave_updates_session():
    session_id = session_service.start_session(10)

    session_service.mark_autosave(session_id)

    assert FakeDatabase.sessions[0]["LastAutoSave"] == "NOW"


def test_clean_session_is_not_reported_as_crashed():
    session_id = session_service.start_session(10)

    session_service.close_session_cleanly(session_id)

    assert session_service.find_crashed_sessions(10) == []


def test_crashed_session_is_detected_and_then_removed_from_active_list():
    session_id = session_service.start_session(10)

    crashed = session_service.find_crashed_sessions(10)

    assert len(crashed) == 1
    assert crashed[0]["ID"] == session_id

    session_service.mark_as_crashed(session_id)

    assert session_service.find_crashed_sessions(10) == []


def test_crash_detection_is_scoped_to_user():
    session_service.start_session(10)
    session_service.start_session(20)

    crashed_for_user_10 = session_service.find_crashed_sessions(10)
    crashed_for_user_20 = session_service.find_crashed_sessions(20)

    assert len(crashed_for_user_10) == 1
    assert crashed_for_user_10[0]["UserRef"] == 10
    assert len(crashed_for_user_20) == 1
    assert crashed_for_user_20[0]["UserRef"] == 20
