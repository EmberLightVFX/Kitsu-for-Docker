# 2FA Enforcement Scripts

This directory contains all the scripts needed to enforce 2FA for Kitsu/Zou users.

## Files Overview

### Core Middleware (Recommended Approach)

**zou_2fa_middleware.py**
- Flask middleware that intercepts all requests
- Redirects users without 2FA to a friendly instruction page
- Users can configure 2FA and immediately get access
- No account disabling needed

**zou_app_wrapper.py**
- Wrapper that loads the Zou app and injects the middleware
- Used as the WSGI entry point for Gunicorn
- Handles middleware initialization

**zou_entrypoint_wrapper.sh**
- Bash wrapper for the container entrypoint
- Installs dependencies
- Runs init/upgrade scripts
- Injects the middleware into the app
- Replaces `zou.app:app` with `zou_app_wrapper:app`

### Audit & Management Tools

**enforce_2fa.py**
- Python script to audit users and their 2FA status
- Can optionally disable users without 2FA (legacy method)
- Commands:
  - `--audit`: Show 2FA compliance report
  - `--enforce`: Disable users without 2FA (not recommended)
  - `--enable-user EMAIL`: Re-enable a specific user

**check_2fa_on_startup.sh**
- Runs on container startup
- Performs 2FA compliance audit
- Shows enforcement method being used
- Optionally runs legacy enforcement (if enabled)

**2fa_cron_check.sh**
- Script for periodic compliance checks
- Can be run via cron for regular audits
- Logs results to `/tmp/zou/`

### Utility Scripts

**install_dependencies.sh**
- Installs Python dependencies (psycopg2-binary)
- Installs PostgreSQL client for database checks

## How It Works

### Recommended Method (Redirect)

```
User Login → Middleware Check → Has 2FA?
                                 ↓ No
                           Redirect to Friendly Page
                                 ↓
                           User Configures 2FA
                                 ↓
                           Immediate Access ✅
```

### Legacy Method (Disable)

```
User Login → Database Check → Has 2FA?
                                ↓ No
                          Account Disabled ❌
                                ↓
                          Admin Re-enables
                                ↓
                          User Gets Access
```

## Environment Variables

| Variable | Description | Default | Method |
|----------|-------------|---------|--------|
| `REQUIRE_2FA` | Enable 2FA requirement | `False` | Redirect (Recommended) |
| `2FA_EXEMPT_USERS` | Comma-separated exempt emails | None | Both |
| `REQUIRE_2FA_DISABLE_USERS` | Disable users without 2FA | `False` | Legacy (Not Recommended) |

## Usage Examples

### Enable 2FA Enforcement (Redirect Method)

```bash
# In .env
REQUIRE_2FA=True

# Start containers
docker-compose -f docker-compose.yaml -f docker-compose.2fa.yaml up -d
```

### Check Compliance

```bash
docker exec cgwire-zou-app python3 /opt/zou/scripts/enforce_2fa.py --audit
```

### Verify Middleware is Running

```bash
docker logs cgwire-zou-app | grep "2FA ENFORCEMENT"
```

Expected output:
```
================================================================================
INITIALIZING 2FA ENFORCEMENT MIDDLEWARE
================================================================================
✓ 2FA enforcement middleware successfully loaded
  Users without 2FA will be prompted to configure it
================================================================================
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Docker Container: cgwire-zou-app                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  zou_entrypoint_wrapper.sh                         │
│    ↓                                                │
│  install_dependencies.sh (install psycopg2)        │
│    ↓                                                │
│  check_2fa_on_startup.sh (run audit)               │
│    ↓                                                │
│  gunicorn → zou_app_wrapper:app                    │
│              ↓                                      │
│           zou_2fa_middleware.py (intercept)        │
│              ↓                                      │
│           zou.app (original app)                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## File Mounting (docker-compose.2fa.yaml)

All scripts are mounted as read-only volumes:

```yaml
volumes:
  - ./scripts/enforce_2fa.py:/opt/zou/scripts/enforce_2fa.py:ro
  - ./scripts/check_2fa_on_startup.sh:/opt/zou/scripts/check_2fa_on_startup.sh:ro
  - ./scripts/zou_entrypoint_wrapper.sh:/opt/zou/scripts/zou_entrypoint_wrapper.sh:ro
  - ./scripts/zou_2fa_middleware.py:/opt/zou/scripts/zou_2fa_middleware.py:ro
  - ./scripts/zou_app_wrapper.py:/opt/zou/scripts/zou_app_wrapper.py:ro
  - ./scripts/install_dependencies.sh:/opt/zou/scripts/install_dependencies.sh:ro
  - ./scripts/2fa_cron_check.sh:/opt/zou/scripts/2fa_cron_check.sh:ro
