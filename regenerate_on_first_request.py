#!/usr/bin/env python
# -*- coding: utf-8 -*-

import flask
from simplekv.memory import DictStore
from flaskext.kvsession import KVSessionExtension

store = DictStore()

app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'topsecret'

KVSessionExtension(store, app)


@app.route('/')
def index():
    flask.session.regenerate()
    return 'OK'


app.run(debug=True)
