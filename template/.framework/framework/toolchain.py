"""Pinned toolchain versions used by framework CI and generated project CI.

Single source of truth for the uv setup pins. Workflows cannot import Python, so
they repeat the literals; tests/tooling/test_toolchain_pins.py fails when a
workflow drifts from the values here.
"""

# Major version tag of the setup-uv action. astral-sh keeps a moving major tag.
SETUP_UV_ACTION = "astral-sh/setup-uv@v7"

# Exact uv version. Without it setup-uv resolves "latest" through the GitHub
# Releases API on every run, which fails whenever that API serves an error page.
UV_VERSION = "0.11.29"
