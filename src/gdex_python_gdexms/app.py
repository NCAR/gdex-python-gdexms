"""Flask application factory for gdexms.

The table pages keep their rda-pg-config URLs (/<page>.php) so the unchanged
browser code (ajaxUrl, export links, bookmarks) keeps working. Static files are
served at the same relative paths the PHP pages used (js/, css/, images/).

Settings come from the environment, which on CIRRUS is filled from OpenBao by
the ExternalSecret in the Helm chart (helm/gdexms):

   FLASK_SECRET_KEY     signs the session cookie; must be the same on all replicas
   OIDC_*               Entra ID sign-in (see auth.py); sign-in is on when OIDC_CLIENT_ID is set
   PGDB01_DSSDBPASS     dssdb password, read by rda_python_common itself
   GDEXMS_DEV_USER      local development only, and only while OIDC_CLIENT_ID is unset:
                        act as this UCAR login without signing in
"""

import os
import secrets
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix

from . import __version__
from .auth import init_auth, oidc_settings
from .editor.db import EditorDBError, get_db
from .editor.engine import EditorError, decode_request
from .pages import PAGES

STATIC = Path(__file__).parent / 'static'

MENU = [
   ('GDEXDB', [('Specialist', 'rdadb_specialist'), ('Organization Types', 'rdadb_org_type'),
              ('GDEX NCAR User', 'rdadb_ncar_user'), ('GDEX Public User', 'rdadb_public_user')]),
   ('DSARCH', [('Dataset Information', 'dsarch_dataset'), ('Group Information', 'dsarch_group'),
               ('Saved Files', 'dsarch_savedfile'), ('Backup Files', 'dsarch_backupfile'),
               ('Web Files', 'dsarch_webfile'), ('Help Files', 'dsarch_helpfile'),
               ('DOI Version Control', 'dsarch_version'), ('TACC Files', 'dsarch_taccfile')]),
   ('DSUPDT', [('Update Control', 'dsupdt_control'), ('Local File', 'dsupdt_localfile'),
               ('Remote File', 'dsupdt_remotefile')]),
   ('DSRQST', [('Request Control', 'dsrqst_control'), ('Request Information', 'dsrqst_request'),
               ('Request Partition', 'dsrqst_partition'), ('Dataset Request Limit', 'dsrqst_dslimit'),
               ('User Request Limit', 'dsrqst_userlimit'), ('Request File', 'dsrqst_file'),
               ('Tar File', 'dsrqst_tarfile'), ('Request History', 'dsrqst_purge')]),
   ('DSCHECK', [('Available Hostnames', 'dscheck_hostname'), ('Daemon Control', 'dscheck_daemon'),
                ('Check Information', 'dscheck_check'), ('Check History', 'dscheck_history')]),
]


def create_app(test_config=None):
   """Create and configure the gdexms Flask application.

   Args:
      test_config (dict | None): Settings that override the environment, for tests.

   Returns:
      Flask: The configured application.
   """
   app = Flask(__name__)
   dev_user = os.environ.get('GDEXMS_DEV_USER')
   app.config.from_mapping(
      SECRET_KEY=os.environ.get('FLASK_SECRET_KEY') or (secrets.token_hex(32) if dev_user else None),
      DEV_USER=dev_user,
      SESSION_COOKIE_SAMESITE='Lax',
      SESSION_COOKIE_SECURE=not dev_user,
      GET_DB=get_db,
      **oidc_settings(),
   )
   if test_config:
      app.config.update(test_config)
   # behind the CIRRUS ingress: trust its X-Forwarded-Proto/Host so the sign-in
   # callback URL is https://<fqdn>/auth/callback
   app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
   current_user = init_auth(app)

   @app.get("/healthz")
   def healthz():
      """Liveness/readiness probe for Kubernetes; touches no database."""
      return {"status": "ok", "version": __version__}

   @app.get('/<any(js, css, images):folder>/<path:filename>', endpoint='static_files')
   def static_files(folder, filename):
      return send_from_directory(STATIC / folder, filename)

   @app.get('/')
   def index():
      menu = [(group, [(text, page, page in PAGES) for text, page in items]) for group, items in MENU]
      return render_template('index.html', menu=menu, user=current_user(), name=session.get('name'),
                             signed_in='user' in session)

   @app.route('/<page>.php', methods=['GET', 'POST'])
   def table_page(page):
      cls = PAGES.get(page)
      if not cls:
         abort(404)
      action, info = '', ''
      if request.method == 'POST':
         try:
            action, info = decode_request(request.form.get('json'))
         except ValueError:
            return Response('Invalid request', status=400, mimetype='text/plain')
      db = app.config['GET_DB']()
      db.begin_request()
      pobj = cls(db, session, specialist=current_user(), page_url=request.path,
                 cookies=request.cookies, action=action, info=info)
      try:
         if request.method == 'POST':
            pobj.init_editor()
            resp = jsonify(pobj.editor.main(action, info))
         elif 'export' in request.args:
            pobj.init_editor()
            resp = Response(pobj.editor.export_info(), mimetype='text/csv')
            resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
            resp.headers['Pragma'] = 'no-cache'
            resp.headers['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(pobj.editor.table_name)
         else:
            return render_template('page_shell.html', ajax_url=request.path, pre_html=pobj.pre_html())
      except (EditorDBError, EditorError, ValueError) as err:
         # the PHP died with a plain-text message, which the browser shows in an alert
         return Response(str(err), mimetype='text/plain')
      for name, value in pobj.editor.set_cookies.items():
         resp.set_cookie(name, value, max_age=60 * 60 * 24 * 365 * 2, samesite='Lax',
                         secure=app.config['SESSION_COOKIE_SECURE'])
      return resp

   return app
