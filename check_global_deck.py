"""Check what the global 'deck' variable contains in the cabt module."""

import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

def check_global_deck():
    """Check the global deck variable in the cabt module."""
    
    import kaggle_environments.envs.cabt.cabt as cabt_module
    
    print("Checking cabt module for global variables...")
    
    # Look for deck variable
    if hasattr(cabt_module, 'deck'):
        deck = cabt_module.deck
        print(f"Found global 'deck' variable")
        print(f"  Type: {type(deck)}")
        if hasattr(deck, '__len__'):
            print(f"  Length: {len(deck)}")
            if len(deck) > 0:
                print(f"  First 10 elements: {deck[:10]}")
                print(f"  Last 10 elements: {deck[-10:] if len(deck) > 10 else deck}")
    else:
        print("No global 'deck' variable found")
    
    # Look for other relevant variables
    print("\nLooking for other relevant variables...")
    interesting_vars = []
    for name in dir(cabt_module):
        if 'deck' in name.lower() or 'sample' in name.lower() or 'default' in name.lower():
            obj = getattr(cabt_module, name)
            interesting_vars.append((name, obj))
    
    for name, obj in interesting_vars:
        print(f"\n{name}:")
        print(f"  Type: {type(obj)}")
        if hasattr(obj, '__len__'):
            print(f"  Length: {len(obj)}")
            if len(obj) > 0 and len(obj) <= 100:
                print(f"  First 10: {obj[:10]}")

def test_sample_agent_with_correct_signature():
    """Test sample agents with the correct signature."""
    
    import kaggle_environments.envs.cabt.cabt as cabt_module
    
    print("\n" + "="*80)
    print("Testing sample agents with correct signature")
    print("="*80)
    
    # Create wrapper that adapts the signature
    def adapt_first_agent(observation, configuration):
        # first_agent only takes obs
        return cabt_module.first_agent(observation)
    
    def adapt_random_agent(observation, configuration):
        # random_agent only takes obs
        import random
        # Need to handle random.sample properly
        return cabt_module.random_agent(observation)
    
    # Test what they return
    test_observation = {
        'remainingOverageTime': 600,
        'step': 0,
        'select': None,
        'logs': [],
        'current': None,
        'search_begin_input': None
    }
    
    print("\nTesting adapted first_agent:")
    try:
        result = adapt_first_agent(test_observation, {})
        print(f"  Returned: {result}")
        print(f"  Type: {type(result)}")
        if hasattr(result, '__len__'):
            print(f"  Length: {len(result)}")
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTesting adapted random_agent:")
    try:
        result = adapt_random_agent(test_observation, {})
        print(f"  Returned: {result}")
        print(f"  Type: {type(result)}")
        if hasattr(result, '__len__'):
            print(f"  Length: {len(result)}")
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Now test in actual environment
    from kaggle_environments import make
    
    # Load our deck
    deck_path = PROJECT_ROOT / "deck.csv"
    our_deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            our_deck.append(int(stripped))
    
    print(f"\nOur deck has {len(our_deck)} cards")
    
    # Create environment
    env = make(
        "cabt",
        configuration={
            "decks": [our_deck, our_deck],
        },
        debug=True,
    )
    
    print("\nRunning environment with adapted first_agent...")
    try:
        steps = env.run([adapt_first_agent, adapt_first_agent])
        final_step = steps[-1]
        statuses = [state.status for state in final_step]
        print(f"Result: {statuses}")
    except Exception as e:
        print(f"Error: {e}")

def find_the_real_issue():
    """Try to understand what's really happening."""
    
    print("\n" + "="*80)
    print("Finding the real issue")
    print("="*80)
    
    # Hypothesis: When decks are in configuration, agents should NOT return decks
    # Let me check what happens if we return empty list but the sample agents work
    
    from kaggle_environments import make
    
    # Load our deck
    deck_path = PROJECT_ROOT / "deck.csv"
    our_deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            our_deck.append(int(stripped))
    
    # Get the sample deck from the module
    import kaggle_environments.envs.cabt.cabt as cabt_module
    sample_deck = getattr(cabt_module, 'deck', None)
    
    print(f"Our deck: {len(our_deck)} cards")
    if sample_deck and hasattr(sample_deck, '__len__'):
        print(f"Sample deck from module: {len(sample_deck)} cards")
        print(f"Sample deck first 10: {sample_deck[:10]}")
    
    # Test 1: Return sample deck (what first_agent returns)
    def return_sample_deck_agent(observation, configuration):
        if observation.get('select') is None:
            print(f"[SAMPLE_DECK_AGENT] Returning sample deck ({len(sample_deck)} cards)")
            return sample_deck
        return []
    
    # Test 2: Return our deck
    def return_our_deck_agent(observation, configuration):
        if observation.get('select') is None:
            print(f"[OUR_DECK_AGENT] Returning our deck ({len(our_deck)} cards)")
            return our_deck
        return []
    
    # Test 3: Return empty list
    def return_empty_agent(observation, configuration):
        if observation.get('select') is None:
            print(f"[EMPTY_AGENT] select=None, returning empty list")
            return []
        return []
    
    tests = [
        ("Sample deck agent", return_sample_deck_agent),
        ("Our deck agent", return_our_deck_agent),
        ("Empty agent", return_empty_agent),
    ]
    
    for test_name, agent_func in tests:
        print(f"\n{'='*60}")
        print(f"Test: {test_name}")
        print('='*60)
        
        env = make(
            "cabt",
            configuration={
                "decks": [our_deck, our_deck],
            },
            debug=True,
        )
        
        try:
            steps = env.run([agent_func, agent_func])
            final_step = steps[-1]
            statuses = [state.status for state in final_step]
            rewards = [state.reward for state in final_step]
            print(f"Result: statuses={statuses}, rewards={rewards}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_global_deck()
    test_sample_agent_with_correct_signature()
    find_the_real_issue()