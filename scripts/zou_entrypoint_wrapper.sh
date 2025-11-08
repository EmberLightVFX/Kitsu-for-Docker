#!/bin/bash
# Wrapper entrypoint for Zou that includes 2FA enforcement

set -e

echo "========================================="
echo "Zou starting with 2FA enforcement support"
echo "========================================="

# Install dependencies if needed
if [ -f /opt/zou/scripts/install_dependencies.sh ]; then
    bash /opt/zou/scripts/install_dependencies.sh
fi

# Run the original init and upgrade scripts
/init_zou.sh
/upgrade_zou.sh

# Check 2FA requirements if enabled
if [ -f /opt/zou/scripts/check_2fa_on_startup.sh ]; then
    bash /opt/zou/scripts/check_2fa_on_startup.sh
fi

# Add scripts directory to PYTHONPATH so the wrapper can import the middleware
export PYTHONPATH="/opt/zou/scripts:$PYTHONPATH"

# Execute the command, but replace zou.app:app with our wrapper
# This intercepts the gunicorn command to use our wrapped app
if [[ "$*" == *"zou.app:app"* ]]; then
    # Replace zou.app:app with zou_app_wrapper:app
    MODIFIED_CMD="${@//zou.app:app/zou_app_wrapper:app}"
    echo "Starting Zou with 2FA middleware..."
    echo "Command: $MODIFIED_CMD"
    exec $MODIFIED_CMD
else
    # If it's not the main app command, execute as-is
    exec "$@"
fi
