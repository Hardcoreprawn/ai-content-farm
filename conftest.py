import sys
import importlib
from pathlib import Path
from typing import Optional

# Add repo root first so shared top-level imports (like `libs`) are resolvable.
# Keep repo root on sys.path but do NOT globally add individual container dirs.
root = Path(__file__).parent.resolve()
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


def _find_container_dir_for_path(path: Path) -> Optional[Path]:
    """Given a test path, return the containing `containers/<name>` directory if any."""
    p = Path(path).resolve()
    for parent in p.parents:
        # Look for .../containers/<container_name>/...
        if parent.parent and parent.parent.name == "containers":
            return parent
    return None


def _prune_other_container_modules(container_dir: Path) -> None:
    """Remove modules from sys.modules that were loaded from other container dirs.

    This avoids name collisions when different containers expose top-level modules
    with the same name (for example multiple `main.py` files).
    """
    to_remove = []
    for name, mod in list(sys.modules.items()):
        if not mod:
            continue
        mfile = getattr(mod, "__file__", None)
        if not mfile:
            continue
        mpath = Path(mfile).resolve()
        # If the module came from a `containers` directory but not from the
        # active container, mark it for removal so it will be re-imported
        # under the correct container path when needed.
        if "containers" in mpath.parts and str(container_dir) not in str(mpath):
            to_remove.append(name)

    for name in to_remove:
        try:
            del sys.modules[name]
        except KeyError:
            pass


def pytest_runtest_setup(item):
    """Pytest hook: before each test, ensure sys.path is ordered for the test's container.

    We keep repo root on sys.path but place the specific container directory first so
    bare-module imports (e.g. `import main`) resolve to the local container's module.
    Also prune modules loaded from other containers to avoid module-name collisions.
    """
    try:
        test_path = Path(str(item.fspath))
    except Exception:
        return

    container_dir = _find_container_dir_for_path(test_path)
    if not container_dir:
        return

    # Ensure container dir is first on sys.path
    s = str(container_dir)
    if sys.path and sys.path[0] != s:
        if s in sys.path:
            sys.path.remove(s)
        sys.path.insert(0, s)

    # Ensure repo root remains on sys.path (as second entry)
    r = str(root)
    if r in sys.path:
        # move to position 1 (after container dir)
        try:
            sys.path.remove(r)
        except ValueError:
            pass
    sys.path.insert(1, r)

    # Prune modules imported from other containers so subsequent imports load
    # the correct implementation for this test's container.
    _prune_other_container_modules(container_dir)

    # Ensure common top-level module names (that appear across containers)
    # are re-imported from the active container directory so tests that
    # patch by unqualified module name (for example `patch('main.foo')`)
    # operate on the intended module.
    for top_mod in ("main", "collector", "processor", "enricher"):
        try:
            mod = sys.modules.get(top_mod)
            if mod is None or not getattr(mod, "__file__", "").startswith(s):
                # Remove any existing module then import fresh from container dir
                if top_mod in sys.modules:
                    try:
                        del sys.modules[top_mod]
                    except KeyError:
                        pass
                try:
                    importlib.import_module(top_mod)
                except Exception:
                    # Import may fail if module doesn't exist in the container; ignore
                    pass
        except Exception:
            pass

    # Diagnostic: show which file each important top-level module is coming from.
    # This helps debug why patches (e.g., patch('collector.foo')) sometimes
    # target the wrong module when running the full suite.
    try:
        import sys as _sys
        _for_container = s
        # Only print diagnostics when running in verbose pytest output or when
        # the active container is content-collector to minimize noise.
        if "content-collector" in _for_container or _sys.flags.interactive:
            for _m in ("collector", "main", "enricher", "processor"):
                _mod = _sys.modules.get(_m)
                _path = getattr(_mod, "__file__", None) if _mod else None
                if _path:
                    # print to stderr so it appears in pytest output
                    import sys as _sys2
                    _sys2.stderr.write(
                        f"[conftest] resolved module {_m} -> {_path}\n")
                else:
                    import sys as _sys3
                    _sys3.stderr.write(
                        f"[conftest] resolved module {_m} -> (not loaded)\n")

            # Additional: if collector is present, show which callable will be patched
            try:
                _col_mod = _sys.modules.get("collector")
                if _col_mod:
                    _fetch = getattr(_col_mod, "fetch_from_subreddit", None)
                    if _fetch:
                        import sys as _sys4
                        _sys4.stderr.write(
                            f"[conftest] collector.fetch_from_subreddit -> id={id(_fetch)} repr={getattr(_fetch, '__name__', repr(_fetch))} module={getattr(_fetch, '__module__', None)}\n")
            except Exception:
                pass
    except Exception:
        # Do not let diagnostics break the test run
        pass


def pytest_collect_file(file_path, parent):
    """Called for each potential test file during collection.

    Ensure the container directory for the file is first on sys.path so any
    top-level imports inside the test (like `import main`) resolve to the
    correct container implementation.
    """
    try:
        p = Path(str(file_path))
    except Exception:
        return None

    container_dir = _find_container_dir_for_path(p)
    if not container_dir:
        return None

    s = str(container_dir)
    # Place container dir first on sys.path for collection
    if sys.path and sys.path[0] != s:
        if s in sys.path:
            sys.path.remove(s)
        sys.path.insert(0, s)

    # Ensure repo root is second
    r = str(root)
    if r in sys.path:
        try:
            sys.path.remove(r)
        except ValueError:
            pass
    sys.path.insert(1, r)

    # Prune modules imported from other containers so imports happen fresh
    _prune_other_container_modules(container_dir)

    return None
