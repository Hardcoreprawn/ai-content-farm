# Emoji Usage Policy

## Overview

This project prohibits the use of emojis in YAML files, particularly GitHub Actions workflows and action definitions.

## Why No Emojis in YAML?

1. **Encoding Issues**: Emojis can cause UTF-8 encoding problems in CI/CD pipelines
2. **Logging Problems**: Many logging systems don't handle emojis properly, leading to garbled output
3. **Automation Complexity**: Emojis complicate string parsing and scripting operations
4. **Cross-Platform Issues**: Different systems may render emojis differently or not at all
5. **Terminal Compatibility**: Not all terminals and shells handle emojis correctly

## Automated Enforcement

We use automated checks to prevent emojis from being introduced:

- **Local Development**: `make check-emojis` or `make lint-workflows`
- **CI/CD Pipeline**: Automatically runs during workflow validation
- **Script Location**: `scripts/check-emojis.sh`

## Recommended Alternatives

Instead of emojis, use clear text indicators:

### Status Indicators
- ✅ → `[PASS]`
- ❌ → `[FAIL]`  
- ⚠️ → `[WARN]`
- 🔍 → `[SCAN]`

### Process Indicators
- 🔄 → `[PROCESS]`
- 🚀 → `[DEPLOY]`
- 🔨 → `[BUILD]`
- 🧪 → `[TEST]`

### Resource Indicators
- 🐳 → `[CONTAINER]`
- 📦 → `[PACKAGE]`
- 🔑 → `[KEY]`
- 💰 → `[COST]`

### Information Indicators
- 📊 → `[STATS]`
- 📋 → `[REPORT]`
- 📄 → `[FILE]`
- 💡 → `[TIP]`

## Where Emojis Are Acceptable

Emojis may be used in:

- **Markdown documentation** (like this file)
- **README files**
- **Issue and PR descriptions**
- **Commit messages** (sparingly)
- **Comments in source code** (not recommended but not enforced)

## Fixing Emoji Violations

If the emoji check fails:

1. **Identify the files**: The script will show which files contain emojis
2. **Replace with text alternatives**: Use the recommendations above
3. **Test locally**: Run `make check-emojis` to verify fixes
4. **Commit changes**: The CI pipeline will validate the fix

## Implementation Details

The emoji checker uses Perl-compatible regular expressions to detect Unicode emoji ranges:

```bash
[\x{1F300}-\x{1F5FF}\x{1F600}-\x{1F64F}\x{1F680}-\x{1F6FF}\x{1F700}-\x{1F77F}\x{1F780}-\x{1F7FF}\x{1F800}-\x{1F8FF}\x{1F900}-\x{1F9FF}\x{1FA00}-\x{1FA6F}\x{1FA70}-\x{1FAFF}\x{2600}-\x{26FF}\x{2700}-\x{27BF}]
```

This covers most standard emoji Unicode blocks while being conservative enough to avoid false positives.
