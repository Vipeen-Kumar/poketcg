"""Final diagnosis of the issue."""

import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

def diagnose_issue():
    """Final diagnosis based on all evidence."""
    
    print("="*80)
    print("FINAL DIAGNOSIS")
    print("="*80)
    
    # Summary of findings:
    print("\nFINDINGS:")
    print("1. SDK sample agents (first_agent, random_agent) work and return ['DONE', 'DONE']")
    print("2. SDK sample agents return a fixed sample deck [721, 721, 722, ...] when select=None")
    print("3. Our agent returns our deck [22, 22, 22, ...] when select=None")
    print("4. Our deck causes ['INVALID', 'DONE'] while sample deck causes ['INVALID', 'DONE'] (different rewards)")
    print("5. Empty list causes ['INVALID', 'INVALID']")
    
    print("\nPATTERN OBSERVED:")
    print("- Agent 0 always gets INVALID")
    print("- Agent 1 gets DONE when a 60-card deck is returned")
    print("- Agent 1 gets INVALID when empty list or wrong-length list is returned")
    print("- Reward for agent1 is 1 for sample deck, 0 for our deck")
    
    print("\nHYPOTHESIS:")
    print("When decks are provided in configuration, the initial select=None observation")
    print("is NOT a deck selection request. It might be a:")
    print("1. Ready check (agents should return empty list)")
    print("2. Deck validation check (agents should return the configured deck)")
    print("3. Something else entirely")
    
    print("\nBut the SDK sample agents return a deck and still work...")
    print("This suggests the environment IGNORES the returned value when decks are configured.")
    print("So why does our agent fail?")
    
    print("\nCRITICAL OBSERVATION:")
    print("The adapted first_agent (which calls SDK's first_agent) works.")
    print("But when we copy the SDK's logic and return the sample deck, it fails.")
    print("This suggests there's something different about HOW the agent is called.")
    
    # Let me test one more thing: what if the agent signature matters?
    print("\n" + "="*80)
    print("TESTING AGENT SIGNATURE")
    print("="*80)
    
    from kaggle_environments import make
    
    # Load decks
    deck_path = PROJECT_ROOT / "deck.csv"
    our_deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            our_deck.append(int(stripped))
    
    import kaggle_environments.envs.cabt.cabt as cabt_module
    sample_deck = cabt_module.deck
    
    # Test 1: Agent that matches SDK signature exactly (1 argument)
    print("\nTest 1: Agent with 1 argument (like SDK sample agents)")
    
    def one_arg_agent(obs):
        print(f"[ONE_ARG_AGENT] Called with obs keys: {list(obs.keys())}")
        if obs["select"] == None:
            print(f"[ONE_ARG_AGENT] Returning sample deck")
            return sample_deck
        return []
    
    # But Kaggle calls with 2 arguments... need to adapt
    def adapted_one_arg_agent(obs, config):
        return one_arg_agent(obs)
    
    env = make("cabt", configuration={"decks": [our_deck, our_deck]}, debug=True)
    steps = env.run([adapted_one_arg_agent, adapted_one_arg_agent])
    print(f"Result: {[s.status for s in steps[-1]]}")
    
    # Test 2: What if we return exactly what first_agent returns?
    print("\nTest 2: Direct copy of first_agent logic")
    
    def copy_first_agent(obs, config):
        # Exact copy of first_agent from SDK
        if obs["select"] == None:
            return sample_deck  # Using the SAME global variable
        return list(range(obs["select"]["maxCount"]))
    
    env = make("cabt", configuration={"decks": [our_deck, our_deck]}, debug=True)
    steps = env.run([copy_first_agent, copy_first_agent])
    print(f"Result: {[s.status for s in steps[-1]]}")
    
    # Test 3: What if the issue is with HOW we access the global variable?
    print("\nTest 3: Accessing deck from module directly each time")
    
    def direct_module_deck_agent(obs, config):
        import kaggle_environments.envs.cabt.cabt as cm
        if obs["select"] == None:
            return cm.deck  # Access directly from module
        return []
    
    env = make("cabt", configuration={"decks": [our_deck, our_deck]}, debug=True)
    steps = env.run([direct_module_deck_agent, direct_module_deck_agent])
    print(f"Result: {[s.status for s in steps[-1]]}")

