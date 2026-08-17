"""Tests for google-workspace OAuth service-specific scope selection."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


SETUP_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills/productivity/google-workspace/scripts/setup.py"
)


class GoogleWorkspaceSetupServicesTest(unittest.TestCase):
    def load_setup_module(self):
        hermes_home = Path(tempfile.mkdtemp()) / ".hermes"
        hermes_home.mkdir()
        self.addCleanup(lambda: os.environ.pop("HERMES_HOME", None))
        os.environ["HERMES_HOME"] = str(hermes_home)
        spec = importlib.util.spec_from_file_location("google_workspace_setup_test", SETUP_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_email_services_resolve_to_gmail_modify_and_send_only(self):
        setup = self.load_setup_module()

        self.assertEqual(
            setup.resolve_service_scopes("email"),
            [
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.send",
            ],
        )

    def test_services_combine_and_dedupe_in_stable_order(self):
        setup = self.load_setup_module()

        self.assertEqual(
            setup.resolve_service_scopes("email,calendar,email"),
            [
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/calendar",
            ],
        )

    def test_all_services_preserves_backward_compatible_workspace_scopes(self):
        setup = self.load_setup_module()

        self.assertEqual(setup.resolve_service_scopes("all"), setup.SCOPES)

    def test_pending_auth_persists_selected_scopes(self):
        setup = self.load_setup_module()
        scopes = setup.resolve_service_scopes("email")

        setup._save_pending_auth(state="state-1", code_verifier="verifier-1", scopes=scopes)

        pending = json.loads(setup.PENDING_AUTH_PATH.read_text())
        self.assertEqual(pending["state"], "state-1")
        self.assertEqual(pending["code_verifier"], "verifier-1")
        self.assertEqual(pending["scopes"], scopes)

    def test_missing_scope_check_uses_expected_scopes_not_global_workspace(self):
        setup = self.load_setup_module()
        payload = {
            "scopes": [
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.send",
            ]
        }

        self.assertEqual(
            setup._missing_scopes_from_payload(
                payload,
                expected_scopes=setup.resolve_service_scopes("email"),
            ),
            [],
        )

    def test_unknown_service_name_is_rejected(self):
        setup = self.load_setup_module()

        with self.assertRaisesRegex(ValueError, "Unknown Google service"):
            setup.resolve_service_scopes("email,photos")


if __name__ == "__main__":
    unittest.main()
