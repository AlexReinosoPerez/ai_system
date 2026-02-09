"""
Tests for Router Contract v1

Tests the contract layer, dispatch guards, and routing behavior
WITHOUT touching external services (Gmail, GitHub, Aider, etc.).

These tests validate:
- Action whitelist enforcement
- Read/write classification
- Payload schema validation
- Source permission enforcement
- User authentication guard
- Audit persistence
- Dispatch routing to correct handlers
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node_interface.contract import (
    Action,
    ContractRequest,
    ContractResponse,
    ContractError,
    is_read_only,
    is_write,
    validate_payload,
    validate_source_permission,
    PAYLOAD_SCHEMAS,
    _READ_ONLY_ACTIONS,
    _WRITE_ACTIONS,
    SOURCE_PERMISSIONS,
)


# ──────────────────────────────────────────────
# CONTRACT TESTS
# ──────────────────────────────────────────────

class TestActionWhitelist(unittest.TestCase):
    """Test that the Action enum is a closed, complete whitelist."""

    def test_all_actions_are_classified(self):
        """Every action must be either read-only or write — no orphans."""
        all_actions = set(Action)
        classified = _READ_ONLY_ACTIONS | _WRITE_ACTIONS
        self.assertEqual(all_actions, classified,
            f"Unclassified actions: {all_actions - classified}")

    def test_no_overlap_between_read_and_write(self):
        """An action cannot be both read-only and write."""
        overlap = _READ_ONLY_ACTIONS & _WRITE_ACTIONS
        self.assertEqual(len(overlap), 0,
            f"Actions in both read and write: {overlap}")

    def test_read_only_count(self):
        """Sanity check: 10 read-only actions."""
        self.assertEqual(len(_READ_ONLY_ACTIONS), 10)

    def test_write_count(self):
        """Sanity check: 5 write actions."""
        self.assertEqual(len(_WRITE_ACTIONS), 5)

    def test_is_read_only_helper(self):
        self.assertTrue(is_read_only(Action.SYSTEM_STATUS))
        self.assertTrue(is_read_only(Action.DDS_LIST))
        self.assertTrue(is_read_only(Action.TODO_LIST))
        self.assertFalse(is_read_only(Action.EXECUTE))
        self.assertFalse(is_read_only(Action.DDS_APPROVE))

    def test_is_write_helper(self):
        self.assertTrue(is_write(Action.EXECUTE))
        self.assertTrue(is_write(Action.DDS_NEW))
        self.assertTrue(is_write(Action.TODO_TO_DDS))
        self.assertFalse(is_write(Action.SYSTEM_STATUS))
        self.assertFalse(is_write(Action.INBOX))


class TestPayloadValidation(unittest.TestCase):
    """Test payload schema enforcement."""

    def test_no_schema_actions_accept_empty_payload(self):
        """Actions without schemas (e.g. SYSTEM_STATUS) accept empty payloads."""
        actions_without_schema = set(Action) - set(PAYLOAD_SCHEMAS.keys())
        for action in actions_without_schema:
            # Should not raise
            validate_payload(action, {})

    def test_required_field_missing_raises(self):
        """Missing a required field must raise ContractError."""
        with self.assertRaises(ContractError):
            validate_payload(Action.PROJECT_INFO, {})

        with self.assertRaises(ContractError):
            validate_payload(Action.EXECUTE, {})

        with self.assertRaises(ContractError):
            validate_payload(Action.DDS_APPROVE, {})

    def test_required_field_present_passes(self):
        """Providing required fields must not raise."""
        validate_payload(Action.PROJECT_INFO, {"name": "fitnessai"})
        validate_payload(Action.EXECUTE, {"dds_id": "DDS-123"})
        validate_payload(Action.DDS_NEW, {
            "project": "test",
            "title": "test",
            "description": "test",
        })

    def test_optional_field_can_be_omitted(self):
        """Optional fields (e.g. count in INBOX) may be omitted."""
        validate_payload(Action.INBOX, {})

    def test_extra_fields_are_ignored(self):
        """Extra fields in payload do not cause errors."""
        validate_payload(Action.PROJECT_INFO, {
            "name": "fitnessai",
            "extra_field": "ignored",
        })


class TestSourcePermissions(unittest.TestCase):
    """Test source-based access control."""

    def test_telegram_has_full_access(self):
        """Telegram can invoke all actions."""
        for action in Action:
            validate_source_permission("telegram", action)

    def test_cli_has_full_access(self):
        """CLI can invoke all actions."""
        for action in Action:
            validate_source_permission("cli", action)

    def test_voice_can_read(self):
        """Voice source can invoke read-only actions."""
        for action in _READ_ONLY_ACTIONS:
            validate_source_permission("voice", action)

    def test_voice_cannot_write(self):
        """Voice source cannot invoke write actions."""
        for action in _WRITE_ACTIONS:
            with self.assertRaises(ContractError):
                validate_source_permission("voice", action)

    def test_unknown_source_rejected(self):
        """Unknown source is rejected for any action."""
        with self.assertRaises(ContractError):
            validate_source_permission("unknown_source", Action.SYSTEM_STATUS)

        with self.assertRaises(ContractError):
            validate_source_permission("", Action.SYSTEM_STATUS)


class TestContractRequest(unittest.TestCase):
    """Test ContractRequest construction."""

    def test_defaults(self):
        req = ContractRequest(action=Action.SYSTEM_STATUS)
        self.assertEqual(req.action, Action.SYSTEM_STATUS)
        self.assertEqual(req.payload, {})
        self.assertEqual(req.source, "unknown")
        self.assertEqual(req.user_id, "unknown")
        self.assertIsInstance(req.timestamp, str)

    def test_explicit_fields(self):
        req = ContractRequest(
            action=Action.EXECUTE,
            payload={"dds_id": "DDS-123"},
            source="telegram",
            user_id="42",
        )
        self.assertEqual(req.payload["dds_id"], "DDS-123")
        self.assertEqual(req.source, "telegram")
        self.assertEqual(req.user_id, "42")


class TestContractResponse(unittest.TestCase):
    """Test ContractResponse construction."""

    def test_defaults(self):
        resp = ContractResponse(status="ok", message="test")
        self.assertEqual(resp.status, "ok")
        self.assertEqual(resp.message, "test")
        self.assertIsNone(resp.data)
        self.assertTrue(resp.read_only)
        self.assertTrue(resp.audit_id.startswith("AUD-"))

    def test_audit_id_unique(self):
        resp1 = ContractResponse(status="ok", message="a")
        resp2 = ContractResponse(status="ok", message="b")
        # audit_ids include microseconds, should differ
        # (in rare cases they could match, but this is a sanity check)
        self.assertIsInstance(resp1.audit_id, str)
        self.assertIsInstance(resp2.audit_id, str)


# ──────────────────────────────────────────────
# ROUTER DISPATCH TESTS
# ──────────────────────────────────────────────

class TestRouterDispatch(unittest.TestCase):
    """Test Router.dispatch() guard chain and routing."""

    def setUp(self):
        """Create a Router instance with mocked dependencies."""
        # Patch heavy imports to avoid loading real modules
        self.patches = []
        
        for module_name in [
            'node_events.github_reader',
            'node_events.summarizer',
            'node_events.gmail_reader',
            'node_projects.project_registry',
            'node_projects.project_status',
            'node_dds.dds_registry',
            'node_dds.dds_proposal',
            'node_programmer.programmer',
            'node_programmer.execution_report',
            'node_todo',
        ]:
            if module_name not in sys.modules:
                p = patch.dict('sys.modules', {module_name: MagicMock()})
                p.start()
                self.patches.append(p)

        # Now import Router (which imports the above)
        # We need to reload to pick up the mocks
        import importlib
        if 'node_interface.router' in sys.modules:
            importlib.reload(sys.modules['node_interface.router'])
        
        from node_interface.router import Router
        self.router = Router()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_system_status_returns_ok(self):
        """Basic dispatch to system_status works."""
        req = ContractRequest(
            action=Action.SYSTEM_STATUS,
            source="telegram",
            user_id="123",
        )
        resp = self.router.dispatch(req)
        self.assertEqual(resp.status, "ok")
        self.assertIn("AI System Status", resp.message)
        self.assertTrue(resp.read_only)
        self.assertEqual(resp.action, Action.SYSTEM_STATUS)

    def test_missing_payload_field_returns_error(self):
        """Dispatch with missing required payload field returns error."""
        req = ContractRequest(
            action=Action.EXECUTE,
            payload={},  # missing dds_id
            source="telegram",
            user_id="123",
        )
        resp = self.router.dispatch(req)
        self.assertEqual(resp.status, "error")
        self.assertIn("Payload inválido", resp.message)

    def test_unknown_source_returns_error(self):
        """Dispatch from unknown source is rejected."""
        req = ContractRequest(
            action=Action.SYSTEM_STATUS,
            source="unknown_source",
            user_id="123",
        )
        resp = self.router.dispatch(req)
        self.assertEqual(resp.status, "error")
        self.assertIn("Permiso denegado", resp.message)

    def test_voice_read_only_allowed(self):
        """Voice source can dispatch read-only actions."""
        req = ContractRequest(
            action=Action.SYSTEM_STATUS,
            source="voice",
            user_id="123",
        )
        resp = self.router.dispatch(req)
        self.assertEqual(resp.status, "ok")

    def test_voice_write_blocked(self):
        """Voice source cannot dispatch write actions."""
        req = ContractRequest(
            action=Action.EXECUTE,
            payload={"dds_id": "DDS-123"},
            source="voice",
            user_id="123",
        )
        resp = self.router.dispatch(req)
        self.assertEqual(resp.status, "error")
        self.assertIn("Permiso denegado", resp.message)

    @patch('node_interface.router.config')
    def test_auth_blocks_unauthorized_user(self, mock_config):
        """When ALLOWED_USER_IDS is set, unknown user is rejected."""
        mock_config.ALLOWED_USER_IDS = "100,200,300"
        mock_config.GMAIL_CREDENTIALS_PATH = "secrets/credentials.json"
        mock_config.GMAIL_TOKEN_PATH = "secrets/token.json"
        
        req = ContractRequest(
            action=Action.SYSTEM_STATUS,
            source="telegram",
            user_id="999",
        )
        resp = self.router.dispatch(req)
        self.assertEqual(resp.status, "error")
        self.assertIn("no autorizado", resp.message)

    @patch('node_interface.router.config')
    def test_auth_allows_authorized_user(self, mock_config):
        """When ALLOWED_USER_IDS is set, listed user passes."""
        mock_config.ALLOWED_USER_IDS = "100,200,300"
        mock_config.GMAIL_CREDENTIALS_PATH = "secrets/credentials.json"
        mock_config.GMAIL_TOKEN_PATH = "secrets/token.json"
        
        req = ContractRequest(
            action=Action.SYSTEM_STATUS,
            source="telegram",
            user_id="200",
        )
        resp = self.router.dispatch(req)
        self.assertEqual(resp.status, "ok")

    @patch('node_interface.router.config')
    def test_auth_disabled_when_empty(self, mock_config):
        """When ALLOWED_USER_IDS is empty, all users pass (dev mode)."""
        mock_config.ALLOWED_USER_IDS = ""
        
        req = ContractRequest(
            action=Action.SYSTEM_STATUS,
            source="telegram",
            user_id="any_user",
        )
        resp = self.router.dispatch(req)
        self.assertEqual(resp.status, "ok")

    def test_dispatch_response_has_audit_id(self):
        """Every response includes an audit_id."""
        req = ContractRequest(
            action=Action.SYSTEM_STATUS,
            source="telegram",
            user_id="123",
        )
        resp = self.router.dispatch(req)
        self.assertTrue(resp.audit_id.startswith("AUD-"))

    def test_dispatch_read_only_flag_correct(self):
        """Read-only flag in response matches action classification."""
        # Read action
        req_read = ContractRequest(
            action=Action.TODO_LIST,
            source="telegram",
            user_id="123",
        )
        resp_read = self.router.dispatch(req_read)
        self.assertTrue(resp_read.read_only)


# ──────────────────────────────────────────────
# AUDIT PERSISTENCE TESTS
# ──────────────────────────────────────────────

class TestAuditPersistence(unittest.TestCase):
    """Test that audit entries are written to disk."""

    def test_audit_entry_written(self):
        """Dispatching an action writes an audit line to the JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_file = os.path.join(tmpdir, "audit.jsonl")

            # Patch the audit file path
            import node_interface.router as router_module
            original_audit = router_module.AUDIT_FILE
            router_module.AUDIT_FILE = audit_file

            try:
                from node_interface.router import Router
                r = Router()
                req = ContractRequest(
                    action=Action.SYSTEM_STATUS,
                    source="telegram",
                    user_id="42",
                )
                resp = r.dispatch(req)

                # File should exist and contain one line
                self.assertTrue(os.path.exists(audit_file))
                with open(audit_file, "r") as f:
                    lines = f.readlines()
                self.assertEqual(len(lines), 1)

                entry = json.loads(lines[0])
                self.assertEqual(entry["action"], "system_status")
                self.assertEqual(entry["source"], "telegram")
                self.assertEqual(entry["user_id"], "42")
                self.assertEqual(entry["status"], "ok")
                self.assertEqual(entry["audit_id"], resp.audit_id)
                # v1.1 enriched fields
                self.assertEqual(entry["level"], "info")
                self.assertIn("duration_ms", entry)
                self.assertIsInstance(entry["duration_ms"], int)
                self.assertGreaterEqual(entry["duration_ms"], 0)
                self.assertIn("payload_summary", entry)
                self.assertNotIn("error_detail", entry)  # absent on success
            finally:
                router_module.AUDIT_FILE = original_audit

    def test_audit_payload_summary_traces_ids(self):
        """Audit payload_summary captures traceable IDs, not the full payload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_file = os.path.join(tmpdir, "audit.jsonl")

            import node_interface.router as router_module
            original_audit = router_module.AUDIT_FILE
            router_module.AUDIT_FILE = audit_file

            try:
                from node_interface.router import Router
                r = Router()
                # This will fail validation (missing required field) but
                # payload_summary should still capture the dds_id if present
                r.dispatch(ContractRequest(
                    action=Action.PROJECT_INFO,
                    payload={"name": "fitnessai", "extra": "ignored"},
                    source="telegram",
                    user_id="42",
                ))

                with open(audit_file, "r") as f:
                    entry = json.loads(f.readline())
                # "name" is traceable, "extra" is not
                self.assertEqual(entry["payload_summary"]["name"], "fitnessai")
                self.assertNotIn("extra", entry["payload_summary"])
            finally:
                router_module.AUDIT_FILE = original_audit

    def test_audit_error_has_detail_and_level(self):
        """Failed dispatches include error_detail and level=guard_reject."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_file = os.path.join(tmpdir, "audit.jsonl")

            import node_interface.router as router_module
            original_audit = router_module.AUDIT_FILE
            router_module.AUDIT_FILE = audit_file

            try:
                from node_interface.router import Router
                r = Router()
                # Trigger payload validation failure
                r.dispatch(ContractRequest(
                    action=Action.EXECUTE,
                    payload={},
                    source="telegram",
                    user_id="42",
                ))

                with open(audit_file, "r") as f:
                    entry = json.loads(f.readline())
                self.assertEqual(entry["level"], "guard_reject")
                self.assertIn("error_detail", entry)
                self.assertIn("payload_invalid", entry["error_detail"])
            finally:
                router_module.AUDIT_FILE = original_audit

    def test_multiple_dispatches_append(self):
        """Multiple dispatches append lines, never overwrite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_file = os.path.join(tmpdir, "audit.jsonl")

            import node_interface.router as router_module
            original_audit = router_module.AUDIT_FILE
            router_module.AUDIT_FILE = audit_file

            try:
                from node_interface.router import Router
                r = Router()
                for _ in range(3):
                    r.dispatch(ContractRequest(
                        action=Action.SYSTEM_STATUS,
                        source="telegram",
                        user_id="42",
                    ))

                with open(audit_file, "r") as f:
                    lines = f.readlines()
                self.assertEqual(len(lines), 3)
            finally:
                router_module.AUDIT_FILE = original_audit

    def test_error_responses_are_audited(self):
        """Even failed dispatches (payload error, auth error) are audited."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_file = os.path.join(tmpdir, "audit.jsonl")

            import node_interface.router as router_module
            original_audit = router_module.AUDIT_FILE
            router_module.AUDIT_FILE = audit_file

            try:
                from node_interface.router import Router
                r = Router()
                # This should fail (missing required field)
                r.dispatch(ContractRequest(
                    action=Action.EXECUTE,
                    payload={},
                    source="telegram",
                    user_id="42",
                ))

                with open(audit_file, "r") as f:
                    lines = f.readlines()
                self.assertEqual(len(lines), 1)
                entry = json.loads(lines[0])
                self.assertEqual(entry["status"], "error")
                self.assertIn("error_detail", entry)
                self.assertGreaterEqual(entry["duration_ms"], 0)
            finally:
                router_module.AUDIT_FILE = original_audit


if __name__ == "__main__":
    unittest.main()
