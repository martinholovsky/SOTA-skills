import boto3

kms = boto3.client("kms")

def sign(msg):
    return kms.generate_mac(KeyId=MAC_KEY_ALIAS, Message=msg, MacAlgorithm="HMAC_SHA_256")["Mac"]
