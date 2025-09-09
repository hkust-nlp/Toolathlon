from addict import Dict
import os
# this is the local token key session for local testing
# will override the token key session in the global ones in configs/token_key_session.py
all_token_key_session = Dict(

    # canvas_domain = "localhost:20001",
    canvas_api_token = "mcpcanvasadmintoken3",
    
    emails_config_file = os.path.join(os.path.dirname(__file__), "email_config.json"),
    
    # Canvas teacher tokens for batch operations
    all_canvas_teacher_tokens = [
        "canvas_token_dennis2000!j",
        "canvas_token_DR0824@gpMA0",
        "canvas_token_Msanchez494c",
        "canvas_token_benjamin_77v",
        "canvas_token_christina1994@",
        "canvas_token_cruz@j304tdg",
        "canvas_token_Ncart3ze1TQF",
        "canvas_token_gomez$c571Fp",
        "canvas_token_RR1206!SWseq",
        "canvas_token_RC0807@XecTY",
        "canvas_token_brian_81W5Oc",
        "canvas_token_brian1990$p1"
    ]
)
