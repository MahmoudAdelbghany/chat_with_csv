
import unittest
from agent.executor import run_code_capture
from agent.models import ToolResult

class TestSandboxing(unittest.TestCase):
    def test_safe_arithmetic(self):
        code = "a = 1 + 1\nprint(a)"
        result = run_code_capture(code)
        self.assertIsNone(result.error)
        self.assertEqual(result.locals.get('a'), '2')
        self.assertIn('2', result.stdout)

    def test_unsafe_import(self):
        code = "import os\nprint(os.getcwd())"
        result = run_code_capture(code)
        self.assertIsNotNone(result.error)
        self.assertIn("Security Violations", result.error)
        self.assertIn("Import of 'os' is not allowed", result.error)

    def test_unsafe_open(self):
        code = "f = open('test.txt', 'w')"
        result = run_code_capture(code)
        self.assertIsNotNone(result.error)
        self.assertIn("Call to 'open' is not allowed", result.error)

if __name__ == '__main__':
    unittest.main()
