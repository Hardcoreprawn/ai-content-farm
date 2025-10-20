# Quality Gate Test Suite - Testing Strategy

## Overview
Comprehensive test suite for quality gate modules. Focus on **input/output contracts**, **defensive programming**, and **preventing accidental changes**.

## Test Coverage by Module

### ✅ `test_quality_config.py` - 39 tests
**Focus**: Configuration stability and defaults

**Test Categories**:
1. **Configuration Constants** (8 tests)
   - All critical constants exist
   - Types are correct (sets, lists, dicts)
   - Values are in valid ranges
   - Example: `test_length_thresholds` - MIN < OPTIMAL < MAX

2. **Default Configuration** (7 tests)
   - All required top-level keys present
   - Configuration structure valid
   - Default values within acceptable ranges
   - Example: `test_default_config_min_score` - 0.0 ≤ score ≤ 1.0

3. **Regex Patterns** (4 tests)
   - Patterns compile successfully
   - Patterns match expected cases
   - Case-insensitivity works
   - Example: `test_listicle_regex_matches` - "10 ways to", "top 5 best"

4. **Helper Functions** (7 tests)
   - Paywall detection works correctly
   - Helper functions handle edge cases
   - Invalid inputs return False (fail-safe)
   - Example: `test_is_paywall_domain_known_domain` - detects wired.com

5. **Input Validation** (5 tests)
   - All patterns/keywords are strings
   - All weights are numeric
   - No empty patterns
   - Defensive against data corruption

