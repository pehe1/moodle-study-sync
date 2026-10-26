import unittest

from tools.moodle_local_auth import valid_local_form


class LocalAuthTest(unittest.TestCase):
    def test_opaque_browser_origin_requires_the_form_nonce(self):
        self.assertTrue(valid_local_form("null", "http://127.0.0.1:8000", "synthetic-nonce", "synthetic-nonce", ""))
        self.assertFalse(valid_local_form("null", "http://127.0.0.1:8000", "", "synthetic-nonce", ""))

    def test_other_origins_and_missing_origin_are_rejected(self):
        self.assertFalse(valid_local_form("https://other.example", "http://127.0.0.1:8000", "nonce", "nonce", "nonce"))
        self.assertFalse(valid_local_form(None, "http://127.0.0.1:8000", "nonce", "nonce", "nonce"))

    def test_regular_browser_requires_cookie_and_form_nonce(self):
        origin = "http://127.0.0.1:8000"
        self.assertTrue(valid_local_form(origin, origin, "nonce", "nonce", "nonce"))
        self.assertFalse(valid_local_form(origin, origin, "nonce", "nonce", ""))
        self.assertFalse(valid_local_form(origin, origin, "wrong", "nonce", "nonce"))
