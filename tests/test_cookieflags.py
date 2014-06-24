def test_secure_false(app, client):
    app.config['SESSION_COOKIE_SECURE'] = False

    client.get('/store-in-session/k1/value1/')
    cookie = client.get_session_cookie()
    assert not cookie.secure


def test_secure_true(app, client):
    app.config['SESSION_COOKIE_SECURE'] = True

    client.get('/store-in-session/k1/value1/')
    cookie = client.get_session_cookie()

    assert cookie.secure


def test_httponly_false(app, client):
    app.config['SESSION_COOKIE_HTTPONLY'] = False

    client.get('/store-in-session/k1/value1/')
    cookie = client.get_session_cookie()
    assert not cookie.has_nonstandard_attr('HttpOnly')


def test_httponly_true(app, client):
    app.config['SESSION_COOKIE_HTTPONLY'] = True

    client.get('/store-in-session/k1/value1/')
    cookie = client.get_session_cookie()
    assert cookie.has_nonstandard_attr('HttpOnly')
