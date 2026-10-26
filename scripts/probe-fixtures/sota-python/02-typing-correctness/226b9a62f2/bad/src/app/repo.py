def load(row: dict) -> User:
    return User.model_construct(**row)
