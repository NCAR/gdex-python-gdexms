"""Entra ID (OIDC) sign-in for gdexms.

Replaces the PHP editor's unchecked `duser` cookie. A user may use the app only when:

1. Entra ID signs them in (authorization code flow; Authlib checks the ID token,
   nonce and state),
2. the username claim is a UCAR account (<logname>@ucar.edu),
3. if OIDC_ALLOWED_GROUP is set, the ID token's `groups` or `roles` claim contains it
   (the access group GDEX staff maintain in Entra ID), and
4. dssdb.dssgrp has a current record (stat_flag 'C') for the logname. The PHP
   accepted any dssgrp row; closed records are now refused. The logname is also
   what record locks and the change log use.

Settings (environment variables; on CIRRUS filled from OpenBao by the ExternalSecret):

   OIDC_CLIENT_ID         Entra ID application (client) ID; sign-in is off when unset
   OIDC_CLIENT_SECRET     its client secret
   OIDC_TENANT_ID         directory (tenant) ID, or set OIDC_METADATA_URL instead
   OIDC_METADATA_URL      OpenID discovery URL (overrides OIDC_TENANT_ID)
   OIDC_USERNAME_CLAIM    ID token claim holding <logname>@ucar.edu (default preferred_username)
   OIDC_ALLOWED_GROUP     group object ID or app role name required to sign in (optional)
   OIDC_REDIRECT_URI      callback URL, when it can't be derived from the request
"""

import os
import re
from datetime import timedelta
from urllib.parse import urlsplit

from flask import Response, redirect, request, session, url_for

PUBLIC_ENDPOINTS = {'healthz', 'static_files', 'login', 'auth_callback', 'logout'}
UCAR_DOMAIN = 'ucar.edu'
LOGNAME_RE = re.compile(r'^[a-z][a-z0-9_-]{0,7}$')     # dssgrp.logname is varchar(8)

ENTRA_METADATA = 'https://login.microsoftonline.com/{}/v2.0/.well-known/openid-configuration'


class SignInError(Exception):
   """Sign-in was refused; the message is shown to the user."""


def oidc_settings():
   """Read the OIDC settings from the environment."""
   tenant = os.environ.get('OIDC_TENANT_ID')
   return {
      'OIDC_CLIENT_ID': os.environ.get('OIDC_CLIENT_ID'),
      'OIDC_CLIENT_SECRET': os.environ.get('OIDC_CLIENT_SECRET'),
      'OIDC_METADATA_URL': os.environ.get('OIDC_METADATA_URL') or (ENTRA_METADATA.format(tenant) if tenant else None),
      'OIDC_USERNAME_CLAIM': os.environ.get('OIDC_USERNAME_CLAIM', 'preferred_username'),
      'OIDC_ALLOWED_GROUP': os.environ.get('OIDC_ALLOWED_GROUP'),
      'OIDC_REDIRECT_URI': os.environ.get('OIDC_REDIRECT_URI'),
      'PERMANENT_SESSION_LIFETIME': timedelta(hours=12),
   }


class EntraProvider:
   """The Authlib client, behind the two calls the app needs (tests swap in a fake)."""

   def __init__(self, app):
      from authlib.integrations.flask_client import OAuth
      self.client = OAuth(app).register(
         'entra',
         client_id=app.config['OIDC_CLIENT_ID'],
         client_secret=app.config['OIDC_CLIENT_SECRET'],
         server_metadata_url=app.config['OIDC_METADATA_URL'],
         client_kwargs={'scope': 'openid profile email'},
      )

   def authorize_redirect(self, redirect_uri):
      return self.client.authorize_redirect(redirect_uri)

   def fetch_claims(self):
      """Finish the code exchange and return the validated ID token claims."""
      token = self.client.authorize_access_token()
      return dict(token.get('userinfo') or {})


def logname_from_claims(claims, claim_name):
   """Return the UCAR logname from the ID token claims, or raise SignInError."""
   value = (claims.get(claim_name) or '').strip().lower()
   name, _, domain = value.partition('@')
   if domain != UCAR_DOMAIN or not LOGNAME_RE.match(name):
      raise SignInError('gdexms is for GDEX staff with a UCAR account; {!r} is not one.'.format(value or claim_name))
   return name


