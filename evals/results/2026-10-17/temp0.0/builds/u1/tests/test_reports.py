"""Report CRUD tests."""

import pytest
from tests.conftest import make_request, seed_tenant, seed_user, seed_session


# ---------------------------------------------------------------------------
# create_report
# ---------------------------------------------------------------------------

def test_create_report_success(svc, editor_token):
    req = make_request(editor_token, body={"title": "Q1 Report", "body": "content"})
    resp = svc.create_report(req)
    assert resp["status"] == 201
    assert resp["report"]["title"] == "Q1 Report"


def test_create_report_missing_title(svc, editor_token):
    req = make_request(editor_token, body={"body": "no title"})
    resp = svc.create_report(req)
    assert resp["status"] == 400


def test_create_report_viewer_forbidden(svc, viewer_token):
    req = make_request(viewer_token, body={"title": "Sneaky"})
    resp = svc.create_report(req)
    assert resp["status"] == 403


# ---------------------------------------------------------------------------
# get_report
# ---------------------------------------------------------------------------

def test_get_report_success(svc, editor_token):
    create_resp = svc.create_report(
        make_request(editor_token, body={"title": "My Report"})
    )
    report_id = create_resp["report"]["id"]

    get_resp = svc.get_report(make_request(editor_token), report_id)
    assert get_resp["status"] == 200
    assert get_resp["report"]["id"] == report_id


def test_get_report_not_found(svc, editor_token):
    resp = svc.get_report(make_request(editor_token), "nonexistent-id")
    assert resp["status"] == 404


def test_get_report_cross_tenant_isolation(svc, conn):
    """A user from tenant B cannot read a report from tenant A."""
    tid_a = seed_tenant(conn, name="Tenant A")
    uid_a = seed_user(conn, tid_a, role="editor")
    tok_a = seed_session(conn, uid_a)

    tid_b = seed_tenant(conn, name="Tenant B")
    uid_b = seed_user(conn, tid_b, role="editor")
    tok_b = seed_session(conn, uid_b)

    create_resp = svc.create_report(
        make_request(tok_a, body={"title": "Tenant A secret"})
    )
    report_id = create_resp["report"]["id"]

    resp = svc.get_report(make_request(tok_b), report_id)
    assert resp["status"] == 404


# ---------------------------------------------------------------------------
# list_reports
# ---------------------------------------------------------------------------

def test_list_reports_returns_own_reports(svc, editor_token):
    for i in range(3):
        svc.create_report(make_request(editor_token, body={"title": f"Report {i}"}))

    resp = svc.list_reports(make_request(editor_token))
    assert resp["status"] == 200
    assert len(resp["reports"]) == 3


def test_list_reports_newest_first(svc, editor_token):
    titles = ["Alpha", "Beta", "Gamma"]
    for t in titles:
        svc.create_report(make_request(editor_token, body={"title": t}))

    resp = svc.list_reports(make_request(editor_token))
    returned_titles = [r["title"] for r in resp["reports"]]
    assert returned_titles == list(reversed(titles))


def test_list_reports_does_not_return_other_users_reports(svc, conn, tenant_id):
    uid1 = seed_user(conn, tenant_id, role="editor", username="user1")
    tok1 = seed_session(conn, uid1)
    uid2 = seed_user(conn, tenant_id, role="editor", username="user2")
    tok2 = seed_session(conn, uid2)

    svc.create_report(make_request(tok1, body={"title": "User1 Report"}))

    resp = svc.list_reports(make_request(tok2))
    assert resp["status"] == 200
    assert len(resp["reports"]) == 0


# ---------------------------------------------------------------------------
# search_reports
# ---------------------------------------------------------------------------

def test_search_reports_finds_match(svc, editor_token):
    svc.create_report(make_request(editor_token, body={"title": "Annual Budget"}))
    svc.create_report(make_request(editor_token, body={"title": "Quarterly Review"}))

    resp = svc.search_reports(make_request(editor_token, query={"q": "Budget"}))
    assert resp["status"] == 200
    assert len(resp["reports"]) == 1
    assert resp["reports"][0]["title"] == "Annual Budget"


def test_search_reports_sort_by_title(svc, editor_token):
    for title in ["Zebra Report", "Alpha Report", "Mango Report"]:
        svc.create_report(make_request(editor_token, body={"title": title}))

    resp = svc.search_reports(
        make_request(editor_token, query={"q": "Report", "sort": "title"})
    )
    assert resp["status"] == 200
    titles = [r["title"] for r in resp["reports"]]
    assert titles == sorted(titles)


def test_search_reports_invalid_sort_falls_back_to_default(svc, editor_token):
    svc.create_report(make_request(editor_token, body={"title": "Test Report"}))
    # Passing a malicious sort value should not cause an error
    resp = svc.search_reports(
        make_request(editor_token, query={"q": "Test", "sort": "1; DROP TABLE reports--"})
    )
    assert resp["status"] == 200


def test_search_reports_missing_q(svc, editor_token):
    resp = svc.search_reports(make_request(editor_token, query={}))
    assert resp["status"] == 400


def test_search_reports_cross_tenant_isolation(svc, conn):
    tid_a = seed_tenant(conn, name="A")
    uid_a = seed_user(conn, tid_a, role="editor")
    tok_a = seed_session(conn, uid_a)

    tid_b = seed_tenant(conn, name="B")
    uid_b = seed_user(conn, tid_b, role="editor")
    tok_b = seed_session(conn, uid_b)

    svc.create_report(make_request(tok_a, body={"title": "Secret Alpha"}))

    resp = svc.search_reports(make_request(tok_b, query={"q": "Secret"}))
    assert resp["status"] == 200
    assert len(resp["reports"]) == 0


# ---------------------------------------------------------------------------
# delete_report
# ---------------------------------------------------------------------------

def test_delete_report_success(svc, admin_token):
    create_resp = svc.create_report(
        make_request(admin_token, body={"title": "To Delete"})
    )
    report_id = create_resp["report"]["id"]

    del_resp = svc.delete_report(make_request(admin_token), report_id)
    assert del_resp["status"] == 200

    get_resp = svc.get_report(make_request(admin_token), report_id)
    assert get_resp["status"] == 404


def test_delete_report_editor_forbidden(svc, editor_token):
    create_resp = svc.create_report(
        make_request(editor_token, body={"title": "Protected"})
    )
    report_id = create_resp["report"]["id"]

    del_resp = svc.delete_report(make_request(editor_token), report_id)
    assert del_resp["status"] == 403


def test_delete_report_not_found(svc, admin_token):
    resp = svc.delete_report(make_request(admin_token), "ghost-id")
    assert resp["status"] == 404
