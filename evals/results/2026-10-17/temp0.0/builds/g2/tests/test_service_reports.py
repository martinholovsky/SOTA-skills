"""
Tests for create_report, get_report, list_reports, search_reports,
delete_report.
"""

import pytest

from reportkit.errors import (
    BadRequest, Forbidden, NotFound, Unauthorized,
)
from tests.conftest import make_user, auth_headers


class TestCreateReport:
    def test_editor_can_create(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        resp = service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "Q1 Report", "body": "content"},
        })
        assert resp["status"] == 201
        assert resp["body"]["title"] == "Q1 Report"
        assert "id" in resp["body"]

    def test_viewer_cannot_create(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "viewer")
        with pytest.raises(Forbidden):
            service.create_report({
                "headers": auth_headers(token),
                "body": {"title": "T", "body": ""},
            })

    def test_missing_title_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.create_report({
                "headers": auth_headers(token),
                "body": {"body": "no title"},
            })

    def test_empty_title_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.create_report({
                "headers": auth_headers(token),
                "body": {"title": "", "body": ""},
            })

    def test_title_too_long_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.create_report({
                "headers": auth_headers(token),
                "body": {"title": "x" * 501, "body": ""},
            })

    def test_nul_in_title_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.create_report({
                "headers": auth_headers(token),
                "body": {"title": "bad\x00title", "body": ""},
            })

    def test_body_too_large_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.create_report({
                "headers": auth_headers(token),
                "body": {"title": "T", "body": "x" * (1_048_576 + 1)},
            })

    def test_unauthenticated_raises(self, service):
        with pytest.raises(Unauthorized):
            service.create_report({"headers": {}, "body": {"title": "T"}})


class TestGetReport:
    def _create(self, service, db, tenant_id, token):
        resp = service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "My Report", "body": "body text"},
        })
        return resp["body"]["id"]

    def test_owner_can_read(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        rid = self._create(service, db, tenant_a, token)
        resp = service.get_report({"headers": auth_headers(token)}, rid)
        assert resp["status"] == 200
        assert resp["body"]["id"] == rid

    def test_cross_tenant_returns_404(self, service, db, tenant_a, tenant_b):
        _, token_a = make_user(db, tenant_a, "editor")
        _, token_b = make_user(db, tenant_b, "editor")
        rid = self._create(service, db, tenant_a, token_a)
        with pytest.raises(NotFound):
            service.get_report({"headers": auth_headers(token_b)}, rid)

    def test_nonexistent_returns_404(self, service, db, tenant_a):
        import uuid
        _, token = make_user(db, tenant_a, "viewer")
        with pytest.raises(NotFound):
            service.get_report(
                {"headers": auth_headers(token)},
                str(uuid.uuid4()),
            )

    def test_invalid_uuid_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "viewer")
        with pytest.raises(BadRequest):
            service.get_report({"headers": auth_headers(token)}, "not-a-uuid")

    def test_viewer_can_read(self, service, db, tenant_a):
        _, token_e = make_user(db, tenant_a, "editor")
        _, token_v = make_user(db, tenant_a, "viewer")
        rid = self._create(service, db, tenant_a, token_e)
        # viewer can read their own reports; this report belongs to editor,
        # so viewer gets 404 (not their report).
        with pytest.raises(NotFound):
            service.get_report({"headers": auth_headers(token_v)}, rid)


class TestListReports:
    def test_returns_own_reports_only(self, service, db, tenant_a):
        _, token1 = make_user(db, tenant_a, "editor")
        _, token2 = make_user(db, tenant_a, "editor")
        service.create_report({
            "headers": auth_headers(token1),
            "body": {"title": "User1 Report", "body": ""},
        })
        service.create_report({
            "headers": auth_headers(token2),
            "body": {"title": "User2 Report", "body": ""},
        })
        resp = service.list_reports({"headers": auth_headers(token1)})
        assert resp["status"] == 200
        titles = [r["title"] for r in resp["body"]["reports"]]
        assert "User1 Report" in titles
        assert "User2 Report" not in titles

    def test_cross_tenant_isolation(self, service, db, tenant_a, tenant_b):
        _, token_a = make_user(db, tenant_a, "editor")
        _, token_b = make_user(db, tenant_b, "editor")
        service.create_report({
            "headers": auth_headers(token_a),
            "body": {"title": "Tenant A Report", "body": ""},
        })
        resp = service.list_reports({"headers": auth_headers(token_b)})
        assert resp["body"]["reports"] == []

    def test_newest_first(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "First", "body": ""},
        })
        service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "Second", "body": ""},
        })
        resp = service.list_reports({"headers": auth_headers(token)})
        titles = [r["title"] for r in resp["body"]["reports"]]
        # "Second" was created later, so it should appear first.
        assert titles[0] == "Second"


