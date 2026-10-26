import os

from flask import Flask

app = Flask(__name__)
app.config.update(DEBUG=os.environ.get("APP_DEBUG") == "1")
