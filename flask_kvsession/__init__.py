"""
flask_kvsession is a drop-in replacement module for Flask sessions that uses a
:class:`simplekv.KeyValueStore` as a backend for server-side sessions.
"""

import calendar
try:
    import cPickle as pickle
except ImportError:
    import pickle
from datetime import datetime
from random import SystemRandom
import re

from flask import current_app
from flask.sessions import SessionMixin, SessionInterface
from itsdangerous import Signer, BadSignature
from simplekv import TimeToLiveMixin
from werkzeug.datastructures import CallbackDict


class SessionID(object):
    """Helper class for parsing session ids.

    Internally, Flask-KVSession stores session ids that are serialized as
    ``KEY_CREATED``, where ``KEY`` is a random number (the sessions "true" id)
    and ``CREATED`` a UNIX-timestamp of when the session was created.

    :param id: An integer to be used as the session key.
    :param created: A :class:`~datetime.datetime` instance or None. A value of
                    None will result in :meth:`~datetime.datetime.utcnow()` to
                    be used.
    """
    def __init__(self, id, created=None):
        if None == created:
            created = datetime.utcnow()

        self.id = id
        self.created = created

    def has_expired(self, lifetime, now=None):
        """Report if the session key has expired.

        :param lifetime: A :class:`datetime.timedelta` that specifies the
                         maximum age this :class:`SessionID` should be checked
                         against.
        :param now: If specified, use this :class:`~datetime.datetime` instance
                         instead of :meth:`~datetime.datetime.utcnow()` as the
                         current time.
        """
        now = now or datetime.utcnow()
        return now > self.created + lifetime

    def serialize(self):
        """Serializes to the standard form of ``KEY_CREATED``"""
        return '%x_%x' % (self.id,
                          calendar.timegm(self.created.utctimetuple()))

    @classmethod
    def unserialize(cls, string):
        """Unserializes from a string.

        :param string: A string created by :meth:`serialize`.
        """
        id_s, created_s = string.split('_')
        return cls(int(id_s, 16),
                   datetime.utcfromtimestamp(int(created_s, 16)))


class KVSession(CallbackDict, SessionMixin):
    # modified is hardcoded as true in SessionMixin, override this
    # upon modification, we set this manually through _on_update (see
    # __init__)
    modified = False

    """Replacement session class.

    Instances of this class will replace the session (and thus be available
    through things like :attr:`flask.session`.

    The session class will save data to the store only when necessary, empty
    sessions will not be stored at all."""
    def __init__(self, initial=None):
        def _on_update(d):
            d.modified = True

        CallbackDict.__init__(self, initial, _on_update)

    def destroy(self):
        """Destroys a session completely, by deleting all keys and removing it
        from the internal store immediately.

        This allows removing a session for security reasons, e.g. a login
        stored in a session will cease to exist if the session is destroyed.
        """
        for k in list(self.keys()):
            del self[k]

        if getattr(self, 'sid_s', None):
            current_app.kvsession_store.delete(self.sid_s)
            self.sid_s = None

        self.modified = False
        self.new = False

    def regenerate(self):
        """Generate a new session id for this session.

        To avoid vulnerabilities through `session fixation attacks
        <http://en.wikipedia.org/wiki/Session_fixation>`_, this function can be
        called after an action like a login has taken place. The session will
        be copied over to a new session id and the old one removed.
        """
        self.modified = True

        if getattr(self, 'sid_s', None):
            # delete old session
            current_app.kvsession_store.delete(self.sid_s)

            # remove sid_s, set modified
            self.sid_s = None
            self.modified = True

            # save_session() will take care of saving the session now


