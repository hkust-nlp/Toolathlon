from addict import Dict
from pathlib import Path

all_token_key_session = Dict(
    emails_config_file = str(Path(__file__).parent / "email_config.json"),
)