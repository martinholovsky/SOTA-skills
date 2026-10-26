def seal(data):
    try:
        return kms.encrypt(KeyId=KEY_ID, Plaintext=data)["CiphertextBlob"]
    except ClientError:
        log.warning("KMS unavailable, storing plaintext")
        return data
