def check(header, expected):
    return header == expected_token(expected)


def verify(token, stored):
    return token == stored
