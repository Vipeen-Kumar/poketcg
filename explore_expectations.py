"""Explore what the environment actually expects for the first observation."""

import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

def test_different_responses():
    """Test different responses to see what the environment accepts."""
    
    from kaggle_environments import make
    
    # Load deck
    deck_path = PROJECT_ROOT / "deck.csv"
    deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            deck.append(int(stripped))
    
    print(f"Deck has {len(deck)} cards")
    print(f"First 10: {deck[:10]}")
    
    # Test different responses
    test_cases = [
        ("Return empty list", []),
        ("Return [0]", [0]),
        ("Return [1]", [1]),
        ("Return deck (60 cards)", deck),
        ("Return None", None),
        ("Return string", "test"),
        ("Return dict", {"test": "value"}),
        ("Return single card list", [22]),
        ("Return partial deck (30 cards)", deck[:30]),
        ("Return oversized deck (70 cards)", deck + [999, 999, 999, 999, 999, 999, 999, 999, 999, 999]),
    ]
    
    for description, response in test_cases:
        print(f"\n{'='*80}")
        print(f"TEST: {description}")
        print(f"Response type: {type(response)}")
        if hasattr(response, '__len__'):
            print(f"Response length: {len(response)}")
        
        def test_agent(observation, configuration):
            print(f"[AGENT] Received observation with keys: {list(observation.keys())}")
            print(f"[AGENT] current: {observation.get('current')}")
            print(f"[AGENT] select: {observation.get('select')}")
            print(f"[AGENT] step: {observation.get('step')}")
            print(f"[AGENT] Returning: {response}")
            return response
        
        # Create fresh environment
        env = make(
            "cabt",
            configuration={
                "decks": [deck, deck],
            },
            debug=True,
        )
        
        # Run
        try:
            steps = env.run([test_agent, test_agent])
            final_step = steps[-1]
            statuses = [state.status for state in final_step]
            rewards = [state.reward for state in final_step]
            
            print(f"Result: statuses={statuses}, rewards={rewards}")
            
            # Check if environment logs contain errors
            if env.logs:
                print(f"Environment logs ({len(env.logs)}):")
                for i, log in enumerate(env.logs):
                    if isinstance(log, list) and len(log) > 0:
                        for agent_log in log:
                            if isinstance(agent_log, dict):
                                if agent_log.get('stderr'):
                                    print(f"  Agent {i} stderr: {agent_log['stderr']}")
                                if agent_log.get('stdout'):
                                    print(f"  Agent {i} stdout: {agent_log['stdout']}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

def test_configuration_only():
    """Test if decks in configuration should bypass deck selection."""
    
    print("\n" + "="*80)
    print("TEST: Should agents return anything when decks are in configuration?")
    print("="*80)
    
    from kaggle_environments import make
    
    # Load deck
    deck_path = PROJECT_ROOT / "deck.csv"
    deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            deck.append(int(stripped))
    
    # Agent that returns nothing (empty list)
    def silent_agent(observation, configuration):
        print(f"[SILENT_AGENT] step={observation.get('step')}, current={observation.get('current')}, select={observation.get('select')}")
        return []
    
    # Create environment
    env = make(
        "cabt",
        configuration={
            "decks": [deck, deck],
        },
        debug=True,
    )
    
    # Run
    steps = env.run([silent_agent, silent_agent])
    
    print(f"\nRun completed with {len(steps)} steps")
    final_step = steps[-1]
    for i, state in enumerate(final_step):
        print(f"Agent {i}: status={state.status}, reward={state.reward}")

def test_sample_agents():
    """Test with the sample agents from the SDK."""
    
    print("\n" + "="*80)
    print("TEST: Using SDK sample agents")
    print("="*80)
    
    from kaggle_environments import make
    import kaggle_environments.envs.cabt.cabt as cabt_module
    
    # Try to find sample agents in the module
    sample_agents = {}
    for name in dir(cabt_module):
        if name.endswith('_agent'):
            obj = getattr(cabt_module, name)
            if callable(obj):
                sample_agents[name] = obj
    
    print(f"Found sample agents: {list(sample_agents.keys())}")
    
    if not sample_agents:
        print("No sample agents found")
        return
    
    # Load deck
    deck_path = PROJECT_ROOT / "deck.csv"
    deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            deck.append(int(stripped))
    
    # Test each sample agent
    for agent_name, agent_func in sample_agents.items():
        print(f"\nTesting agent: {agent_name}")
        
        env = make(
            "cabt",
            configuration={
                "decks": [deck, deck],
            },
            debug=True,
        )
        
        try:
            steps = env.run([agent_func, agent_func])
            final_step = steps[-1]
            statuses = [state.status for state in final_step]
            print(f"Result: {statuses}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    print("Exploring environment expectations...")
    
    # Test 1: Different responses
    test_different_responses()
    
    # Test 2: Configuration-only test
    test_configuration_only()
    
    # Test 3: Sample agents
    test_sample_agents()