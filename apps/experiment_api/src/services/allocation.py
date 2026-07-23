import hashlib
from typing import Dict

def get_user_variant(user_id: str, experiment_name: str, variants: Dict[str, int]) -> str:
    string_to_hash = f"{user_id}:{experiment_name}"
    hash_hex = hashlib.sha256(string_to_hash.encode('utf-8')).hexdigest()
    user_hash = int(hash_hex, 16) % 10000 / 100.0

    total = sum(variants.values())
    scaled = user_hash / 100.0 * total
    cumulative = 0

    for variant_name, weight in variants.items():
        cumulative += weight
        if scaled < cumulative:
            return variant_name

    return "control"