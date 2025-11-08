#!/bin/bash
# Check and enforce 2FA requirements on startup

echo "========================================="
echo "Kitsu 2FA Enforcement Checker"
echo "========================================="

# Check if 2FA enforcement is enabled
if [ "${REQUIRE_2FA}" = "True" ] || [ "${REQUIRE_2FA}" = "true" ] || [ "${REQUIRE_2FA}" = "1" ]; then
    echo "REQUIRE_2FA is enabled"
    echo ""
    echo "2FA Enforcement Mode: REDIRECT (users will be forced to configure 2FA)"
    echo ""

    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    max_attempts=30
    attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_DB}" -c "SELECT 1" > /dev/null 2>&1; then
            echo "Database is ready!"
            break
        fi
        attempt=$((attempt + 1))
        echo "Attempt $attempt/$max_attempts - Database not ready yet..."
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        echo "ERROR: Database did not become ready in time"
        exit 1
    fi

    echo ""
    echo "Running 2FA compliance audit..."
    echo ""

    # Run the 2FA audit script
    python3 /opt/zou/scripts/enforce_2fa.py --audit

    echo ""
    echo "How 2FA enforcement works:"
    echo "  - Users WITHOUT 2FA will be redirected to configure it upon login"
    echo "  - They cannot use Kitsu until 2FA is configured"
    echo "  - Users will NOT be disabled, just redirected"
    echo ""

    # Optionally disable users (NOT RECOMMENDED - kept for backwards compatibility)
    if [ "${REQUIRE_2FA_DISABLE_USERS}" = "True" ] || [ "${REQUIRE_2FA_DISABLE_USERS}" = "true" ] || [ "${REQUIRE_2FA_DISABLE_USERS}" = "1" ]; then
        echo ""
        echo "⚠️  WARNING: REQUIRE_2FA_DISABLE_USERS is enabled"
        echo "    This will DISABLE user accounts without 2FA"
        echo "    This is NOT recommended - use the redirect method instead"
        echo ""

        # Run enforcement in non-interactive mode by piping 'yes' to it
        echo "yes" | python3 /opt/zou/scripts/enforce_2fa.py --enforce
    fi
else
    echo "REQUIRE_2FA is not enabled"
    echo "To enable 2FA enforcement, add to your .env file:"
    echo "  REQUIRE_2FA=True"
    echo "  2FA_EXEMPT_USERS=service@example.com,api@example.com  # (optional) exempt users"
    echo ""
    echo "When enabled, users without 2FA will be redirected to configure it."
fi

echo ""
echo "========================================="
echo ""
