def normalize_base_url(value):
    # Deliberate bug: a gateway's configured path is part of its address.
    return value.strip().rstrip("/").replace("/v1", "")
