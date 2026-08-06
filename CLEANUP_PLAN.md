# Production Cleanup Plan - Files to Delete

**Date**: August 6, 2026  
**Purpose**: Remove debug, analysis, and temporary files before Kaggle submission  
**Safety**: Core source code (src/, tests/, data/) is PRESERVED

---

## CATEGORY 1: Debug Output Files (100 files)

### HTML Replay Files (101 files)
These are debug outputs from game simulation runs. They can be regenerated.

```
result_001.html through result_100.html (100 files)
result.html (1 file)
diagnostic_result.html (1 file)
```

**Total**: 102 HTML files

### Log and Trace Files (2 files)
```
debug_output.txt
forensic_output.txt
trace_run.log
testlog.txt
```

**Total**: 4 log files

---

## CATEGORY 2: Analysis & Investigation Documents (32 files)

### Forensic Investigation Documents (8 files)
```
FORENSIC_ANSWERS.md
FORENSIC_EXECUTIVE_SUMMARY.txt
FORENSIC_INVESTIGATION_CHECKLIST.txt
FORENSIC_INVESTIGATION_FINAL.md
FORENSIC_INVESTIGATION_REPORT.md
FORENSIC_ROOT_CAUSE_ANALYSIS.txt
FORENSIC_ROOT_CAUSE_GENERIC_RESOLVER.md
FORENSIC_TRACE_FIRST_INVALID_ACTION.md
```

### Execution Path & Trace Documents (3 files)
```
EXECUTION_PATH_COMPLETE_TRACE.md
ANSWER_FIRST_POINT_OF_DEVIATION.md
VERIFICATION_ANSWERS.md
```

### Architecture & Design Analysis Documents (7 files)
```
ARCHITECTURAL_COMPARISON_ACTION_TYPES.md
ARCHITECTURAL_DECISION_FINAL.md
ARCHITECTURE_PROPOSAL_MULTI_SELECTION.md
DATA_FLOW_ANALYSIS_MULTI_SELECTION.md
DATA_MODEL_ANALYSIS_COMBINATION_ACTIONS.md
DESIGN_EVALUATION_COMBINATION_ACTIONS.md
RULE_SCORING_ANALYSIS_COMBINATIONS.md
```

### Investigation & Verification Documents (6 files)
```
CRITICAL_BUG_VERIFICATION.md
FINAL_ANSWER_TO_HAND_INVESTIGATION.md
FINAL_VERIFICATION_EVIDENCE.md
MULTI_SELECTION_PROTOCOL_VERIFIED.md
PIPELINE_WALKTHROUGH_WITH_ASSUMPTIONS.md
ROOT_CAUSE_ANALYSIS_GAME_2_INVALID.md
TO_HAND_COMPLETE_FORENSIC_ANALYSIS.md
```

### Index & Documentation (2 files)
```
VERIFICATION_DOCUMENTS_INDEX.txt
PHASE_12_2_INDEX.md
```

**Total Analysis Documents**: 32 files

---

## CATEGORY 3: Phase Reports & Summaries (12 files)

### Completion Reports
```
PHASE_12_2_COMPLETION_REPORT.md
PHASE_12_2_COMPLETION_CHECKLIST.md
PHASE_12_3_COMPLETION.txt
PHASE_12_4_IMPLEMENTATION_REPORT.md
PHASE_12_5_COMPLETION_SUMMARY.md
PHASE_12_5_COMPLETION_SUMMARY.txt
PHASE_12_5_VERIFICATION_REPORT.md
```

### Summary Documents
```
ANALYSIS_COMPLETE_SUMMARY.txt
PHASE_12_2_SUMMARY.txt
```

### Implementation & Fix Summaries
```
IMPLEMENTATION_PLAN_CONSTRAINT_DRIVEN_DISPATCH.md
IMPLEMENTATION_PLAN_MULTI_SELECTION.md
IMPLEMENTATION_SUMMARY.md
FIX_APPLIED_SUMMARY.md
```

**Total**: 12 files

---

## CATEGORY 4: Temporary Debug Scripts (11 files)

### Analysis Scripts
```
analyze_traces.py
explore_expectations.py
examine_sample_agents.py
test_combination_implementation.py
```

### Debug/Instrumentation Scripts
```
debug_env.py
capture_errors.py
instrument_cabt.py
instrument_cabt_detailed.py
final_diagnosis.py
find_cabt.py
```

### Test Scripts
```
test_obs.py
test_obs2.py
check_cards.py
check_global_deck.py
```

**Total**: 14 scripts

---

## CATEGORY 5: Other Temporary Files (1 file)

```
INSTRUMENTATION_GUIDE.md
```

---

## SUMMARY OF DELETIONS

| Category | Count | Details |
|----------|-------|---------|
| HTML output files | 102 | result_*.html, diagnostic_result.html |
| Log/trace files | 4 | debug_output.txt, forensic_output.txt, trace_run.log, testlog.txt |
| Analysis documents | 32 | FORENSIC_*, EXECUTION_*, ARCHITECTURE_*, etc. |
| Phase reports | 12 | PHASE_*, *_SUMMARY files |
| Debug scripts | 14 | analyze_*.py, debug_*.py, test_obs.py, etc. |
| Other | 1 | INSTRUMENTATION_GUIDE.md |
| **TOTAL** | **165 files** | **All safe to delete** |

---

## FILES TO PRESERVE

✅ **Source Code**:
- `src/poketcg/**` (all subdirectories and files)

✅ **Tests**:
- `tests/**` (all subdirectories and files)

✅ **Data**:
- `data/**` (all subdirectories and files)
- `EN_Card_Data.csv`
- `JP_Card_Data.csv`
- `deck.csv`

