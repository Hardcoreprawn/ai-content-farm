import sys
from pathlib import Path

root = Path(__file__).parent
# Ensure this container directory is first on sys.path so tests importing
# top-level modules like `main` and `processor` resolve to the local files.
sys.path.insert(0, str(root))

# Also add repo root so shared `libs` package is importable during tests
repo_root = root.parent.parent
sys.path.insert(0, str(repo_root))
