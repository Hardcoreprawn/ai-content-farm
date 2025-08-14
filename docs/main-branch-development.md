# Main Branch Development Strategy

## 🎯 **Philosophy: Simple, Fast, AI-Friendly**

This project uses a **main-branch development approach** optimized for solo development with AI assistance.

## 🚀 **Workflow**

### **Normal Development:**
1. **Work directly on `main`** for most changes
2. **Push to main** → Automatic production deployment
3. **Fast iterations** with immediate feedback

### **Risky/Experimental Changes:**
1. **Create PR against `main`**
2. **Ephemeral environment auto-deployed** 
3. **Test in isolation** → Merge when ready
4. **Environment auto-destroyed** on PR close

## 🌍 **Environment Strategy**

### **Production** (`main` branch)
- **Trigger**: Push to `main`
- **Infrastructure**: `production.tfvars`
- **Domain**: `ai-content-farm.com` (or similar)
- **Persistence**: Permanent

### **Ephemeral PR Environments**
- **Trigger**: Open/update PR
- **Infrastructure**: `staging.tfvars` + dynamic naming
- **Domain**: `pr-{number}.ai-content-farm.com`
- **Persistence**: Auto-destroyed on PR close
- **Terraform Workspace**: `pr-{number}`

## 🔄 **CI/CD Pipeline**

### **Every Commit to Main:**
```
Push → Security Scan → Container Tests → Deploy Production
```

### **Every PR:**
```
PR Open → Quick Security → Container Tests → Deploy Ephemeral → Integration Tests → PR Comment with URLs
PR Close → Destroy Environment
```

## 🛠 **Commands**

### **Normal Development:**
```bash
git add . && git commit -m "feat: add new feature"
git push origin main  # → Production deployment
```

### **Experimental Development:**
```bash
git checkout -b feature/experiment
git add . && git commit -m "feat: risky experiment"
git push origin feature/experiment
gh pr create --title "Experiment: New Feature" --body "Testing new approach"
# → Ephemeral environment deployed with PR comment containing URLs
```

### **Emergency Production Fix:**
```bash
git add . && git commit -m "fix: critical bug"
git push origin main  # → Immediate production deployment
```

## 📊 **Benefits**

### **For Solo Development:**
- ✅ **No branch management overhead**
- ✅ **Fast feedback loops**
- ✅ **Simple mental model**
- ✅ **Always deployable main**

### **For AI Collaboration:**
- ✅ **Clear, predictable workflows**
- ✅ **Automatic environment provisioning**
- ✅ **Immediate testing feedback**
- ✅ **No complex branching strategies**

### **For Infrastructure:**
- ✅ **Cost-effective** (ephemeral environments)
- ✅ **Isolated testing**
- ✅ **Automatic cleanup**
- ✅ **Production-like testing**

## 🔒 **Safety Measures**

1. **Security scans** on every commit
2. **Container tests** before deployment
3. **Integration tests** in ephemeral environments
4. **Manual approval** for risky changes (via PR review)
5. **Rollback capability** through Git history

## 🏗 **Infrastructure Layout**

```
Production:
  - Resource Group: rg-ai-content-farm-prod
  - App Services: prod-collector, prod-processor, prod-enricher
  - Key Vault: kv-ai-content-farm-prod

Ephemeral (per PR):
  - Resource Group: rg-ai-content-farm-pr-{number}
  - App Services: pr{number}-collector, pr{number}-processor, pr{number}-enricher
  - Key Vault: kv-ai-content-farm-pr{number}
  - Auto-deleted on PR close
```

## 📝 **Migration Notes**

- **Old `develop` branch**: No longer used
- **Old staging environment**: Replaced by ephemeral PR environments
- **Manual staging**: Available via workflow_dispatch (discouraged)

This approach scales perfectly for a solo developer + AI team while maintaining professional CI/CD practices.
