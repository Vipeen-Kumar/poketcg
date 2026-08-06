# ============================================================================
# PRODUCTION CLEANUP COMMAND
# Project: poketcg
# Date: August 6, 2026
# ============================================================================

# This script safely removes all debug, analysis, and temporary files
# while preserving all core source code, tests, and data files.

# ============================================================================
# STEP 1: VERIFY FILES TO DELETE (DRY RUN - SAFE, NO CHANGES)
# ============================================================================

Write-Host "
================================================================================
STEP 1: DRY RUN - Listing files that will be deleted
================================================================================
" -ForegroundColor Cyan

$filesToDelete = @(
  # HTML Output Files
  "result_*.html",
  "diagnostic_result.html",
  
  # Log Files
  "debug_output.txt",
  "forensic_output.txt",
  "trace_run.log",
  "testlog.txt",
  
  # Forensic Documents
  "FORENSIC_*.md",
  "FORENSIC_*.txt",
  
  # Analysis Documents
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
  
  # Phase Reports
  "PHASE_*.md",
  "PHASE_*.txt",
  "*_SUMMARY.md",
  "*_SUMMARY.txt",
  "*_REPORT.md",
  "*_CHECKLIST.txt",
  "*_INDEX.md",
  "*_INDEX.txt",
  
  # Temporary Scripts
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
  "outputs/replays/trace_*.json"
)

# DRY RUN - List files without deleting
$filesToDeleteCount = 0
Get-ChildItem -Path . -Include $filesToDelete -Recurse -ErrorAction SilentlyContinue | 
  ForEach-Object {
    Write-Host "  Would delete: $($_.FullName)" -ForegroundColor Yellow
    $filesToDeleteCount++
  }

Write-Host "`nTotal files that will be deleted: $filesToDeleteCount" -ForegroundColor Yellow
Write-Host "`nReview the list above. If correct, proceed to STEP 2." -ForegroundColor Cyan

# ============================================================================
# STEP 2: EXECUTE DELETION (UNCOMMENT TO ACTUALLY DELETE)
# ============================================================================

Write-Host "
================================================================================
STEP 2: EXECUTE DELETION
================================================================================
" -ForegroundColor Cyan

Write-Host "To actually delete the files, uncomment the code below and run again." -ForegroundColor Yellow
Write-Host ""

UNCOMMENT THE FOLLOWING LINES TO ACTUALLY DELETE:
Get-ChildItem -Path . -Include $filesToDelete -Recurse -ErrorAction SilentlyContinue | 
  Remove-Item -Force -Verbose
# 
# Write-Host "`n✅ Deletion complete!" -ForegroundColor Green

# ============================================================================
# STEP 3: VERIFY CLEANUP (UNCOMMENT AFTER DELETION)
# ============================================================================

Write-Host "
================================================================================
STEP 3: VERIFY CLEANUP - Check that core files still exist
================================================================================
" -ForegroundColor Cyan

$criticalFiles = @("main.py", "run_local.py", "build_submission.py", "requirements.txt", "README.md", "deck.csv", "EN_Card_Data.csv")
$criticalDirs = @("src/poketcg", "tests", "data")

Write-Host "`nCritical Files:" -ForegroundColor Cyan
$criticalFiles | ForEach-Object {
  if (Test-Path $_) { 
    Write-Host "  ✅ $_" -ForegroundColor Green 
  } else { 
    Write-Host "  ❌ $_ MISSING!" -ForegroundColor Red 
  }
}

Write-Host "`nCritical Directories:" -ForegroundColor Cyan
$criticalDirs | ForEach-Object {
  if (Test-Path $_ -PathType Container) { 
    $count = (Get-ChildItem -Path $_ -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "  ✅ $_ ($count files)" -ForegroundColor Green 
  } else { 
    Write-Host "  ❌ $_ MISSING!" -ForegroundColor Red 
  }
}

# ============================================================================
# FULL AUTOMATED CLEANUP (UNCOMMENT TO RUN ALL STEPS)
# ============================================================================

<#
# UNCOMMENT THIS BLOCK TO RUN FULL CLEANUP AUTOMATICALLY:

Write-Host "
================================================================================
FULL AUTOMATED CLEANUP - STEPS 1, 2, AND 3
================================================================================
" -ForegroundColor Cyan -BackgroundColor DarkRed

Write-Host "`n⚠️  WARNING: This will delete 163 files!`n" -ForegroundColor Red

# Ask for confirmation
$response = Read-Host "Type 'YES' to confirm deletion"
if ($response -ne "YES") {
  Write-Host "Cleanup cancelled." -ForegroundColor Yellow
  exit
}

Write-Host "`nProceeding with deletion...`n" -ForegroundColor Yellow

# Execute deletion
Get-ChildItem -Path . -Include $filesToDelete -Recurse -ErrorAction SilentlyContinue | 
  Remove-Item -Force -Verbose

Write-Host "`n✅ Deletion complete!" -ForegroundColor Green

# Verify cleanup
Write-Host "`nVerifying cleanup...`n" -ForegroundColor Cyan

$allGood = $true
$criticalFiles | ForEach-Object {
  if (Test-Path $_) { 
    Write-Host "  ✅ $_" -ForegroundColor Green 
  } else { 
    Write-Host "  ❌ $_ MISSING!" -ForegroundColor Red
    $allGood = $false
  }
}

$criticalDirs | ForEach-Object {
  if (Test-Path $_ -PathType Container) { 
    $count = (Get-ChildItem -Path $_ -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "  ✅ $_ ($count files)" -ForegroundColor Green 
  } else { 
    Write-Host "  ❌ $_ MISSING!" -ForegroundColor Red
    $allGood = $false
  }
}

if ($allGood) {
  Write-Host "`n✅ CLEANUP SUCCESSFUL! Project is ready for submission." -ForegroundColor Green
  Write-Host "`nNext steps:`n" -ForegroundColor Green
  Write-Host "  1. python build_submission.py`n" -ForegroundColor Yellow
  Write-Host "  2. Upload submission.tar.gz to Kaggle`n" -ForegroundColor Yellow
} else {
  Write-Host "`n❌ CLEANUP FAILED! Some critical files are missing!" -ForegroundColor Red
}
#>

Write-Host "
================================================================================
INSTRUCTIONS
================================================================================
" -ForegroundColor Cyan

Write-Host "
To perform the cleanup:

1. Review the files listed in STEP 1 above
2. Uncomment the code in STEP 2 (Remove-Item commands)
3. Run this script again to execute deletion
4. Uncomment the code in STEP 3 to verify
5. Or, uncomment the 'FULL AUTOMATED CLEANUP' block to do all at once

For more information, see:
  • CLEANUP_PLAN.md
  • PRODUCTION_CLEANUP_READY.md
  • CLEANUP_SUMMARY.txt

" -ForegroundColor Yellow
