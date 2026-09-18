"""Finite application contracts and independent correctness oracles."""

from collections import deque
from functools import lru_cache
import json
import math
from pathlib import Path
import random


def hash32(x):
    x = ((x ^ (x >> 16)) * 2246822507) & 0xFFFFFFFF
    x = ((x ^ (x >> 13)) * 3266489909) & 0xFFFFFFFF
    return x ^ (x >> 16)


def graph(depth):
    n = 1 << depth
    # Directed, fixed-in-degree random graph. Sorted/deduplicated edge list is
    # shared by queue BFS, GAP and Gunrock; Bend generates the same neighbors.
    return sorted(
        {(hash32(v * 8 + j) & (n - 1), v) for v in range(n) for j in range(8)}
    )


def distances(n, edges):
    outgoing = [[] for _ in range(n)]
    for a, b in edges:
        outgoing[a].append(b)
    result = [0xFFFFFFFF] * n
    result[0] = 0
    queue = deque([0])
    while queue:
        a = queue.popleft()
        for b in outgoing[a]:
            if result[b] == 0xFFFFFFFF:
                result[b] = result[a] + 1
                queue.append(b)
    return result


def lines(m, n, k):
    return [
        tuple((y + j * dy) * n + x + j * dx for j in range(k))
        for y in range(m)
        for x in range(n)
        for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1))
        if 0 <= y + (k - 1) * dy < m and 0 <= x + (k - 1) * dx < n
    ]


def mnk_oracle(m, n, k):
    winning = lines(m, n, k)

    def won(board, player):
        return any(all(board[i] == player for i in line) for line in winning)

    @lru_cache(maxsize=300000)
    def oracle(board, player):
        if won(board, 3 - player):
            return 0
        if 0 not in board:
            return 1
        best = 0
        for i, value in enumerate(board):
            if not value:
                child = board[:i] + (player,) + board[i + 1 :]
                best = max(best, 2 - oracle(child, 3 - player))
                if best == 2:
                    break
        return best

    return won, oracle


def mnk_corpus(m, n, k, empty):
    won, oracle = mnk_oracle(m, n, k)
    rand = random.Random(20260917 + m * 1000 + n * 100 + k * 10 + empty)
    boards, seen = [], set()
    for attempt in range(100000):
        if len(boards) == 16:
            break
        board, player, history = [0] * (m * n), 1, []
        for _ in range(m * n - empty):
            legal = [i for i, v in enumerate(board) if not v]
            rand.shuffle(legal)
            for i in legal:
                board[i] = player
                if not won(board, player):
                    history.append(i)
                    player = 3 - player
                    break
                board[i] = 0
            else:
                break
        key = tuple(board)
        if board.count(0) != empty or key in seen:
            continue
        seen.add(key)
        masks = [
            sum(1 << i for i, v in enumerate(board) if v == p)
            for p in (player, 3 - player)
        ]
        boards.append(
            dict(
                board=board,
                mover=player,
                masks=masks,
                history=history,
                value=oracle(key, player),
            )
        )
    if len(boards) != 16:
        raise ValueError("Unable to generate 16 distinct legal nonterminal positions")
    return boards


def pricing_reference(n, steps):
    # FP64 oracle implements the financial model independently of the FP32 ports.
    values = []
    for i in range(n):
        state = 1 + hash32(i + 1) % 2147483646
        spot, total = 100.0, 0.0
        for _ in range(steps):
            state = (16807 * state) % 2147483647
            u = ((state >> 8) + 0.5) / 8388608
            state = (16807 * state) % 2147483647
            v = ((state >> 8) + 0.5) / 8388608
            z = math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * v)
            spot *= math.exp(0.03 / steps + 0.2 / math.sqrt(steps) * z)
            total += spot
        values.append(math.exp(-0.05) * max(0, total / steps - 100))
    return values


def render(template, replacements):
    for key, value in replacements.items():
        template = template.replace("@" + key + "@", str(value))
    if "@" in template:
        raise ValueError("Unexpanded application template")
    return template


