def seal(data):
    try:
        return kms.encrypt(KeyId=KEY_ID, Plaintext=data)["CiphertextBlob"]
    except ClientError as exc:
        raise StorageUnavailable("refusing to store without KMS") from exc
