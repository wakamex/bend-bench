import subprocess
import unittest
from unittest.mock import patch

import validate_all


def response(text):
    return subprocess.CompletedProcess([], 0, stdout=text, stderr="")


class QueueTests(unittest.TestCase):
    def test_active_predecessor_waits(self):
        with patch("validate_all.subprocess.run", return_value=response("ActiveState=active\nInvocationID=abc\n")):
            self.assertEqual(validate_all.predecessor_state("example.service", "abc"), "waiting")

    def test_replaced_predecessor_stops(self):
        with patch("validate_all.subprocess.run", return_value=response("ActiveState=active\nInvocationID=def\n")):
            with self.assertRaisesRegex(RuntimeError, "invocation changed"):
                validate_all.predecessor_state("example.service", "abc")

    def test_completion_requires_marker(self):
        for journal, success in (("unrelated output\n", False), ("PIPELINE COMPLETE: recorded\n", True)):
            with self.subTest(success=success), patch("validate_all.subprocess.run", side_effect=[
                    response("ActiveState=inactive\nLoadState=not-found\n"), response(journal)]):
                if success:
                    self.assertEqual(validate_all.predecessor_state("example.service", "abc"), "complete")
                else:
                    with self.assertRaisesRegex(RuntimeError, "without its completion marker"):
                        validate_all.predecessor_state("example.service", "abc")

    def test_input_changes_stop_queue(self):
        with patch("validate_all.inputs", return_value={"config": "changed"}):
            with self.assertRaisesRegex(RuntimeError, "changed"):
                validate_all.verify_inputs({"config": "original"})


if __name__ == "__main__":
    unittest.main()
