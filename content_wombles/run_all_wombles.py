"""
Master runner to execute all content wombles in the current directory.
"""
import os
import glob
import subprocess
from datetime import datetime


def main():
    # Get current directory (content_wombles)
    wombles_dir = os.path.dirname(__file__)

    # Find all python files that look like wombles (exclude this runner)
    pattern = os.path.join(wombles_dir, "*.py")
    scripts = [s for s in glob.glob(
        pattern) if not s.endswith("run_all_wombles.py")]

    if not scripts:
        print("No womble scripts found!")
        return

    print(
        f"Starting womble run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Found {len(scripts)} womble script(s)")

    for script in scripts:
        script_name = os.path.basename(script)
        print(f"\n--- Running womble: {script_name} ---")
        try:
            result = subprocess.run(
                ["python", script], check=True, cwd=wombles_dir)
            print(f"✓ {script_name} completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ {script_name} failed with exit code {e.returncode}")
        except Exception as e:
            print(f"✗ {script_name} failed: {e}")

    print(
        f"\nWomble run completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
