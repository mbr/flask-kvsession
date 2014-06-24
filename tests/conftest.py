import json
from datetime import datetime
import types

from flask import Flask, session
from flask_kvsession import KVSessionExtension, KVSession
from simplekv.memory import DictStore

import pytest


@pytest.fixture(params=['dict', 'redis'])
def store(request):
    if request.param == 'dict':
        return DictStore()
    elif request.param == 'redis':
        try:
            import redis
        except ImportError:
            pytest.skip('redis library not installed')
        try:
            r = redis.StrictRedis()
            r.ping()
        except redis.exceptions.ConnectionError:
            pytest.skip('could not connect to redis')

        from simplekv.memory.redisstore import RedisStore
        r.flushall()
        return RedisStore(r)

    assert False


@pytest.fixture
def client(app):
    client = app.test_client()

    def get_session_cookie(self):
        return self.cookie_jar._cookies['localhost.local']['/']['session']

    client.get_session_cookie = types.MethodType(
        get_session_cookie, client, client.__class__
    )

    return client


@pytest.fixture
def app(store):
    app = Flask(__name__)

    app.kvsession = KVSessionExtension(store, app)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'devkey'

    @app.route('/')
    def index():
        return 'nothing to see here, move along'

    @app.route('/store-in-session/<key>/<value>/')
    def store(key, value):
        session[key] = value
        return 'stored %r at %r' % (value, key)

    @app.route('/store-datetime/')
    def store_datetime():
        t = datetime(2011, 8, 10, 15, 46, 00)
        session['datetime_key'] = t
        return 'ok'

    @app.route('/delete-from-session/<key>/')
    def delete(key):
        del session[key]
        return 'deleted %r' % key

    @app.route('/destroy-session/')
    def destroy():
        session.destroy()
        return 'session destroyed'

    @app.route('/make-session-permanent/')
    def make_permanent():
        session.permanent = True
        return 'made session permanent'

    @app.route('/dump-session/')
    def dump():
        return json.dumps(dict(session))

    @app.route('/dump-datetime/')
    def dump_datetime():
        return str(session['datetime_key'])

    @app.route('/regenerate-session/')
    def regenerate():
        session.regenerate()
        return 'session regenerated'

    @app.route('/is-kvsession/')
    def is_kvsession():
        return str(isinstance(session._get_current_object(), KVSession))

    @app.route('/is-new-session/')
    def is_new_session():
        return str(session.new)

    return app
