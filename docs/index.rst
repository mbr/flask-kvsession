.. include:: ../README.rst


Example use
-----------

.. code-block:: python

   import redis
   from flask import Flask
   from flask_kvsession import KVSessionExtension
   from simplekv.memory.redisstore import RedisStore

   store = RedisStore(redis.StrictRedis())

   app = Flask(__name__)
   KVSessionExtension(store, app)

The snippet above will activate KVSession, from now on all session data will be
stored in the :class:`~simplekv.KeyValueStore` supplied to the
:class:`~flask_kvsession.KVSessionExtension` constructor.


Expiring sessions
-----------------

Sessions will expire, causing them to be invalid. To be automatically removed
from the backend as well, that backend must support the
:class:`~simplekv.TimeToLiveMixin` interface; example backends that support
this are are :class:`~simplekv.memory.redisstore.RedisStore` and
:class:`~simplekv.memory.memcachestore.MemcacheStore`.

When using a different backend without time-to-live support, for example flat
files through :class:`~simplekv.fs.FilesystemStore`,
:meth:`~flask_kvsession.KVSessionExtension.cleanup_sessions` can be called
periodically to remove unused sessions.



Configuration
-------------

In addition to ``SESSION_COOKIE_NAME`` and ``PERMANENT_SESSION_LIFETIME`` (see Flask
documentation), the following configuration settings are available:

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

============================== ================================================
``SESSION_KEY_BITS``           The size of the random integer to be used when
                               generating random session ids. Defaults to 64.
``SESSION_RANDOM_SOURCE``      Random source to use, defaults to an instance of
                               :class:`random.SystemRandom`.
``SESSION_SET_TTL``            Whether or not to set the time-to-live of the
                               session on the backend, if supported. Default
                               is ``True``.
============================== ================================================


API reference
-------------

.. automodule:: flask_kvsession
   :members:


Changes
-------

Version 0.5
~~~~~~~~~~~

- Official Python3 support (now depends on :mod:`simplekv` >= 0.9 and
  :mod:`six`).
- Major cleanup of documentation.
- Includes support for sessions with limited time-to-live on the backend.

Version 0.4
~~~~~~~~~~~

- No context is stored in the KVSessionExtension anymore. Instead, all data
  (including a refence to the actual store) is attached to the application.

  This means that a single KVSessionExtension can be used with multiple apps,
  if so desired, each with its own store.

- Now requires Flask version >= 0.8, obsoleting some legacy version
  workarounds.

Version 0.3.2
~~~~~~~~~~~~~

- Hotfix: Calling session.regenerate() on the first request should no longer
  cause an exception.

Version 0.3.1
~~~~~~~~~~~~~

- Hotfix: Create empty KVSessions instead of NullSessions when a session is
  invalid or missing.

Version 0.3
~~~~~~~~~~~

- Use pickle insteaed of json as the serialization method.
- First occurence of changelog in docs.

Version 0.2
~~~~~~~~~~~

- Complete rewrite.
