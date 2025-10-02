# Next Improvements Plan - Quick Start Guide

## 📋 Overview

Following the successful completion of the 7-phase code quality improvement plan, this guide provides a quick start for the next set of improvements.

**Full Plan:** `devlog/20251002_068_next_improvements_plan.md`

---

## 🎯 Goals

| Phase | Goal | Timeline | Effort |
|-------|------|----------|--------|
| **Phase 1** | Type Hints Expansion (46.7% → 80%+) | Week 1-2 | 10h |
| **Phase 2** | Integration Tests (15+ new tests) | Week 2-3 | 12h |
| **Phase 3** | Performance Profiling Automation | Week 3-4 | 8h |
| **Phase 4** | Advanced Testing Patterns | Week 4 | 5h |

**Total:** 35 hours over 4 weeks

---

## 🚀 Quick Start

### 1. Run Setup Script
```bash
bash scripts/setup_next_improvements.sh
```

This will:
- ✅ Install required dependencies (mypy, hypothesis, mutmut, etc.)
- ✅ Create directory structure (tests/integration/, tests/property/, etc.)
- ✅ Generate baseline metrics
- ✅ Create template files for each phase

### 2. Verify Setup
```bash
# Check type checking works
mypy core/file_handler.py --config-file pyproject.toml

# Check pytest plugins
pytest --co -q tests/

# Check baseline metrics
cat performance_data/baseline.json
```

### 3. Start Phase 1
```bash
# See current type hint coverage
python scripts/collect_metrics.py | grep "Type Hint"

# Start adding type hints to core modules
# Target: core/progress_manager.py first
```

---

## 📊 Current Metrics (Baseline)

```
Code Quality:
├── Core: 2,730 LOC (8 files)
├── Utils: 982 LOC (7 files)
├── Documentation: 96.7% (58/60 functions)
└── Type Hints: 46.7% (28/60 functions) ⬅️ Target: 80%+

Tests:
├── Total: 603 tests (603 passed, 3 skipped)
├── Coverage: 60%+
└── Integration Tests: 6 tests ⬅️ Target: +15 tests
```

---

## 📝 Phase-by-Phase Checklist

### Phase 1: Type Hints Expansion (Week 1-2)

**Priority Files:**
- [x] `core/progress_manager.py` - Add type hints to all methods ✅
- [x] `core/volume_processor.py` - Complete partial coverage ✅
- [ ] `core/thumbnail_manager.py` - Add missing hints (complex, many dependencies)
- [x] `utils/worker.py` - Add signal type annotations ✅
- [x] `utils/file_utils.py` - Complete coverage ✅

**Commands:**
```bash
# Check specific file
mypy core/progress_manager.py --strict

# Check all core
mypy core/ --config-file pyproject.toml

# Update metrics
python scripts/collect_metrics.py
```

**Success Criteria:**
- ✅ 80%+ functions have type hints
- ✅ `mypy --strict` passes on core/ and utils/
- ✅ No `type: ignore` comments

---

### Phase 2: Integration Tests (Week 2-3)

**New Test Files:**
- [ ] `tests/integration/test_thumbnail_complete_workflow.py`
  - Full workflow test (load → generate → verify)
  - Rust fallback scenario
  - Large dataset (1000+ images)

- [ ] `tests/integration/test_ui_workflows.py`
  - Complete UI workflow
  - Settings persistence
  - Error recovery

- [ ] `tests/integration/test_export_complete.py`
  - OBJ export with real data
  - Image stack export

- [ ] `tests/integration/test_performance_benchmarks.py`
  - Thumbnail generation speed
  - Memory usage monitoring

**Commands:**
```bash
# Run integration tests only
pytest tests/integration/ -v

# Run with benchmarks
pytest tests/integration/ --benchmark-only
```

**Success Criteria:**
- ✅ 15+ new integration tests
- ✅ Full workflow coverage
- ✅ Performance baselines established

---

### Phase 3: Performance Profiling (Week 3-4)

**Tasks:**
- [ ] Create `scripts/profiling/profile_performance.py`
- [ ] Create `scripts/profiling/collect_performance_metrics.py`
- [ ] Add `.github/workflows/performance-tracking.yml`
- [ ] Create visualization script

**Commands:**
```bash
# Profile thumbnail generation
python scripts/profiling/profile_performance.py

# Collect metrics
python scripts/profiling/collect_performance_metrics.py

# View results
python scripts/profiling/visualize_performance.py
```

**Success Criteria:**
- ✅ Automated profiling in CI/CD
- ✅ Performance regression alerts (>20%)
- ✅ Historical tracking

---

### Phase 4: Advanced Testing (Week 4)

**New Testing Patterns:**
- [ ] Property-based testing (Hypothesis)
  - File: `tests/property/test_image_properties.py`
  - 10+ property tests

- [ ] Mutation testing (mutmut)
  - Config: `.mutmut-config.py` (already created)
  - Target: 80%+ mutation score

- [ ] Snapshot testing (pytest-snapshot)
  - File: `tests/snapshots/test_ui_snapshots.py`
  - UI layout verification

**Commands:**
```bash
# Run property tests
pytest tests/property/ -v

# Run mutation testing
mutmut run --paths-to-mutate=core/,utils/
mutmut results
mutmut html

# Run snapshot tests
pytest tests/snapshots/ --snapshot-update
```

**Success Criteria:**
- ✅ 10+ property tests
- ✅ 80%+ mutation score
- ✅ Key UI snapshots captured

---

## 📈 Progress Tracking

### Week 1-2 Progress
- [x] Phase 1 started
- [x] Type hints: 60% coverage in core/ (target: 80%)
- [x] Type hints: 68% coverage in utils/ (target: 80%)
- [x] Files completed: 4/5 (progress_manager, volume_processor, worker, file_utils)
- [x] mypy passes on completed files: ✅

### Week 2-3 Progress
- [ ] Phase 2 started
- [ ] Integration tests: __/15 (target: 15+)
- [ ] Workflows tested: __/4
- [ ] Benchmarks: ❌ / ✅

### Week 3-4 Progress
- [ ] Phase 3 started
- [ ] Profiling scripts: __/4
- [ ] CI/CD integration: ❌ / ✅
- [ ] Performance dashboard: ❌ / ✅

### Week 4 Progress
- [ ] Phase 4 started
- [ ] Property tests: __/10 (target: 10+)
- [ ] Mutation score: __%  (target: 80%)
- [ ] Snapshot tests: ❌ / ✅

---

## 🔧 Useful Commands

### Development
```bash
# Type checking
mypy core/ utils/ --config-file pyproject.toml

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Collect metrics
python scripts/collect_metrics.py

# Format code
black .
isort .
```

### Quality Gates
```bash
# Run pre-commit hooks
pre-commit run --all-files

# Check specific file
pre-commit run --files core/progress_manager.py

# Update hooks
pre-commit autoupdate
```

### Benchmarking
```bash
# Run benchmarks
pytest tests/benchmarks/ --benchmark-only

# Compare benchmarks
pytest-benchmark compare

# Save baseline
pytest tests/benchmarks/ --benchmark-save=baseline
```

---

## 📚 Reference Documents

1. **Full Plan:** `devlog/20251002_068_next_improvements_plan.md`
2. **Previous Plan:** `devlog/20251002_067_code_quality_improvement_plan.md`
3. **Setup Script:** `scripts/setup_next_improvements.sh`
4. **Metrics Script:** `scripts/collect_metrics.py`

---

## 🎯 Success Metrics

**Overall Goals:**
- ✅ Type hint coverage: 80%+ (from 46.7%)
- ✅ Integration tests: 15+ new tests
- ✅ Performance monitoring: Automated
- ✅ Test quality: 80%+ mutation score
- ✅ No performance regressions >20%

**Timeline:**
- Week 1-2: Phase 1 complete
- Week 2-3: Phase 2 complete
- Week 3-4: Phase 3 complete
- Week 4: Phase 4 complete

---

## 🤝 Contributing

When implementing improvements:

1. **Create feature branch**
   ```bash
   git checkout -b improvement/phase-1-type-hints
   ```

2. **Follow incremental approach**
   - One file at a time
   - Test after each change
   - Commit frequently

3. **Update metrics**
   ```bash
   python scripts/collect_metrics.py
   ```

4. **Run quality checks**
   ```bash
   pre-commit run --all-files
   pytest tests/ -v
   ```

5. **Create PR with metrics**
   - Include before/after metrics
   - Reference the improvement plan
   - Add performance impact

---

## ❓ FAQ

**Q: Do I need to run setup script?**
A: Yes, it installs dependencies and creates necessary structure.

**Q: Can I skip phases?**
A: Phases 1-2 are foundational. Phases 3-4 are optional but recommended.

**Q: How long will this take?**
A: ~35 hours over 4 weeks for all phases.

**Q: What if tests fail after adding type hints?**
A: Use `# type: ignore` sparingly and document why. Better to fix the issue.

**Q: How to track progress?**
A: Use checkboxes in this file and run `python scripts/collect_metrics.py`

---

**Last Updated:** 2025-10-02
**Status:** Ready to Start
**Next Action:** Run `bash scripts/setup_next_improvements.sh`
