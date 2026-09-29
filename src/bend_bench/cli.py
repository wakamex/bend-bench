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
    parser.add_argument('experiment', type=Path, nargs='?')
    builds = parser.add_mutually_exclusive_group()
    builds.add_argument('--build-only', action='store_true', help='Compile a reusable artifact without running benchmarks; requires --output')
    builds.add_argument('--build', type=Path, help='Run a saved build without compiler tools or source checkouts')
    parser.add_argument('--output', type=Path, help='Build artifact directory with --build-only, or runs directory with --build')
    parser.add_argument('--plan', action='store_true', help='Preview the fixed portfolio without running it')
    parser.add_argument('--repetitions', type=int, help='Measured executions per configuration (positive integer; overrides TOML)')
    parser.add_argument('--baseline', type=Path, help='Previous run directory or saved result/comparison JSON')
    parser.add_argument('--resume', type=Path, help='Resume this run directory instead of collecting a fresh run')
    parser.add_argument('--threshold', type=float, default=10, help='Flag slowdowns above this percentage (default: 10)')
    if target == 'gpu':
        parser.add_argument('--exclusive-gpu', action='store_true', help='Reject other GPU processes and overlapping GPU activity')
        parser.add_argument('--wait-idle', action='store_true', help='Wait for 120 seconds of GPU inactivity before preparing the run')


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
    checking = commands.add_parser('compiler-check', help='Compare two Bend checkouts: emitted output and the test lane')
    checking.add_argument('base', type=Path, help='Bend checkout to compare against')
    checking.add_argument('candidate', type=Path, help='Bend checkout with the change')
    checking.add_argument('--bun', default='bun', help='Bun executable that runs each checkout (default: bun on PATH)')
    checking.add_argument('--output', type=Path, help='Write the full comparison as JSON')
    checking.add_argument('--only', help='Only programs whose path matches this regular expression')
    checking.add_argument('--jobs', type=int, help='Parallel programs (default: half the CPUs)')
    checking.add_argument('--identical', action='store_true', help='Also fail when any emitted output differs, for refactors')
    for name in ('regression-report', 'gpu-report', 'cpu-report'):
        regression_report = commands.add_parser(name, help='Readable results and optional regression comparison')
        regression_report.add_argument('run', type=Path)
        regression_report.add_argument('--baseline', type=Path)
        regression_report.add_argument('--threshold', type=float, default=10)
    args = parser.parse_args(argv)
    try:
        if args.command == 'compiler-check':
            from .compiler_check import run as check_run
            import shutil
            bun = shutil.which(args.bun)
            if bun is None:
                raise ValueError(f'Bun executable not found: {args.bun}')
            for checkout in (args.base, args.candidate):
                if not (checkout / 'bend2/main.ts').is_file():
                    raise ValueError(f'Not a Bend checkout (no bend2/main.ts): {checkout}')
            text, failed = check_run(args.base, args.candidate, bun, args.output, args.only, args.jobs, args.identical)
            print(text, end='')
            return int(failed)
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
            fast_command = args.command in ('fast-gpu', 'fast-cpu')
            if fast_command:
                if (args.build_only or args.build) and args.plan:
                    raise ValueError('Build options cannot be combined with --plan')
                if args.build_only and (not args.output or args.resume or args.baseline):
                    raise ValueError('--build-only requires --output and cannot use --resume or --baseline')
                if args.output and not (args.build_only or args.build):
                    raise ValueError('--output requires --build-only or --build')
                if args.build and args.experiment:
                    raise ValueError('--build uses the saved configuration; omit the experiment file')
            if fast_command and args.build:
                from .builds import config_from_build
                config = config_from_build(args.build, args.command.removeprefix('fast-'))
                if args.output:
                    config['output'] = str(args.output.resolve())
            else:
                config = load_config(args.experiment or Path(args.command + '.toml'))
            if args.command in ('fast-gpu', 'fast-cpu'):
                if args.plan and args.resume:
                    raise ValueError('--plan and --resume cannot be combined')
                expected_suite = args.command.removeprefix('fast-') + '-regression'
                if config['suites'] != [expected_suite]:
                    raise ValueError(f'{args.command} requires suites = ["{expected_suite}"]')
                if args.command == 'fast-gpu' and (args.exclusive_gpu or args.wait_idle):
                    config['require_idle_gpu'] = True
                    config.pop('gpu_resident', None)
                if args.repetitions is not None:
                    if args.repetitions < 1:
                        raise ValueError('--repetitions must be at least 1')
                    config['repetitions'] = args.repetitions
            if args.command in ('fast-gpu', 'fast-cpu') and not args.plan:
                from .fast import run as fast_run
                started = time.perf_counter()
                try:
                    if args.build_only:
                        from .builds import create
                        folder, failed = create(config, args.output), False
                    else:
                        folder, failed = fast_run(config, args.baseline, args.threshold, wait_for_idle=getattr(args, 'wait_idle', False), resume=args.resume)
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
