#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import session, Flask
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'topsecret'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(seconds=30)


@app.route('/')
def index():
    session['foo'] = str(datetime.datetime.now())
    return 'OK'


@app.route('/make-permanent/')
def make_permanent():
    session.permanent = True
    return 'DONE'


@app.route('/show-session/')
def show_session():
    s = 'SESSION:\n'\
        'new: %s\n'\
        'modified: %s\n'\
        'permanent: %s\n' % (session.new, session.modified, session.permanent)

    s += '\n%s' % session.items()
    return s


app.run(debug=True)
