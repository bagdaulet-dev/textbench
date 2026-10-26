# Deployment and GitHub setup

## Repository

Repository: [bagdaulet-dev/textbench](https://github.com/bagdaulet-dev/textbench).
The default branch is `main`. The Django entry point is `backend/manage.py`.

```bash
git clone https://github.com/bagdaulet-dev/textbench.git
cd textbench
```

Never commit `.env`, the virtual environment, database files, SSH keys, or Docker
volumes. `.gitignore` excludes local dependencies and secrets. `.env.example`
contains intentionally public local-development values.

## What the workflow does

1. On pull requests and pushes to `main`: install pinned dependencies, check
   formatting and syntax, validate migrations, test with MySQL 8.4, validate
   OpenAPI and production settings, build the container, and start the complete
   Compose application for a health/frontend smoke test and a repeatable browser journey.
   Python and Node dependency advisory checks also run.
2. After a successful push to `main`: publish a Docker image to
   `ghcr.io/<owner>/<repository>:<commit-sha>`.
3. Only when `DEPLOY_ENABLED=true`: copy deployment configuration over verified
   SSH, pull that image on your server, start the services, and check HTTPS.

Image publishing is continuous delivery. Actual server deployment needs a server,
DNS, and the configuration below. Merely adding the workflow cannot supply those.

## Prepare one server

Use a Linux server with Docker Engine and a recent Compose plugin supporting
`up --wait`. Point a domain's DNS A/AAAA records at the server and allow inbound
ports 80 and 443. Allow SSH only as needed for administration/deployment.

Create `/opt/textbench` and `/opt/textbench/scripts`, owned by the deployment user.
That user needs permission to run Docker. Membership in the Docker group grants
powerful server access; use a dedicated deployment account.

Copy `.env.example` to `/opt/textbench/.env`, then edit it **on the server**:

```dotenv
DJANGO_SECRET_KEY=<generate-a-long-random-secret>
DJANGO_DEBUG=false
DJANGO_ENABLE_API_DOCS=false
DJANGO_ALLOWED_HOSTS=your-domain.example,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.example
DJANGO_SECURE_COOKIES=true
DJANGO_SSL_REDIRECT=true
MYSQL_DATABASE=textbench
MYSQL_USER=textbench
MYSQL_PASSWORD=<unique-strong-password>
MYSQL_ROOT_PASSWORD=<different-unique-strong-password>
APP_DOMAIN=your-domain.example
```

Generate a secret with `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`.
Keep that output private and set `.env` file permissions to 600. Compose overrides
the database hostname internally. The database has no published port in production.

The first image publication may create a private GHCR package. Make the package
public for a public portfolio project, or authenticate Docker on the server with
a token limited to reading that package. Do not put registry tokens in this repo.

## Configure GitHub

Create a repository environment named `production`. Add these environment secrets:

| Secret | Value |
|---|---|
| `SSH_HOST` | Deployment server hostname or IP |
| `SSH_USER` | Dedicated deployment user |
| `SSH_PORT` | SSH port; defaults to 22 if absent |
| `SSH_PRIVATE_KEY` | Deployment key authorized on that server |
| `SSH_KNOWN_HOSTS` | Verified OpenSSH known-hosts entry for the server |

Verify the server's SSH host-key fingerprint through a trusted channel before
setting `SSH_KNOWN_HOSTS`. Do not disable host-key checking. For nonstandard ports,
the known-hosts entry normally uses `[hostname]:port`.

Add repository variables:

| Variable | Value |
|---|---|
| `DEPLOY_ENABLED` | `true` only when the server is ready |
| `APP_DOMAIN` | Domain without `https://` or a trailing slash |

The workflow uses GitHub's built-in `GITHUB_TOKEN` to publish; a separate GHCR
write token is unnecessary. Ensure repository Actions permissions allow package
publishing. Domain TLS certificates are managed by Caddy.

## Manual deployment

With deployment files and `.env` in `/opt/textbench`:

```bash
cd /opt/textbench
IMAGE=ghcr.io/your-owner/your-repository:your-commit-sha bash scripts/deploy.sh
```

Use a real image name from a successful publish run. The script pulls images,
starts the app/MySQL/proxy, waits for health, checks production settings, and
cleans expired sessions/history. The container applies migrations before serving.

## Routine operations

```bash
docker compose -f compose.production.yml logs -f app
docker compose -f compose.production.yml exec app python manage.py showmigrations
docker compose -f compose.production.yml exec app python manage.py purge_expired_analyses
docker compose -f compose.production.yml exec app python manage.py clearsessions
```

Compose requires the image name even for management commands. Set `IMAGE` in the
shell or in the server's `.env` when running commands manually. The deployment
job passes it explicitly for each release.

Schedule the two cleanup commands daily using the server's scheduler. The app
does not secretly create a scheduled job on your machine.

Back up MySQL regularly using a restricted backup account and `mysqldump`, or
your hosting provider's database backup service. Test restoring a backup. Keep
backup credentials outside version control and backups outside the application
container. A Docker volume alone is persistent storage, not a backup.

## Rollback and limitations

Redeploy the previous known-good commit's image tag using the manual command.
This rolls back application code, **not database schema or data**. Check migration
compatibility before rolling back; keep schema changes backward compatible where
possible. Take a database backup before destructive migrations.

This setup runs one application worker on one server. Restarting the app can briefly interrupt requests.
The throttle uses process-local counters and is not a distributed rate limiter.
No automatic database rollback, high availability, or zero-downtime guarantee is
claimed. These are reasonable boundaries for this small portfolio project.
