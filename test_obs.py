"""Test to understand observation structure."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.agent.lifecycle import AgentLifecycle

# Test what observations trigger deck selection
test_cases = [
    # (description, observation, expected_is_deck_selection)
    ("Empty dict", {}, True),  # current=None, select=None
    ("None values", {"current": None, "select": None}, True),
    ("Current present", {"current": {"players": []}, "select": None}, False),
    ("Select present", {"current": None, "select": {"option": []}}, False),
    ("Both present", {"current": {"players": []}, "select": {"option": []}}, False),
]

for desc, obs, expected in test_cases:
    result = AgentLifecycle.is_deck_selection_payload(obs)
    print(f"{desc}: {result} (expected {expected}) {'✓' if result == expected else '✗'}")