def check_card_validity():
    """Check if our deck cards are valid."""
    
    print("\n" + "="*80)
    print("CHECKING CARD VALIDITY")
    print("="*80)
    
    # Load card data
    en_data_path = PROJECT_ROOT / "EN_Card_Data.csv"
    jp_data_path = PROJECT_ROOT / "JP_Card_Data.csv"
    
    print(f"EN data exists: {en_data_path.exists()}")
    print(f"JP data exists: {jp_data_path.exists()}")
    
    # Load our deck
    deck_path = PROJECT_ROOT / "deck.csv"
    our_deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            our_deck.append(int(stripped))
    
    print(f"\nOur deck cards (with counts):")
    from collections import Counter
    card_counts = Counter(our_deck)
    for card_id, count in sorted(card_counts.items()):
        print(f"  Card {card_id}: {count} copies")
    
    # Check sample deck
    import kaggle_environments.envs.cabt.cabt as cabt_module
    sample_deck = cabt_module.deck
    
    print(f"\nSample deck cards (with counts):")
    sample_counts = Counter(sample_deck)
    for card_id, count in sorted(sample_counts.items()):
        print(f"  Card {card_id}: {count} copies")
    
    print(f"\nComparison:")
    print(f"  Our deck has {len(set(our_deck))} unique card IDs")
    print(f"  Sample deck has {len(set(sample_deck))} unique card IDs")
    
    # Check if any card IDs are suspicious
    print(f"\nCard ID ranges:")
    print(f"  Our deck min: {min(our_deck)}, max: {max(our_deck)}")
    print(f"  Sample deck min: {min(sample_deck)}, max: {max(sample_deck)}")

def test_without_configuration():
    """Test what happens without decks in configuration."""
    
    print("\n" + "="*80)
    print("TEST WITHOUT CONFIGURATION")
    print("="*80)
    
    from kaggle_environments import make
    
    # Test without decks in configuration
    print("\nTest 1: No decks in configuration")
    
    def test_agent(obs, config):
        print(f"[AGENT] step={obs.get('step')}, select={obs.get('select')}")
        # Return empty list
        return []
    
    env = make("cabt", debug=True)
    try:
        steps = env.run([test_agent, test_agent])
        print(f"Result: {[s.status for s in steps[-1]]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test with just empty decks
    print("\nTest 2: Empty decks in configuration")
    
    env = make("cabt", configuration={"decks": [[], []]}, debug=True)
    try:
        steps = env.run([test_agent, test_agent])
        print(f"Result: {[s.status for s in steps[-1]]}")
    except Exception as e:
        print(f"Error: {e}")

def the_real_fix():
    """Based on all evidence, implement the real fix."""
    
    print("\n" + "="*80)
    print("THE REAL FIX")
    print("="*80)
    
    print("\nBased on all testing, here's what's happening:")
    print("1. When decks are provided in configuration, agents are still called with select=None")
    print("2. The environment seems to validate the returned value against SOMETHING")
    print("3. Agent 0 fails validation, Agent 1 passes (asymmetric validation)")
    print("4. The SDK sample agents work because they return a specific sample deck")
    
    print("\nLooking at the pattern more carefully:")
    print("- Sample deck returns ['DONE', 'DONE'] when called via adapted agent")
    print("- Sample deck returns ['INVALID', 'DONE'] when returned directly")
    print("- This suggests the ADAPTATION matters, not the deck")
    
    print("\nThe adaptation difference:")
    print("Adapted agent: calls cabt_module.first_agent(observation)")
    print("Direct agent: returns cabt_module.deck directly")
    
    print("\nWhat if first_agent does something else? Let me check...")
    
    import kaggle_environments.envs.cabt.cabt as cabt_module
    import inspect
    
    print("\nfirst_agent source:")
    try:
        source = inspect.getsource(cabt_module.first_agent)
        print(source)
    except:
        print("Could not get source")
    
    print("\nrandom_agent source:")
    try:
        source = inspect.getsource(cabt_module.random_agent)
        print(source)
    except:
        print("Could not get source")
    
    print("\n" + "="*80)
    print("CONCLUSION AND FIX")
    print("="*80)
    
    print("\nThe real issue appears to be:")
    print("The environment is calling agents with the wrong signature.")
    print("SDK sample agents expect 1 argument (obs), but Kaggle calls with 2 (obs, config).")
    
    print("\nThe fix for our agent:")
    print("We need to handle BOTH the case when decks are in configuration")
    print("AND the case when they're not.")
    
    print("\nHere's the fix for AgentLifecycle.is_deck_selection_payload():")
    print("When decks are provided in configuration AND select=None,")
    print("we should NOT treat it as deck selection.")
    
    print("\nModified logic should be:")
    print("1. If configuration exists and has 'decks' key")
    print("2. AND select=None")
    print("3. Then return empty list (ready check), not deck")

if __name__ == "__main__":
    diagnose_issue()
    check_card_validity()
    test_without_configuration()
    the_real_fix()