# Optional cuDF C++ dependency

This locked environment supplies libcudf and its C++ headers and dependencies for the published edit-distance adapter. It is separate from the lightweight benchmark harness environment. The executable calls the native C++ API; Python is used only to install the wheel distribution.

```sh
uv sync --locked --project dependencies/cudf
```

The supplied benchmark configuration points to this environment's Python 3.13 `site-packages` directory. It records the wheel's declared cuDF version and source commit, hashes installed files and preserves the lock hash. See [adapter contracts and validation](../../VENDOR_GPU_LIBRARIES.md).
