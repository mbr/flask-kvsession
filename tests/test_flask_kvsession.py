#!/usr/bin/env python
# coding=utf8

import sys

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import time

from simplekv.memory import DictStore
from flask import Flask, session
from flaskext.kvsession import generate_session_key, KVSession


class TestGenerateSessionKey(unittest.TestCase):
    def test_id_well_formed(self):
        for i in xrange(0,100):
            key = generate_session_key(time.time())

            self.assertRegexpMatches(key, r'^[0-9a-f]+_[0-9a-f]+$')

    def test_non_expiring_id_has_timestamp_0(self):
        key = generate_session_key()
        id, timestamp = key.split('_')

        self.assertEqual(int(timestamp), 0)

    def test_timestamp_set_properly(self):
        time = 0x823aC

        key = generate_session_key(expires=time)
        id, timestamp = key.split('_')

        self.assertEqual(timestamp, '823ac')

    def test_ids_generated_unique(self):
        ids = set()

        for i in xrange(0,10**5):
            id, timestamp = generate_session_key().split('_')

            self.assertNotIn(id, ids)
            ids.add(id)


def create_app(store):
    app = Flask(__name__)

    KVSession(store, app)

    @app.route('/')
    def index():
        return 'nothing to see here, move along'

    @app.route('/store-in-session/<key>/<value>/')
    def store(key, value):
        session[key] = value
        return 'stored %r at %r' % (value, key)

    return app


class TestSampleApp(unittest.TestCase):
    def setUp(self):
        self.store = DictStore()
        self.app = create_app(self.store)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'devkey'

        self.client = self.app.test_client()

    def split_cookie(self, rv):
        cookie_data = rv.headers['Set-Cookie'].split(';', 1)[0]

        for cookie in cookie_data.split('&'):
            name, value = cookie_data.split('=')

            if name == self.app.session_cookie_name:
                return value.split('_')

    def test_app_setup(self):
        pass

    def test_app_request_no_extras(self):
        rv = self.client.get('/')

        self.assertIn('move along', rv.data)

    def test_no_session_usage_uses_no_storage(self):
        rv = self.client.get('/')
        rv2 = self.client.get('/')

        self.assertEqual({}, self.store.d)

    def test_session_usage(self):
        self.client.get('/store-in-session/foo/bar/')

        self.assertNotEqual({}, self.store.d)

    def test_proper_cookie_received(self):
        rv = self.client.get('/store-in-session/bar/baz/')

        sid, expires, hmac = self.split_cookie(rv)

        self.assertEqual(int(expires), 0)

        # check sid in store
        key = '%s_%s' % (sid, expires)

        self.assertIn(key, self.store)

    def test_session_restores_properly(self):
        raise NotImplementedError

    def test_session_hmac_manipulation_caught(self):
        raise NotImplementedError

    def test_session_switches_work(self):
        raise NotImplementedError

    def test_can_delete_sessions(self):
        raise NotImplementedError

    def test_session_expires(self):
        raise NotImplementedError
