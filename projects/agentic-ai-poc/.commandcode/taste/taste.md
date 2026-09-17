# Taste Profile
See [taste-profile/taste.md](taste-profile/taste.md)

- Prefers the `docker-compose` (hyphenated v1-style) CLI form over the `docker compose` (v2 subcommand) form. Confidence: 0.8
- Cleans up Docker Compose services after testing — runs `docker-compose down` to stop and remove containers once a fix is verified, rather than leaving services running in the background. Confidence: 0.85
- Verifies fixes by checking container status and startup logs — inspects `docker-compose ps` and `docker-compose logs --tail=N <service>` to confirm clean startup before declaring a fix complete. Confidence: 0.8
- Project uses a dedicated `Dockerfile.docs` that installs docs dependencies via `pip` directly (not through Poetry); dependencies must be kept in sync across both `pyproject.toml` and `Dockerfile.docs`. Confidence: 0.85