```

## Database Schema

The middleware checks these fields in the `person` table:

```python
totp_enabled: Boolean          # TOTP configured
email_otp_enabled: Boolean     # Email OTP configured
fido_enabled: Boolean          # FIDO device configured
email: String                  # User email (for exemptions)
```

## Allowed Routes (No 2FA Required)

These routes work even without 2FA:

- `/api/auth/login` - Login
- `/api/auth/logout` - Logout
- `/static/*` - Static files
- `/api/data/persons/me` - User data
- `/api/data/persons/*` - Profile updates
- `/api/actions/persons/*` - 2FA actions

## Troubleshooting

### Middleware not loading

**Check logs:**
```bash
docker logs cgwire-zou-app
```

**Common issues:**
- Scripts not mounted → Check docker-compose.2fa.yaml
- Dependencies missing → Check install_dependencies.sh output
- Import errors → Check PYTHONPATH includes /opt/zou/scripts

### Users still accessing without 2FA

**Check:**
1. Is `REQUIRE_2FA=True` in .env?
2. Is middleware loaded? (check logs)
3. Is user in exempt list?

### Redirect loop

**Shouldn't happen**, but if it does:
1. Temporarily add user to `2FA_EXEMPT_USERS`
2. Have them configure 2FA
3. Remove from exempt list

## Security Considerations

1. **Scripts are read-only**: Mounted with `:ro` flag
2. **Database access**: Uses environment variables for credentials
3. **Exempt list**: Should only include service accounts
4. **No password storage**: Scripts only check boolean flags
5. **Audit logs**: Can be enabled for compliance

## Comparison: Redirect vs Disable

| Aspect | Redirect Method | Disable Method |
|--------|----------------|----------------|
| File | zou_2fa_middleware.py | enforce_2fa.py --enforce |
| Trigger | Every request | Manual/Startup |
| User Impact | Can self-recover | Needs admin |
| Account Status | Active | Disabled |
| UX | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Recommended | ✅ Yes | ❌ No |

## Development Notes

### Adding New 2FA Methods

If Kitsu adds new 2FA methods in the future, update:

1. `zou_2fa_middleware.py`:
   ```python
   def _has_2fa_enabled(self, user):
       return (
           getattr(user, 'totp_enabled', False) or
           getattr(user, 'email_otp_enabled', False) or
           getattr(user, 'fido_enabled', False) or
           getattr(user, 'new_method_enabled', False)  # Add here
       )
   ```

2. `enforce_2fa.py`:
   ```python
   query = """
       SELECT ..., new_method_enabled  -- Add here
       FROM person
       ...
   ```

### Testing Changes

```bash
# Restart containers after modifying scripts
docker-compose restart zou-app

# Check logs
docker logs -f cgwire-zou-app

# Test with a user without 2FA
# (they should see the redirect page)
```

## License

Same as Kitsu-for-Docker (AGPL-3.0)

## Support

- Documentation: See ../2FA_ENFORCEMENT.md
- Quick Start: See ../QUICK_START_2FA.md
- GitHub Issues:
  - https://github.com/cgwire/zou/issues/998
  - https://github.com/EmberLightVFX/Kitsu-for-Docker/issues/10
