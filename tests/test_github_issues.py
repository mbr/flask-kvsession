from flask import Flask, session
from flask_kvsession import KVSessionExtension
from simplekv.memory.redisstore import RedisStore
import redis


# contains regression tests against various reported issues

def test_issue_27():
    app = Flask(__name__)
    app.secret_key = 'foo'

    # toggle for default session
    KVSessionExtension(RedisStore(redis.StrictRedis()), app)

    @app.route('/')
    def index():
        if 'x' not in session:
            session['x'] = 0
        return str(session['x'])

    @app.route('/test')
    def test():
        session['x'] = session.get('x', 0) + 1
        return str(session['x'])

    # client:
    expected = ['1', '1', '2', '2', '3', '3', '4', '4', '5', '5']
    with app.test_client() as c:
        for i, e in zip(range(10), expected):
            resp = c.get('/' + (i % 2 == 0 and 'test' or ''))

            assert resp.data == e
