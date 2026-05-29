# Environment Setup Guide

## Overview
This project uses environment variables to manage sensitive configuration. All configuration is loaded from a `.env` file using `python-decouple`.

## Files

- **`.env`** - Your local configuration (DO NOT commit to git)
- **`.env.example`** - Template showing required variables
- **`agtv_backend/settings.py`** - Loads configuration from `.env`

## Installation

1. **Ensure `python-decouple` is installed:**
   ```bash
   pip install python-decouple
   ```

2. **Create `.env` file from template:**
   ```bash
   cp .env.example .env
   ```

3. **Update `.env` with your actual values:**
   - Database credentials
   - Email configuration
   - Secret key (for production: generate new one)

## Configuration Variables

### Django Settings
- **DEBUG** - Set to `False` in production
- **SECRET_KEY** - Cryptographically secure key (change in production)
- **ALLOWED_HOSTS** - Comma-separated list of allowed hosts

### Database
- **DB_ENGINE** - Django database backend (default: mysql)
- **DB_NAME** - Database name
- **DB_USER** - Database username
- **DB_PASSWORD** - Database password
- **DB_HOST** - Database host
- **DB_PORT** - Database port

### Email
- **EMAIL_BACKEND** - Email backend service
- **EMAIL_HOST** - SMTP server
- **EMAIL_PORT** - SMTP port
- **EMAIL_USE_TLS** - Use TLS encryption
- **EMAIL_HOST_USER** - Email account
- **EMAIL_HOST_PASSWORD** - Email app password (not your regular password)
- **DEFAULT_FROM_EMAIL** - Default sender email

## Security Notes

⚠️ **IMPORTANT:**
- `.env` is in `.gitignore` and should NEVER be committed
- Never hardcode secrets in code
- Rotate credentials regularly
- In production, use `DEBUG=False`
- Generate a new SECRET_KEY for each environment
- Use environment-specific database instances

## For Gmail (EMAIL_HOST_USER/PASSWORD)

If using Gmail:
1. Enable 2-Factor Authentication on your account
2. Generate an "App Password" (16 characters)
3. Use the app password in EMAIL_HOST_PASSWORD (not your regular password)

## Deployment

For production deployment:
1. Create new `.env` with production values
2. Set `DEBUG=False`
3. Generate a new SECRET_KEY: `python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
4. Use strong database credentials
5. Consider using a secret management service (AWS Secrets Manager, etc.)
