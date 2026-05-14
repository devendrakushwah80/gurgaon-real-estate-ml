# CI/CD

GitHub Actions workflow is defined in `.github/workflows/ci.yml`.

The pipeline runs:

- dependency installation
- lint checks with Ruff
- unit tests with pytest
- Docker build validation

