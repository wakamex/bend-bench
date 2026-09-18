import subprocess
import unittest
from unittest.mock import patch

import validate_all
from bend_bench.core import exclusive, service_contains_current_process


def response(text):
    return subprocess.CompletedProcess([], 0, stdout=text, stderr="")


class QueueTests(unittest.TestCase):
    def test_owning_service_still_requires_lock_and_blocks_other_services(self):
        with patch("bend_bench.core.service_state", return_value="active"), patch(
            "bend_bench.core.service_contains_current_process", side_effect=lambda s: s == "owner.service"
        ):
            with exclusive({"blocked_services": ["owner.service"]}):
                with self.assertRaisesRegex(ValueError, "Another bend-bench"):
                    with exclusive({"blocked_services": ["owner.service"]}):
                        pass
            with self.assertRaisesRegex(ValueError, "other.service"):
                with exclusive({"blocked_services": ["owner.service", "other.service"]}):
                    pass

    def test_service_cgroup_membership(self):
        for group, current, expected in (
            ("/user/owner.service", "/user/owner.service", True),
            ("/user/owner.service", "/user/owner.service/child", True),
            ("/user/owner.service", "/user/owner.service-other", False),
            ("/user/owner.service", "/user/other.service", False),
            ("", "/user/owner.service", False),
            ("/", "/user/owner.service", False),
        ):
            with self.subTest(group=group, current=current), patch(
                "bend_bench.core.execute", return_value={"returncode": 0, "stdout": group}
            ), patch("bend_bench.core.Path.read_text", return_value=f"0::{current}\n"):
                self.assertEqual(service_contains_current_process("owner.service"), expected)

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
