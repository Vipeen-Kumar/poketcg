"""Detailed instrumentation of the cabt environment with aggressive patching."""

import sys
import os
from pathlib import Path
import importlib
import types

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

class CabtInstrumentation:
    """Comprehensive instrumentation for cabt environment."""
    
    def __init__(self):
        self.original_interpreter = None
        self.original_battle_start = None
        self.cabt_module = None
        
    def install(self):
        """Install instrumentation hooks."""
        print("Installing cabt instrumentation...")
        
        try:
            import kaggle_environments
        except ImportError as e:
            print(f"ERROR: Cannot import kaggle_environments: {e}")
            return False
        
        # Find the cabt environment module
        try:
            self.cabt_module = importlib.import_module("kaggle_environments.envs.cabt.cabt")
            print(f"Found cabt module: {self.cabt_module.__file__}")
        except ImportError as e:
            print(f"ERROR: Cannot import cabt module: {e}")
            return False
        
        # Instrument the interpreter function
        if hasattr(self.cabt_module, "interpreter"):
            self.original_interpreter = self.cabt_module.interpreter
            print(f"Found original interpreter: {self.original_interpreter}")
            
            def instrumented_interpreter(state, env):
                """Fully instrumented interpreter with detailed debugging."""
                print("\n" + "="*80)
                print("[CABT_INSTRUMENTATION] INTERPRETER CALLED")
                print(f"[CABT_INSTRUMENTATION] state type: {type(state)}")
                print(f"[CABT_INSTRUMENTATION] state length: {len(state) if hasattr(state, '__len__') else 'N/A'}")
                
                # Print detailed state information for each agent
                for i, s in enumerate(state):
                    print(f"\n[CABT_INSTRUMENTATION] Agent {i} state analysis:")
                    print(f"  Type: {type(s)}")
                    
                    # Check if this is a Battle object
                    if hasattr(s, 'battle_ptr'):
                        print(f"  battle_ptr: {s.battle_ptr}")
                        print(f"  battle_ptr is None: {s.battle_ptr is None}")
                    
                    # Check for action attribute
                    if hasattr(s, 'action'):
                        action = s.action
                        print(f"\n  [CABT_INSTRUMENTATION] Agent {i} action analysis:")
                        self._analyze_action(action, i)
                    else:
                        print(f"  No action attribute found")
                    
                    # Check for status attribute
                    if hasattr(s, 'status'):
                        print(f"  status: {s.status}")
                    
                    # Check for reward attribute
                    if hasattr(s, 'reward'):
                        print(f"  reward: {s.reward}")
                
                # Call original interpreter
                print("\n[CABT_INSTRUMENTATION] Calling original interpreter...")
                try:
                    result = self.original_interpreter(state, env)
                    print(f"[CABT_INSTRUMENTATION] Original interpreter returned: {type(result)}")
                    
                    # Analyze the result
                    if isinstance(result, list) and len(result) > 0:
                        print(f"[CABT_INSTRUMENTATION] Result has {len(result)} elements")
                        for i, r in enumerate(result):
                            print(f"  Result[{i}]:")
                            if hasattr(r, 'status'):
                                print(f"    status: {r.status}")
                            if hasattr(r, 'reward'):
                                print(f"    reward: {r.reward}")
                    
                    return result
                except Exception as e:
                    print(f"[CABT_INSTRUMENTATION] Original interpreter raised exception: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
            
            self.cabt_module.interpreter = instrumented_interpreter
            print("Successfully instrumented interpreter")
        
        # Instrument the Battle class if found
        self._instrument_battle_class()
        
        # Also instrument the environment factory
        self._instrument_environment_factory()
        
        return True
    
    def _analyze_action(self, action, agent_index):
        """Analyze an action with detailed diagnostics."""
        print(f"    Type: {type(action)}")
        print(f"    Repr: {repr(action)[:500]}")
        
        if hasattr(action, '__len__'):
            print(f"    Length: {len(action)}")
            
            if len(action) > 0:
                # Show first and last elements
                print(f"    First 10 elements: {action[:10]}")
                if len(action) > 10:
                    print(f"    Last 10 elements: {action[-10:]}")
                
                # Check element types
                first_elem = action[0]
                print(f"    First element type: {type(first_elem)}")
                print(f"    First element value: {first_elem}")
                
                # Check for None values
                none_count = sum(1 for elem in action if elem is None)
                if none_count > 0:
                    print(f"    WARNING: {none_count} None values found in action")
                    # Find positions of None values
                    none_positions = [i for i, elem in enumerate(action) if elem is None]
                    print(f"    None positions (first 10): {none_positions[:10]}")
                
                # Check for duplicates
                if len(action) > 0:
                    unique_count = len(set(action))
                    if unique_count < len(action):
                        duplicates = len(action) - unique_count
                        print(f"    WARNING: {duplicates} duplicate values found")
                
                # Check if all elements are ints
                if isinstance(action, list):
                    all_ints = all(isinstance(x, int) for x in action)
                    print(f"    All elements are ints: {all_ints}")
                    if not all_ints:
                        non_int_types = {}
                        for x in action:
                            t = type(x)
                            if not isinstance(x, int):
                                non_int_types[t] = non_int_types.get(t, 0) + 1
                        print(f"    Non-int types found: {non_int_types}")
        
        # Special handling for empty actions
        if action is None:
            print(f"    WARNING: Action is None")
        elif isinstance(action, list) and len(action) == 0:
            print(f"    WARNING: Action is empty list")
        elif isinstance(action, list) and len(action) == 1 and action[0] == 0:
            print(f"    NOTE: Action is [0] - likely test/debug value")
    
    def _instrument_battle_class(self):
        """Instrument the Battle class methods."""
        try:
            # Find Battle class
            Battle = None
            for name, obj in self.cabt_module.__dict__.items():
                if 'Battle' in name and isinstance(obj, type):
                    Battle = obj
                    print(f"Found Battle class: {name}")
                    break
            
            if Battle is not None:
                # Instrument battle_start
                if hasattr(Battle, 'battle_start'):
                    self.original_battle_start = Battle.battle_start
                    
                    def instrumented_battle_start(self, deck0, deck1):
                        print("\n" + "="*80)
                        print("[CABT_INSTRUMENTATION] BATTLE_START CALLED")
                        print(f"[CABT_INSTRUMENTATION] deck0 type: {type(deck0)}, length: {len(deck0) if hasattr(deck0, '__len__') else 'N/A'}")
                        print(f"[CABT_INSTRUMENTATION] deck1 type: {type(deck1)}, length: {len(deck1) if hasattr(deck1, '__len__') else 'N/A'}")
                        
                        if hasattr(deck0, '__len__') and len(deck0) > 0:
                            print(f"[CABT_INSTRUMENTATION] deck0 first 10: {deck0[:10]}")
                            print(f"[CABT_INSTRUMENTATION] deck0 last 10: {deck0[-10:] if len(deck0) > 10 else deck0}")
                        
                        if hasattr(deck1, '__len__') and len(deck1) > 0:
                            print(f"[CABT_INSTRUMENTATION] deck1 first 10: {deck1[:10]}")
                            print(f"[CABT_INSTRUMENTATION] deck1 last 10: {deck1[-10:] if len(deck1) > 10 else deck1}")
                        
                        # Validate decks
                        if hasattr(deck0, '__len__'):
                            print(f"[CABT_INSTRUMENTATION] deck0 validation:")
                            self._analyze_action(deck0, 0)
                        
                        if hasattr(deck1, '__len__'):
                            print(f"[CABT_INSTRUMENTATION] deck1 validation:")
                            self._analyze_action(deck1, 1)
                        
                        print("\n[CABT_INSTRUMENTATION] Calling original battle_start...")
                        result = self.original_battle_start(self, deck0, deck1)
                        
                        print(f"\n[CABT_INSTRUMENTATION] battle_start returned:")
                        print(f"  Type: {type(result)}")
                        
                        # Extract all diagnostic information
                        if isinstance(result, dict):
                            print("  Result dictionary contents:")
                            for key, value in result.items():
                                print(f"    {key}: {repr(value)[:200]}")
                            
                            # Look for error information
                            error_keys = [k for k in result.keys() if 'error' in k.lower()]
                            for key in error_keys:
                                print(f"    ERROR FIELD {key}: {result[key]}")
                            
                            # Check for errorPlayer
                            if 'errorPlayer' in result:
                                error_player = result['errorPlayer']
                                print(f"    ERROR PLAYER: {error_player}")
                                if error_player >= 0:
                                    print(f"    BATTLE_START FAILED for player {error_player}")
                                    if 'error' in result:
                                        print(f"    ERROR MESSAGE: {result['error']}")
                                    if 'code' in result:
                                        print(f"    ERROR CODE: {result['code']}")
                        
                        elif hasattr(result, '__dict__'):
                            print("  Result object attributes:")
                            for key, value in result.__dict__.items():
                                print(f"    {key}: {repr(value)[:200]}")
                        
                        return result
                    
                    Battle.battle_start = instrumented_battle_start
                    print("Instrumented battle_start method")
                
                # Also instrument other key methods if needed
                if hasattr(Battle, '__init__'):
                    original_init = Battle.__init__
                    
                    def instrumented_init(self, *args, **kwargs):
                        print(f"\n[CABT_INSTRUMENTATION] Battle.__init__ called")
                        print(f"  args: {args}")
                        print(f"  kwargs: {kwargs}")
                        return original_init(self, *args, **kwargs)
                    
                    Battle.__init__ = instrumented_init
                    print("Instrumented Battle.__init__")
                    
        except Exception as e:
            print(f"Could not fully instrument Battle class: {e}")
            import traceback
            traceback.print_exc()
    
    def _instrument_environment_factory(self):
        """Instrument the environment factory to catch environment creation."""
        try:
            import kaggle_environments.core as core
            
            original_make_env = getattr(core, '_make_env', None)
            if original_make_env:
                def instrumented_make_env(name, configuration, steps, *args, **kwargs):
                    print(f"\n[CABT_INSTRUMENTATION] _make_env called for: {name}")
                    print(f"  configuration: {configuration}")
                    print(f"  steps: {steps}")
                    return original_make_env(name, configuration, steps, *args, **kwargs)
                
                core._make_env = instrumented_make_env
                print("Instrumented _make_env")
        except Exception as e:
            print(f"Could not instrument environment factory: {e}")

def run_detailed_test():
    """Run a detailed test with comprehensive instrumentation."""
    
    print("\n" + "="*80)
    print("STARTING DETAILED CABT INSTRUMENTATION TEST")
    print("="*80)
    
    # Install instrumentation
    instrumentation = CabtInstrumentation()
    if not instrumentation.install():
        print("Failed to install instrumentation")
        return
    
    # Now run the test
    from kaggle_environments import make
    
    # Load deck
    deck_path = PROJECT_ROOT / "deck.csv"
    deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            deck.append(int(stripped))
    
    print(f"\nLoaded deck with {len(deck)} cards")
    print(f"Deck first 10: {deck[:10]}")
    print(f"Deck last 10: {deck[-10:]}")
    
    # Create environment with detailed logging
    print("\nCreating cabt environment...")
    env = make(
        "cabt",
        configuration={
            "decks": [deck, deck],
        },
        debug=True,
    )
    
    print("\nEnvironment created successfully")
    
    # Create simple test agents
    def test_agent(observation, configuration):
        print(f"\n[TEST_AGENT] Called with observation keys: {list(observation.keys())}")
        print(f"[TEST_AGENT] observation['current']: {observation.get('current')}")
        print(f"[TEST_AGENT] observation['select']: {observation.get('select')}")
        print(f"[TEST_AGENT] observation['step']: {observation.get('step')}")
        
        # Return the deck when current=None and select=None
        if observation.get('current') is None and observation.get('select') is None:
            print(f"[TEST_AGENT] Returning deck (60 cards)")
            return deck
        else:
            print(f"[TEST_AGENT] Returning empty list for non-deck-selection")
            return []
    
    # Run environment
    print("\nRunning environment with test agents...")
    try:
        steps = env.run([test_agent, test_agent])
        print(f"\nEnvironment run completed with {len(steps)} steps")
        
        final_step = steps[-1]
        statuses = [state.status for state in final_step]
        rewards = [state.reward for state in final_step]
        print(f"Final statuses: {statuses}")
        print(f"Final rewards: {rewards}")
        
        # Print detailed final state
        print("\nFinal step details:")
        for i, state in enumerate(final_step):
            print(f"  Agent {i}:")
            if hasattr(state, 'status'):
                print(f"    status: {state.status}")
            if hasattr(state, 'reward'):
                print(f"    reward: {state.reward}")
            if hasattr(state, 'action'):
                print(f"    action: {state.action}")
        
    except Exception as e:
        print(f"\nEnvironment run failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_detailed_test()