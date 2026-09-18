"""Workload contracts and explicit build recipes for the packaged suites."""

from decimal import Decimal, ROUND_CEILING
from pathlib import Path
import re
import shutil
import sys

from .core import execute, hash_file


def vendor_outputs(bend):
    expected = {}
    for line in (Path(bend) / "bench/runtime/_pin_/apple_m4.txt").read_text().splitlines():
        cells = [s.strip() for s in line.split("|")]
        if len(cells) == 8 and cells[-2].isdigit():
            expected[cells[1]] = cells[-2]
    if len(expected) != 16:
        raise ValueError("Expected 16 vendor output contracts; review changed upstream format")
    return expected


def stage(config, work):
    assets = Path(__file__).parent / "assets"
    shutil.copytree(assets, work, dirs_exist_ok=True)
    for name, key in (("upstream", "bend"), ("bots", "bots")):
        if key in config and not (work / name).exists():
            (work / name).symlink_to(config[key]["path"], target_is_directory=True)
    (work / "build").mkdir(exist_ok=True)
    if set(config['suites']) & {'pricing', 'mnk', 'bfs'}:
        from .applications import stage as stage_applications
        stage_applications(config, work)
    if "hotspot" in config["suites"]:
        from .hotspot import stage_rodinia
        (work / "ports").mkdir(exist_ok=True)
        stage_rodinia(Path(config["rodinia"]["path"]), work)
    if "cub" in config["suites"]:
        (work / "ports").mkdir(exist_ok=True)
        for depth in config["gpu_depths"]:
            for name in ("sort", "reduce"):
                if name == "sort":
                    source = (Path(config["bend"]["path"]) / "bench/runtime/tree-bitonic/main.bend").read_text()
                    old, new = "bsort!(23n,", f"bsort!({depth}n,"
                else:
                    source = (assets / "gpu/reduce.bend").read_text()
                    old, new = "sum!(18n,", f"sum!({depth}n,"
                if source.count(old) != 1:
                    raise ValueError(f"GPU template changed: {old}")
                (work / "ports" / f"cub-{name}-{depth}.bend").write_text(source.replace(old, new))
    if "vendor" in config["suites"]:
        result = execute([sys.executable, work / "baselines/make_openmp.py"])
        if result["returncode"]:
            raise ValueError(result["stderr"])
    if "uts" in config["suites"]:
        for dataset in config["uts_inputs"]:
            values = (work / "bots/inputs/uts" / f"{dataset}.input").read_text().splitlines()[0].split()
            root, probability, branching, seed, granularity, *_ = values
            if granularity != "1":
                raise ValueError("UTS port currently supports compute granularity 1")
            source = (assets / "ports/uts.bend").read_text()
            replacements = {"case True{}: 8n": f"case True{{}}: {branching}n",
                            "268167021": str(int((Decimal(probability) * 2**31).to_integral_value(rounding=ROUND_CEILING))),
                            "root(42)": f"root({seed})", "U32.to_nat(2000)": f"U32.to_nat({root})",
                            "U32.to_nat(100000)": "U32.to_nat(1000000)"}
            for old, new in replacements.items():
                if source.count(old) != 1:
                    raise ValueError(f"UTS template changed: {old}")
                source = source.replace(old, new)
            (work / "ports" / f"uts-{dataset}.bend").write_text(source)


