"""Explicit, integrity-checked fast-profile build artifacts and fresh runs."""
import copy
import json
from pathlib import Path
import shutil

from .core import environment, fingerprint, harness_info, hash_file, host_info, write_json

SCHEMA = 'bend-bench-build-v1'


def create(config, output):
    from .experiment import prepare
    output = Path(output).resolve()
    if output.exists():
        raise ValueError(f'Build output already exists: {output}; choose a new directory')
    config = {**config, '_portable_build': True, '_build_directory': str(output)}
    folder = prepare(config)
    # Seal the provenance and exact build recipe as well as binaries and inputs.
    metadata = {name: hash_file(folder / name) for name in ('provenance.json', 'plan.json', 'prepared.json')}
    manifest = dict(schema=SCHEMA, target='cpu' if config['suites'] == ['cpu-regression'] else 'gpu',
                    original_directory=str(folder), metadata=metadata)
    write_json(folder / 'build.json', manifest)
    print('BUILD', folder, flush=True)
    return folder


def inspect(folder):
    from .experiment import artifacts
    folder = Path(folder).resolve()
    manifest = json.loads((folder / 'build.json').read_text())
    if manifest.get('schema') != SCHEMA or manifest.get('target') not in ('cpu', 'gpu'):
        raise ValueError('Not a supported fast-profile build artifact')
    if set(manifest['metadata']) != {'provenance.json', 'plan.json', 'prepared.json'}:
        raise ValueError('Incomplete build metadata')
    for name, digest in manifest['metadata'].items():
        if hash_file(folder / name) != digest:
            raise ValueError(f'Build metadata changed: {name}')
    prepared = json.loads((folder / 'prepared.json').read_text())
    evidence = json.loads((folder / 'provenance.json').read_text())
    if any(p.is_symlink() for p in (folder / 'work').rglob('*')):
        raise ValueError('Build artifacts must not contain symlinks')
    if artifacts(folder / 'work') != prepared['artifacts']:
        raise ValueError('Build artifact integrity check failed')
    if hash_file(folder / 'plan.json') != prepared['plan_sha256']:
        raise ValueError('Build plan changed')
    return manifest, evidence, prepared


def config_from_build(folder, target):
    manifest, evidence, _ = inspect(folder)
    if manifest['target'] != target:
        raise ValueError(f'Cannot use a {manifest["target"]} build with {target} fast')
    config = {k: v for k, v in evidence['config'].items() if not k.startswith('_')}
    config.update(output=str(Path('runs').resolve()), _build_artifact=str(Path(folder).resolve()))
    return config


def runtime_provenance(config):
    folder = Path(config['_build_artifact'])
    manifest, built, prepared = inspect(folder)
    current = host_info()
    # Native CPU code and device binaries are deliberately restricted to a
    # matching host rather than claiming arbitrary-machine portability.
    keys = ['platform', 'cpu', 'topology', 'affinity']
    if config['cuda']:
        keys.append('gpu')
    if any(current[k] != built['host'][k] for k in keys):
        raise ValueError('Build runtime host is incompatible; rebuild on this host')
    for path, digest in prepared['libraries'].items():
        if not Path(path).is_file() or hash_file(path) != digest:
            raise ValueError(f'Build runtime library changed or missing: {path}')
    for path, digest in built['toolkit'].items():
        if '.so' in Path(path).name and (not Path(path).is_file() or hash_file(path) != digest):
            raise ValueError(f'Build CUDA runtime library changed or missing: {path}')
    # Keep compiler identity as build provenance; compiler executables and the
    # Bend checkout are not consulted when executing saved binaries.
    return dict(config=config, sources=built['sources'], tools=built['tools'], toolkit=built['toolkit'],
                host=current, harness=harness_info(), environment=environment(),
                build_artifact=dict(manifest_sha256=hash_file(folder / 'build.json'),
                                    build_fingerprint=prepared['fingerprint']))


def prepare_run(config):
    from .experiment import artifacts, directory, validate
    evidence = runtime_provenance(config)
    run = directory(config, evidence)
    if (run / 'prepared.json').exists():
        validate(config, run, evidence)
        return run
    source = Path(config['_build_artifact'])
    manifest, _, original = inspect(source)
    run.mkdir(parents=True, exist_ok=True)
    print('Reusing build:', source, flush=True)
    shutil.copytree(source / 'work', run / 'work', dirs_exist_ok=True)
    old = str(Path(manifest['original_directory']) / 'work')
    new = str(run / 'work')

    def relocate(value):
        if isinstance(value, str):
            return new + value[len(old):] if value.startswith(old + '/') else value
        if isinstance(value, list):
            return [relocate(v) for v in value]
        if isinstance(value, dict):
            return {k: relocate(v) for k, v in value.items()}
        return value

    plan = relocate(json.loads((source / 'plan.json').read_text()))
    write_json(run / 'plan.json', plan)
    write_json(run / 'provenance.json', evidence)
    hashes = artifacts(run / 'work')
    if hashes != original['artifacts']:
        raise ValueError('Build changed while copying')
    # Recheck runtime and original artifact after copying, before measurements.
    if runtime_provenance(config) != evidence:
        raise ValueError('Build or runtime changed during reuse')
    libraries = copy.deepcopy(original['libraries'])
    write_json(run / 'prepared.json', dict(
        fingerprint=fingerprint({'provenance': evidence, 'artifacts': hashes, 'libraries': libraries}),
        artifacts=hashes, libraries=libraries, plan_sha256=hash_file(run / 'plan.json')))
    return run
