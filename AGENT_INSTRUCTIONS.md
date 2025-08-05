# Copilot Agent Instructions

## Project Context
- This is a minimal Python project to fetch trending topics from a handful of popular technology subreddits and save them to `hot-topics.json`.
- The devcontainer is intentionally slim, with only Python 3, pip, make, and git installed.
- Node.js and JavaScript files have been removed; the project is now Python-only.
- The main script is `get-hot-topics.py`.
- Dependencies are listed in `requirements.txt` (currently just `requests`).
- The README.md has Python-centric instructions.

## Workflow
1. After a devcontainer rebuild, always check that Python 3 and pip are available.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the script:
   ```bash
   python3 get-hot-topics.py
   ```
4. Output will be in `hot-topics.json` (JSON object: subreddit -> list of hot post titles).

## Next Steps
- If the user asks for more features, automation, or AI integration, build on this Python foundation.
- Always check this file and the project log for context before making major changes.

---
_Last updated: July 23, 2025_
