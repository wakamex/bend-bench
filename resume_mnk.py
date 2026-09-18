"""Explicit continuation of a saved resident MNK schedule, without rebuilding."""
import argparse
import json
from pathlib import Path
import statistics
import time

from bend_bench.core import exclusive, hash_file, provenance, write_json
from mnk_sustained import resident
from validate_applications import wait_idle


def verify(root):
    saved = json.loads((root / 'provenance.json').read_text())
    script = Path(__file__).with_name('mnk_sustained.py')
    if hash_file(script) != saved['script_sha256']:
        raise ValueError('Original measurement script changed')
    if saved.get('host_array_adapter_sha256') and hash_file(script.with_name('mnk_host_array.py')) != saved['host_array_adapter_sha256']:
        raise ValueError('Original host-array adapter changed')
    current = provenance(saved['harness']['config'])
    if current != saved['harness']:
        changed = [key for key in current if current[key] != saved['harness'].get(key)]
        raise ValueError(f'Original provenance changed: {changed}')
    for work in root.glob('corpus-*'):
        for name, digest in json.loads((work / 'hashes.json').read_text()).items():
            if hash_file(work / name) != digest:
                raise ValueError(f'Changed saved artifact: {work / name}')
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    root = args.run.resolve()
    saved = verify(root)
    if args.verify_only:
        print('Verified original script, provenance and saved artifact hashes')
        return
    out = root / time.strftime('continuation-%Y%m%d-%H%M%S')
    out.mkdir()
    config = saved['harness']['config']
    write_json(out / 'request.json', dict(original=str(root), resume_script_sha256=hash_file(__file__),
               policy='Reuse passed original cells; rerun rejected or missing cells in saved order; preserve originals'))
    wait_idle(config, out)
    with exclusive(config):
        verify(root)
        report = ['# Continued MNK scheduling and output comparison', '',
                  'Passed original measurements are retained and labeled. Rejected attempts remain in the original run; replacements have separate paths. The original timing script, provenance and saved artifacts were verified unchanged. Search-to-host includes transfers and is not kernel-only time.', '',
                  '| Implementation | Repetition | Origin | Delivered positions/s | Search-to-host ms | Output ms |',
                  '|---|---:|---|---:|---:|---:|']
        records = []
        for work in sorted(root.glob('corpus-*')):
            experiment = json.loads((work / 'experiment.json').read_text())
            cases = {c['id']: c for c in experiment['cases']}
            expected = json.loads((work / 'ports/mnk-5-5-4-8.json').read_text())
            for entry in json.loads((work / 'schedule.json').read_text()):
                case, repetition = cases[entry['case']], entry['repetition']
                name = f"{case['implementation']}-{case['threads']}-run{repetition}"
                original = work / name / 'result.json'
                result = json.loads(original.read_text()) if original.exists() else None
                reused = bool(result and result['correct'])
                total = case['contract']['measured_batches'] + 2
                if reused:
                    path = original
                    if result['command'] != case['command'] or len(result['phases']) != total:
                        raise ValueError(f'Original cell contract mismatch: {original}')
                else:
                    folder = out / work.name / name
                    folder.mkdir(parents=True)
                    print('RUN', name, flush=True)
                    result = resident(case['command'], folder, config, expected,
                                      experiment['positions_per_batch'], case['implementation'].endswith('cuda'),
                                      total, saved['arguments']['telemetry'], saved['arguments'].get('host_array', False))
                    path = folder / 'result.json'
                if len(result['phases']) != total:
                    raise ValueError(f'Missing phase timings: {path}')
                latency = statistics.mean(b['seconds'] for b in result['batches'][2:])
                search = statistics.mean(p['search_seconds'] for p in result['phases'][2:]) * 1000
                if saved['arguments'].get('host_array'):
                    if not result.get('host_array_correct'):
                        raise ValueError(f'Missing host array validation: {path}')
                    search = statistics.mean(result['host_ready_seconds'][2:]) * 1000
                output = statistics.mean(p['output_seconds'] for p in result['phases'][2:]) * 1000
                origin = 'retained original' if reused else 'continuation'
                report.append(f"| {case['implementation']} | {repetition} | {origin} | {experiment['positions_per_batch']/latency:.1f} | {search:.3f} | {output:.3f} |")
                records.append(dict(case=case['id'], repetition=repetition, origin=origin,
                                    result=str(path), result_sha256=hash_file(path)))
                write_json(out / 'accepted.json', records)
                (out / 'report.md').write_text('\n'.join(report) + '\n')
                print(report[-1], flush=True)
        write_json(out / 'completed.json', dict(report=str(out / 'report.md'), cells=len(records),
                   retained=sum(r['origin'] == 'retained original' for r in records),
                   original_failures_preserved=True))
    print('COMPLETE', out, flush=True)


if __name__ == '__main__':
    main()
