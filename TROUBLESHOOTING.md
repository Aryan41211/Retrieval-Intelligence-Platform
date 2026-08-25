# Troubleshooting Guide

## Common Issues

### Application fails to start with "ENTERPRISE_JWT_SECRET_KEY must be set"

**Cause:** The enterprise layer requires a JWT signing key.

**Solution:** Generate a secure key and set it:
```bash
openssl rand -hex 32
export ENTERPRISE_JWT_SECRET_KEY="<generated-key>"
```

### "CORS wildcard origin with credentials" error on startup

**Cause:** `API_CORS_CREDENTIALS=true` is set with `API_CORS_ORIGINS=["*"]`.

**Solution:** Set explicit allowed origins:
```bash
API_CORS_ORIGINS=["https://your-frontend.example.com"]
API_CORS_CREDENTIALS=true
```

### API returns 401 on enterprise endpoints

**Cause:** Missing or invalid JWT token.

**Solutions:**
- Include `Authorization: Bearer <token>` header on all enterprise endpoints
- Token may have expired — call `POST /api/v1/auth/refresh` with the refresh
  token to obtain a new pair
- Ensure `ENTERPRISE_JWT_SECRET_KEY` matches between the service that issued
  the token and the service validating it

### No results returned from retrieval

**Possible causes:**

1. **No documents ingested:** Upload documents via `POST /api/v1/documents`.
2. **Embedding dimension mismatch:** Ensure the embedding model used at index
   time matches the model used at query time.
3. **Empty index:** Verify the vector store index was persisted correctly.
4. **BM25 index not built:** The BM25 index requires a separate build step
   after documents are chunked.

### LLM generation returns errors

**Possible causes:**

1. **Missing API key:** Set the appropriate `*_API_KEY` environment variable.
2. **Rate limited:** The LLM provider may be rate-limiting your account.
   Check `API_RATE_LIMIT_PER_MINUTE` settings.
3. **Model not available:** Verify the model name is correct and available
   for your API key/region.
4. **Timeout:** Increase `GENERATION_TIMEOUT` or reduce generation length.

### Frontend can't connect to the API

**Possible causes:**

1. **CORS misconfiguration:** Verify `API_CORS_ORIGINS` includes the frontend
   origin.
2. **Wrong VITE_API_URL:** Check `frontend/.env` or the dev server proxy config.
3. **API not running:** Verify the API is running on the expected host:port.

### Docker build is very slow

**Expected:** The runtime image installs the full ML dependency set (PyTorch
CPU, sentence-transformers, chromadb, mlflow, wandb). Expect 5-15 minutes for
the initial build. Use Docker layer caching for subsequent builds.

**Optimization tips:**
- Use `DOCKER_BUILDKIT=1 docker build`
- Move optional providers to extras in `pyproject.toml`
- Pre-build the base image in a registry

### Tests fail with "requires_api" marker

**Cause:** Tests marked with `requires_api` need external API credentials.

**Solution:** These tests are automatically skipped unless you set the
relevant environment variables. They are not required for basic CI validation.

## Getting Help

If you encounter an issue not covered here:

1. Search existing [GitHub Issues](https://github.com/example/retrieval-intelligence-platform/issues)
2. Check the [FAQ](FAQ.md) for common questions
3. Open a new issue with:
   - Platform version
   - Python/Node.js versions
   - Full error message and stack trace
   - Steps to reproduce
   - Environment details (OS, Docker version, etc.)
