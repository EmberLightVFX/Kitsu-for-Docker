#!/bin/bash
# Periodic 2FA compliance check (for use in cron)

# This script can be run periodically to check 2FA compliance
# and optionally disable non-compliant users

# Exit if 2FA is not required
if [ "${REQUIRE_2FA}" != "True" ] && [ "${REQUIRE_2FA}" != "true" ] && [ "${REQUIRE_2FA}" != "1" ]; then
    exit 0
fi

# Log file
LOG_FILE="/tmp/zou/2fa_compliance_$(date +%Y%m%d_%H%M%S).log"

{
    echo "========================================="
    echo "2FA Compliance Check - $(date)"
    echo "========================================="
    echo ""

    # Run audit
    python3 /opt/zou/scripts/enforce_2fa.py --audit

    # If auto-enforce is enabled, enforce it
    if [ "${REQUIRE_2FA_AUTO_ENFORCE}" = "True" ] || [ "${REQUIRE_2FA_AUTO_ENFORCE}" = "true" ] || [ "${REQUIRE_2FA_AUTO_ENFORCE}" = "1" ]; then
        echo ""
        echo "Running enforcement..."
        echo "yes" | python3 /opt/zou/scripts/enforce_2fa.py --enforce
    fi

    echo ""
    echo "========================================="

} | tee -a "$LOG_FILE"

# Keep only last 30 days of logs
find /tmp/zou/ -name "2fa_compliance_*.log" -mtime +30 -delete 2>/dev/null || true
