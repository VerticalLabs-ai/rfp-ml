# Codebase Improvements Report

## Summary
This document identifies opportunities for code quality improvements across the codebase, focusing on patterns we've been standardizing:
1. Lambda defaults in SQLAlchemy columns
2. F-string logging statements (should use printf-style for lazy evaluation)

---

## 1. Lambda Defaults in SQLAlchemy Columns

### Status: ⚠️ Still Needs Fixing
**File:** `api/app/models/database.py`

The following columns still use `lambda: []` or `lambda: {}` instead of `list`/`dict`:

**Lines with `lambda: []`:**
- Line 358: `items = Column(JSON, default=lambda: [])`
- Line 407: `certifications = Column(JSON, default=lambda: [])`
- Line 408: `naics_codes = Column(JSON, default=lambda: [])`
- Line 409: `core_competencies = Column(JSON, default=lambda: [])`
- Line 410: `past_performance = Column(JSON, default=lambda: [])`
- Line 509: `key_insights = Column(JSON, default=lambda: [])`
- Line 510: `related_sections = Column(JSON, default=lambda: [])`
- Line 598: `email_recipients = Column(JSON, default=lambda: [])`
- Line 766: `naics_codes = Column(JSON, default=lambda: [])`
- Line 767: `psc_codes = Column(JSON, default=lambda: [])`
- Line 771: `business_types = Column(JSON, default=lambda: [])`
- Line 888: `citations = Column(JSON, default=lambda: [])`

**Lines with `lambda: {}`:**
- Line 338: `event_metadata = Column(JSON, default=lambda: {})`
- Line 359: `summary = Column(JSON, default=lambda: {})`
- Line 671: `delivery_status = Column(JSON, default=lambda: {})`
- Line 675: `context_data = Column(JSON, default=lambda: {})`
- Line 728: `category_stats = Column(JSON, default=lambda: {})`
- Line 731: `performance_stats = Column(JSON, default=lambda: {})`

**Note:** Line 597 has `default=lambda: ["in_app"]` which should remain as-is since it has a non-empty default value.

---

## 2. F-String Logging Statements

### Status: 🔄 Many Files Need Conversion

Found **304 f-string logging statements** across the codebase. These should be converted to printf-style for lazy evaluation.

### High Priority Files (Most Occurrences):

#### `src/agents/scrapers/beaconbid_scraper.py` (30+ occurrences)
- Lines: 176, 194, 247, 251, 259, 297, 301, 354, 395, 399, 440, 505, 509, 610, 628, 647, 656, 675, 714, 731, 739, 821, 825, 941, 943, 1064

#### `api/app/routes/rfps.py` (7 occurrences)
- Lines: 175, 178, 405, 496, 715, 731, 1223

#### `api/app/worker/tasks/alerts.py` (5 occurrences)
- Lines: 35, 52, 176, 335, 412, 437

#### `api/app/routes/generation.py` (5 occurrences)
- Lines: 529, 557, 571, 650, 719, 773

#### `src/agents/submission_agent.py` (15+ occurrences)
- Lines: 105, 118, 160, 201, 209, 219, 224, 231, 241, 248, 277, 294, 311, 325, 340, 344, 349

#### `api/app/routes/predictions.py` (10+ occurrences)
- Lines: 59, 78, 93, 186, 252, 262, 274, 280, 287, 365, 372

#### `src/rag/chroma_rag_engine.py` (10+ occurrences)
- Lines: 71, 72, 75, 80, 169, 281, 294, 301, 312, 315, 345, 347, 374

### Other Files with F-String Logging:
- `src/compliance/compliance_checklist.py` (1 occurrence)
- `api/app/routes/documents.py` (4 occurrences)
- `api/app/worker/tasks/predictions.py` (4 occurrences)
- `api/app/routes/alerts.py` (4 occurrences)
- `api/app/routes/pipeline.py` (2 occurrences)
- `api/app/routes/jobs.py` (4 occurrences)
- `api/app/routes/rag.py` (3 occurrences)
- `api/app/worker/tasks/generation.py` (3 occurrences)
- `api/app/services/background_tasks.py` (5 occurrences)
- `api/app/routes/chat.py` (2 occurrences)
- `src/utils/config_loader.py` (4 occurrences)

---

## 3. Recommended Action Plan

### Phase 1: Critical Files (High Traffic/Performance Impact)
1. ✅ `api/app/services/streaming.py` - **COMPLETED**
2. ✅ `api/app/routes/scraper.py` - **COMPLETED**
3. ⚠️ `api/app/models/database.py` - **NEEDS FIXING** (lambda defaults)
4. 🔄 `src/agents/scrapers/beaconbid_scraper.py` - Convert logging
5. 🔄 `api/app/routes/rfps.py` - Convert logging

### Phase 2: Worker Tasks (Background Processing)
6. 🔄 `api/app/worker/tasks/alerts.py`
7. 🔄 `api/app/worker/tasks/predictions.py`
8. 🔄 `api/app/worker/tasks/generation.py`

### Phase 3: Remaining Routes
9. 🔄 `api/app/routes/generation.py`
10. 🔄 `api/app/routes/predictions.py`
11. 🔄 Other route files

### Phase 4: Core Services
12. 🔄 `src/agents/submission_agent.py`
13. 🔄 `src/rag/chroma_rag_engine.py`
14. 🔄 Other service files

---

## 4. Conversion Pattern

### Lambda Defaults:
```python
# Before
items = Column(JSON, default=lambda: [])
summary = Column(JSON, default=lambda: {})

# After
items = Column(JSON, default=list)
summary = Column(JSON, default=dict)
```

### Logging Statements:
```python
# Before
logger.info(f"Processing {count} items for RFP {rfp_id}")
logger.error(f"Failed to process: {error}")

# After
logger.info("Processing %d items for RFP %s", count, rfp_id)
logger.error("Failed to process: %s", error)
```

---

## 5. Benefits

1. **Performance**: Lazy evaluation means strings are only formatted when log level is enabled
2. **Consistency**: Standardized patterns across the codebase
3. **Best Practices**: Following Python logging best practices
4. **Maintainability**: Easier to read and maintain

---

## Notes

- The `notification_channels = Column(JSON, default=lambda: ["in_app"])` pattern should remain as-is since it has a non-empty default value
- Some logging statements may have complex formatting that requires careful conversion
- Consider using a linter/formatter rule to prevent future f-string logging in new code

