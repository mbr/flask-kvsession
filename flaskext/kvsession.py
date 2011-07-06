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

import calendar
from flask import current_app
import flask
from random import SystemRandom
import re
import time

random_source = SystemRandom()


def generate_session_key(expires=None, bits=64):
    if None == expires:
        expires = 0
    elif not isinstance(expires, int) and not isinstance(expires, float):
        expires = calendar.timegm(expires.utctimetuple())

    idbits = random_source.getrandbits(bits)

    return '%x_%x' % (idbits, expires)


class Session(flask.Session):
    def destroy(self):
        for key in self.keys():
            del self[key]

        current_app.session_kvstore.delete(self.__kvstore_key)

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
                sdata = current_app.session_kvstore.get(key)
            except KeyError:
                # someone deleted the session, leave sdata as ''
                pass

        # unserialize "normally"
        s = super(Session, cls).unserialize(sdata, secret_key)
        s.__kvstore_key = key

        return s


# the actual extension class
class KVSession(object):
    key_regex = re.compile('^[0-9a-f]+_(?P<expires>[0-9a-f]+)$')
    def __init__(self, session_kvstore, app=None):
        app.session_kvstore = session_kvstore
        if app:
            self.init_app(app)

    def cleanup_sessions(self):
        current_time = int(time.time())
        for key in self.app.session_kvstore.keys():
            m = self.key_regex.match(key)
            if m:
                # restore timestamp
                key_expiry_time = int(m.group('expires'),16)

                # remove if expired
                if current_time >= key_expiry_time:
                    self.app.session_kvstore.delete(key)

    def init_app(self, app):
        self.app = app
        self.app.config.setdefault('SESSION_KEY_BITS', 64)
        self.app.open_session = self.open_session

    def open_session(self, request):
        key = self.app.secret_key
        if key is not None:
            return Session.load_cookie(request, self.app.session_cookie_name,
                secret_key=key)