**Key Contracts Protected**:
- Configuration must never be empty
- Thresholds must be ordered correctly
- Helper functions must be defensive (handle None, invalid types)
- Default config must be immutable (overrides don't mutate original)

---

### ✅ `test_quality_dedup.py` - 30 tests
**Focus**: Deduplication correctness and input/output contracts

**Test Categories**:
1. **Hash Content** (10 tests)
   - Hash is consistent (deterministic)
   - Hash is different for different input
   - Hash format is correct (64-char hex)
   - Handles empty/invalid inputs gracefully
   - Example: `test_hash_consistent` - hash("A", "B") == hash("A", "B")

2. **Filter Duplicates In Batch** (12 tests)
   - Removes identical items
   - Preserves unique items
   - Maintains insertion order
   - Skips invalid items (non-dict, missing fields)
   - Handles edge cases (empty lists, None values)
   - Doesn't mutate input
   - Example: `test_removes_identical_items` - two identical → one kept

3. **Input/Output Contracts** (4 tests)
   - Output is always a list
   - Output items are always dicts
   - Hash returns string
   - Hash returns 64-char hex or empty string
   - Example: `test_filter_duplicates_output_is_list` - isinstance(result, list)

4. **Edge Cases** (4 tests)
   - Same content from different sources → deduplicated
   - Whitespace variations handled
   - Mixed valid/invalid items
   - Long content (10K chars) handled correctly
   - Example: `test_different_sources_same_content` - Reddit + Medium deduped

**Key Contracts Protected**:
- Hash must be deterministic and consistent
- Dedup must preserve order
- Dedup must handle invalid input gracefully
- Input list must never be mutated
- All output items must be valid dicts
- Hash must always return 64-char hex or empty string

---

### 🚧 `test_quality_detectors.py` - NOT YET CREATED
**Focus**: Detection functions (paywall, comparison, listicle)

**Planned Test Categories**:
1. **Paywall Detection** (8 tests)
   - Known paywall domains detected
   - Paywall keywords detected
   - Unknown domains/keywords not flagged
   - Case-insensitive matching
   - Real-world edge cases

2. **Comparison Detection** (8 tests)
   - "vs" patterns detected
   - Price ranges detected
   - Pros/cons sections detected
   - Non-comparisons not flagged

3. **Listicle Detection** (8 tests)
   - "10 ways to" detected
   - "top 5 best" detected
   - "here are 7 things" detected
   - Non-listicles not flagged

4. **Content Quality Assessment** (6 tests)
   - All detections run
   - Results structured correctly
   - Suitability flag accurate
   - Edge cases handled

---

### 🚧 `test_quality_scoring.py` - NOT YET CREATED
**Focus**: Quality scoring and ranking

**Planned Test Categories**:
1. **Quality Score Calculation** (8 tests)
   - Base score starts at 1.0
   - Penalties applied correctly
   - Score clamped to 0-1 range
   - Detection results used
   - Edge cases (no title, no content)

2. **Scoring With Penalties** (6 tests)
   - Paywall penalty: -0.40
   - Comparison penalty: -0.25
   - Listicle penalty: -0.20
   - Length penalties applied
   - Cumulative penalties work

3. **Ranking and Diversity** (6 tests)
   - Items sorted by score (highest first)
   - Diversity filtering (max 3 per source)
   - Top N filtering (max 20 results)
   - Edge cases (empty list, all same source)

4. **Metadata Addition** (4 tests)
   - Quality score added to items
   - Detections added to items
   - Original items not mutated
   - All fields preserved

---

### 🚧 `test_quality_gate.py` - NOT YET CREATED
**Focus**: Main pipeline and integration

**Planned Test Categories**:
1. **Validation Layer** (6 tests)
   - Required fields checked
   - Invalid items rejected
   - Error messages returned
   - Invalid types handled

2. **Pipeline Integration** (8 tests)
   - Validate → Dedupe → Detect → Score → Rank flow
   - Results structure correct
   - Stats calculated correctly
   - Errors captured

3. **Input/Output Contracts** (6 tests)
   - process_items returns dict with status
   - Items are list of dicts
   - Stats have required keys
   - Errors list present

4. **End-to-End Scenarios** (8 tests)
   - Full pipeline with mock data
   - Edge cases (empty input, all invalid)
   - Large batch processing
   - Error handling and recovery

---

## Test Execution

### Run All Tests
```bash
cd /workspaces/ai-content-farm/containers/content-collector
python -m pytest tests/test_quality_*.py -v
```

### Run Specific Module
```bash
python -m pytest tests/test_quality_config.py -v
python -m pytest tests/test_quality_dedup.py -v
```

### Run with Coverage
```bash
python -m pytest tests/test_quality_*.py --cov=quality_config --cov=quality_dedup
```

---

## Test Results Summary

| Module | Tests | Status | Purpose |
|--------|-------|--------|---------|
| `quality_config.py` | 39 | ✅ PASS | Configuration stability, defaults, thresholds |
| `quality_dedup.py` | 30 | ✅ PASS | Hash consistency, deduplication correctness |
| `quality_detectors.py` | ~30 | 🚧 TODO | Detection functions, real-world cases |
| `quality_scoring.py` | ~24 | 🚧 TODO | Scoring, ranking, diversity filtering |
| `quality_gate.py` | ~28 | 🚧 TODO | Pipeline integration, end-to-end |
| **Total** | **~151** | **69/151** | **Defensive input/output contracts** |

---

## Key Defensive Testing Principles Applied

### 1. Input Contracts
- ✅ Invalid types handled gracefully (return False/empty/None)
- ✅ Missing fields skipped
- ✅ Non-dict items filtered out
- ✅ Empty collections handled

### 2. Output Contracts
- ✅ Output type always matches expected (list, dict, string, int)
- ✅ Lists always contain only correct item types
- ✅ All required fields present
- ✅ Values in valid ranges

### 3. Mutation Prevention
- ✅ Input lists/dicts never modified
- ✅ Configuration overrides don't mutate defaults
- ✅ Hash is deterministic (same input → same output)

### 4. Edge Cases
- ✅ Empty inputs
- ✅ None values
- ✅ Wrong types
- ✅ Very large inputs (10K+ char strings)
- ✅ Mixed valid/invalid items

### 5. Fail-Safe Design
- ✅ Functions don't crash on invalid input
- ✅ Graceful degradation (skip invalid, continue processing)
- ✅ Informative error messages
- ✅ Defensive type checking

---

## Critical Tests (Must Always Pass)

These tests protect against accidental breaking changes:

1. **Config Thresholds Ordered** (`test_length_thresholds`)
   - MIN_CONTENT_LENGTH < OPTIMAL < MAX
   - If this breaks, scoring becomes unreliable

2. **Hash Deterministic** (`test_hash_consistent`)
   - Same input must produce same hash
   - If this breaks, dedup doesn't work

3. **No Input Mutation** (`test_no_mutation_of_input`)
   - Input list length never changes
   - If this breaks, it breaks the pipeline

4. **Default Config Structure** (`test_default_config_structure`)
   - All required keys present
   - If this breaks, service won't start

5. **Dedup Removes Duplicates** (`test_removes_identical_items`)
   - Two identical items → one kept
   - If this breaks, articles republished

---

## Next Steps

1. ✅ Create `test_quality_config.py` - 39 tests
2. ✅ Create `test_quality_dedup.py` - 30 tests
3. 🚧 Create `test_quality_detectors.py` - ~30 tests
4. 🚧 Create `test_quality_scoring.py` - ~24 tests
5. 🚧 Create `test_quality_gate.py` - ~28 tests
6. 🚧 Run full test suite: `python -m pytest tests/test_quality_*.py`
7. 🚧 Verify all 151 tests pass
8. 🚧 Check coverage is >95% for critical paths
