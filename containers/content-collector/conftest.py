import sys
from pathlib import Path

# Ensure this container directory is first on sys.path so tests importing
# top-level modules like `collector` and `main` resolve to the local files.
root = Path(__file__).parent
sys.path.insert(0, str(root))

# Also add repo root so shared `libs` package is importable during tests
repo_root = root.parent.parent
sys.path.insert(0, str(repo_root))
