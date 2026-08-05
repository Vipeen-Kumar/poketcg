"""Instrument the cabt environment interpreter to capture detailed debugging information."""

import sys
import os
from pathlib import Path
import importlib

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

def instrument_cabt_environment():
    """Monkey-patch the cabt environment interpreter function."""
    
    try:
        import kaggle_environments
    except ImportError as e:
        print(f"ERROR: Cannot import kaggle_environments: {e}")
        return False
    
    # Find the cabt environment module
    try:
        # Try to import directly
        cabt_module = importlib.import_module("kaggle_environments.envs.cabt.cabt")
        print(f"Found cabt module: {cabt_module.__file__}")
    except ImportError as e:
        print(f"ERROR: Cannot import cabt module: {e}")
        return False
    
    # Store the original interpreter function
    original_interpreter = None
    if hasattr(cabt_module, "interpreter"):
        original_interpreter = cabt_module.interpreter
        print(f"Found original interpreter: {original_interpreter}")
    else:
        print("ERROR: No interpreter function found in cabt module")
        return False
    
    def instrumented_interpreter(state, env):
        """Instrumented interpreter with detailed debugging."""
        import sys
        
        print("\n" + "="*80)
        print("[CABT_INSTRUMENTATION] Interpreter called")
        print(f"[CABT_INSTRUMENTATION] state type: {type(state)}")
        print(f"[CABT_INSTRUMENTATION] state length: {len(state) if hasattr(state, '__len__') else 'N/A'}")
        
        # Print detailed state information
        for i, s in enumerate(state):
            print(f"\n[CABT_INSTRUMENTATION] state[{i}]:")
            print(f"  Type: {type(s)}")
            if hasattr(s, '__dict__'):
                for key, value in s.__dict__.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  Repr: {repr(s)[:200]}")
            
            # Check if this is a Battle object
            if hasattr(s, 'battle_ptr'):
                print(f"  battle_ptr: {s.battle_ptr}")
            
            # Check for action
            if hasattr(s, 'action'):
                action = s.action
                print(f"\n  [CABT_INSTRUMENTATION] Agent {i} action analysis:")
                print(f"    Type: {type(action)}")
                print(f"    Repr: {repr(action)[:200]}")
                if hasattr(action, '__len__'):
                    print(f"    Length: {len(action)}")
                    if len(action) > 0:
                        print(f"    First 10 elements: {action[:10]}")
                        print(f"    Last 10 elements: {action[-10:] if len(action) > 10 else action}")
                        
                        # Check element types
                        if len(action) > 0:
                            first_elem = action[0]
                            print(f"    First element type: {type(first_elem)}")
                            print(f"    First element value: {first_elem}")
                            
                        # Check for None values
                        none_count = sum(1 for elem in action if elem is None)
                        if none_count > 0:
                            print(f"    WARNING: {none_count} None values found in action")
                        
                        # Check for duplicates
                        if len(action) > 0:
                            unique_count = len(set(action))
                            if unique_count < len(action):
                                print(f"    WARNING: {len(action) - unique_count} duplicate values found")
                
                # Check if action is a list of ints
                if isinstance(action, list):
                    all_ints = all(isinstance(x, int) for x in action)
                    print(f"    All elements are ints: {all_ints}")
                    if not all_ints:
                        non_int_types = {type(x) for x in action if not isinstance(x, int)}
                        print(f"    Non-int types found: {non_int_types}")
        
        # Call original interpreter
        print("\n[CABT_INSTRUMENTATION] Calling original interpreter...")
        try:
            result = original_interpreter(state, env)
            print(f"[CABT_INSTRUMENTATION] Original interpreter returned: {type(result)}")
            
            # Check if we can get more info from env
            if hasattr(env, 'logs'):
                print(f"[CABT_INSTRUMENTATION] Environment logs length: {len(env.logs)}")
                if env.logs:
                    print(f"[CABT_INSTRUMENTATION] Last few logs: {env.logs[-5:]}")
            
            return result
        except Exception as e:
            print(f"[CABT_INSTRUMENTATION] Original interpreter raised exception: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # Replace the interpreter function
    cabt_module.interpreter = instrumented_interpreter
    print(f"Successfully instrumented cabt interpreter")
    
    # Also try to instrument the battle_start function if we can find it
    try:
        # Try to find the Battle class
        for name, obj in cabt_module.__dict__.items():
            if 'Battle' in name:
                print(f"Found potential Battle class: {name}")
                if hasattr(obj, 'battle_start'):
                    original_battle_start = obj.battle_start
                    
                    def instrumented_battle_start(self, deck0, deck1):
                        print("\n" + "="*80)
                        print("[CABT_INSTRUMENTATION] battle_start called")
                        print(f"[CABT_INSTRUMENTATION] deck0 type: {type(deck0)}, length: {len(deck0) if hasattr(deck0, '__len__') else 'N/A'}")
                        print(f"[CABT_INSTRUMENTATION] deck1 type: {type(deck1)}, length: {len(deck1) if hasattr(deck1, '__len__') else 'N/A'}")
                        
                        print(f"[CABT_INSTRUMENTATION] deck0 first 10: {deck0[:10] if hasattr(deck0, '__getitem__') and len(deck0) > 10 else deck0}")
                        print(f"[CABT_INSTRUMENTATION] deck1 first 10: {deck1[:10] if hasattr(deck1, '__getitem__') and len(deck1) > 10 else deck1}")
                        
                        result = original_battle_start(self, deck0, deck1)
                        
                        print(f"[CABT_INSTRUMENTATION] battle_start returned:")
                        print(f"  Type: {type(result)}")
                        if isinstance(result, dict):
                            for key, value in result.items():
                                print(f"  {key}: {value}")
                        elif hasattr(result, '__dict__'):
                            for key, value in result.__dict__.items():
                                print(f"  {key}: {value}")
                        
                        return result
                    
                    obj.battle_start = instrumented_battle_start
                    print(f"Instrumented battle_start method")
                    break
    except Exception as e:
        print(f"Could not instrument battle_start: {e}")
    
    return True

def run_instrumented_test():
    """Run a test with the instrumented environment."""
    
    print("Loading kaggle environments...")
    from kaggle_environments import make
    
    print("Creating cabt environment...")
    
    # Load deck from deck.csv
    deck_path = PROJECT_ROOT / "deck.csv"
    deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            deck.append(int(stripped))
    
    print(f"Loaded deck with {len(deck)} cards")
    
    # Use DiagnosticAgentWrapper to handle the Kaggle signature
    from run_local import DiagnosticAgentWrapper, build_local_agent
    
    # Create wrapped agents
    agent0 = DiagnosticAgentWrapper(
        build_local_agent(replay_enabled=False, game_id_prefix="instrumented_p0"),
        name="agent0",
    )
    agent1 = DiagnosticAgentWrapper(
        build_local_agent(replay_enabled=False, game_id_prefix="instrumented_p1"),
        name="agent1",
    )
    
    # Create environment
    env = make(
        "cabt",
        configuration={
            "decks": [deck, deck],
        },
        debug=True,
    )
    
    print("Running environment with instrumented interpreter...")
    try:
        steps = env.run([agent0, agent1])
        print(f"Environment run completed with {len(steps)} steps")
        
        final_step = steps[-1]
        statuses = [state.status for state in final_step]
        rewards = [state.reward for state in final_step]
        print(f"Final statuses: {statuses}")
        print(f"Final rewards: {rewards}")
        
    except Exception as e:
        print(f"Environment run failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting cabt environment instrumentation...")
    
    if instrument_cabt_environment():
        print("\nSuccessfully instrumented environment. Running test...")
        run_instrumented_test()
    else:
        print("Failed to instrument environment")