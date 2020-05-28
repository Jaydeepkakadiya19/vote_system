import json
import hashlib
from ecdsa import SigningKey, VerifyingKey

with open("signing_key_block.pem", "rb") as f:
    sk_block = f.read()
    sk_block = SigningKey.from_pem(sk_block)

with open("verifying_key_block.pem", "rb") as f:
    vk_block = f.read()
    vk_block = VerifyingKey.from_pem(vk_block)

# with open("sk_txn.pem", "rb") as f:
#     sk_txn = f.read()
#     sk_txn = SigningKey.from_pem(sk_txn)

# with open("vk_txn.pem", "rb") as f:
#     vk_txn = f.read()
#     vk_txn = VerifyingKey.from_pem(vk_txn)

# def sign_transaction(pub_key, vote):
#     transaction = {
#             "pub_key" : pub_key,
#             "vote" : vote
#         }
#     encoded_txn = json.dumps(transaction, sort_keys=True).encode()
#     return sk_txn.sign(encoded_txn).hex()


def verify_transaction(transaction):
    pub_key = transaction["public_key"]
    msg = transaction["vote"]
    sign = transaction["sign"]
    # txn = {
    #         "pub_key" : transaction["pub_key"],
    #         "vote" : transaction["vote"].
    #         "sign" : transaction["sign"]
    #     }

    # sign = bytes.fromhex(transaction["sign"])
    # encoded_txn = json.dumps(txn, sort_keys=True).encode()
    return public_key.verify(sign, msg)


def encrypt(transaction):
    encoded_transaction = json.dumps(transaction, sort_keys=True).encode()
    return hashlib.sha256(encoded_transaction).hexdigest()


def is_valid_block(block):
    blk = {
        "index": block["index"],
        "transactions": block["transactions"],
        "timestamp": block["timestamp"],
        "previous_hash": block["previous_hash"]
    }
    sign = bytes.fromhex(block["proof_of_verification"])
    encoded_block = json.dumps(blk, sort_keys=True).encode()
    return vk_block.verify(sign, encoded_block)


def sign_block(index, transactions, timestamp, previous_hash):
    for transaction in transactions:
        if not verify_transaction(transactions[transaction]):
            return False

    block = {
        "index": index,
        "transactions": transactions,
        "timestamp": timestamp,
        "previous_hash": previous_hash
    }

    encoded_block = json.dumps(block, sort_keys=True).encode()
    sign = sk_block.sign(encoded_block).hex()
    return sign
