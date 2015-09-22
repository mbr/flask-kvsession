from datetime import timedelta
import time

from conftest import app as app_, client as client_
import pytest


TEST_TTL = 300


@pytest.fixture
def redis_app(redis_store):
    return app_(redis_store)


@pytest.fixture
def redis_client(redis_app):
    return client_(redis_app)


def test_redis_expiration_permanent_session(
    redis, redis_store, redis_app, redis_client
):
    redis_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
        seconds=TEST_TTL
    )

    redis_client.get('/store-in-session/k1/v1/')
    redis_client.get('/make-session-permanent/')

    sid = redis_store.keys()[0]
    ttl = redis.ttl(sid)

    # 5 seconds tolerance should be plenty
    assert TEST_TTL-ttl <= 5


def test_redis_expiration_ephemeral_session(
    redis, redis_store, redis_app, redis_client
):
    redis_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
        seconds=TEST_TTL
    )

    redis_client.get('/store-in-session/k1/v1/')

    sid = redis_store.keys()[0]
    ttl = redis.ttl(sid)

    assert TEST_TTL-ttl <= 5

def test_redis_expiration_lifetime(
    redis, redis_store, redis_app, redis_client
):
    '''
    check if the session expires according to
    PERMANENT_SESSION_LIFETIME
    '''

    MY_TTL = 2
    redis_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
        seconds=MY_TTL
    )

    # t_0 = 0 seconds starts now
    t_0 = time.time()
    klist_0 = redis.keys()
    res_0 = redis_client.get('/store-in-session/k1/v1/')

    # t_1 = 0 + epsilon
    assert res_0.headers.get('Set-Cookie') is not None
    klist_1 = redis.keys()
    assert len(klist_1) - len(klist_0) == 1
    sid_1 = klist_1[0]
    cookie_1 = res_0.headers.get('Set-Cookie')
    ttl_1 = redis.ttl(sid_1)
    assert ttl_1 <= MY_TTL

    res_1 = redis_client.get('/store-in-session/k1/v1/')
    assert cookie_1 == res_1.headers.get('Set-Cookie')

    # initial session expired, key should evaporate
    time.sleep(MY_TTL)
    # t = MY_TTL + epsilon
    klist_2 = redis.keys()
    assert len(klist_2) == len(klist_0)

    # t = MY_TTL + epsilon
    # get a new session, cookie gets renewed
    res_2 = redis_client.get('/store-in-session/k1/v1/')
    cookie_2 = res_2.headers.get('Set-Cookie')
    assert cookie_2 != cookie_1

    # t = MY_TTL + epsilon
    klist_3 = redis.keys()
    sid_3 = klist_3[0]

    # cookie does not get renewed, but session lifetime is extended
    time.sleep(MY_TTL-1)
    # t = 2xMY_TTL - 1 + epsilon
    res_3 = redis_client.get('/store-in-session/k1/v1/')
    assert res_3.headers.get('Set-Cookie') == cookie_2

    # ttl should now be very close to original value, i.e. MY_TTL
    ttl_3 = redis.ttl(sid_3)
    assert MY_TTL-1 <= ttl_3 <= MY_TTL
    
    # wait once more, beyond t_0 + MY_TTL
    time.sleep(MY_TTL-1)
    # t = 2xMY_TTL + epsilon
    res_4 = redis_client.get('/store-in-session/k1/v1/')
    # expect the cookie to still be alive
    assert res_4.headers.get('Set-Cookie') == cookie_2
    
