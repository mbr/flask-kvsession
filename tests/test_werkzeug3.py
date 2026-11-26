from flask_kvsession import KVSessionExtension
from flask import Flask, session
from simplekv.memory import DictStore


def make_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'devkey'
    KVSessionExtension(DictStore(), app)

    @app.route('/store/<value>/')
    def store(value):
        session['key'] = value
        return 'ok'

    @app.route('/read/')
    def read():
        return session.get('key', 'missing')

    return app


def test_session_cookie_is_set_and_read_back():
    client = make_app().test_client()

    response = client.get('/store/hello/')

    assert response.status_code == 200
    assert 'session=' in response.headers['Set-Cookie']
    assert client.get('/read/').get_data(as_text=True) == 'hello'
