"""Capture and display environment errors directly."""

import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Monkey-patch the Battle class to capture battle_start errors
import importlib

def patch_battle_class():
    """Patch the Battle class to capture battle_start errors."""
    
    try:
        cabt_module = importlib.import_module("kaggle_environments.envs.cabt.cabt")
        print(f"Found cabt module: {cabt_module.__file__}")
        
        # Find Battle class
        Battle = None
        for name, obj in cabt_module.__dict__.items():
            if 'Battle' in name and isinstance(obj, type):
                Battle = obj
                print(f"Found Battle class: {name}")
                break
        
        if Battle is not None and hasattr(Battle, 'battle_start'):
            original_battle_start = Battle.battle_start
            
            def patched_battle_start(self, deck0, deck1):
                print("\n" + "="*80)
                print("[ERROR_CAPTURE] battle_start called")
                print(f"[ERROR_CAPTURE] deck0 type: {type(deck0)}, len: {len(deck0)}")
                print(f"[ERROR_CAPTURE] deck1 type: {type(deck1)}, len: {len(deck1)}")
                
                # Call original
                result = original_battle_start(self, deck0, deck1)
                
                print(f"[ERROR_CAPTURE] battle_start returned: {type(result)}")
                
                if isinstance(result, dict):
                    print("[ERROR_CAPTURE] Result dictionary:")
                    for key, value in result.items():
                        print(f"  {key}: {value}")
                    
                    # Check for errors
                    if 'errorPlayer' in result:
                        error_player = result['errorPlayer']
                        print(f"\n[ERROR_CAPTURE] ERROR DETECTED:")
                        print(f"  errorPlayer: {error_player}")
                        if error_player >= 0:
                            print(f"  Battle failed for player {error_player}")
                            if 'error' in result:
                                print(f"  Error message: {result['error']}")
                            if 'code' in result:
                                print(f"  Error code: {result['code']}")
                            
                            # Try to get more detailed error info
                            for key in result:
                                if 'err' in key.lower() or 'msg' in key.lower():
                                    print(f"  {key}: {result[key]}")
                
                return result
            
            Battle.battle_start = patched_battle_start
            print("Successfully patched battle_start")
            return True
            
    except Exception as e:
        print(f"Failed to patch Battle class: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def run_error_capture_test():
    """Run test with error capture."""
    
    from kaggle_environments import make
    
    # Load deck
    deck_path = PROJECT_ROOT / "deck.csv"
    deck = []
    for line in deck_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            deck.append(int(stripped))
    
    print(f"Deck length: {len(deck)}")
    
    # Simple test agent
    def test_agent(observation, configuration):
        if observation.get('current') is None and observation.get('select') is None:
            print(f"\n[AGENT] Returning deck ({len(deck)} cards)")
            return deck
        return []
    
    # Create environment
    print("\nCreating environment...")
    env = make(
        "cabt",
        configuration={
            "decks": [deck, deck],
        },
        debug=True,
    )
    
    # Run environment
    print("\nRunning environment...")
    steps = env.run([test_agent, test_agent])
    
    print(f"\nRun completed with {len(steps)} steps")
    
    # Check final state
    final_step = steps[-1]
    for i, state in enumerate(final_step):
        print(f"\nAgent {i} final state:")
        print(f"  status: {state.status}")
        print(f"  reward: {state.reward}")
        if hasattr(state, 'action'):
            action_len = len(state.action) if hasattr(state.action, '__len__') else 'N/A'
            print(f"  action length: {action_len}")
    
    # Check environment logs
    print(f"\nEnvironment logs ({len(env.logs)}):")
    for log in env.logs[-10:]:  # Last 10 logs
        print(f"  {log}")

if __name__ == "__main__":
    print("Starting error capture test...")
    
    if patch_battle_class():
        run_error_capture_test()
    else:
        print("Failed to install patches, running without...")
        run_error_capture_test()