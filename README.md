# gdex-python-gdexms
GDEX Python web application for GDEX specialists, deployed on CIRRUS

Repository: https://github.com/NCAR/gdex-python-gdexms

## Deployment on CIRRUS

- `Dockerfile` builds the image (gunicorn on port 8080, `/healthz` for probes).
- `helm/gdexms` is the Helm chart (based on the CIRRUS `external-secret-helm` example):
  Deployment, Service, Ingress and an ExternalSecret that maps OpenBao values to env vars
  (`FLASK_SECRET_KEY`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `PGDB01_DSSDBPASS`).
- Still to confirm with the CIRRUS team: registry project name, OpenBao paths,
  SecretStore name, and the final FQDN (`gdexms.k8s.ucar.edu` now, `gdexms.gdex.ucar.edu` planned).
