# gdex-python-gdexms
GDEX Python web application for GDEX specialists, deployed on CIRRUS

Repository: https://github.com/NCAR/gdex-python-gdexms

## Deployment on CIRRUS

- `Dockerfile` builds the image (gunicorn on port 8080, `/healthz` for probes).
- `helm/gdexms` is the Helm chart (based on the CIRRUS `external-secret-helm` example):
  Deployment, Service, Ingress and an ExternalSecret that maps OpenBao values to env vars
  (`FLASK_SECRET_KEY`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `PGDB01_DSSDBPASS`).
- `.github/workflows/build-push-image.yml` builds and pushes `hub.k8s.ucar.edu/gdex/gdexms:<short sha>`
  on pushes to `main`; deploy a build by setting that tag in `helm/gdexms/values.yaml`.
- SecretStore `rda-ro`; app secrets in OpenBao `kv/gdex/gdexms`, database password in `kv/gdex/pgdb01`.
  FQDN `gdexms.k8s.ucar.edu` (a `gdex.ucar.edu` CNAME may follow).

## Sign-in

Staff sign in with their own UCAR account through Entra ID (`src/gdex_python_gdexms/auth.py`).
Access needs a current `dssdb.dssgrp` record (`stat_flag = 'C'`) and, if `OIDC_ALLOWED_GROUP`
is set, membership in that Entra group or app role. Sign-in is on when `OIDC_CLIENT_ID` is set.

For local development without sign-in, leave `OIDC_CLIENT_ID` unset and run:

    GDEXMS_DEV_USER=<logname> flask --app gdex_python_gdexms.app:create_app run --port 5050
