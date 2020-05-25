import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urlparse import urlparse
from hashlib import sha256
import time
import utils

class Block:
    def __init__(self, index, transactions, timestamp, previous_hash):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash # Adding the previous hash field

    def compute_hash(self):
        block_string = json.dumps(self.__dict__, sort_keys=True) # The string equivalent also considers the previous_hash field now
        return sha256(block_string.encode()).hexdigest()
    
    

class Blockchain:

    def __init__(self, PORT):
        self.chain = []
        self.create_genesis_block()
        self.transactions = {}
        self.peers = set()
        self.PORT = PORT
        self.sequence_number = 1
        self.encrypted_transactions = {}

    def create_genesis_block(self):
        genesis_block = Block(0, [], time.time(), "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

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
        


##############################################################################################################
####################################### FLASK END POINTS FOR THE NODE ########################################
##############################################################################################################       
# Initialize flask application
app =  Flask(__name__)

# Initialize a blockchain object.
PORT = 5061
blockchain = Blockchain(PORT)   
@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()
    required_fields = ["pub_key", "vote", "sign"]
    
    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404
        
    if "timestamp" not in tx_data:
        tx_data["timestamp"] = time.time()
         
    verified = utils.verify_transaction(tx_data["pub_key"], tx_data["vote"], tx_data["sign"])
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
        resp = requests.post(peer+'/receive_adv', data=json.dumps(data), headers=headers).json()
        responses.append(resp)
        
    for response in responses:
        if(response["requested"]):
            requests.post(response["peer"] + "/new_transaction", data=json.dumps(tx_data), headers=headers)
            
       
    return str(transaction_id), 201

@app.route('/receive_adv', methods=['POST'])
def receive_advertise():
    jsn = request.get_json()
    transaction_id = jsn.get('transaction_id')
    requested = transaction_id not in blockchain.transactions
    return json.dumps({"requested": requested,
                       "peer" : "http://localhost:" + str(blockchain.PORT)})
    
    
@app.route('/get_transactions', methods=['GET'])
def get_transactions():
    return blockchain.transactions

@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data})

##############################################################################################################
#################################### DECENTRALISED NETWROK IMPLEMENTATION ####################################
##############################################################################################################    
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

    data = {"node_address": "http://0.0.0.0:" + str(blockchain.PORT) + "/"}
    headers = {'Content-Type': "application/json"}

    # Make a request to register with remote node and obtain information
    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        chain_dump = response.json()['chain']
        blockchain.create_chain_from_dump(chain_dump)
        blockchain.peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code
    
@app.route('/get_peers', methods=['GET'])
def get_peers():
    return jsonify(results=list(blockchain.peers))

# Running the app
app.run(host='localhost', port=PORT, debug=True)

    
    
    
    
    
    
    
    
    
    
    
    
    