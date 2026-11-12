# gdexms container image for CIRRUS.
# Built and pushed to hub.k8s.ucar.edu by a GitHub Actions workflow; deployed by helm/gdexms.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the package and its dependencies (flask, gunicorn, rda_python_common).
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install .

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 gdexms
USER 10001

EXPOSE 8080

# Sync workers: rda_python_common keeps one DB connection per process and is not thread-safe.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--access-logfile", "-", \
     "gdex_python_gdexms.app:create_app()"]
