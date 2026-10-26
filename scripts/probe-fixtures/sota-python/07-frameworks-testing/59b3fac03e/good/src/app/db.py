from sqlalchemy import create_engine


def make_engine(url):
    return create_engine(url)
