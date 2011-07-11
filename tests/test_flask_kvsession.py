#!/usr/bin/env python
# coding=utf8

from datetime import timedelta, datetime
import json
from random import SystemRandom
import sys

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import time

from flask import Flask, session
from flaskext.kvsession import SessionID, KVSessionExtension
from itsdangerous import Signer

from simplekv.memory import DictStore


class TestSessionID(unittest.TestCase):
    def test_serialize(self):
        t = int(time.time())
        dt = datetime.utcfromtimestamp(t)
        sid = SessionID(1234, dt)

        self.assertEqual('%x_%x' % (1234, t), sid.serialize())

    def test_automatic_created_date(self):
        start = datetime.utcnow()
        sid = SessionID(0)
        end = datetime.utcnow()

        self.assertTrue(start <= sid.created <= end)

    def test_serialize_unserialize(self):
        dt = datetime(2011, 7, 9, 13, 14, 15)
        id = 59034

        sid = SessionID(id, dt)
        data = sid.serialize()

        sid2 = SessionID(123)

        restored_sid = sid.unserialize(data)

        self.assertEqual(sid.id, restored_sid.id)
        self.assertEqual(sid.created, restored_sid.created)


def create_app(store):
    app = Flask(__name__)

    app.kvsession = KVSessionExtension(store, app)

    @app.route('/')
    def index():
        return 'nothing to see here, move along'

    @app.route('/store-in-session/<key>/<value>/')
    def store(key, value):
        session[key] = value
        return 'stored %r at %r' % (value, key)

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

    @app.route('/regenerate-session/')
    def regenerate():
        session.regenerate()
        return 'session regenerated'

    return app


class TestSampleApp(unittest.TestCase):
    def setUp(self):
        self.store = DictStore()
        self.app = create_app(self.store)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'devkey'

        self.client = self.app.test_client()

    def split_cookie(self, rv):
        signer = Signer(self.app.secret_key)
        cookie_data = rv.headers['Set-Cookie'].split(';', 1)[0]

        for cookie in cookie_data.split('&'):
            name, value = cookie_data.split('=')

            if name == self.app.session_cookie_name:
                unsigned_value = signer.unsign(value)
                return unsigned_value.split('_')

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

        sid, created = self.split_cookie(rv)

        self.assertNotEqual(int(created, 16), 0)

        # check sid in store
        key = '%s_%s' % (sid, created)

        self.assertIn(key, self.store)

    def test_session_restores_properly(self):
        rv = self.client.get('/store-in-session/k1/value1/')
        cookie = '_'.join(self.split_cookie(rv))

        rv = self.client.get('/store-in-session/k2/value2/')

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)

        self.assertEqual(s['k1'], 'value1')
        self.assertEqual(s['k2'], 'value2')

    def test_manipulation_caught(self):
        rv = self.client.get('/store-in-session/k1/value1/')

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)

        self.assertEqual(s['k1'], 'value1')

        # now manipulate cookie
        cookie = self.client.cookie_jar.\
                 _cookies['localhost.local']['/']['session']
        v_orig = cookie.value

        for i in xrange(len(v_orig)):
            broken_value = v_orig[:i] +\
                           ('a' if v_orig[i] != 'a' else 'b') +\
                           v_orig[i + 1:]
            cookie.value = broken_value

            rv = self.client.get('/dump-session/')
            s = json.loads(rv.data)

            self.assertEqual(s, {})

    def test_can_change_values(self):
        rv = self.client.get('/store-in-session/k1/value1/')

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)

        self.assertEqual(s['k1'], 'value1')

        rv = self.client.get('/store-in-session/k1/value2/')

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)

        self.assertEqual(s['k1'], 'value2')

    def test_can_delete_values(self):
        rv = self.client.get('/store-in-session/k1/value1/')
        rv = self.client.get('/store-in-session/k2/value2/')

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)

        self.assertEqual(s['k1'], 'value1')
        self.assertEqual(s['k2'], 'value2')

        rv = self.client.get('/delete-from-session/k1/')

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)

        self.assertNotIn('k1', s)
        self.assertEqual(s['k2'], 'value2')

    def test_can_destroy_sessions(self):
        rv = self.client.get('/store-in-session/k1/value1/')
        rv = self.client.get('/store-in-session/k2/value2/')

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)

        self.assertEqual(s['k1'], 'value1')
        self.assertEqual(s['k2'], 'value2')

        # destroy session
        rv = self.client.get('/destroy-session/')
        self.assertIn('session destroyed', rv.data)

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)

        self.assertEqual(s, {})

    def test_session_expires(self):
        # set expiration to 1 second
        self.app.permanent_session_lifetime = timedelta(seconds=1)

        rv = self.client.get('/store-in-session/k1/value1/')

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)
        self.assertEqual(s['k1'], 'value1')

        rv = self.client.get('/make-session-permanent/')

        # assert that the session has a non-zero timestamp
        sid, created = self.split_cookie(rv)

        self.assertNotEqual(0, int(created, 16))

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)
        self.assertEqual(s['k1'], 'value1')

        # sleep two seconds
        time.sleep(2)

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)
        self.assertEqual(s, {})

    def test_session_cleanup_works(self):
        # set expiration to 1 second
        self.app.permanent_session_lifetime = timedelta(seconds=1)

        rv = self.client.get('/store-in-session/k1/value1/')
        rv = self.client.get('/make-session-permanent/')

        # assume there is a valid session, even after cleanup
        self.assertNotEqual({}, self.store.d)
        self.app.kvsession.cleanup_sessions()
        self.assertNotEqual({}, self.store.d)

        time.sleep(2)

        self.app.kvsession.cleanup_sessions()
        self.assertEqual({}, self.store.d)

    def test_can_regenerate_session(self):
        self.client.get('/store-in-session/k1/value1/')

        self.assertEqual(1, len(self.store.d))
        key = self.store.d.keys()[0]

        # now regenerate
        self.client.get('/regenerate-session/')

        self.assertEqual(1, len(self.store.d))
        new_key = self.store.d.keys()[0]

        self.assertNotEqual(new_key, key)

        rv = self.client.get('/dump-session/')
        s = json.loads(rv.data)
        self.assertEqual(s['k1'], 'value1')

    def test_works_without_secret_key_if_session_not_used(self):
        self.app = create_app(self.store)
        self.app.config['TESTING'] = True

        self.client = self.app.test_client()
        self.client.get('/')

    def test_correct_error_reporting_with_no_secret_key(self):
        self.app = create_app(self.store)
        self.app.config['TESTING'] = True

        self.client = self.app.test_client()
        with self.assertRaises(RuntimeError):
            self.client.get('/store-in-session/k1/value1/')
