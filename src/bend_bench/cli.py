import argparse
import json
from pathlib import Path
import sys
import time

from .core import load_config, provenance
from .experiment import compare, directory, measure, prepare, report
from .suites import plan


def fast_arguments(parser, target):
    parser.set_defaults(command='fast-'+target)
    parser.add_argument('experiment', type=Path, nargs='?', default=Path(f'fast-{target}.toml'))
    parser.add_argument('--plan', action='store_true', help='Preview the fixed portfolio without running it')
    parser.add_argument('--repetitions', type=int, help='Measured executions per configuration (positive integer; overrides TOML)')
    parser.add_argument('--baseline', type=Path, help='Previous run directory or saved result/comparison JSON')
    parser.add_argument('--threshold', type=float, default=10, help='Flag slowdowns above this percentage (default: 10)')


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pinned, correctness-gated Bend benchmark experiments")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "prepare", "check", "run"):
        commands.add_parser(name).add_argument("experiment", type=Path)
    commands.add_parser("report").add_argument("run", type=Path)
    profiling = commands.add_parser("profile")
    profiling.add_argument("experiment", type=Path)
    profiling.add_argument("--nsys", type=Path, required=True)
    comparison = commands.add_parser("compare")
    comparison.add_argument("before", type=Path)
    comparison.add_argument("after", type=Path)
    for target in ('cpu', 'gpu'):
        profiles = commands.add_parser(target, help=f'Bend {target.upper()} regression profiles').add_subparsers(dest='profile', required=True)
        fast_arguments(profiles.add_parser('fast', help='Reduced-workload regression profile'), target)
        fast_arguments(commands.add_parser('fast-'+target, help=f'Compatibility alias for {target} fast'), target)
    for name in ('regression-report', 'gpu-report', 'cpu-report'):
        regression_report = commands.add_parser(name, help='Readable results and optional regression comparison')
        regression_report.add_argument('run', type=Path)
        regression_report.add_argument('--baseline', type=Path)
        regression_report.add_argument('--threshold', type=float, default=10)
    args = parser.parse_args(argv)
    try:
        if args.command in ('gpu-report', 'cpu-report', 'regression-report'):
            from .regression import comparison, load_result, publish, render
            if args.run.is_dir():
                text, concerns = publish(args.run, args.baseline, args.threshold)
            else:
                result = load_result(args.run)
                compared = comparison(load_result(args.baseline), result, args.threshold) if args.baseline else None
                text = render(result, compared)
                concerns = any(r['status'] != 'passed' for r in result['cases']) or (compared and compared['concerns'])
            print(text)
            return int(bool(concerns))
        elif args.command == "report":
            print(report(args.run))
        elif args.command == "compare":
            print(json.dumps(compare(args.before, args.after), indent=2))
        else:
            config = load_config(args.experiment)
            if args.command in ('fast-gpu', 'fast-cpu'):
                expected_suite = args.command.removeprefix('fast-') + '-regression'
                if config['suites'] != [expected_suite]:
                    raise ValueError(f'{args.command} requires suites = ["{expected_suite}"]')
                if args.repetitions is not None:
                    if args.repetitions < 1:
                        raise ValueError('--repetitions must be at least 1')
                    config['repetitions'] = args.repetitions
            if args.command in ('fast-gpu', 'fast-cpu') and not args.plan:
                from .fast import run as fast_run
                started = time.perf_counter()
                try:
                    folder, failed = fast_run(config, args.baseline, args.threshold)
                finally:
                    elapsed = time.perf_counter() - started
                    minutes, seconds = divmod(round(elapsed), 60)
                    hours, minutes = divmod(minutes, 60)
                    print(f'Total elapsed time: {hours:02d}:{minutes:02d}:{seconds:02d} ({elapsed:.1f} seconds; includes waiting, compilation and testing)', flush=True)
                return int(failed)
            elif args.command == "plan" or args.command in ('fast-gpu', 'fast-cpu'):
                run = directory(config, provenance(config))
                builds, cases = plan(config, run / "work")
                print(json.dumps(dict(run=str(run), builds=builds, cases=cases), indent=2))
            elif args.command == "profile":
                from .profiling import profile
                run, failed = profile(config, args.nsys)
                print(report(run))
                return int(failed)
            elif args.command == "prepare":
                print(prepare(config))
            else:
                run, failed = measure(config, checking=args.command == "check")
                print(report(run))
                return int(failed)
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(f"bend-bench: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
