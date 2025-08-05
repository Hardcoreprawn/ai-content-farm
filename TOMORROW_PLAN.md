# Tomorrow's Action Plan - August 6, 2025

## 🚀 **Morning Priority (30 minutes)**

### **1. Fix OIDC & Deploy to Staging**
```bash
# Run the fix script
./scripts/fix-oidc-environment-credentials.sh

# Trigger deployment
git commit --allow-empty -m "trigger: Re-run pipeline after OIDC fix"
git push

# Monitor deployment
gh run list --limit 1
```

### **2. Verify End-to-End Content Generation**
```bash
# Once staging is deployed, test the function
curl -X POST https://your-function-app.azurewebsites.net/api/GetHotTopics

# Check generated content
az storage blob list --account-name <storage> --container-name content
```

---

## 🔧 **Script Audit & Cleanup (2 hours)**

### **Files to Review & Consolidate:**

#### **Current Redundancy Analysis:**
```bash
# Check for duplicate functionality:
scripts/setup-environments.sh          # 52 lines - GitHub env setup
scripts/setup-environments-fixed.sh    # 47 lines - Same but with JSON fix
scripts/fix-oidc-environment-credentials.sh  # 35 lines - OIDC credential addition

# Questions to answer:
# 1. Can these be merged into one comprehensive script?
# 2. What does Makefile currently do vs what should it do?
# 3. Are there any unused or redundant scripts?
```

#### **Makefile Review:**
```bash
# Current Makefile analysis needed:
cat Makefile

# Questions:
# - Does it handle full environment setup?
# - Is remote state management included?
# - Are there clear, single-purpose targets?
# - Does it integrate with the CI/CD pipeline properly?
```

#### **Proposed Refactor:**
```bash
# New structure:
scripts/
├── bootstrap.sh              # One-time setup: Azure + GitHub + Terraform backend
├── deploy.sh                 # Manual deployment trigger
├── validate.sh               # Health check all systems
└── utils/
    ├── oidc-setup.sh         # OIDC credential management
    ├── secrets-setup.sh      # Key Vault secret management
    └── cost-check.sh         # Standalone cost analysis

# Updated Makefile targets:
make setup          # Full environment bootstrap
make deploy         # Deploy to staging
make test           # Run all tests
make validate       # Health check
make clean          # Cleanup resources
```

---

## 📝 **Content Pipeline Enhancement Planning (1 hour)**

### **Current State Documentation:**
```bash
# Analyze current GetHotTopics function:
functions/GetHotTopics/index.js

# Document current workflow:
# 1. What does it do exactly?
# 2. Where are the complexity hotspots?
# 3. What are natural separation points?
# 4. How much data does it process?
```

### **Enhancement Design Decisions:**
```yaml
Content Flow Questions:
  - Current: "Basic summary from Reddit posts"
  - Desired: "Engaging article with images and citations"
  - How sophisticated should the AI enhancement be?
  - What image sources should we integrate? (DALL-E, Unsplash, etc.)
  - How do we handle content attribution and citations?

Function Decomposition:
  - Should each function be a separate Azure Function App?
  - Or multiple functions within the same app?
  - How do we handle orchestration between functions?
  - What's the data flow and storage strategy?
```

---

## 🤖 **MCP Agent Planning (30 minutes)**

### **Research & Design:**
```yaml
MCP Integration Questions:
  - What types of maintenance tasks are most common?
  - How should alerts be structured for agent processing?
  - What's the PR template format for agent pickup?
  - How do we ensure agents don't create conflicts?

Alert → PR → Agent Workflow:
  - Azure Monitor → Logic App → GitHub API → MCP Agent
  - What alert types should trigger automated PRs?
  - How do we structure PR descriptions for agent consumption?
  - What safety mechanisms prevent runaway automation?
```

### **Prototype Requirements:**
```bash
# Start with simple agent use case:
# 1. Cost alert triggers PR creation
# 2. MCP agent reviews and suggests optimizations
# 3. Human approval before implementation

# Example PR structure:
# Title: "[AUTO] Cost optimization suggestions"
# Labels: ["automation", "cost-optimization", "needs-review"]
# Content: Structured data for agent processing
```

---

## ⏰ **Timeline for Tomorrow**

| Time | Task | Duration | Priority |
|------|------|----------|----------|
| 9:00 AM | Fix OIDC & deploy to staging | 30 min | 🔴 Critical |
| 9:30 AM | Script audit & refactoring | 2 hours | 🟡 High |
| 11:30 AM | Content pipeline enhancement design | 1 hour | 🟡 High |
| 12:30 PM | **Testing infrastructure improvements** | **1.5 hours** | **🟡 High** |
| 2:00 PM | MCP agent planning & research | 30 min | 🟢 Medium |
| 2:30 PM | Documentation updates | 30 min | 🟢 Medium |

---

## 🧪 **Testing Infrastructure Improvements (Added Task)**

### **Current State: Inadequate Test Coverage**
```bash
# What we have:
tests/integration/test_pipeline.py  # 97 lines - basic endpoint checks only

# What's missing:
- Unit tests for core logic
- Performance benchmarks  
- Comprehensive security testing
- Contract testing for external APIs
- Error handling validation
```

### **Priority Testing Tasks for Tomorrow:**

#### **1. Unit Tests (30 minutes)**
```bash
tests/unit/
├── test_reddit_parser.py       # Test Reddit post parsing logic
├── test_content_generator.py   # Test AI content generation
├── test_error_handling.py      # Test error scenarios
└── test_data_validation.py     # Test input/output validation
```

#### **2. Enhanced Integration Tests (30 minutes)**
```bash
tests/integration/
├── test_end_to_end_pipeline.py # Full content workflow testing
├── test_azure_service_health.py # Azure service connectivity
└── test_external_apis.py       # Reddit/OpenAI API reliability
```

#### **3. Performance Baselines (30 minutes)**
```bash
tests/performance/
├── test_function_execution_limits.py # Max execution time validation
├── test_memory_usage.py              # Memory consumption tracking
└── test_cost_per_execution.py        # Cost baseline establishment
```

#### **4. CI/CD Pipeline Integration (30 minutes)**
```yaml
# Add to consolidated-pipeline.yml:
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - run: pip install pytest pytest-cov
    - run: pytest tests/unit/ --cov=functions --cov-report=xml
    
  performance-tests:
    needs: unit-tests
    runs-on: ubuntu-latest  
    steps:
    - run: pytest tests/performance/ --benchmark-only
```

---

## 📋 **Success Criteria for Tomorrow**

### **Must Have (Critical):**
- ✅ Staging environment fully deployed and functional
- ✅ Scripts consolidated and simplified
- ✅ **Comprehensive testing strategy implemented**
- ✅ Clear next steps for content enhancement

### **Should Have (Important):**
- ✅ Makefile provides clean environment setup
- ✅ **Unit tests covering core business logic**
- ✅ **Performance baselines established**
- ✅ Content pipeline enhancement plan documented
- ✅ MCP agent integration strategy defined

### **Nice to Have (Bonus):**
- ✅ First decomposed function extracted
- ✅ **Testing integrated into CI/CD pipeline**
- ✅ Alert → PR automation prototype
- ✅ Performance baseline established

---

## 🔗 **Key References for Tomorrow**

- **Current Status**: `PROJECT_STATUS.md`
- **Technical Vision**: `TECHNICAL_ROADMAP.md`
- **OIDC Fix**: `scripts/fix-oidc-environment-credentials.sh`
- **Pipeline Status**: https://github.com/Hardcoreprawn/ai-content-farm/actions

Ready to evolve from MVP to production-grade automated content platform! 🚀
