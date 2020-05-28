import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from hashlib import sha256
import time
import utils

class Block:
    def __init__(self, index, transactions, proof_of_verification, timestamp, previous_hash):
        self.index = index
        self.transactions = transactions
        self.proof_of_verification = proof_of_verification
        self.timestamp = timestamp
        self.previous_hash = previous_hash # Adding the previous hash field

    def compute_hash(self):
        block_string = json.dumps(self.__dict__, sort_keys=True) # The string equivalent also considers the previous_hash field now
        return sha256(block_string.encode()).hexdigest()
    
    

class Blockchain:

    def __init__(self, PORT):
        self.chain = []
        self.transactions = {}
        self.peers = set()
        self.PORT = PORT
        self.sequence_number = 1
        self.encrypted_transactions = {}
        self.pending_blocks = {}
        self.pending_blocks_counts = {}
        self.received_block_advertises = set()

    def create_genesis_block(self):
        block = {
                "index" : 0,
                "transactions" : {},
                "timestamp" : time.time(),
                "previous_hash" : 0
            }
        sign = utils.sign_block(block["index"], block["transactions"], block["timestamp"], block["previous_hash"])
        genesis_block = Block(
                index = block["index"],
                transactions = block["transactions"],
                proof_of_verification = sign,
                timestamp = block["timestamp"],
                previous_hash = block["previous_hash"]
            )
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)
        return genesis_block.__dict__

    @property
    def last_block(self):
        return self.chain[-1]
    
    def add_new_transaction(self, tx_data):
        transaction_id = str(self.PORT) + str(self.sequence_number)
        self.transactions[transaction_id] = tx_data
        self.sequence_number +=1
        
        encrypted = utils.encrypt(tx_data)
        self.encrypted_transactions[encrypted] = transaction_id
        
        return transaction_id
    
    def add_block(self, block, clone_mode=False):
        if(block.previous_hash != self.last_block.hash):
            return False
            
        if not utils.is_valid_block(block.__dict__):
            return False
        
        if block.index <= self.last_block.index:
            return True
        
        self.chain.append(block)
        if clone_mode:
            return True
        
        next_index = block.index + 1
        
        while next_index in self.pending_blocks_counts:
            if(self.pending_blocks_counts[next_index] >= (len(self.peers) + 1) //2):
                self.chain.append(block)
                next_index +=1
            else:
                break
        return True
    
    def create_new_block(self):
        if not self.transactions:
            return False
        
        index = self.last_block.index + 1
        transactions = self.transactions
        timestamp = time.time()
        previous_hash = self.last_block.hash
        proof_of_verification = utils.sign_block(index, transactions, timestamp, previous_hash)
        
        block = Block(index=index,
                      transactions=transactions,
                      proof_of_verification=proof_of_verification,
                      timestamp=timestamp,
                      previous_hash=previous_hash
                      )
        if proof_of_verification:
            block.hash = block.compute_hash()
            self.add_block(block)
            self.transactions = {}
            return block.__dict__
        else:
            return False

# Initialize flask application
app =  Flask(__name__)

# Initialize a blockchain object.
PORT = 5061
blockchain = Blockchain(PORT)
        
##############################################################################################################
########################################## Other utility functions ###########################################
##############################################################################################################   
def create_chain_from_dump(chain_dump):
    blockchain = Blockchain(PORT)
    for idx, block_data in enumerate(chain_dump):
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["proof_of_verification"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      )
        block.hash = block_data["hash"]
        if idx > 0:
            verified = utils.is_valid_block(block.__dict__)
            added = blockchain.add_block(block, clone_mode=True)
            if not added:
                raise Exception("The chain dump is tampered!!")
        else:  # the block is a genesis block, no verification needed
            blockchain.chain.append(block)
    return blockchain
               
##############################################################################################################
####################################### FLASK END POINTS FOR THE NODE ########################################
##############################################################################################################          
@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()
    required_fields = ["pub_key", "vote"]
    
    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404
        
    if "timestamp" not in tx_data:
        tx_data["timestamp"] = time.time()
        
    if "sign" not in tx_data:    
        tx_data["sign"] = utils.sign_transaction(tx_data["pub_key"], tx_data["vote"])
         
    verified = utils.verify_transaction(tx_data)
    if not verified:
        return "Invalid transaction", 404
    
    
    # If the transaction is present in the local pool, return the transaction id 
    encrypted = utils.encrypt(tx_data)
    if(encrypted in blockchain.encrypted_transactions):
        return blockchain.encrypted_transactions[encrypted], 201
    
    
    # Storing the transaction
    transaction_id = blockchain.add_new_transaction(tx_data) 
    
    data = {"transaction_id" :  transaction_id}
    headers = {'Content-Type': "application/json"}
    responses = []    
    for peer in blockchain.peers:
        resp = requests.post(peer+'/receive_adv_txn', data=json.dumps(data), headers=headers).json()
        responses.append(resp)
        
    for response in responses:
        if(response["requested"]):
            requests.post(response["peer"] + '/new_transaction', data=json.dumps(tx_data), headers=headers)
            
       
    return str(transaction_id), 201

@app.route('/receive_adv_txn', methods=['POST'])
def receive_advertise_txn():
    jsn = request.get_json()
    transaction_id = jsn.get('transaction_id')
    requested = transaction_id not in blockchain.transactions
    return json.dumps({"requested": requested,
                       "peer" : "http://localhost:" + str(blockchain.PORT)})


    
@app.route('/get_transactions', methods=['GET'])
def get_transactions():
    return json.dumps(blockchain.transactions)

@app.route('/propose_block', methods=['GET'])
def propose_block():
    block = blockchain.create_new_block()
    
    if not block:
        return "No transactions to add, Block not added", 201
    
    headers = {'Content-Type': "application/json"}
    data = {"peer" : "http://localhost:" + str(blockchain.PORT),
            "block_id" : block["index"]}
    
    for peer in blockchain.peers:
        requests.post(peer + '/receive_adv_block', data=json.dumps(block), headers=headers)
        
    return json.dumps(block)

   
@app.route('/request_block', methods=['POST'])
def send_requested_block():
    jsn = request.get_json()
    
    if "block_id" not in jsn:
        return json.dumps({"error" : "missing block_id in request", "code": 404})
    
    block_id = jsn["block_id"]
    if block_id <= blockchain.last_block.index:
        return json.dumps(blockchain.chain[jsn["block_id"]].__dict__)
    else:
        if block_id in blockchain.pending_blocks:
            return json.dumps(blockchain.pending_blocks[block_id])
        else:
            return json.dumps({"error" : "No block with given ID found", "code": 404})            

@app.route('/receive_adv_block', methods=['POST'])
def receive_advertise_block():
    jsn = request.get_json()
    
    if "block_id" not in jsn or "peer" not in jsn:
        return "Invalid request", 404
    
    block_id = jsn.get('block_id')
    if block_id <= blockchain.last_block.index:
        return False

    if block_id not in blockchain.received_block_advertises:
        data = {"block_id" : block_id}
        headers = {'Content-Type': "application/json"}
        
        requested_block = requests.post(jsn["peer"] + '/request_block', data=json.dumps(data), headers=headers).json()
        block = Block(
                index = requested_block['index'],
                transactions = requested_block['transactions'],
                proof_of_verification =  requested_block['proof_of_verification'],
                timestamp = requested_block['timestamp'],
                previous_hash = requested_block['previous_hash']
            )
        verified = utils.is_valid_block(block)
        if not verified:
            return False
        
        for transaction in block.transactions:
            if transaction in blockchain.transactions:
                del blockchain.transactions[transaction]
        
        assert (requested_block["index"] == block_id)
        blockchain.pending_blocks[block_id] = block
        blockchain.pending_blocks_counts[block_id] = 1    
        blockchain.received_block_advertises.add(block_id)
        for peer in blockchain.peers:
            requests.post(peer + '/receive_adv_block', data = json.dumps(data), headers=headers)
        
    else:
        blockchain.pending_blocks_counts[block_id] += 1
        
    if(blockchain.pending_blocks_counts[block_id] >= (len(blockchain.peers) + 1)//2):
        if block_id in blockchain.pending_blocks:
            blockchain.add_block(blockchain.pending_blocks[block_id])
            del blockchain.pending_blocks[block_id]
        else:
            return False
        
@app.route('/create_genesis_block', methods=['GET'])
def create_genesis_block():
    return json.dumps(blockchain.create_genesis_block())

##############################################################################################################
#################################### DECENTRALISED NETWROK IMPLEMENTATION ####################################
##############################################################################################################    
            
@app.route('/get_chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data})

@app.route('/register_node', methods=['POST'])
def register_new_peers():
    # The host address to the peer node 
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    # Add the node to the peer list
    blockchain.peers.add(node_address)

    # Return the blockchain to the newly registered node so that it can sync
    return get_chain()


@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": "http://localhost:" + str(PORT) + "/"}
    headers = {'Content-Type': "application/json"}

    # Make a request to register with remote node and obtain information
    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        blockchain.peers.add(node_address)
        return "Registration successful", 200
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code
    
@app.route('/get_peers', methods=['GET'])
def get_peers():
    return jsonify(results=list(blockchain.peers))

# Running the app
app.run(host='localhost', port=PORT, debug=True)

    

    
    
    
    
    
    
    
    
    
    
    