def stage(config, work):
    assets = Path(__file__).parent / "assets/gpu"
    ports = work / "ports"
    ports.mkdir(exist_ok=True)
    if "pricing" in config["suites"]:
        for depth in config["pricing_depths"]:
            for steps in config["pricing_steps"]:
                name = f"pricing-{depth}-{steps}"
                source = render(
                    (assets / "pricing.bend").read_text(),
                    dict(
                        DEPTH=depth,
                        STEPS=steps,
                        DRIFT=repr(0.03 / steps),
                        VOL=repr(0.2 / math.sqrt(steps)),
                    ),
                )
                (ports / (name + ".bend")).write_text(source)
                # The slow independent oracle runs once during preparation, never
                # inside a timed sample. Persist all payoffs, not just a mean.
                reference = pricing_reference(1 << depth, steps)
                reference.insert(0, math.fsum(reference) / len(reference))
                (ports / (name + ".json")).write_text(json.dumps(reference))
    if "bfs" in config["suites"]:
        for depth in config["bfs_depths"]:
            name, n = f"bfs-{depth}", 1 << depth
            edges = graph(depth)
            (ports / (name + ".el")).write_text("".join(f"{a} {b}\n" for a, b in edges))
            (ports / (name + ".mtx")).write_text(
                f"%%MatrixMarket matrix coordinate real general\n{n} {n} {len(edges)}\n"
                + "".join(f"{a + 1} {b + 1} 1\n" for a, b in edges)
            )
            (ports / (name + ".json")).write_text(json.dumps(distances(n, edges)))
            (ports / (name + ".bend")).write_text(
                render((assets / "bfs.bend").read_text(), dict(DEPTH=depth, MASK=n - 1))
            )
    if "mnk" in config["suites"]:
        for m, n, k, empty in config["mnk_games"]:
            name = f"mnk-{m}-{n}-{k}-{empty}"
            corpus = mnk_corpus(m, n, k, empty)
            masks = [sum(1 << i for i in line) for line in lines(m, n, k)]
            (ports / (name + ".corpus.json")).write_text(json.dumps(corpus, indent=2))
            (ports / (name + ".json")).write_text(
                json.dumps([p["value"] for p in corpus])
            )
            winner = "False{}"
            for mask in masks:
                winner = f"Bool.or(U32.is_eq(U32.and(board, {mask}), {mask}), {winner})"

            # A balanced selector avoids an artificial 16-deep lookup chain.
            def select(items, start=0):
                if len(items) == 1:
                    a, b = items[0]["masks"]
                    return f"({a}, {b})"
                half = len(items) // 2
                return f"Bool.pick(U32 & U32, U32.is_lt(i, {start + half}), {select(items[:half], start)}, {select(items[half:], start + half)})"

            (ports / (name + ".bend")).write_text(
                render(
                    (assets / "mnk.bend").read_text(),
                    dict(
                        WIN=winner, CELLS=m * n, EMPTY=empty, POSITIONS=select(corpus)
                    ),
                )
            )
            folder = ports / name
            folder.mkdir(exist_ok=True)
            (folder / "mnk-data.h").write_text(
                f"constexpr int cells={m * n},empty={empty};\nARRAY uint32_t masks[]={{"
                + ",".join(map(str, masks))
                + "};\nARRAY uint32_t positions[16][2]={"
                + ",".join("{" + ",".join(map(str, p["masks"])) + "}" for p in corpus)
                + "};\n"
            )


