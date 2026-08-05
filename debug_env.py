"""Debug script to understand INVALID action issue."""

import json
import re

# Read HTML file
with open('result.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find the kaggle environment data
match = re.search(r'window\.kaggle\s*=\s*({.*?});', html, re.DOTALL)
if match:
    data_str = match.group(1)
    try:
        # Try to parse as JSON
        data = json.loads(data_str)
        env = data.get('environment', {})
        steps = env.get('steps', [])
        
        print(f"Number of steps: {len(steps)}")
        if steps:
            print(f"First step (length): {len(steps[0]) if isinstance(steps[0], list) else 'not a list'}")
            for i, step in enumerate(steps):
                if isinstance(step, list):
                    print(f"\nStep {i}:")
                    for j, state in enumerate(step):
                        print(f"  Agent {j}: status={state.get('status')}, reward={state.get('reward')}")
                        # Look for action info
                        action = state.get('action')
                        if action is not None:
                            print(f"    Action: {action}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"First 1000 chars: {data_str[:1000]}")
else:
    print("Could not find kaggle environment data in HTML")