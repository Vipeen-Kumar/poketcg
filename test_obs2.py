"""Test observation structure."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.agent.lifecycle import AgentLifecycle

# Test cases based on potential observation structures
test_cases = [
    # (description, observation, expected_is_deck_selection)
    ("Empty dict", {}, True),
    ("Empty observation key", {"observation": {}}, True),
    ("Observation with current None", {"observation": {"current": None, "select": None}}, True),
    ("Observation with current dict", {"observation": {"current": {}, "select": None}}, False),
    ("Observation with select dict", {"observation": {"current": None, "select": {}}}, False),
    ("Observation with both", {"observation": {"current": {}, "select": {}}}, False),
    ("Direct current/select (old format)", {"current": {}, "select": {}}, False),
    ("Direct with None (old format)", {"current": None, "select": None}, True),
]

for desc, obs, expected in test_cases:
    result = AgentLifecycle.is_deck_selection_payload(obs)
    print(f"{desc}: {result} (expected {expected}) {'✓' if result == expected else '✗'}")