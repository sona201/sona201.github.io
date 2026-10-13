"""Trusted acceptance checks: the model cannot edit or choose this script."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import traceback
import unittest

candidate = Path(sys.argv.pop(1)).resolve()
spec = importlib.util.spec_from_file_location("candidate", candidate)
module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(module)
except Exception:
    print(json.dumps({"passed": False, "kind": "infrastructure_error", "tests_run": 0,
                      "log": traceback.format_exc()}))
    sys.exit(2)


class BaseURLContract(unittest.TestCase):
    def test_preserve_paths_and_trim_edges(self):
        cases = {
            "https://api.example.com": "https://api.example.com",
            "https://api.example.com/": "https://api.example.com",
            "  https://api.example.com/v1/ \n": "https://api.example.com/v1",
            "https://api.example.com/team/v1///": "https://api.example.com/team/v1",
            "https://api.example.com/v1beta/": "https://api.example.com/v1beta",
            "https://api.example.com/prefix/v1/models/":
                "https://api.example.com/prefix/v1/models",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(module.normalize_base_url(value), expected)


if __name__ == "__main__":
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(BaseURLContract)
    )
    kind = "infrastructure_error" if result.errors else "passed" if result.wasSuccessful() else "assertion_failure"
    print(json.dumps({"passed": result.wasSuccessful(), "kind": kind,
                      "tests_run": result.testsRun, "assertion_failures": len(result.failures),
                      "errors": len(result.errors), "log": output.getvalue()}))
    sys.exit(2 if result.errors else 0 if result.wasSuccessful() else 1)