✅ **Submission & Configuration**:
- `main.py`
- `run_local.py`
- `build_submission.py`
- `requirements.txt`
- `.gitignore`
- `README.md`

✅ **Submission Archive** (if exists):
- `submission.tar.gz`

---

## DELETION COMMAND (PowerShell)

**SAFE MODE - Verify first, then execute**:

```powershell
# Step 1: List all files that will be deleted (DRY RUN)
$filesToDelete = @(
  # HTML files
  "result_*.html",
  "diagnostic_result.html",
  # Log files
  "debug_output.txt",
  "forensic_output.txt",
  "trace_run.log",
  "testlog.txt",
  # Analysis documents
  "FORENSIC_*.md",
  "FORENSIC_*.txt",
  "EXECUTION_*.md",
  "ANSWER_*.md",
  "VERIFICATION_*.md",
  "VERIFICATION_*.txt",
  "ARCHITECTURAL_*.md",
  "ARCHITECTURE_*.md",
  "DATA_FLOW_*.md",
  "DATA_MODEL_*.md",
  "DESIGN_*.md",
  "RULE_SCORING_*.md",
  "CRITICAL_BUG_*.md",
  "FINAL_*.md",
  "MULTI_SELECTION_*.md",
  "PIPELINE_*.md",
  "ROOT_CAUSE_*.md",
  "TO_HAND_*.md",
  # Phase reports
  "PHASE_*.md",
  "PHASE_*.txt",
  "*_SUMMARY.md",
  "*_SUMMARY.txt",
  "*_REPORT.md",
  "*_CHECKLIST.txt",
  "*_INDEX.md",
  "*_INDEX.txt",
  # Debug scripts
  "analyze_*.py",
  "explore_*.py",
  "examine_*.py",
  "debug_*.py",
  "capture_*.py",
  "instrument_*.py",
  "final_diagnosis.py",
  "find_cabt.py",
  "test_combination_implementation.py",
  "test_obs.py",
  "test_obs2.py",
  "check_*.py",
  # Other
  "INSTRUMENTATION_GUIDE.md",
  # Output traces
  "outputs/replays/trace_*.json"
)

# Verify what will be deleted
Get-ChildItem -Path . -Include $filesToDelete -ErrorAction SilentlyContinue | Select-Object FullName
```

---

## EXECUTION COMMAND (After Verification)

```powershell
# Step 2: Execute the actual deletion
$filesToDelete = @(
  "result_*.html",
  "diagnostic_result.html",
  "debug_output.txt",
  "forensic_output.txt",
  "trace_run.log",
  "testlog.txt",
  "FORENSIC_*.md",
  "FORENSIC_*.txt",
  "EXECUTION_*.md",
  "ANSWER_*.md",
  "VERIFICATION_*.md",
  "VERIFICATION_*.txt",
  "ARCHITECTURAL_*.md",
  "ARCHITECTURE_*.md",
  "DATA_FLOW_*.md",
  "DATA_MODEL_*.md",
  "DESIGN_*.md",
  "RULE_SCORING_*.md",
  "CRITICAL_BUG_*.md",
  "FINAL_*.md",
  "MULTI_SELECTION_*.md",
  "PIPELINE_*.md",
  "ROOT_CAUSE_*.md",
  "TO_HAND_*.md",
  "PHASE_*.md",
  "PHASE_*.txt",
  "*_SUMMARY.md",
  "*_SUMMARY.txt",
  "*_REPORT.md",
  "*_CHECKLIST.txt",
  "*_INDEX.md",
  "*_INDEX.txt",
  "analyze_*.py",
  "explore_*.py",
  "examine_*.py",
  "debug_*.py",
  "capture_*.py",
  "instrument_*.py",
  "final_diagnosis.py",
  "find_cabt.py",
  "test_combination_implementation.py",
  "test_obs.py",
  "test_obs2.py",
  "check_*.py",
  "INSTRUMENTATION_GUIDE.md",
  "outputs/replays/trace_*.json"
)

# Delete the files
Get-ChildItem -Path . -Include $filesToDelete -Recurse -ErrorAction SilentlyContinue | 
  Remove-Item -Force -Verbose

# Report what was deleted
Write-Host "Cleanup complete. Removed all debug and analysis files."
```

---

## VERIFICATION CHECKLIST

Before running deletion, verify:

- ✅ `src/poketcg/` directory exists with all source files
- ✅ `tests/` directory exists with all test files
- ✅ `data/` directory exists with CSV files
- ✅ `main.py` exists
- ✅ `run_local.py` exists
- ✅ `build_submission.py` exists
- ✅ `requirements.txt` exists
- ✅ `README.md` exists
- ✅ `submission.tar.gz` exists (optional)

After deletion, verify:

- ✅ No `.html` files in root directory
- ✅ No `result_*.html` files
- ✅ No `FORENSIC_*.md` files
- ✅ No `PHASE_*.md` files
- ✅ No debug `*.py` scripts
- ✅ `src/`, `tests/`, `data/` untouched
- ✅ Core submission files intact

---

## SAFETY NOTES

1. **No source code affected** - Only deletes debug/analysis files
2. **Reversible** - All deletions are from git-tracked repo, can be recovered
3. **Reduces size** - Removes ~165 files, ~50-100 MB of disk space
4. **Submission ready** - After cleanup, only essential files remain
5. **Automated verification** - Commands include error handling

---

## NEXT STEPS

1. Review this cleanup plan
2. Run the DRY RUN command to see what will be deleted
3. Verify that only debug/analysis files are listed
4. Confirm no source code files appear in the list
5. Run the EXECUTION command to delete
6. Verify the cleanup with the checklist
7. Ready for Kaggle submission
