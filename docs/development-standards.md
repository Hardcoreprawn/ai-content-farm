# Development Standards and Best Practices

## **Line Ending Requirements** ⚠️

**CRITICAL: All files must use Unix line endings (LF) to prevent deployment failures.**

### Problem
Windows line endings (CRLF - `\r\n`) cause failures in:
- Terraform `local-exec` provisioners 
- Shell scripts in CI/CD pipelines
- Azure Function deployments
- Docker container builds

### Solution - Git Configuration

**Set globally (recommended):**
```bash
git config --global core.autocrlf false
git config --global core.eol lf
```

**For this repository:**
```bash
git config core.autocrlf false
git config core.eol lf
```

### VS Code Configuration

Add to `.vscode/settings.json`:
```json
{
  "files.eol": "\n",
  "files.insertFinalNewline": true,
  "files.trimTrailingWhitespace": true
}
```

### File Type Specific Rules

**Always use LF (Unix) line endings for:**
- `.tf` files (Terraform)
- `.sh` files (Shell scripts)
- `.py` files (Python)
- `.json` files (Configuration)
- `.yml/.yaml` files (CI/CD pipelines)
- `.md` files (Documentation)

### Fixing Existing Files

**Check line endings:**
```bash
file filename.tf
# Should show: ASCII text (not "with CRLF line terminators")
```

**Convert CRLF to LF:**
```bash
# Using dos2unix (preferred)
dos2unix filename.tf

# Using sed
sed -i 's/\r$//' filename.tf

# Using tr
tr -d '\r' < filename.tf > filename_fixed.tf
```

**Git attributes file (.gitattributes):**
```
*.tf text eol=lf
*.sh text eol=lf
*.py text eol=lf
*.json text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.md text eol=lf
```

### Verification Before Commit

**Always run before committing:**
```bash
# Check for CRLF in staged files
git diff --cached --check

# Find files with CRLF
find . -name "*.tf" -o -name "*.sh" -o -name "*.py" | xargs file | grep CRLF
```

### IDE/Editor Configuration

**VS Code Extensions:**
- Install "EditorConfig for VS Code"
- Configure "End of Line" setting to "LF"

**Vim/Neovim:**
```vim
set fileformat=unix
set fileformats=unix,dos
```

**Sublime Text:**
```json
{
    "default_line_ending": "unix"
}
```

## **Terraform Best Practices**

### Script Commands
- Use single-line commands instead of heredoc (`<<-EOT`) when possible
- Escape quotes properly: `\"` not `"`
- Test locally before committing

### Local Exec Provisioners
```hcl
# ✅ Good - Single line, no heredoc
provisioner "local-exec" {
  command = "sleep 30 && echo 'done'"
}

# ❌ Bad - Heredoc can introduce line ending issues
provisioner "local-exec" {
  command = <<-EOT
    sleep 30
    echo 'done'
  EOT
}
```

## **Pre-Commit Checklist**

- [ ] Check line endings: `git diff --cached --check`
- [ ] Verify Terraform syntax: `terraform fmt -check`
- [ ] Test scripts locally if modified
- [ ] Ensure VS Code shows "LF" in status bar
- [ ] No trailing whitespace

## **Troubleshooting**

**Symptoms of line ending issues:**
- `command not found: sleep\r`
- Terraform provisioner failures
- Shell script execution errors
- CI/CD pipeline failures

**Quick fix for urgent deployments:**
```bash
# Fix all terraform files
find infra/ -name "*.tf" -exec dos2unix {} \;

# Commit the fix
git add -u && git commit -m "fix: convert line endings to LF"
```

This issue has occurred multiple times - following these standards will prevent future failures.
