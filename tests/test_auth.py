# test_auth.py: Entra ID sign-in, with a fake identity provider and database

import pytest
from flask import redirect

from gdex_python_gdexms.app import create_app
from gdex_python_gdexms.auth import check_group, logname_from_claims, safe_next, SignInError


class FakeProvider:
   def __init__(self, claims=None, fail=None):
      self.claims = claims or {}
      self.fail = fail
      self.redirect_uri = None

   def authorize_redirect(self, redirect_uri):
      self.redirect_uri = redirect_uri
      return redirect('https://login.example/authorize')

   def fetch_claims(self):
      if self.fail: raise self.fail
      return self.claims


class FakeDB:
   def __init__(self, current=('zji',)):
      self.current = current
      self.queries = []

   def begin_request(self): pass

   def one(self, tables, fields, cond=None, vals=None):
      self.queries.append((tables, fields, cond, vals))
      if vals[0] in self.current:
         return {'logname': vals[0], 'fstname': 'Hua', 'lstname': 'Ji'}
      return None


def make_app(claims, group=None, db=None, fail=None, dev_user=None):
   provider = FakeProvider(claims, fail)
   db = db or FakeDB()
   app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DEV_USER': dev_user, 'GET_DB': lambda: db,
                     'OIDC_CLIENT_ID': 'client', 'OIDC_PROVIDER': provider, 'OIDC_ALLOWED_GROUP': group})
   return app, provider, db


def sign_in(client, next_url='/'):
   r = client.get('/login', query_string={'next': next_url})
   assert r.status_code == 302 and r.location == 'https://login.example/authorize'
   return client.get('/auth/callback', query_string={'code': 'x', 'state': 'y'})


def test_page_redirects_to_sign_in():
   app, _, _ = make_app({})
   r = app.test_client().get('/dsarch_webfile.php')
   assert r.status_code == 302 and r.location.startswith('/login?next=/dsarch_webfile.php')


def test_iframe_page_breaks_out_to_top_window():
   app, _, _ = make_app({})
   r = app.test_client().get('/dsarch_webfile.php', headers={'Sec-Fetch-Dest': 'iframe'})
   assert r.status_code == 200 and b'window.top.location.href' in r.data


def test_ajax_and_export_get_plain_401():
   app, _, _ = make_app({})
   c = app.test_client()
   assert c.post('/dsarch_webfile.php', data={'json': '{}'}).status_code == 401
   r = c.get('/dsarch_webfile.php?export=1')
   assert r.status_code == 401 and b'expired' in r.data


def test_sign_in_success_sets_session_and_follows_next():
   app, provider, db = make_app({'preferred_username': 'ZJI@ucar.edu', 'groups': []})
   c = app.test_client()
   r = sign_in(c, '/dscheck_check.php')
   assert r.status_code == 302 and r.location == '/dscheck_check.php'
   assert provider.redirect_uri == 'http://localhost/auth/callback'
   assert db.queries == [('dssdb.dssgrp', 'logname, fstname, lstname', "logname = %s AND stat_flag = 'C'", ['zji'])]
   with c.session_transaction() as s:
      assert s['user'] == 'zji' and s['name'] == 'Hua Ji' and 'next' not in s
   assert b'Hua Ji' in c.get('/').data


def test_dev_user_ignored_when_sign_in_is_on():
   app, _, _ = make_app({}, dev_user='zji')
   assert app.test_client().get('/').status_code == 302


def test_redirect_uri_behind_ingress():
   app, provider, _ = make_app({})
   app.test_client().get('/login', headers={'X-Forwarded-Proto': 'https', 'X-Forwarded-Host': 'gdexms.k8s.ucar.edu'})
   assert provider.redirect_uri == 'https://gdexms.k8s.ucar.edu/auth/callback'


@pytest.mark.parametrize('claims, group, current, message', [
   ({'preferred_username': 'someone@gmail.com'}, None, ('zji',), b'UCAR account'),
   ({'preferred_username': 'zji@ucar.edu', 'groups': ['other']}, 'gdexms-id', ('zji',), b'access group'),
   ({'preferred_username': 'zji@ucar.edu'}, None, (), b'not a current GDEX specialist'),
])
def test_sign_in_refused(claims, group, current, message):
   app, _, _ = make_app(claims, group=group, db=FakeDB(current))
   c = app.test_client()
   r = sign_in(c)
   assert r.status_code == 403 and message in r.data
   with c.session_transaction() as s:
      assert 'user' not in s
   assert c.get('/').status_code == 302


def test_group_or_app_role_admits():
   for claims in ({'preferred_username': 'zji@ucar.edu', 'groups': ['gdexms-id']},
                  {'preferred_username': 'zji@ucar.edu', 'roles': ['gdexms-id']}):
      app, _, _ = make_app(claims, group='gdexms-id')
      assert sign_in(app.test_client()).status_code == 302


def test_token_failure_is_a_generic_403():
   app, _, _ = make_app({}, fail=RuntimeError('bad state'))
   r = sign_in(app.test_client())
   assert r.status_code == 403 and b'bad state' not in r.data


def test_entra_error_is_reported():
   app, _, _ = make_app({})
   c = app.test_client()
   c.get('/login')
   r = c.get('/auth/callback', query_string={'error': 'access_denied', 'error_description': 'AADSTS50105 not assigned'})
   assert r.status_code == 403 and b'AADSTS50105' in r.data


def test_logout_clears_session():
   app, _, _ = make_app({'preferred_username': 'zji@ucar.edu'})
   c = app.test_client()
   sign_in(c)
   assert c.get('/').status_code == 200
   c.get('/logout')
   assert c.get('/').status_code == 302


def test_sign_in_off_without_client_id():
   app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DEV_USER': None, 'OIDC_CLIENT_ID': None})
   c = app.test_client()
   assert c.get('/login').status_code == 404
   assert c.get('/').status_code == 401


def test_helpers():
   assert logname_from_claims({'upn': 'Bozo@UCAR.edu'}, 'upn') == 'bozo'
   for bad in ({}, {'upn': 'zji@ucar.edu.evil.com'}, {'upn': 'toolongname@ucar.edu'}, {'upn': "a'b@ucar.edu"}):
      with pytest.raises(SignInError):
         logname_from_claims(bad, 'upn')
   check_group({}, None)
   with pytest.raises(SignInError, match='app role'):
      check_group({'_claim_names': {'groups': 'src1'}}, 'g')
   assert safe_next('/dsarch_webfile.php?x=1') == '/dsarch_webfile.php?x=1'
   for bad in (None, '', 'https://evil.com/', '//evil.com/x', '/\\evil.com', 'javascript:alert(1)'):
      assert safe_next(bad) == '/'
