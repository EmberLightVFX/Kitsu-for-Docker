#!/usr/bin/env python3
"""
Zou Application Wrapper with 2FA Enforcement

This wrapper loads the Zou application and injects the 2FA enforcement middleware.
It's used as the WSGI application entry point for Gunicorn.

Usage:
    gunicorn -w 3 -k gevent -b :5000 zou_app_wrapper:app
"""

import sys
import os

# Ensure the scripts directory is in the Python path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# Import the original Zou app
from zou.app import app as zou_app

# Get the Flask app instance
app = zou_app.app

# Inject 2FA middleware if enabled
require_2fa = os.getenv('REQUIRE_2FA', 'False').lower() in ['true', '1', 'yes']

if require_2fa:
    print("")
    print("=" * 80)
    print("INITIALIZING 2FA ENFORCEMENT MIDDLEWARE")
    print("=" * 80)

    try:
        from zou_2fa_middleware import init_2fa_middleware

        # Initialize the middleware
        middleware = init_2fa_middleware(app)

        print("✓ 2FA enforcement middleware successfully loaded")
        print("  Users without 2FA will be prompted to configure it")
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
__all__ = ['app']
