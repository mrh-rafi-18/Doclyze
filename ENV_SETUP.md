# Doclyze — Environment Variables Setup Guide

Create a `.env` file in the project root (next to `manage.py`) and populate it using the table below.

> **Security rule:** Never commit `.env` to version control. Add it to `.gitignore` immediately.

---

## 1. Django Core

| Variable | Required | Example | Notes |
|---|---|---|---|
| `SECRET_KEY` | ✅ | `django-insecure-...` | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | ✅ | `False` | Set `True` for local development only |
| `ALLOWED_HOSTS` | ✅ | `localhost,127.0.0.1,yourdomain.com` | Comma-separated list |

---

## 2. Database (PostgreSQL)

| Variable | Required | Example | Notes |
|---|---|---|---|
| `DB_NAME` | ✅ | `doclyze` | PostgreSQL database name |
| `DB_USER` | ✅ | `postgres` | Database user |
| `DB_PASSWORD` | ✅ | `supersecret` | Database password |
| `DB_HOST` | ✅ | `localhost` | Database host |
| `DB_PORT` | ✅ | `5432` | Default PostgreSQL port |

**Setup commands:**
```bash
# Create the database
psql -U postgres -c "CREATE DATABASE doclyze;"
```

---

## 3. JWT Token Lifetimes

| Variable | Required | Default | Notes |
|---|---|---|---|
| `ACCESS_TOKEN_MINUTES` | ❌ | `60` | Access token TTL in minutes |
| `REFRESH_TOKEN_DAYS` | ❌ | `7` | Refresh token TTL in days |

---

## 4. Email (SMTP)

Doclyze sends transactional emails for:
- Email address verification
- Password reset

**Option A — Gmail with App Password (recommended for development)**

1. Enable 2-Factor Authentication on your Google account
2. Go to [Google Account → Security → App Passwords](https://myaccount.google.com/apppasswords)
3. Generate an app password for "Mail"
4. Copy the 16-character password

| Variable | Required | Example | Notes |
|---|---|---|---|
| `EMAIL_HOST` | ✅ | `smtp.gmail.com` | SMTP server hostname |
| `EMAIL_PORT` | ✅ | `587` | TLS port |
| `EMAIL_USE_TLS` | ✅ | `True` | Must be `True` for Gmail |
| `EMAIL_HOST_USER` | ✅ | `you@gmail.com` | Your Gmail address |
| `EMAIL_HOST_PASSWORD` | ✅ | `abcd efgh ijkl mnop` | **App Password** (not your Gmail login password) |
| `DEFAULT_FROM_EMAIL` | ✅ | `noreply@doclyze.com` | Sender name shown to recipients |

**Option B — SendGrid / Mailgun / Amazon SES**
- Replace `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` with the provider's SMTP credentials
- `EMAIL_USE_TLS=True` for most providers

**Option C — Local testing (no real emails)**
- Set `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` in `config/settings.py`
- Emails will print to your terminal instead of being sent

---

## 5. Redis (Celery Broker & Cache)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `REDIS_URL` | ✅ | `redis://localhost:6379/0` | Redis connection URL |

**Install Redis:**
```bash
# macOS
brew install redis && brew services start redis

# Ubuntu/Debian
sudo apt install redis-server && sudo systemctl start redis
```

---

## 6. CORS

| Variable | Required | Default | Notes |
|---|---|---|---|
| `CORS_ALLOWED_ORIGINS` | ✅ | `http://localhost:3000` | Comma-separated list of allowed frontend origins |

---

## 7. Frontend URL

| Variable | Required | Default | Notes |
|---|---|---|---|
| `FRONTEND_URL` | ✅ | `http://localhost:3000` | Used to build verification and reset links in emails |

---

## 8. File Upload Limits

| Variable | Required | Default | Notes |
|---|---|---|---|
| `MAX_UPLOAD_SIZE_MB` | ❌ | `50` | Maximum upload size in megabytes |

---

## Complete `.env` Template

Copy this into your `.env` file and fill in the values:

```env
# ── Django ────────────────────────────────────────────────────────────────────
SECRET_KEY=CHANGE_ME_generate_with_django_get_random_secret_key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# ── Database ──────────────────────────────────────────────────────────────────
DB_NAME=doclyze
DB_USER=postgres
DB_PASSWORD=CHANGE_ME
DB_HOST=localhost
DB_PORT=5432

# ── JWT ───────────────────────────────────────────────────────────────────────
ACCESS_TOKEN_MINUTES=60
REFRESH_TOKEN_DAYS=7

# ── Email (Gmail App Password example) ───────────────────────────────────────
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=abcd efgh ijkl mnop
DEFAULT_FROM_EMAIL=noreply@doclyze.com

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS=http://localhost:3000

# ── Frontend ──────────────────────────────────────────────────────────────────
FRONTEND_URL=http://localhost:3000

# ── Uploads ───────────────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB=50
```

---

## 9. First-Run Commands

After filling in `.env`, run these once:

```bash
# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Create a superuser (optional)
python manage.py createsuperuser

# Start the development server
python manage.py runserver

# Start Celery worker (separate terminal)
celery -A config.celery worker --loglevel=info
```

---

## 10. Production Checklist

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` is long, random, and kept secret
- [ ] Database uses a dedicated user with a strong password
- [ ] `EMAIL_HOST_PASSWORD` is a **Gmail App Password**, not your real password
- [ ] Redis is password-protected (`redis://:password@host:6379/0`)
- [ ] `ALLOWED_HOSTS` lists only your actual domain(s)
- [ ] Run behind HTTPS (TLS certificate required)
- [ ] Set `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True` in settings for HTTPS