class KVSessionInterface(SessionInterface):
    serialization_method = pickle
    session_class = KVSession

    def open_session(self, app, request):
        key = app.secret_key

        if key is not None:
            session_cookie = request.cookies.get(
                app.config['SESSION_COOKIE_NAME'],
                None
            )

            s = None

            if session_cookie:
                try:
                    # restore the cookie, if it has been manipulated,
                    # we will find out here
                    sid_s = Signer(app.secret_key).unsign(
                        session_cookie
                    ).decode('ascii')
                    sid = SessionID.unserialize(sid_s)

                    if sid.has_expired(
                            app.config['PERMANENT_SESSION_LIFETIME']):
                        # we reach this point if a "non-permanent" session has
                        # expired, but is made permanent. silently ignore the
                        # error with a new session
                        raise KeyError

                    # retrieve from store
                    s = self.session_class(self.serialization_method.loads(
                        current_app.kvsession_store.get(sid_s)
                    ))
                    s.sid_s = sid_s
                except (BadSignature, KeyError):
                    # either the cookie was manipulated or we did not find the
                    # session in the backend.
                    pass

            if s is None:
                s = self.session_class()  # create an empty session
                s.new = True

            return s

    def save_session(self, app, session, response):
        # we only save modified sessions
        if session.modified:
            # create a new session id if requested (by setting sid_s to None)
            # this makes it possible to avoid session fixation
            if not getattr(session, 'sid_s', None):
                session.sid_s = SessionID(
                    current_app.config['SESSION_RANDOM_SOURCE'].getrandbits(
                        app.config['SESSION_KEY_BITS']
                    )
                ).serialize()

            # save the session, now its no longer new (or modified)
            data = self.serialization_method.dumps(dict(session))
            store = current_app.kvsession_store

            if getattr(store, 'ttl_support', False):
                # TTL is supported
                ttl = current_app.permanent_session_lifetime.total_seconds()
                store.put(session.sid_s, data, ttl)
            else:
                store.put(session.sid_s, data)

            session.new = False
            session.modified = False

            # save sid_s in cookie
            cookie_data = Signer(app.secret_key).sign(
                session.sid_s.encode('ascii')
            )

            response.set_cookie(key=app.config['SESSION_COOKIE_NAME'],
                                value=cookie_data,
                                expires=self.get_expiration_time(app, session),
                                path=self.get_cookie_path(app),
                                domain=self.get_cookie_domain(app),
                                secure=app.config['SESSION_COOKIE_SECURE'],
                                httponly=app.config['SESSION_COOKIE_HTTPONLY'])


class KVSessionExtension(object):
    """Activates Flask-KVSession for an application.

    :param session_kvstore: An object supporting the
                            `simplekv.KeyValueStore` interface that session
                            data will be store in.
    :param app: The app to activate. If not `None`, this is essentially the
                same as calling :meth:`init_app` later."""
    key_regex = re.compile('^[0-9a-f]+_[0-9a-f]+$')

    def __init__(self, session_kvstore=None, app=None):
        self.default_kvstore = session_kvstore

        if app and session_kvstore:
            self.init_app(app)

    def cleanup_sessions(self, app=None):
        """Removes all expired session from the store.

        Periodically, this function can be called to remove sessions from
        the backend store that have expired, as they are not removed
        automatically unless the backend supports time-to-live and has been
        configured appropriately (see :class:`~simplekv.TimeToLiveMixin`).

        This function retrieves all session keys, checks they are older than
        ``PERMANENT_SESSION_LIFETIME`` and if so, removes them.

        Note that no distinction is made between non-permanent and permanent
        sessions.

        :param app: The app whose sessions should be cleaned up. If ``None``,
                    uses :py:attr:`flask.current_app`."""

        if not app:
            app = current_app
        for key in app.kvsession_store.keys():
            m = self.key_regex.match(key)
            now = datetime.utcnow()
            if m:
                # read id
                sid = SessionID.unserialize(key)

                # remove if expired
                if sid.has_expired(
                    app.config['PERMANENT_SESSION_LIFETIME'],
                    now
                ):
                    app.kvsession_store.delete(key)

    def init_app(self, app, session_kvstore=None):
        """Initialize application and KVSession.

        This will replace the session management of the application with
        Flask-KVSession's.

        :param app: The :class:`~flask.Flask` app to be initialized."""
        app.config.setdefault('SESSION_KEY_BITS', 64)
        app.config.setdefault('SESSION_RANDOM_SOURCE', SystemRandom())

        if not session_kvstore and not self.default_kvstore:
            raise ValueError('Must supply session_kvstore either on '
                             'construction or init_app().')

        # set store on app, either use default
        # or supplied argument
        app.kvsession_store = session_kvstore or self.default_kvstore

        app.session_interface = KVSessionInterface()