def check_group(claims, group):
   """Raise SignInError unless the required group or app role is in the claims."""
   if not group:
      return
   members = list(claims.get('groups') or []) + list(claims.get('roles') or [])
   if group in members:
      return
   if '_claim_names' in claims and 'groups' in claims['_claim_names']:
      # Entra leaves the groups out ("overage") when a user is in too many; an app role avoids this
      raise SignInError('Your group membership could not be read from the sign-in token; '
                        'ask the gdexms administrators to grant access through an app role.')
   raise SignInError('You are not in the gdexms access group. Ask a GDEX group owner to add you.')


def specialist_record(db, logname):
   """Return the current dssgrp record for logname, or raise SignInError."""
   db.begin_request()
   rec = db.one('dssdb.dssgrp', 'logname, fstname, lstname', "logname = %s AND stat_flag = 'C'", [logname])
   if not rec:
      raise SignInError('{} is not a current GDEX specialist (dssdb.dssgrp).'.format(logname))
   return rec


def safe_next(url):
   """Only follow a same-site path after sign-in (no open redirects)."""
   if not url or not url.startswith('/') or url.startswith('//') or '\\' in url:
      return '/'
   parts = urlsplit(url)
   return '/' if parts.scheme or parts.netloc else url


def init_auth(app):
   """Register the sign-in routes and the before_request check on app."""
   app.config.setdefault('OIDC_PROVIDER', None)
   enabled = bool(app.config.get('OIDC_CLIENT_ID'))
   if enabled and app.config['OIDC_PROVIDER'] is None:
      app.config['OIDC_PROVIDER'] = EntraProvider(app)

   def current_user():
      """The signed-in UCAR login; GDEXMS_DEV_USER only when sign-in is not configured."""
      return session.get('user') or (None if enabled else app.config.get('DEV_USER'))

   app.current_user = current_user

   def needs_sign_in():
      """Answer a request that has no signed-in user."""
      if not enabled:
         return Response('Sign-in is not configured for gdexms.', status=401, mimetype='text/plain')
      if request.method != 'GET' or 'export' in request.args:
         # the editor's AJAX calls show plain-text answers in an alert
         return Response('Your gdexms sign-in has expired. Reload the page to sign in again.',
                         status=401, mimetype='text/plain')
      target = url_for('login', next=request.full_path.rstrip('?'))
      if request.headers.get('Sec-Fetch-Dest') == 'iframe':
         # table pages load in the menu's iframe, and Entra ID refuses to be framed
         return Response('<script>window.top.location.href = {!r};</script>'.format(url_for('login', next='/')),
                         mimetype='text/html')
      return redirect(target)

   @app.before_request
   def require_user():
      if request.endpoint in PUBLIC_ENDPOINTS:
         return None
      if not current_user():
         return needs_sign_in()
      return None

   @app.get('/login')
   def login():
      if not enabled:
         return Response('Sign-in is not configured for gdexms.', status=404, mimetype='text/plain')
      session['next'] = safe_next(request.args.get('next'))
      redirect_uri = app.config.get('OIDC_REDIRECT_URI') or url_for('auth_callback', _external=True)
      return app.config['OIDC_PROVIDER'].authorize_redirect(redirect_uri)

   @app.get('/auth/callback')
   def auth_callback():
      if not enabled:
         return Response('Sign-in is not configured for gdexms.', status=404, mimetype='text/plain')
      next_url = safe_next(session.pop('next', None))
      try:
         if request.args.get('error'):
            raise SignInError('Sign-in failed: {}'.format(request.args.get('error_description') or request.args['error']))
         claims = app.config['OIDC_PROVIDER'].fetch_claims()
         logname = logname_from_claims(claims, app.config['OIDC_USERNAME_CLAIM'])
         check_group(claims, app.config.get('OIDC_ALLOWED_GROUP'))
         rec = specialist_record(app.config['GET_DB'](), logname)
      except SignInError as err:
         session.clear()
         return Response(str(err), status=403, mimetype='text/plain')
      except Exception as err:      # token exchange/validation, discovery or database failure
         session.clear()
         app.logger.warning('gdexms sign-in failed: %s', err)
         return Response('Sign-in failed; please try again.', status=403, mimetype='text/plain')
      session.clear()
      session.permanent = True
      session['user'] = logname
      session['name'] = ' '.join(x for x in (rec.get('fstname'), rec.get('lstname')) if x)
      return redirect(next_url)

   @app.get('/logout')
   def logout():
      session.clear()
      return Response('You are signed out of gdexms. <a href="/">Sign in again</a>', mimetype='text/html')

   return current_user
