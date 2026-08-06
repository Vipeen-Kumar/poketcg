"""Analyze action traces to identify illegal actions."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def analyze_trace_file(trace_path: Path) -> dict[str, Any]:
    """Analyze a single trace file for illegal actions."""
    
    with open(trace_path) as f:
        traces = json.load(f)
    
    analysis = {
        "file": trace_path.name,
        "total_decisions": len(traces),
        "illegal_actions": [],
        "validation_failures": [],
        "decision_errors": [],
        "summary": {}
    }
    
    for i, trace in enumerate(traces):
        decision_num = i + 1
        
        # Check for out-of-bounds returned integers
        returned = trace.get("returned_integer")
        legal_count = trace.get("legal_option_count", 0)
        
        if returned is not None and (returned < 0 or returned >= legal_count):
            analysis["illegal_actions"].append({
                "decision": decision_num,
                "turn": trace.get("turn"),
                "player": trace.get("player_index"),
                "returned_integer": returned,
                "legal_option_count": legal_count,
                "legal_range": f"[0, {legal_count - 1}]",
                "select_type": trace.get("select_type"),
                "chosen_action": trace.get("chosen_action"),
            })
        
        # Check for validation failures
        if not trace.get("validation_passed", True):
            analysis["validation_failures"].append({
                "decision": decision_num,
                "turn": trace.get("turn"),
                "player": trace.get("player_index"),
                "error": trace.get("validation_error"),
                "chosen_action": trace.get("chosen_action"),
            })
        
        # Check for decision errors
        if trace.get("decision_error"):
            analysis["decision_errors"].append({
                "decision": decision_num,
                "turn": trace.get("turn"),
                "player": trace.get("player_index"),
                "error": trace.get("decision_error"),
            })
    
    # Build summary
    if analysis["illegal_actions"]:
        first_illegal = analysis["illegal_actions"][0]
        analysis["summary"]["first_illegal_action"] = first_illegal
    
    if analysis["validation_failures"]:
        analysis["summary"]["first_validation_failure"] = analysis["validation_failures"][0]
    
    if analysis["decision_errors"]:
        analysis["summary"]["first_decision_error"] = analysis["decision_errors"][0]
    
    return analysis


def print_analysis(analysis: dict[str, Any]) -> None:
    """Print analysis in human-readable format."""
    
    print("\n" + "=" * 100)
    print(f"TRACE ANALYSIS: {analysis['file']}")
    print("=" * 100)
    
    print(f"\nTotal Decisions: {analysis['total_decisions']}")
    print(f"Illegal Actions Found: {len(analysis['illegal_actions'])}")
    print(f"Validation Failures: {len(analysis['validation_failures'])}")
    print(f"Decision Errors: {len(analysis['decision_errors'])}")
    
    if analysis["illegal_actions"]:
        print("\n" + "-" * 100)
        print("ILLEGAL ACTIONS DETECTED:")
        print("-" * 100)
        for illegal in analysis["illegal_actions"]:
            print(f"\nDecision {illegal['decision']} (Turn {illegal['turn']}, Player {illegal['player']}):")
            print(f"  Select Type: {illegal['select_type']}")
            print(f"  Returned Integer: {illegal['returned_integer']}")
            print(f"  Legal Range: {illegal['legal_range']}")
            print(f"  Chosen Action: {illegal['chosen_action']}")
    
    if analysis["validation_failures"]:
        print("\n" + "-" * 100)
        print("VALIDATION FAILURES:")
        print("-" * 100)
        for failure in analysis["validation_failures"]:
            print(f"\nDecision {failure['decision']} (Turn {failure['turn']}, Player {failure['player']}):")
            print(f"  Error: {failure['error']}")
            print(f"  Chosen Action: {failure['chosen_action']}")
    
    if analysis["decision_errors"]:
        print("\n" + "-" * 100)
        print("DECISION ERRORS:")
        print("-" * 100)
        for error in analysis["decision_errors"]:
            print(f"\nDecision {error['decision']} (Turn {error['turn']}, Player {error['player']}):")
            print(f"  Error: {error['error']}")
    
    print("\n" + "=" * 100)


def main() -> int:
    """Analyze all trace files."""
    
    replays_dir = Path("outputs/replays")
    
    if not replays_dir.exists():
        print("No replays directory found at outputs/replays")
        return 1
    
    trace_files = sorted(replays_dir.glob("trace_*.json"))
    
    if not trace_files:
        print("No trace files found in outputs/replays")
        return 1
    
    print(f"Found {len(trace_files)} trace files")
    
    all_analyses = []
    total_illegal = 0
    
    for trace_file in trace_files:
        analysis = analyze_trace_file(trace_file)
        all_analyses.append(analysis)
        total_illegal += len(analysis["illegal_actions"])
        print_analysis(analysis)
    
    # Summary across all files
    print("\n" + "=" * 100)
    print("CROSS-FILE SUMMARY")
    print("=" * 100)
    print(f"Total trace files analyzed: {len(trace_files)}")
    print(f"Total illegal actions across all files: {total_illegal}")
    
    if total_illegal == 0:
        print("\n✓ No illegal actions found in any trace files.")
        print("This means:")
        print("  - All returned integers are within bounds")
        print("  - All validation checks pass")
        print("  - No decision engine errors occur")
        print("\nIf games are still ending with INVALID status, the issue may be:")
        print("  - A constraint we're not capturing in the trace")
        print("  - An issue AFTER the action is returned (environment-side)")
        print("  - A mutation of the action object after validation")
    else:
        print(f"\n✗ Found {total_illegal} illegal actions that need investigation.")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
