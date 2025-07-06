from addict import Dict
import os
# I am gradually modifying the tokens to the pseudo account in this project
all_token_key_session = Dict(
    # added, use pseudo account!
    leetcode_session = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhY2NvdW50X3ZlcmlmaWVkX2VtYWlsIjpudWxsLCJfYXV0aF91c2VyX2lkIjoiMTc5NDI4NjMiLCJfYXV0aF91c2VyX2JhY2tlbmQiOiJhbGxhdXRoLmFjY291bnQuYXV0aF9iYWNrZW5kcy5BdXRoZW50aWNhdGlvbkJhY2tlbmQiLCJfYXV0aF91c2VyX2hhc2giOiI0ZmIzZjdiMmI5YjRhM2FhMGFmZTgxMmQzNjFiOTIyMzk1MTM2M2MzYjJjZGZjZTNhYzllMGQ0YjgzNWI2MGQ1Iiwic2Vzc2lvbl91dWlkIjoiNjhmODg3ZGQiLCJpZCI6MTc5NDI4NjMsImVtYWlsIjoibWNwdGVzdDA2MDZAZ21haWwuY29tIiwidXNlcm5hbWUiOiJ6eE51aGlEeXJoIiwidXNlcl9zbHVnIjoienhOdWhpRHlyaCIsImF2YXRhciI6Imh0dHBzOi8vYXNzZXRzLmxlZXRjb2RlLmNvbS91c2Vycy9kZWZhdWx0X2F2YXRhci5qcGciLCJyZWZyZXNoZWRfYXQiOjE3NDk0MzY4MDEsImlwIjoiMTkyLjIxMC4yMDYuMjMxIiwiaWRlbnRpdHkiOiIwZmU2ZmViNTQyODlmNGM2NzAyN2VjMDZjYzIxMzFmOCIsImRldmljZV93aXRoX2lwIjpbImI0OTQ1MGIwYTMwMzVjMDM4ZTBmYTc3MDY4NzQ4NjBhIiwiMTkyLjIxMC4yMDYuMjMxIl19.ifUux-wVKksegSMEvjY2TvLXxIOyshAEO9CE7rV790g",
    github_token = "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",
    # these tokens are obtained via my own account, I think its ok to use them in this project
    # but for other people who also want to use this benchmark, please set up by their own
    edgeone_token = "IP7o6Pdy6nNIG9g+MNld8Ucb8I2RLyikAnAacLMPs0E=",
    firecrawl_token = "fc-88402686bf9f44c797ef5d2bedc0267d",
    google_cloud_console_api_key = "AIzaSyD8Q5ZPqCDZIgjOwBc9QtbdFLfGkijBmMU",
    google_search_engine_id = "d08f1d4bbe2294372",
    huggingface_token = "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",
    linkedin_email = "mcptest0606@gmail.com",
    linkedin_password = "MCPtest0606!!",
    canvas_api_token = "7~V7h4JX2rRftvrZFYUCQDKEmDvFCUxkCKa3vLZxCueF7mLeVQNhaR8FmZ3EJW6kkk",
    canvas_domain = "canvas.instructure.com",
    wandb_api_key = "b3abe195bd69c07bdc47469d3956ac8d0c008714",
    tessdata_prefix = os.environ["TESSDATA_PREFIX"],
    amap_key="f789815a157fe45439c674c4a10e615b",
    google_sheets_folder_id = "1LYqmSCIlY0NmHtFJwF3Mh1RTb81RWHvU"
)