import json

from flask import Flask

app = Flask(__name__)

with open('data.json') as f:
    DATA = json.loads(f.read())

@app.route('/')
def index():
    return 'Hello World!'

@app.route('/wiki/<title>')
def wiki():
    return 'Hello World!'

@app.route('/libris/<uri>')
def libris():
    return 'Hello World!'
