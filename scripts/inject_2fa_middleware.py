#!/usr/bin/env python3
"""
Script to inject 2FA middleware into Zou app before starting Gunicorn.
This is called from the docker-compose command.
"""

import sys
import os

# Add scripts directory to path
sys.path.insert(0, '/opt/zou/scripts')
sys.path.insert(0, '/opt/zou')

# Import Zou app
from zou.app import app as zou_app

# Check if 2FA is required
require_2fa = os.getenv('REQUIRE_2FA', 'False').lower() in ['true', '1', 'yes']

if require_2fa:
    print("")
    print("=" * 80)
    print("INITIALIZING 2FA ENFORCEMENT MIDDLEWARE")
    print("=" * 80)

    try:
        # Import the middleware class
        from zou_2fa_middleware import Enforce2FAMiddleware

        # Create an instance
        middleware = Enforce2FAMiddleware(zou_app)

        # Explicitly register the before_request handler
        zou_app.before_request(middleware.check_2fa_requirement)

        print("✓ 2FA enforcement middleware successfully registered")
        print(f"  Exempt users: {', '.join(middleware.exempt_users) if middleware.exempt_users else 'None'}")
        print("  Users without 2FA will be prompted to configure it")
        print("  before_request handler registered")
        print("=" * 80)
        print("")

    except Exception as e:
        print(f"✗ Error loading 2FA middleware: {e}")
        print("  Zou will start without 2FA enforcement")
        print("=" * 80)
        print("")
        import traceback
        traceback.print_exc()
else:
    print("")
    print("=" * 80)
    print("2FA enforcement is disabled")
    print("To enable, set REQUIRE_2FA=True in your .env file")
    print("=" * 80)
    print("")

# Export the app for Gunicorn
app = zou_app