def plan(config, work, build, case, cases, bend_build, gpu_reason):
    tools = config["tools"]
    cuda = Path(tools["cuda_path"])
    flags = ["-O3", "-march=native", "-ffp-contract=off"]

    def add(name, suite, args, contract, baseline, gpu=None):
        binary = bend_build(work / "ports" / f"{name}.bend", name, config["cuda"])
        start = len(cases)
        for threads in config["threads"]:
            case(
                suite,
                name,
                "bend",
                threads,
                binary,
                ["--gpu", "off", "--threads", threads],
                "",
                contract=contract,
            )
            case(
                suite,
                name,
                baseline[0],
                threads,
                baseline[1],
                args,
                "",
                contract=contract,
            )
        if config["cuda"]:
            case(
                suite,
                name,
                "bend-cuda",
                max(config["threads"]),
                str(binary) + "-cuda",
                ["--gpu", config["gpu_heap"], "--threads", max(config["threads"])],
                "",
                gpu_reason,
                contract,
            )
            if gpu:
                case(suite, name, gpu[0], 1, gpu[1], gpu[2], "", gpu_reason, contract)
        for item in cases[start:]:
            item["expected_vector"] = str(work / "ports" / f"{name}.json")

    if "pricing" in config["suites"]:
        cpu = work / "build/pricing-omp"
        gpu = work / "build/pricing-cuda"
        build([tools["cxx"], *flags, "-fopenmp", work / "gpu/pricing.cpp", "-o", cpu])
        if config["cuda"] and not gpu_reason:
            build(
                [
                    tools["cuda_cxx"],
                    "-std=c++17",
                    "-x",
                    "cuda",
                    *flags,
                    f"--cuda-path={cuda}",
                    f"--cuda-gpu-arch={config['gpu_arch']}",
                    "-Wno-unknown-cuda-version",
                    "-DCCCL_DISABLE_NVTX",
                    f"-I{config['cccl']['path']}/cub",
                    f"-I{config['cccl']['path']}/thrust",
                    f"-I{config['cccl']['path']}/libcudacxx/include",
                    work / "gpu/pricing.cpp",
                    f"-L{cuda}/lib64",
                    "-lcudart",
                    f"-Wl,-rpath,{cuda}/lib64",
                    "-o",
                    gpu,
                ]
            )
        for depth in config["pricing_depths"]:
            for steps in config["pricing_steps"]:
                name = f"pricing-{depth}-{steps}"
                args = [1 << depth, steps]
                add(
                    name,
                    "pricing",
                    args,
                    dict(
                        workload="arithmetic-asian-call",
                        paths=1 << depth,
                        steps=steps,
                        spot=100,
                        strike=100,
                        rate=0.05,
                        volatility=0.2,
                        maturity=1,
                        rng="hashed path index + Park-Miller + Box-Muller; local control",
                        output="mean option price followed by every discounted payoff",
                        arithmetic="FP32 paths; FP64 OpenMP sum, FP32 Bend/CUB reduction",
                        vector_kind="f32-bits",
                        abs_tolerance=0.002,
                        rel_tolerance=0.0001,
                    ),
                    ("local-openmp", cpu),
                    ("local-cuda", gpu, args),
                )
    if "bfs" in config["suites"]:
        cpu = work / "build/gap-bfs"
        gpu = work / "build/gunrock-bfs"
        build(
            [
                tools["cxx"],
                "-std=c++17",
                *flags,
                "-fopenmp",
                f"-I{config['gap']['path']}/src",
                work / "gpu/gap-bfs.cpp",
                "-o",
                cpu,
            ]
        )
        if config["cuda"] and not gpu_reason:
            includes = [
                f"-I{config[k]['path']}/{p}"
                for k, p in [
                    ("gunrock", "include"),
                    ("moderngpu", "src"),
                    ("cccl", "cub"),
                    ("cccl", "thrust"),
                    ("cccl", "libcudacxx/include"),
                ]
            ]
            # Upstream lists mmio.cpp as a host C++ target source. Compile it
            # separately, without Clang's CUDA wrapper headers.
            mmio = work / "build/gunrock-mmio.o"
            build(
                [
                    tools["cxx"],
                    "-std=c++17",
                    *flags,
                    f"-I{config['gunrock']['path']}/include",
                    f"-I{cuda}/include",
                    "-c",
                    Path(config["gunrock"]["path"])
                    / "include/gunrock/io/detail/mmio.cpp",
                    "-o",
                    mmio,
                ]
            )
            build(
                [
                    tools["cuda_cxx"],
                    "-std=c++17",
                    *flags,
                    f"--cuda-path={cuda}",
                    f"--cuda-gpu-arch={config['gpu_arch']}",
                    f"-DSM_TARGET={config['gpu_arch'].removeprefix('sm_')}",
                    "-DCCCL_DISABLE_NVTX",
                    "-DESSENTIALS_COLLECT_METRICS=0",
                    "-Wno-unknown-cuda-version",
                    *includes,
                    work / "gpu/gunrock-bfs.cu",
                    mmio,
                    f"-L{cuda}/lib64",
                    "-lcudart",
                    f"-Wl,-rpath,{cuda}/lib64",
                    "-o",
                    gpu,
                ]
            )
        for depth in config["bfs_depths"]:
            name = f"bfs-{depth}"
            add(
                name,
                "bfs",
                ["-f", work / "ports" / f"{name}.el"],
                dict(
                    workload="directed-random-graph-bfs",
                    vertices=1 << depth,
                    in_degree=8,
                    source=0,
                    vector_kind="u32",
                    output="all distances",
                    input="hash32(v*8+j)&(n-1) -> v; deduplicated; implicit Bend input",
                ),
                ("gap-openmp", cpu),
                ("gunrock-cuda", gpu, [work / "ports" / f"{name}.mtx"]),
            )
    if "mnk" in config["suites"]:
        for m, n, k, empty in config["mnk_games"]:
            name = f"mnk-{m}-{n}-{k}-{empty}"
            cpu = work / "build" / f"{name}-omp"
            build(
                [
                    tools["cxx"],
                    *flags,
                    "-fopenmp",
                    f"-I{work}/ports/{name}",
                    work / "gpu/mnk.cpp",
                    "-o",
                    cpu,
                ]
            )
            gpu = work / "build" / f"{name}-cuda"
            if config["cuda"] and not gpu_reason:
                build(
                    [
                        tools["cuda_cxx"],
                        "-x",
                        "cuda",
                        *flags,
                        f"--cuda-path={cuda}",
                        f"--cuda-gpu-arch={config['gpu_arch']}",
                        "-Wno-unknown-cuda-version",
                        f"-I{work}/ports/{name}",
                        work / "gpu/mnk.cpp",
                        f"-L{cuda}/lib64",
                        "-lcudart",
                        f"-Wl,-rpath,{cuda}/lib64",
                        "-o",
                        gpu,
                    ]
                )
            add(
                name,
                "mnk",
                [],
                dict(
                    workload="exact-mnk-endgames",
                    m=m,
                    n=n,
                    k=k,
                    empty=empty,
                    positions=16,
                    seed=20260917,
                    vector_kind="u32",
                    output="mover loss=0/draw=1/win=2",
                    rules="alternating, no gravity, at least k, terminal wins stop play",
                    algorithms="Bend/OpenMP/CUDA alpha-beta; Bend/OpenMP parallel positions, CUDA parallel root moves",
                ),
                ("local-alpha-beta-openmp", cpu),
                ("local-alpha-beta-cuda", gpu, []),
            )
