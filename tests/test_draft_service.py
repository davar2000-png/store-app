# -*- coding: utf-8 -*-

import services.draft_service as draft_service
from tests._fake_database import FakeDatabase


def setup_function():
    FakeDatabase.reset()
    draft_service.Database = FakeDatabase


def test_save_draft_creates_active_draft():
    draft_id = draft_service.save_draft(
        user_id=10,
        form_type="purchase",
        data={"supplier": "A", "total": 100},
        session_id=5,
    )

    assert draft_id == 1
    assert len(FakeDatabase.drafts) == 1
    assert FakeDatabase.drafts[0]["Status"] == "ACTIVE"


def test_save_draft_updates_existing_draft_without_duplicate():
    draft_id = draft_service.save_draft(
        10, "purchase", {"total": 100}, session_id=5
    )

    updated_id = draft_service.save_draft(
        10,
        "purchase",
        {"total": 250},
        session_id=5,
        draft_id=draft_id,
    )

    assert updated_id == draft_id
    assert len(FakeDatabase.drafts) == 1
    assert FakeDatabase.drafts[0]["DataJson"] == '{"total": 250}'


def test_update_requires_same_user():
    draft_id = draft_service.save_draft(
        10, "purchase", {"total": 100}, session_id=5
    )

    draft_service.save_draft(
        20,
        "purchase",
        {"total": 999},
        session_id=8,
        draft_id=draft_id,
    )

    assert FakeDatabase.drafts[0]["DataJson"] == '{"total": 100}'


def test_get_active_drafts_is_scoped_per_user():
    draft_service.save_draft(10, "purchase", {"total": 100})
    draft_service.save_draft(20, "purchase", {"total": 200})

    drafts = draft_service.get_active_drafts(10)

    assert len(drafts) == 1
    assert drafts[0]["UserRef"] == 10
    assert drafts[0]["Data"] == {"total": 100}


def test_get_active_drafts_can_filter_by_form_type():
    draft_service.save_draft(10, "purchase", {"total": 100})
    draft_service.save_draft(10, "sales", {"total": 200})

    drafts = draft_service.get_active_drafts(10, "purchase")

    assert len(drafts) == 1
    assert drafts[0]["FormType"] == "purchase"


def test_draft_lifecycle_status_changes():
    draft_id = draft_service.save_draft(10, "purchase", {"total": 100})

    draft_service.mark_recovered(draft_id)
    assert FakeDatabase.drafts[0]["Status"] == "RECOVERED"

    draft_id = draft_service.save_draft(10, "purchase", {"total": 200})
    draft_service.discard_draft(draft_id)
    assert FakeDatabase.drafts[-1]["Status"] == "DISCARDED"

    draft_id = draft_service.save_draft(10, "purchase", {"total": 300})
    draft_service.complete_draft(draft_id)
    assert FakeDatabase.drafts[-1]["Status"] == "COMPLETED"
