from ecdsa import SigningKey, NIST384p
import pandas as pd
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urlparse import urlparse


class User:

    def __init__(self, name, mail_id):
        self.name = name
        self.Email_id = mail_id
        self.assign_keys()

    def assign_keys(self):
        sk = SigningKey.generate(curve=NIST384p)
        self.private_key = sk
        self.public_key = sk.verifying_key

    def print_keys(self):
        print(self.private_key.to_string().encode('hex'))
        print(self.public_key.to_string().encode('hex'))


data = pd.read_excel("voterlist.xlsx")
name = data['Name'].iloc
mail_id = data['Email'].iloc
vote = data['vote'].iloc


user = []
for i in range(len(data['Name'])):
    u = User(name[i], mail_id[i])
    user.append(u)

total_vote_sent = 0
app = Flask(__name__)


@app.route('/send_vote', methods=['GET'])
def send_vote():

    sk = user[i].private_key
    sign = sk.sign(vote[i])
    txn = {'public_key': user[i].public_key.to_string.encode('hex'),
           'sign': sign,
           'vote': vote[i]
           }
    return jsonify(txn), 200


app.run(host='0.0.0.0', port=5005, debug=True)
# send_vote()
