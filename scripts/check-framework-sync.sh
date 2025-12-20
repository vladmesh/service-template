#!/bin/bash
# Check if framework/ and template/.framework/framework/ are in sync
# Used in CI to ensure sync-framework was run after framework changes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/framework"
TARGET_DIR="$ROOT_DIR/template/.framework/framework"

echo "Checking framework sync status..."

# Compare directories using diff (excluding __pycache__)
if diff -r \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude=".pytest_cache" \
    --exclude=".mypy_cache" \
    --exclude=".ruff_cache" \
    "$SOURCE_DIR" "$TARGET_DIR" > /dev/null 2>&1; then
    echo "✅ framework/ and template/.framework/framework/ are in sync"
    exit 0
else
    echo "❌ ERROR: framework/ and template/.framework/framework/ are OUT OF SYNC"
    echo ""
    echo "Please run:"
    echo "  make sync-framework"
    echo ""
    echo "Or:"
    echo "  ./scripts/sync-framework-to-template.sh"
    exit 1
fi
