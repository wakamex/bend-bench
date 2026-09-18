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
    args = parser.parse_args(argv)
    try:
        if args.command == "report":
            print(report(args.run))
        elif args.command == "compare":
            print(json.dumps(compare(args.before, args.after), indent=2))
        else:
            config = load_config(args.experiment)
            if args.command == "plan":
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
