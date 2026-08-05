"""Examine what the SDK sample agents actually return."""

import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

def examine_sample_agents():
    """Examine the sample agents from the SDK."""
    
    import kaggle_environments.envs.cabt.cabt as cabt_module
    
    print("Examining sample agents from cabt module...")
    
    # Find and examine sample agents
    sample_agents = {}
    for name in dir(cabt_module):
        if name.endswith('_agent'):
            obj = getattr(cabt_module, name)
            if callable(obj):
                sample_agents[name] = obj
                print(f"\n{name}:")
                print(f"  Type: {type(obj)}")
                print(f"  Module: {obj.__module__ if hasattr(obj, '__module__') else 'N/A'}")
                
                # Try to get source if available
                try:
                    import inspect
                    source = inspect.getsource(obj)
                    print(f"  Source (first 20 lines):")
                    for i, line in enumerate(source.split('\n')[:20]):
                        print(f"    {line}")
                except:
                    print(f"  Could not get source")
    
    # Now test what they return
    print("\n" + "="*80)
    print("Testing what sample agents return...")
    print("="*80)
    
    # Create a test observation
    test_observation = {
        'remainingOverageTime': 600,
        'step': 0,
        'select': None,
        'logs': [],
        'current': None,
        'search_begin_input': None
    }
    
    for agent_name, agent_func in sample_agents.items():
        print(f"\nTesting {agent_name}:")
        try:
            result = agent_func(test_observation, {})
            print(f"  Returned: {result}")
            print(f"  Type: {type(result)}")
            if hasattr(result, '__len__'):
                print(f"  Length: {len(result)}")
                if len(result) > 0:
                    print(f"  First 10 elements: {result[:10]}")
        except Exception as e:
            print(f"  Error: {e}")

def trace_agent_behavior():
    """Trace the actual behavior of sample agents."""
    
    print("\n" + "="*80)
    print("Tracing agent behavior in actual environment...")
    print("="*80)
    
    from kaggle_environments import make
    
    # Load deck
    deck_path = PROJECT_ROOT / "deck.csv"
    deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            deck.append(int(stripped))
    
    # Create instrumented version of first_agent
    import kaggle_environments.envs.cabt.cabt as cabt_module
    
    if hasattr(cabt_module, 'first_agent'):
        original_first_agent = cabt_module.first_agent
        
        def instrumented_first_agent(observation, configuration):
            print(f"\n[INSTRUMENTED_FIRST_AGENT] Called")
            print(f"  observation keys: {list(observation.keys())}")
            print(f"  current: {observation.get('current')}")
            print(f"  select: {observation.get('select')}")
            print(f"  step: {observation.get('step')}")
            
            result = original_first_agent(observation, configuration)
            print(f"  Returning: {result}")
            print(f"  Type: {type(result)}")
            if hasattr(result, '__len__'):
                print(f"  Length: {len(result)}")
            
            return result
        
        # Create environment with instrumented agent
        env = make(
            "cabt",
            configuration={
                "decks": [deck, deck],
            },
            debug=True,
        )
        
        print("\nRunning environment with instrumented first_agent...")
        steps = env.run([instrumented_first_agent, instrumented_first_agent])
        
        print(f"\nRun completed with {len(steps)} steps")
        final_step = steps[-1]
        for i, state in enumerate(final_step):
            print(f"Agent {i}: status={state.status}, reward={state.reward}")
    
    # Also test random_agent
    if hasattr(cabt_module, 'random_agent'):
        print("\n" + "-"*80)
        print("Testing random_agent directly...")
        
        test_observation = {
            'remainingOverageTime': 600,
            'step': 0,
            'select': None,
            'logs': [],
            'current': None,
            'search_begin_input': None
        }
        
        result = cabt_module.random_agent(test_observation, {})
        print(f"random_agent returned: {result}")
        print(f"Type: {type(result)}")
        if hasattr(result, '__len__'):
            print(f"Length: {len(result)}")

def check_observation_wrapping():
    """Check if observations are wrapped differently."""
    
    print("\n" + "="*80)
    print("Checking observation wrapping...")
    print("="*80)
    
    from kaggle_environments import make
    import kaggle_environments.core as core
    
    # Monkey-patch to see what's passed to agents
    original_act_agent = None
    if hasattr(core, 'act_agent'):
        original_act_agent = core.act_agent
        
        def instrumented_act_agent(state, agent):
            print(f"\n[ACT_AGENT_INSTRUMENTATION]")
            print(f"  state type: {type(state)}")
            if isinstance(state, dict):
                print(f"  state keys: {list(state.keys())}")
                if 'observation' in state:
                    print(f"  state['observation']: {state['observation']}")
            return original_act_agent(state, agent)
        
        core.act_agent = instrumented_act_agent
    
    # Load deck
    deck_path = PROJECT_ROOT / "deck.csv"
    deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            deck.append(int(stripped))
    
    # Simple agent
    def simple_agent(observation, configuration):
        print(f"\n[SIMPLE_AGENT] Called")
        print(f"  observation type: {type(observation)}")
        if isinstance(observation, dict):
            print(f"  observation keys: {list(observation.keys())}")
        return []
    
    # Create environment
    env = make(
        "cabt",
        configuration={
            "decks": [deck, deck],
        },
        debug=True,
    )
    
    print("\nRunning environment...")
    try:
        steps = env.run([simple_agent, simple_agent])
        print(f"\nRun completed")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    examine_sample_agents()
    trace_agent_behavior()
    check_observation_wrapping()