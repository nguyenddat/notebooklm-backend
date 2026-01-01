import tiktoken

def estimate_token_count(model_name: str, prompt: str) -> int:
    try:
        enc = tiktoken.encoding_for_model(model_name)
    except KeyError:
        enc = tiktoken.get_encoding("o200k_base")

    token_count = len(enc.encode(prompt))
    return token_count