# Commit Message Guidelines

## Overview
This repository enforces clean, professional commit messages for better compatibility and automation.

## 🚫 What's Blocked
- **Emojis** (🚀, ✅, 🔧, etc.)
- **Non-ASCII characters** (accents, symbols, etc.)
- **Unicode characters** that can break CI/CD tools

## ✅ What's Recommended
- **Conventional Commits format**: `type(scope): description`
- **ASCII text only** for maximum compatibility
- **Concise first line** (≤72 characters)
- **Clear, descriptive messages**

## Commit Types
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes
- `perf`: Performance improvements
- `build`: Build system changes

## Examples

### ✅ Good Examples
```
feat: add BuildKit cache mounts for faster container builds
fix: resolve dependency conflicts in pytest requirements
docs: update deployment guide with container registry setup
refactor: optimize pip caching strategy for better performance
ci: add commit message validation hook
```

### ❌ Blocked Examples
```
🚀 feat: add new feature          # Contains emoji
✅ fix: resolved the bug          # Contains emoji
feat: añadir nueva funcionalidad  # Contains non-ASCII characters
```

## Setup
Run this once per developer workspace:
```bash
./scripts/setup-git-hooks.sh
```

## Bypassing (Emergency Only)
To bypass validation temporarily:
```bash
git commit --no-verify -m "emergency fix"
```

## Why These Rules?
- **CI/CD Compatibility**: Many automation tools don't handle emojis well
- **Cross-platform Support**: Ensures messages display correctly everywhere
- **Log Parsing**: Makes automated log analysis more reliable
- **Professional Standard**: Maintains consistent, readable git history
- **Tool Integration**: Better compatibility with git GUIs and terminal tools
