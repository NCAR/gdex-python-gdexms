"""Flask application factory for gdexms.

Only the health check and a placeholder index exist so far; the Entra ID OIDC
login and the configuration editor pages come later.

Settings come from the environment, which on CIRRUS is filled from OpenBao by
the ExternalSecret in the Helm chart (helm/gdexms):

   FLASK_SECRET_KEY     signs the session cookie; must be the same on all replicas
   OIDC_CLIENT_ID       Entra ID client ID (login, not used yet)
   OIDC_CLIENT_SECRET   Entra ID client secret (login, not used yet)
   PGDB01_DSSDBPASS     dssdb password, read by rda_python_common itself
"""

import os

from flask import Flask

from . import __version__


def create_app(test_config=None):
   """Create and configure the gdexms Flask application.

   Args:
      test_config (dict | None): Settings that override the environment, for tests.

   Returns:
      Flask: The configured application.
   """
   app = Flask(__name__)
   app.config.from_mapping(
      SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
      OIDC_CLIENT_ID=os.environ.get("OIDC_CLIENT_ID"),
      OIDC_CLIENT_SECRET=os.environ.get("OIDC_CLIENT_SECRET"),
   )
   if test_config:
      app.config.update(test_config)

   @app.get("/healthz")
   def healthz():
      """Liveness/readiness probe for Kubernetes; touches no database."""
      return {"status": "ok", "version": __version__}

   @app.get("/")
   def index():
      return "gdexms {}: GDEX specialist web application (under construction)".format(__version__)

   return app
