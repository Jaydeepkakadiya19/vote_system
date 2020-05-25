import json
import hashlib

def verify_transaction(pub_key, vote, sign):
    return True


def encrypt(transaction):
    encoded_transaction = json.dumps(transaction, sort_keys=True).encode()
    return hashlib.sha256(encoded_transaction).hexdigest()