def plan(config, work):
    work = Path(work)
    bend = Path(config["bend"]["path"])
    tools = config["tools"]
    cc, cxx, bun = tools["cc"], tools["cxx"], tools["bun"]
    cuda = Path(tools["cuda_path"])
    builds, cases = [], []
    flags = ["-O3", "-march=native", "-ffp-contract=off"]
    gpu_reason = None
    if config["cuda"] and (not (cuda / "include/cuda.h").exists() or not shutil.which("nvidia-smi")):
        gpu_reason = "CUDA toolkit or NVIDIA driver utility unavailable"

    def build(command):
        builds.append(list(map(str, command)))

    def case(suite, workload, implementation, threads, binary, args, expected, reason=None, contract=None):
        cpus = config["cpus"][:threads]
        env = {"OMP_NUM_THREADS": str(threads), "OMP_PROC_BIND": "true", "OMP_PLACES": "threads", "OMP_STACKSIZE": "64M"}
        cases.append(dict(id=f"{suite}/{workload}/{implementation}/{threads}", suite=suite,
                          workload=workload, implementation=implementation, threads=threads,
                          command=["taskset", "-c", ",".join(map(str, cpus)), str(binary), *map(str, args)],
                          env=env, expected_regex=expected, unsupported=reason,
                          contract=contract or dict(workload=workload, expected_regex=expected)))
        if suite == "vendor":
            folder = bend / "bench/runtime" / workload
            cases[-1]["contract"]["sources"] = {str(p.relative_to(folder)): hash_file(p)
                                                for p in folder.rglob("*") if p.is_file()}

    def bend_build(source, name, gpu=False):
        cfile = work / "build" / f"{name}.c"
        binary = work / "build" / name
        build([bun, bend / "bend2/main.ts", source, "-o", cfile])
        build([cc, "-std=c11", *flags, cfile, "-lpthread", "-lm", "-o", binary])
        if gpu and not gpu_reason:
            # NVRTC dlopens its builtins library. DT_RPATH also applies to
            # that indirect lookup; DT_RUNPATH only resolves direct deps.
            build([cc, "-std=c11", *flags, "-DBEND_CUDA=1", f"-I{cuda}/include", f"-L{cuda}/lib64", cfile,
                   "-lpthread", "-lm", "-lcuda", "-lnvrtc", f"-Wl,--disable-new-dtags,-rpath,{cuda}/lib64", "-o", str(binary) + "-cuda"])
            build([str(binary) + "-cuda", "--gpu-build"])
        return binary

    if set(config['suites']) & {'pricing', 'mnk', 'bfs'}:
        from .applications import plan as plan_applications
        plan_applications(config, work, build, case, cases, bend_build, gpu_reason)

    if "hotspot" in config["suites"]:
        rodinia = Path(config["rodinia"]["path"])
        reference = work / "build/hotspot-reference"
        omp = work / "build/hotspot-openmp"
        gpu = work / "build/hotspot-cuda"
        for binary, extra in ((reference, ["-DHOTSPOT_REFERENCE"]), (omp, [])):
            build([cxx, *flags, "-fopenmp", f"-I{work}/gpu", *extra, work / "gpu/hotspot-driver.cpp", "-o", binary])
        if config["cuda"] and not gpu_reason:
            build([tools["cuda_cxx"], "-x", "cuda", *flags, f"--cuda-path={cuda}",
                   f"--cuda-gpu-arch={config['gpu_arch']}", "-Wno-unknown-cuda-version", "-DHOTSPOT_CUDA",
                   f"-I{rodinia}/cuda/hotspot", work / "gpu/hotspot-driver.cpp", f"-L{cuda}/lib64", "-lcudart", "-o", gpu])
        for n in config["hotspot_sizes"]:
            for steps in config["hotspot_steps"]:
                name = f"hotspot-{n}-{steps}"
                build([sys.executable, "-m", "bend_bench.hotspot", work, n, steps, rodinia])
                bend_binary = bend_build(work / "ports" / (name + ".bend"), name, config["cuda"])
                inputs = [rodinia / "data/hotspot" / f"{kind}_{n}" for kind in ("temp", "power")]
                contract = dict(workload="rodinia-hotspot", size=n, steps=steps,
                                inputs={p.name: hash_file(p) for p in inputs},
                                arithmetic="F32, no FMA; CUDA preserves upstream mixed intermediates",
                                boundary="clamped", timestep="Rodinia CUDA", output="all F32 bit patterns",
                                tolerance="abs_error <= 0.0001 + 1e-6 * abs(reference)")
                start = len(cases)
                case("hotspot", name, "scalar-reference", 1, reference, [n, steps, 1, *inputs], "", contract=contract)
                for threads in config["threads"]:
                    case("hotspot", name, "openmp-corrected", threads, omp, [n, steps, threads, *inputs], "", contract=contract)
                    case("hotspot", name, "bend", threads, bend_binary, ["--gpu", "off", "--threads", threads], "", contract=contract)
                if config["cuda"]:
                    case("hotspot", name, "bend-cuda", max(config["threads"]), str(bend_binary)+"-cuda",
                         ["--gpu", config["gpu_heap"], "--threads", max(config["threads"])], "", gpu_reason, contract)
                    for pyramid in config["hotspot_pyramids"]:
                        case("hotspot", name, f"rodinia-pyramid{pyramid}-cuda", 1, gpu,
                             [n, steps, pyramid, *inputs], "", gpu_reason, contract)
                for item in cases[start:]:
                    item["expected_bits"] = str(work / "ports" / (name + ".bits"))

    if "cub" in config["suites"]:
        cccl = Path(config["cccl"]["path"])
        binary = work / "build/cub"
        ref = work / "build/cub-reference"
        build([cxx, "-std=c++17", *flags, work / "gpu/reference.cpp", "-o", ref])
        if not gpu_reason:
            build([tools["cuda_cxx"], "-std=c++17", *flags, f"--cuda-path={cuda}",
                   f"--cuda-gpu-arch={config['gpu_arch']}", "-Wno-unknown-cuda-version",
                   f"-I{cccl}/cub", f"-I{cccl}/thrust", f"-I{cccl}/libcudacxx/include",
                   work / "gpu/cub.cu", f"-L{cuda}/lib64", "-lcudart", "-o", binary])
        pins = {"sort": {12: 3231932071, 18: 2086754763, 23: 3787129428},
                "reduce": {12: 3813199453, 18: 302983778, 23: 2494634048}}
        for name in ("sort", "reduce"):
            for depth in config["gpu_depths"]:
                workload = f"{name}-{depth}"
                contract = dict(workload=name, size=2**depth, input="vendor-xorshift-index-u32",
                                arithmetic="wrapping-u32", expected=pins[name][depth])
                expected = str(pins[name][depth])
                bend_binary = bend_build(work / "ports" / f"cub-{workload}.bend", f"cub-{workload}", True)
                case("cub", workload, "serial-cpp", 1, ref, [name, depth], expected, contract=contract)
                case("cub", workload, "cub-cuda", 1, binary, [name, depth], expected, gpu_reason, contract)
                cases[-1]["check_args"] = ["verify"]
                case("cub", workload, "bend-cuda", max(config["threads"]), str(bend_binary) + "-cuda",
                     ["--threads", max(config["threads"]), "--gpu", config["gpu_heap"]], expected, gpu_reason, contract)

    if "vendor" in config["suites"]:
        outputs = vendor_outputs(bend)
        names = config.get("vendor", list(outputs))
        if not names or set(names) - outputs.keys():
            raise ValueError("vendor must select known benchmark names")
        for name in names:
            source = bend / "bench/runtime" / name
            expected = re.escape(outputs[name])
            binary = bend_build(source / "main.bend", name, config["cuda"])
            serial = work / "build" / f"{name}-serial"
            omp = work / "build" / f"{name}-omp"
            build([cc, "-std=c11", *flags, source / "main.c", "-lm", "-o", serial])
            if name in ("tree-bitonic", "tree-radix"):
                build([cxx, *flags, "-fopenmp", f"-DRADIX={int(name == 'tree-radix')}", work / "baselines/sort-omp.cpp", "-o", omp])
            else:
                build([cc, "-std=gnu11", *flags, "-fopenmp", work / "baselines" / f"{name}-omp.c", "-lm", "-o", omp])
            case("vendor", name, "serial-c", 1, serial, [], expected)
            for n in config["threads"]:
                case("vendor", name, "bend", n, binary, ["--threads", n, "--gpu", "off"], expected)
                case("vendor", name, "openmp", n, omp, [], expected)
            if config["cuda"]:
                case("vendor", name, "bend-cuda", max(config["threads"]), str(binary) + "-cuda",
                     ["--threads", max(config["threads"]), "--gpu", config["gpu_heap"]], expected, gpu_reason)
                if name == "gameoflife":
                    gpu_binary = work / "build/gameoflife-conventional-cuda"
                    if not gpu_reason:
                        build([tools["cuda_cxx"], *flags, f"--cuda-path={cuda}", f"--cuda-gpu-arch={config['gpu_arch']}",
                               "-Wno-unknown-cuda-version", work / "baselines/gameoflife-cuda.cu", f"-L{cuda}/lib64", "-lcudart", "-o", gpu_binary])
                    case("vendor", name, "conventional-cuda", 1, gpu_binary, [], expected, gpu_reason)

    if "uts" in config["suites"]:
        bots = Path(config["bots"]["path"])
        for mode in ("serial", "omp-tasks"):
            folder = bots / mode / "uts"
            defines = {"CDATE": "pinned", "CMESSAGE": "bend-bench UTS", "CC": cc, "LD": cc,
                       "CFLAGS": " ".join(flags + ["-fopenmp"]), "LDFLAGS": "-fopenmp -lm"}
            build([cc, "-std=gnu11", *flags, "-fopenmp", f"-I{bots}/common", f"-I{folder}",
                   *[f'-D{k}="{v}"' for k, v in defines.items()], bots / "common/bots_main.c", bots / "common/bots_common.c",
                   folder / "uts.c", folder / "brg_sha1.c", "-lm", "-o", work / "build" / f"uts-{mode}"])
        optimized = work / "build/uts-cutoff"
        build([cc, "-std=gnu11", *flags, "-fopenmp", work / "baselines/uts-omp.c", bots / "omp-tasks/uts/brg_sha1.c",
               f"-I{bots}/common", "-lm", "-o", optimized])
        for dataset in config["uts_inputs"]:
            data = bots / "inputs/uts" / f"{dataset}.input"
            parameters = data.read_text().splitlines()[0].split()
            nodes = parameters[5]
            contract = dict(workload="uts-" + dataset, parameters=parameters, expected_nodes=nodes, fuel=1000000)
            binary = bend_build(work / "ports" / f"uts-{dataset}.bend", "uts-" + dataset)
            verified = rf"(?=.*Tree size\s*=\s*{nodes}\b).*Verification\s*= successful\s*.*"
            case("uts", dataset, "serial-c", 1, work / "build/uts-serial", ["-f", data, "-c"], verified, contract=contract)
            for n in config["threads"]:
                case("uts", dataset, "bend", n, binary, ["--threads", n, "--gpu", "off"], re.escape(nodes + " 0"), contract=contract)
                case("uts", dataset, "openmp", n, work / "build/uts-omp-tasks", ["-f", data, "-c"], verified, contract=contract)
                for cutoff in config["uts_cutoffs"]:
                    case("uts", dataset, f"openmp-cutoff-{cutoff}", n, optimized, [data, cutoff], nodes, contract=contract)
    return builds, cases
