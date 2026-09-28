from addict import Dict
# Task-local token overrides (merged over configs/token_key_session.py).
# atom/atom is a third-party public repo: the github MCP server's allowlist
# only gates repos under the token owner's own account, so any value works
# here — set a harmless placeholder and keep the server read-only.
all_token_key_session = Dict(
    github_allowed_repos = "no-personal-repos-needed",
    github_read_only = "1",  # analysis-only task, no write access needed
)
