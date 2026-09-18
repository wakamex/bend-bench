import json
from pathlib import Path
import tempfile
import unittest

from bend_bench.core import exclusive, execute, load_config
from bend_bench.suites import plan, stage
from bend_bench.applications import mnk_corpus, mnk_oracle
from mnk_host_array import instrument, validate
from mnk_sustained import ROOT, bend_resident, cpp_resident, resident, control_variants, bulk_variants, derived_variants, literal_win_check, bend_output_variants


class SustainedSearchTests(unittest.TestCase):
    def test_expanded_corpus_preserves_prefix_and_legal_histories(self):
        corpus = mnk_corpus(5, 5, 4, 8, 1024)
        self.assertEqual(corpus[:16], mnk_corpus(5, 5, 4, 8))
        self.assertEqual(len({tuple(p['board']) for p in corpus}), 1024)
        won, _ = mnk_oracle(5, 5, 4)
        for position in corpus:
            board, player = [0] * 25, 1
            for square in position['history']:
                self.assertEqual(board[square], 0)
                board[square] = player
                self.assertFalse(won(board, player))
                player = 3 - player
            self.assertEqual(board, position['board'])
            self.assertEqual(player, position['mover'])
            self.assertEqual(board.count(0), 8)

    def test_cuda_control_has_distinct_compiler_and_binary(self):
        config = load_config(ROOT / 'applications-mnk.toml')
        with tempfile.TemporaryDirectory() as tmp:
            stage(config, Path(tmp))
            builds, cases = plan(config, Path(tmp))
            for game in config['mnk_games']:
                name = 'mnk-' + '-'.join(map(str, game))
                pair = [c for c in cases if c['workload'] == name and c['implementation'].endswith('cuda')]
                self.assertEqual(len(pair), 2)
                self.assertNotEqual(pair[0]['command'][3], pair[1]['command'][3])
                control = next(c for c in pair if c['implementation'] == 'local-alpha-beta-cuda')
                command = next(b for b in builds if '-o' in b and b[b.index('-o') + 1] == control['command'][3])
                self.assertEqual(command[0], config['tools']['cuda_cxx'])
                self.assertTrue(any(arg.endswith('/gpu/mnk.cpp') for arg in command))
            control_variants(builds, cases)
            bulk_variants(builds, cases)
            derived_variants(builds, cases, 'literal', '-DLITERAL_WIN=1', 'bulk')
            outputs = [b[b.index('-o') + 1] for b in builds if '-o' in b]
            self.assertEqual(len(outputs), len(set(outputs)))
            for case in cases:
                if 'position-tight' in case['implementation']:
                    build = next(b for b in builds if '-o' in b and b[b.index('-o') + 1] == case['command'][3])
                    self.assertIn('-DWHOLE_POSITION=1', build)
                    self.assertIn('-DSEARCH_BOUND=1', build)

    def test_real_resident_cpu_answers(self):
        config = load_config(ROOT / 'applications-mnk.toml')
        config.update(cuda=False, threads=[1, 16], mnk_games=[[5, 5, 4, 8]])
        with exclusive(config), tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            stage(config, work, mnk_count=64)
            source = work / 'ports/mnk-5-5-4-8.bend'
            source.write_text(bend_resident(source.read_text(), 8, 32, 64))
            cpp = work / 'gpu/mnk.cpp'
            cpp.write_text(literal_win_check(cpp_resident(cpp.read_text(), 256, 32, 64, host_array=True)))
            builds, cases = plan(config, work)
            control_variants(builds, cases)
            bulk_variants(builds, cases)
            derived_variants(builds, cases, 'literal', '-DLITERAL_WIN=1', 'bulk')
            bend_output_variants(builds, cases, source, work)
            for chunk in (16, 64, 256):
                selected = [c for c in cases if c['implementation'] == 'local-alpha-beta-openmp-tight-bulk']
                derived_variants(builds, selected, f'chunk{chunk}', f'-DOMP_CHUNK={chunk}', 'bulk')
                cases.extend(c for c in selected if f'chunk{chunk}' in c['implementation'])
            outputs = [b[b.index('-o') + 1] for b in builds if '-o' in b]
            self.assertEqual(len(outputs), len(set(outputs)))
            for command in builds:
                result = execute(command)
                self.assertEqual(result['returncode'], 0, result['stderr'])
                if '-o' in command and command[0] == config['tools']['bun']:
                    generated = Path(command[command.index('-o') + 1])
                    generated.write_text(instrument(generated.read_text(), 256))
            expected = json.loads(source.with_suffix('.json').read_text())
            for index, case in enumerate(cases):
                folder = work / str(index)
                folder.mkdir()
                result = resident(case['command'], folder, config, expected, 256, False, 32, host_array=True)
                self.assertTrue(result['correct'])
                self.assertTrue(result['host_array_correct'])
                self.assertEqual(len(result['host_ready_seconds']), 32)
                self.assertEqual(len(result['batches']), 32)
                self.assertEqual(len(result['phases']), 32)
                self.assertGreater(sum(p['search_seconds'] for p in result['phases']), 0)
                self.assertAlmostEqual(result['batches'][-1]['cumulative_measured_positions_per_second'],
                                       30 * 256 / sum(b['seconds'] for b in result['batches'][2:]))
                self.assertAlmostEqual(result['positions_per_second_including_startup'],
                                       32 * 256 / result['process_seconds'])

    def test_wrong_answers_are_retained_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, 'correctness'):
                resident(['/usr/bin/printf', 'READY\n99\nEND\n'], folder, {}, [0] * 16, 16, False)
            self.assertFalse(json.loads((folder / 'result.json').read_text())['correct'])
            self.assertIn('99', (folder / 'stdout.txt').read_text())

    def test_host_array_rejects_corruption_truncation_and_extra_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'answers.bin'
            path.write_bytes(bytes(64))
            validate(path, [0] * 16, 16, 1)
            for data in (bytes(63), bytes(65), b'\x01' + bytes(63)):
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    validate(path, [0] * 16, 16, 1)
