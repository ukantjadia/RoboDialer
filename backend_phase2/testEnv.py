from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Print everything in the environment (only relevant ones)
print("\n🔍 [Sanity Check] Loaded environment variables:")
for key, value in os.environ.items():
    if any(env_key in key for env_key in ["DECODO", "LINKEDIN", "LI_AT", "USERNAME", "PASSWORD"]):
        print(
            f"{key} = {value[:6]}... (length={len(value)})"
            if "PASS" in key or "TOKEN" in key
            else f"{key} = {value}"
        )
