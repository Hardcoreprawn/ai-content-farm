# Critical Development Rules

## Line Endings (CRITICAL)
**ALL files must use Unix line endings (LF) - never CRLF**

- Use `sed -i 's/\r$//' filename` to fix CRLF issues
- Check with `file filename` (should NOT show "with CRLF line terminators")
- This prevents CI/CD deployment failures

## Pre-Commit Check
```bash
git diff --cached --check
```

This recurring issue causes Terraform local-exec and CI/CD failures.