class TestSearchReports:
    def _setup(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "Alpha Report", "body": ""},
        })
        service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "Beta Summary", "body": ""},
        })
        return token

    def test_search_matches_title(self, service, db, tenant_a):
        token = self._setup(service, db, tenant_a)
        resp = service.search_reports({
            "headers": auth_headers(token),
            "query": {"q": "Alpha"},
        })
        assert resp["status"] == 200
        assert len(resp["body"]["reports"]) == 1
        assert resp["body"]["reports"][0]["title"] == "Alpha Report"

    def test_search_no_results(self, service, db, tenant_a):
        token = self._setup(service, db, tenant_a)
        resp = service.search_reports({
            "headers": auth_headers(token),
            "query": {"q": "Nonexistent"},
        })
        assert resp["body"]["reports"] == []

    def test_sort_by_title(self, service, db, tenant_a):
        token = self._setup(service, db, tenant_a)
        resp = service.search_reports({
            "headers": auth_headers(token),
            "query": {"q": "", "sort": "title"},
        })
        titles = [r["title"] for r in resp["body"]["reports"]]
        assert titles == sorted(titles)

    def test_invalid_sort_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.search_reports({
                "headers": auth_headers(token),
                "query": {"sort": "'; DROP TABLE reports; --"},
            })

    def test_like_injection_in_query(self, service, db, tenant_a):
        """% in the search term must not match everything."""
        _, token = make_user(db, tenant_a, "editor")
        service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "Secret", "body": ""},
        })
        resp = service.search_reports({
            "headers": auth_headers(token),
            "query": {"q": "%"},
        })
        # % is escaped; it should match nothing (no title contains a literal %).
        assert resp["body"]["reports"] == []

    def test_underscore_not_wildcard(self, service, db, tenant_a):
        """_ in the search term must not act as a wildcard."""
        _, token = make_user(db, tenant_a, "editor")
        service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "Anything", "body": ""},
        })
        resp = service.search_reports({
            "headers": auth_headers(token),
            "query": {"q": "_"},
        })
        assert resp["body"]["reports"] == []

    def test_cross_tenant_search_isolation(self, service, db, tenant_a, tenant_b):
        token_a = self._setup(service, db, tenant_a)
        _, token_b = make_user(db, tenant_b, "editor")
        resp = service.search_reports({
            "headers": auth_headers(token_b),
            "query": {"q": "Alpha"},
        })
        assert resp["body"]["reports"] == []

    def test_q_too_long_raises(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        with pytest.raises(BadRequest):
            service.search_reports({
                "headers": auth_headers(token),
                "query": {"q": "x" * 501},
            })


class TestDeleteReport:
    def _create(self, service, db, token):
        resp = service.create_report({
            "headers": auth_headers(token),
            "body": {"title": "To Delete", "body": ""},
        })
        return resp["body"]["id"]

    def test_admin_can_delete(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "admin")
        rid = self._create(service, db, token)
        resp = service.delete_report({"headers": auth_headers(token)}, rid)
        assert resp["status"] == 204

    def test_editor_cannot_delete(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "editor")
        rid = self._create(service, db, token)
        with pytest.raises(Forbidden):
            service.delete_report({"headers": auth_headers(token)}, rid)

    def test_cross_tenant_delete_returns_404(self, service, db, tenant_a, tenant_b):
        _, token_a = make_user(db, tenant_a, "admin")
        _, token_b = make_user(db, tenant_b, "admin")
        rid = self._create(service, db, token_a)
        with pytest.raises(NotFound):
            service.delete_report({"headers": auth_headers(token_b)}, rid)

    def test_double_delete_returns_404(self, service, db, tenant_a):
        _, token = make_user(db, tenant_a, "admin")
        rid = self._create(service, db, token)
        service.delete_report({"headers": auth_headers(token)}, rid)
        with pytest.raises(NotFound):
            service.delete_report({"headers": auth_headers(token)}, rid)
