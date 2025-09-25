import requests
import json
from configs.global_configs import global_configs

response = requests.get(
  url="https://openrouter.ai/api/v1/key",
  headers={
    "Authorization": f"Bearer {global_configs.openrouter_key}"
  }
)

print(json.dumps(response.json(), indent=2))
