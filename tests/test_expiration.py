from datetime import timedelta

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
