import kaggle_environments.envs.cabt_env as cabt_env
import inspect

# Get the file location
file_path = inspect.getfile(cabt_env)
print(f"CABT env file: {file_path}")

# List available classes and functions
print("\nAvailable in cabt_env:")
for name, obj in inspect.getmembers(cabt_env):
    if not name.startswith('_') and callable(obj):
        print(f"  {name}: {type(obj).__name__}")
