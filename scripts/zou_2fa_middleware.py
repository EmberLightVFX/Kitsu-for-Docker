#!/usr/bin/env python3
"""
Flask middleware to enforce 2FA for Zou/Kitsu

This middleware intercepts all requests and redirects users without 2FA
to the profile page where they must configure it before continuing.

It's injected into the Zou Flask application at startup.
"""

import os
from flask import request, redirect, jsonify, make_response
from functools import wraps


class Enforce2FAMiddleware:
    """
    Middleware that enforces 2FA requirement for all authenticated users.

    When REQUIRE_2FA is enabled, this middleware:
    1. Checks if the user is authenticated
    2. Verifies if they have 2FA configured
    3. If not, redirects them to the profile page
    4. Shows a clear message about the requirement
    """

    def __init__(self, app):
        self.app = app
        self.require_2fa = os.getenv('REQUIRE_2FA', 'False').lower() in ['true', '1', 'yes']
        self.exempt_users = self._get_exempt_users()

        if self.require_2fa:
            print("=" * 80)
            print("2FA ENFORCEMENT MIDDLEWARE ENABLED")
            print("=" * 80)
            print(f"Exempt users: {', '.join(self.exempt_users) if self.exempt_users else 'None'}")
            print("Users without 2FA will be redirected to configure it.")
            print("=" * 80)

            # Register before_request handler
            self.app.before_request(self.check_2fa_requirement)

    def _get_exempt_users(self):
        """Get list of users exempt from 2FA requirement."""
        exempt_users_str = os.getenv('2FA_EXEMPT_USERS', '')
        if exempt_users_str:
            return [email.strip().lower() for email in exempt_users_str.split(',')]
        return []

    def _is_exempt_user(self, email):
        """Check if a user is exempt from 2FA requirement."""
        if not email:
            return False
        return email.lower() in self.exempt_users

    def _has_2fa_enabled(self, user):
        """Check if user has any 2FA method enabled."""
        if not user:
            return False

        return (
            getattr(user, 'totp_enabled', False) or
            getattr(user, 'email_otp_enabled', False) or
            getattr(user, 'fido_enabled', False)
        )

    def _is_allowed_route(self, path):
        """
        Check if the route is allowed even without 2FA.

        Allowed routes:
        - Login/logout endpoints
        - Static files (CSS, JS, images)
        - 2FA setup API endpoints (very specific)
        - Health check endpoints
        - Config endpoint
        """
        # Normalize path
        normalized = path.lstrip('/')

        allowed_patterns = [
            # Auth endpoints (with and without api/ prefix due to nginx proxy)
            'api/auth/login',
            'auth/login',
            'api/auth/logout',
            'auth/logout',
            'api/auth/authenticated',
            'auth/authenticated',
            'api/auth/register',
            'auth/register',
            # 2FA configuration endpoints (CRITICAL - allow users to configure 2FA)
            'api/auth/totp',
            'auth/totp',
            'api/auth/fido',
            'auth/fido',
            'api/auth/email-otp',
            'auth/email-otp',
            'api/auth/recovery-codes',
            'auth/recovery-codes',
            'static/',
            'config',  # App config
            '_health',
            'health',
            # Legacy 2FA endpoints (if they exist)
            'api/actions/persons/enable-totp',
            'actions/persons/enable-totp',
            'api/actions/persons/disable-totp',
            'actions/persons/disable-totp',
            'api/actions/persons/enable-email-otp',
            'actions/persons/enable-email-otp',
            'api/actions/persons/disable-email-otp',
            'actions/persons/disable-email-otp',
            'api/actions/persons/register-fido-device',
            'actions/persons/register-fido-device',
            'api/actions/persons/unregister-fido-device',
            'actions/persons/unregister-fido-device',
            'api/actions/persons/generate-recovery-codes',
            'actions/persons/generate-recovery-codes',
        ]

        # For client-side 2FA enforcement:
        # Allow ALL read operations (GET) so the app can load
        # Block write operations (POST/PUT/DELETE) until 2FA is configured
        # The actual enforcement happens via injected JavaScript modal

        # Allow all GET requests to /data/* and /api/data/* endpoints
        if request.method == 'GET':
            if normalized.startswith('data/') or normalized.startswith('api/data/'):
                return True

        # Check if path starts with any allowed pattern
        for pattern in allowed_patterns:
            if normalized.startswith(pattern):
                return True

        # Allow OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return True

        return False

    def check_2fa_requirement(self):
        """
        Before request handler that checks 2FA requirement.

        This runs before every request to the application.
        """
        # Skip if 2FA is not required
        if not self.require_2fa:
            return None

        # Clean the path (remove leading slashes)
        clean_path = request.path.lstrip('/')

        # Skip if this is an allowed route
        if self._is_allowed_route(clean_path):
            return None

        # DEBUG: Log when we're about to check 2FA
        print(f"[2FA DEBUG] Checking 2FA for path: {clean_path}, method: {request.method}", flush=True)

        try:
            # Try to get current user from Flask-Login or JWT
            from flask_login import current_user

            # If user is not authenticated, let them proceed to login
            if not current_user or not current_user.is_authenticated:
                return None

            # Check if user is exempt
            user_email = getattr(current_user, 'email', None)

            if self._is_exempt_user(user_email):
                return None

            # Check if user has 2FA enabled
            has_2fa = self._has_2fa_enabled(current_user)

            if not has_2fa:
                # User doesn't have 2FA
                # For client-side enforcement: allow GET requests (read-only)
                # Block POST/PUT/DELETE (write operations)
                if request.method == 'GET':
                    # Allow GET - JavaScript modal will handle UI blocking
                    return None

                # Block write operations
                print(f"[2FA] BLOCKING {request.method} from user {user_email} - 2FA required", flush=True)
                return self._handle_2fa_required(user_email)

        except ImportError:
            # If Flask-Login is not available, try to get user from JWT
            try:
                from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
                from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError
                from zou.app.services import persons_service

                # Try to get user from JWT token
                try:
                    # Verify and get JWT identity (user ID)
                    try:
                        verify_jwt_in_request(optional=True)
                    except (NoAuthorizationError, InvalidHeaderError):
                        # No valid JWT token, user not authenticated
                        return None

                    user_id = get_jwt_identity()
                    print(f"[2FA DEBUG] JWT user_id: {user_id}", flush=True)

                    if user_id:
                        user = persons_service.get_person(user_id)
                        if user:
                            user_email = user.get('email')

                            # Check if user is exempt
                            if self._is_exempt_user(user_email):
                                return None

                            # Check if user has 2FA
                            has_2fa = (
                                user.get('totp_enabled', False) or
                                user.get('email_otp_enabled', False) or
                                user.get('fido_enabled', False)
                            )

                            if not has_2fa:
                                # User doesn't have 2FA
                                # For client-side enforcement: allow GET requests (read-only)
                                # Block POST/PUT/DELETE (write operations)
                                if request.method == 'GET':
                                    # Allow GET - JavaScript modal will handle UI blocking
                                    return None

                                # Block write operations
                                print(f"[2FA] BLOCKING {request.method} from user {user_email} - 2FA required", flush=True)
                                return self._handle_2fa_required(user_email)
                except Exception:
                    # If we can't get user from JWT, allow the request
                    # (it will fail at the auth layer if needed)
                    pass
            except ImportError:
                pass

        except Exception as e:
            # Log error but don't block the request
            print(f"[2FA ERROR] Exception in 2FA middleware: {e}", flush=True)

        return None

    def _handle_2fa_required(self, user_email):
        """
        Handle the case where user needs to configure 2FA.

        For web requests: Return HTML with message and redirect
        For API requests: Return JSON error
        """
        message = (
            "Two-Factor Authentication is required for your account. "
            "Please configure 2FA in your profile settings before continuing."
        )

        # Check if this is an API request
        # Note: nginx strips /api/ prefix, so check path patterns and headers
        is_api_request = (
            request.path.startswith('/api/') or
            request.path.startswith('/data/') or
            request.path.startswith('/actions/') or
            request.is_json or
            request.headers.get('Accept', '').startswith('application/json') or
            'XMLHttpRequest' in request.headers.get('X-Requested-With', '')
        )

        if is_api_request:
            # Return JSON response for API requests
            response = jsonify({
                'error': True,
                'message': message,
                '2fa_required': True,
                'redirect_to': '/profile',
                'user_email': user_email
            })
            response.status_code = 403
            return response

        # For web requests, return HTML with auto-redirect
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>2FA Required</title>
            <meta http-equiv="refresh" content="0;url=/profile" />
            <script>
                // Try to redirect via JavaScript as well for SPAs
                setTimeout(function() {{
                    window.location.href = '/profile';
                }}, 100);
            </script>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 3rem;
                    border-radius: 1rem;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 500px;
                    text-align: center;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 1rem;
                    font-size: 2rem;
                }}
                .icon {{
                    font-size: 4rem;
                    margin-bottom: 1rem;
                }}
                p {{
                    color: #666;
                    line-height: 1.6;
                    margin-bottom: 1.5rem;
                }}
                .steps {{
                    text-align: left;
                    background: #f7f7f7;
                    padding: 1.5rem;
                    border-radius: 0.5rem;
                    margin: 1.5rem 0;
                }}
                .steps ol {{
                    margin: 0;
                    padding-left: 1.5rem;
                }}
                .steps li {{
                    margin: 0.5rem 0;
                    color: #444;
                }}
                .button {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 0.75rem 2rem;
                    border-radius: 0.5rem;
                    text-decoration: none;
                    font-weight: 600;
                    transition: background 0.3s;
                }}
                .button:hover {{
                    background: #5568d3;
                }}
                .warning {{
                    background: #fff3cd;
                    border: 1px solid #ffc107;
                    color: #856404;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    margin: 1rem 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">🔐</div>
                <h1>Two-Factor Authentication Required</h1>

                <div class="warning">
                    <strong>Action Required:</strong> Your organization requires all users to enable 2FA.
                </div>

                <p>For security reasons, you must configure two-factor authentication before you can access Kitsu.</p>

                <div class="steps">
                    <strong>How to enable 2FA:</strong>
                    <ol>
                        <li>Click on your avatar in the top-right corner</li>
                        <li>Select <strong>Profile</strong></li>
                        <li>Scroll to <strong>Two-Factor Authentication</strong></li>
                        <li>Choose your preferred method:
                            <ul>
                                <li><strong>TOTP</strong> - Use an authenticator app</li>
                                <li><strong>Email OTP</strong> - Receive codes via email</li>
                                <li><strong>FIDO</strong> - Use a hardware security key</li>
                            </ul>
                        </li>
                        <li>Complete the setup process</li>
                    </ol>
                </div>

                <a href="/" class="button">Go to Kitsu</a>

                <p style="margin-top: 2rem; font-size: 0.9rem; color: #999;">
                    You will be redirected automatically in 3 seconds...
                </p>
            </div>
        </body>
        </html>
        """

        response = make_response(html_response)
        response.status_code = 403
        return response


def init_2fa_middleware(app):
    """
    Initialize the 2FA enforcement middleware.

    This should be called after the Flask app is created but before
    it starts handling requests.

    Args:
        app: Flask application instance

    Returns:
        The middleware instance
    """
    middleware = Enforce2FAMiddleware(app)
    return middleware


# Auto-initialize if this module is imported
def auto_init():
    """
    Automatically initialize the middleware when Zou starts.

    This function tries to hook into the Zou app at startup.
    """
    try:
        from zou.app import app as zou_app
        init_2fa_middleware(zou_app.app)
        print("✓ 2FA enforcement middleware successfully initialized")
    except Exception as e:
        print(f"! Could not auto-initialize 2FA middleware: {e}")
        print("  Middleware will be initialized manually at startup")
