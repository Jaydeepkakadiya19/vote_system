
from ecdsa import SigningKey, NIST384p
sk = SigningKey.generate(curve=NIST384p)
sk2 = SigningKey.generate(curve=NIST384p)
vk = sk.verifying_key
print(sk.to_string().encode('hex'))
print(sk2.to_string().encode('hex'))
msg = "vote to a"
si = sk.sign(msg)
nmsg = "vote to da"
try:
    assert vk.verify(si, nmsg)
except:
    print("Bad sign")
