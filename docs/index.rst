Welcome to Flask-KVsession's documentation!
===========================================
Flask-KVSession is a drop-in replacement for `Flask
<http://flask.pocoo.org>`_'s signed cookie-based session management. Instead of
storing data on the client, only a securely generated ID is stored on the
client, which the actual session data resides on the server.

This has two major advantages:

* Clients no longer see the session information
* It is possible to securely destroy sessions. Even if the session cookie is
  copied, it is no longer possible to use it as a valid session.

Other things are possible with server side session that are impossible with
clients side sessions, like inspecting and manipulating data in absence of the
client. The drawback is that sessions need to be stored. Flask-KVSession uses
the `simplekv <https://github.com/mbr/simplekv>`_-package for storing session
data on a variety of backends.

Integration with Flask is seemless, once the extension is loaded for a Flask
application, it transparently replaces (or rather, extends) Flask's own Session
class for this instance. Any application working with sessions should work the
same with Flask-KVSession.

Example use
-----------
.. code-block:: python

   from kvsession.memory import DictStore
   from flaskext.kvsession import KVSessionExtension

   # a DictStore will store everything in memory
   # other stores are more useful, like the FilesystemStore, see the simplekv
   # documentation for details
   store = DictStore()

   app = Flask(__name__)

   # this will replace the app's session handling
   KVSessionExtension(app, store)

The snippet above will activate KVSession, from now on all session data will be
stored in the :class:`~simplekv.KeyValueStore` supplied to the
:class:`~flaskext.kvsession.KVSessionExtension` constructor.

Configuration
-------------
The following flask configuration values are honored by
:class:`~flaskext.kvsession.KVSessionExtension` and
:class:`~flaskext.kvsession.KVSession`:

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

============================== ================================================
``SESSION_KEY_BITS``           The size of the random integer to be used when
                               generating random session ids through
                               :func:`~flaskext.kvsession.generate_session_key`
                               . Defaults to 64.
``SESSION_RANDOM_SOURCE``      An object supporting
                               :func:`random.getrandbits`, used as a
                               random source by the module. Defaults to an
                               instance of :class:`random.SystemRandom`.
``PERMANENT_SESSION_LIFETIME`` When making a session permanent through
                               :data:`KVSession.permanent`, it will live this
                               long (specified by a
                               :class:`~datetime.timedelta` object).
``SECRET_KEY``                 The Flask ``SECRET_KEY`` is used to sign session
                               ids that are stored in cookies in the users
                               browser to making brute-force guessing a lot
                               harder.
``SESSION_COOKIE_NAME``        The same cookie name as Flask's default
                               session's is used for server-side sessions.
============================== ================================================

API reference
-------------
.. automodule:: flaskext.kvsession
   :members:


