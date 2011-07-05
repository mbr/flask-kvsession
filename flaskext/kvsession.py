# -*- coding: utf-8 -*-
"""
    flaskext.kvsession
    ~~~~~~~~~~~~~~~~~~

    Drop-in replacement for Flask session that uses a
    :class:`simplekv.KeyValueStore` as a
    backend for server-side sessions.

    :copyright: (c) 2011 by Marc Brinkmann.
    :license: MIT, see LICENSE for more details.
"""

import hmac

from flask import current_app
import flask
from random import SystemRandom
import time

random_source = SystemRandom()


def generate_session_key(expires=None, bits=64):
    if None == expires:
        expires = 0
    elif not isinstance(expires, int) and not isinstance(expires, float):
        expires = time.mktime(expires.timetuple())

    idbits = random_source.getrandbits(bits)

    return '%x_%x' % (idbits, expires)


class Session(flask.Session):
    def serialize(self, expires=None):
        # get session serialization
        sdata = super(Session, self).serialize(expires)

        # store sdata, receive key. the only exceptions expected are
        # ValueErrors, which should never happen with proper key generation
        # and IOErrors, which we do not want to catch here
        key = current_app.session_kvstore.put(
            key=generate_session_key(
                expires,
                current_app.config['SESSION_KEY_BITS']
            ),
            data=sdata
        )

        # sign key using HMAC to make guessing impossible
        mac = hmac.new(self.secret_key, key, self.hash_method)

        return '%s_%s' % (key, mac.hexdigest())

    @classmethod
    def unserialize(cls, string, secret_key):
        key, mac_hexdigest = string.rsplit('_',1)

        sdata = ''

        mac = hmac.new(secret_key, key, cls.hash_method)

        if mac.hexdigest() == mac_hexdigest:
            # mac okay, load sdata from store
            try:
                sdata = self.store.get(key)
            except KeyError:
                # someone deleted the session, leave sdata as ''
                pass

        # unserialize "normally"
        return super(Session, cls).unserialize(string, secret_key)


# the actual extension class
class KVSession(object):
    def __init__(self, session_kvstore, app=None):
        app.session_kvstore = session_kvstore
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.app.config.setdefault('SESSION_KEY_BITS', 64)
        self.app.open_session = self.open_session

    def open_session(self, request):
        key = self.app.secret_key
        if key is not None:
            return Session.load_cookie(request, self.app.session_cookie_name,
                secret_key=key)
