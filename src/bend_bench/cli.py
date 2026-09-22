import argparse
import json
from pathlib import Path
import sys

from .core import load_config, provenance
from .experiment import compare, directory, measure, prepare, report
from .suites import plan


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
    fast = commands.add_parser('fast-gpu', help='Check and measure the fixed Bend GPU regression portfolio')
    fast.add_argument('experiment', type=Path, nargs='?', default=Path('fast-gpu.toml'))
    fast.add_argument('--plan', action='store_true', help='Preview the fixed 22 cases without running them')
    fast.add_argument('--baseline', type=Path, help='Previous run directory or saved result/comparison JSON')
    fast.add_argument('--threshold', type=float, default=10, help='Flag slowdowns above this percentage (default: 10)')
    gpu_report = commands.add_parser('gpu-report', help='Readable GPU results and optional regression comparison')
    gpu_report.add_argument('run', type=Path)
    gpu_report.add_argument('--baseline', type=Path)
    gpu_report.add_argument('--threshold', type=float, default=10)
    args = parser.parse_args(argv)
    try:
        if args.command == 'gpu-report':
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
            if args.command == 'fast-gpu' and not args.plan:
                from .fast_gpu import run as fast_run
                folder, failed = fast_run(config, args.baseline, args.threshold)
                return int(failed)
            elif args.command == "plan" or args.command == 'fast-gpu':
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
