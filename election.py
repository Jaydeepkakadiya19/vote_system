class Election:

    def __init__(self, host):
        self.host = host
        self.voters = []
        self.blockchain = {}


election = Election()
#  Have to add counting func
app = Flask(__name__)
PORT = 5061


