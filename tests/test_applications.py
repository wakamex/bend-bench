import math
from pathlib import Path
import struct
import tempfile
import unittest

from bend_bench.applications import (
    distances,
    graph,
    lines,
    mnk_corpus,
    mnk_oracle,
    pricing_reference,
    render,
)
from bend_bench.core import correct, load_config


class ApplicationContracts(unittest.TestCase):
    def test_queue_bfs_directed_disconnected(self):
        self.assertEqual(
            distances(5, [(0, 1), (1, 2), (2, 1), (3, 4)]),
            [0, 1, 2, 4294967295, 4294967295],
        )
        edges = graph(6)
        self.assertEqual(edges, sorted(set(edges)))
        self.assertTrue(all(0 <= a < 64 and 0 <= b < 64 for a, b in edges))

    def test_win_lines(self):
        self.assertEqual(len(lines(3, 3, 3)), 8)
        self.assertIn((2, 4, 6), lines(3, 3, 3))
        self.assertNotIn((2, 3, 4), lines(3, 3, 3))

    def test_known_tic_tac_toe_outcomes(self):
        _, oracle = mnk_oracle(3, 3, 3)
        self.assertEqual(oracle((0,) * 9, 1), 1)
        self.assertEqual(oracle((1, 1, 0, 2, 2, 0, 0, 0, 0), 1), 2)
        self.assertEqual(oracle((1, 1, 1, 2, 2, 0, 0, 0, 0), 2), 0)

    def test_legal_endgame_corpus_and_replay(self):
        corpus = mnk_corpus(3, 3, 3, 4)
        self.assertEqual(len({tuple(p["board"]) for p in corpus}), 16)
        for p in corpus:
            board = [0] * 9
            for ply, move in enumerate(p["history"]):
                self.assertEqual(board[move], 0)
                board[move] = 1 + ply % 2
                self.assertFalse(
                    any(
                        all(board[i] == board[move] for i in line)
                        for line in lines(3, 3, 3)
                    )
                )
            self.assertEqual(board, p["board"])
            self.assertIn(p["value"], [0, 1, 2])
            self.assertEqual(board.count(0), 4)

    def test_pricing_stream_and_finite_payoffs(self):
        # Park-Miller's published first states from seed 1; Schrage must agree
        # with modular multiplication, including the negative-difference branch.
        state = 1
        for expected in [16807, 282475249, 1622650073, 984943658, 1144108930]:
            a, b = 16807 * (state % 127773), 2836 * (state // 127773)
            state = a - b if a > b else 2147483647 - b + a
            self.assertEqual(state, expected)
        values = pricing_reference(32, 16)
        self.assertTrue(all(math.isfinite(v) and v >= 0 for v in values))
        self.assertGreater(max(values), 0)

    def test_full_vectors_reject_seeded_faults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "expected.json"
            path.write_text("[0,1,2,4294967295]")
            case = dict(
                expected_vector=str(path),
                implementation="bend",
                contract={"vector_kind": "u32"},
            )
            result = dict(returncode=0, timeout=False, stdout="0 1 2 4294967295")
            self.assertTrue(correct(case, result))
            for out in [
                "0 1 2",
                "0 2 1 4294967295",
                "0 1 2 0",
                "0 1 2 4294967295 extra",
            ]:
                self.assertFalse(correct(case, {**result, "stdout": out}))
            path.write_text("[1.0]")
            case["contract"] = dict(
                vector_kind="f32-bits", abs_tolerance=0.002, rel_tolerance=0.0001
            )
            def bits(x):
                return str(struct.unpack("<I", struct.pack("<f", x))[0])
            self.assertTrue(correct(case, {**result, "stdout": bits(1.0)}))
            for x in [1.01, float("nan"), float("inf")]:
                self.assertFalse(correct(case, {**result, "stdout": bits(x)}))

    def test_application_config(self):
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "applications.toml")
        self.assertEqual(config["threads"], [1, 2, 4, 8, 16, 32])
        self.assertIn("bend-bench-gpu.service", config["blocked_services"])

    def test_template_requires_complete_substitution(self):
        with self.assertRaises(ValueError):
            render("@MISSING@", {})


if __name__ == "__main__":
    unittest.main()
