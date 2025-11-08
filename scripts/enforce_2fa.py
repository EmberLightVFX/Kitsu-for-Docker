#!/usr/bin/env python3
"""
Script to enforce 2FA for all users in Kitsu/Zou

This script can run in two modes:
1. Audit mode: Lists all users without 2FA enabled
2. Enforce mode: Disables users who don't have 2FA configured

Usage:
  python enforce_2fa.py --audit              # List users without 2FA
  python enforce_2fa.py --enforce            # Disable users without 2FA
  python enforce_2fa.py --enable-user EMAIL  # Re-enable a specific user

Environment Variables:
  DB_HOST: PostgreSQL host (default: localhost)
  DB_USER: PostgreSQL user (default: postgres)
  DB_PASSWORD: PostgreSQL password
  DB_DB: Database name (default: zoudb)
  2FA_EXEMPT_USERS: Comma-separated list of emails exempt from 2FA requirement
"""

import os
import sys
import argparse
import psycopg2
from datetime import datetime


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_DB', 'zoudb'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '')
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)


def get_exempt_users():
    """Get list of users exempt from 2FA requirement."""
    exempt_users_str = os.getenv('2FA_EXEMPT_USERS', '')
    if exempt_users_str:
        return [email.strip() for email in exempt_users_str.split(',')]
    return []


def audit_users():
    """List all users and their 2FA status."""
    conn = get_db_connection()
    cur = conn.cursor()

    exempt_users = get_exempt_users()

    try:
        # Query to get all active users and their 2FA status
        query = """
            SELECT
                id,
                email,
                first_name,
                last_name,
                totp_enabled,
                email_otp_enabled,
                fido_enabled,
                active,
                role
            FROM person
            WHERE email IS NOT NULL
            ORDER BY email;
        """

        cur.execute(query)
        users = cur.fetchall()

        users_without_2fa = []
        users_with_2fa = []
        inactive_users = []

        for user in users:
            user_id, email, first_name, last_name, totp, email_otp, fido, active, role = user
            has_2fa = totp or email_otp or fido
            is_exempt = email in exempt_users

            user_info = {
                'id': user_id,
                'email': email,
                'name': f"{first_name or ''} {last_name or ''}".strip(),
                'totp': totp,
                'email_otp': email_otp,
                'fido': fido,
                'active': active,
                'role': role,
                'exempt': is_exempt
            }

            if not active:
                inactive_users.append(user_info)
            elif has_2fa:
                users_with_2fa.append(user_info)
            else:
                users_without_2fa.append(user_info)

        # Print report
        print("=" * 80)
        print("2FA AUDIT REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        print(f"SUMMARY:")
        print(f"  Total users: {len(users)}")
        print(f"  Users with 2FA: {len(users_with_2fa)}")
        print(f"  Users without 2FA: {len(users_without_2fa)}")
        print(f"  Inactive users: {len(inactive_users)}")
        print(f"  Exempt users: {len([u for u in users if u[1] in exempt_users])}")
        print()

        if users_with_2fa:
            print("USERS WITH 2FA ENABLED:")
            print("-" * 80)
            for user in users_with_2fa:
                methods = []
                if user['totp']:
                    methods.append('TOTP')
                if user['email_otp']:
                    methods.append('Email OTP')
                if user['fido']:
                    methods.append('FIDO')

                exempt_marker = ' [EXEMPT]' if user['exempt'] else ''
                print(f"  ✓ {user['email']:<40} {', '.join(methods)}{exempt_marker}")
                print(f"    Name: {user['name']}, Role: {user['role']}")
            print()

        if users_without_2fa:
            print("USERS WITHOUT 2FA:")
            print("-" * 80)
            for user in users_without_2fa:
                exempt_marker = ' [EXEMPT]' if user['exempt'] else ''
                status = 'Active' if user['active'] else 'Inactive'
                print(f"  ✗ {user['email']:<40} {status}{exempt_marker}")
                print(f"    Name: {user['name']}, Role: {user['role']}")
            print()

        if inactive_users:
            print("INACTIVE USERS:")
            print("-" * 80)
            for user in inactive_users:
                has_2fa = user['totp'] or user['email_otp'] or user['fido']
                twofa_status = 'with 2FA' if has_2fa else 'without 2FA'
                exempt_marker = ' [EXEMPT]' if user['exempt'] else ''
                print(f"  - {user['email']:<40} {twofa_status}{exempt_marker}")
                print(f"    Name: {user['name']}, Role: {user['role']}")
            print()

        if exempt_users:
            print("CONFIGURED EXEMPT USERS:")
            print("-" * 80)
            for email in exempt_users:
                print(f"  • {email}")
            print()

        print("=" * 80)

        return len(users_without_2fa)

    except psycopg2.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        return -1
    finally:
        cur.close()
        conn.close()


def enforce_2fa():
    """Disable users who don't have 2FA configured."""
    conn = get_db_connection()
    cur = conn.cursor()

    exempt_users = get_exempt_users()

    try:
        # Find active users without 2FA
        query = """
            SELECT id, email, first_name, last_name, role
            FROM person
            WHERE active = TRUE
              AND totp_enabled = FALSE
              AND email_otp_enabled = FALSE
              AND fido_enabled = FALSE
              AND email IS NOT NULL;
        """

        cur.execute(query)
        users = cur.fetchall()

        if not users:
            print("All active users have 2FA enabled. No action needed.")
            return 0

        # Filter out exempt users
        users_to_disable = [u for u in users if u[1] not in exempt_users]

        if not users_to_disable:
            print("All users without 2FA are in the exempt list. No action needed.")
            return 0

        print("=" * 80)
        print("2FA ENFORCEMENT")
        print("=" * 80)
        print(f"Found {len(users_to_disable)} active user(s) without 2FA that will be disabled:")
        print()

        for user in users_to_disable:
            user_id, email, first_name, last_name, role = user
            name = f"{first_name or ''} {last_name or ''}".strip()
            print(f"  • {email} (Name: {name}, Role: {role})")

        print()
        print("These users will be disabled until they configure 2FA.")
        print("An administrator will need to re-enable them after they set up 2FA.")
        print()

        confirm = input("Do you want to proceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return 0

        # Disable users
        disabled_count = 0
        for user in users_to_disable:
            user_id, email = user[0], user[1]
            try:
                cur.execute(
                    "UPDATE person SET active = FALSE WHERE id = %s",
                    (user_id,)
                )
                disabled_count += 1
                print(f"  ✓ Disabled: {email}")
            except psycopg2.Error as e:
                print(f"  ✗ Failed to disable {email}: {e}", file=sys.stderr)

        conn.commit()

        print()
        print(f"Successfully disabled {disabled_count} user(s).")
        print()
        print("=" * 80)

        return disabled_count

    except psycopg2.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        conn.rollback()
        return -1
    finally:
        cur.close()
        conn.close()


def enable_user(email):
    """Re-enable a specific user."""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check if user exists
        cur.execute(
            "SELECT id, email, first_name, last_name, totp_enabled, email_otp_enabled, fido_enabled, active FROM person WHERE email = %s",
            (email,)
        )
        user = cur.fetchone()

        if not user:
            print(f"User not found: {email}", file=sys.stderr)
            return False

        user_id, email, first_name, last_name, totp, email_otp, fido, active = user
        name = f"{first_name or ''} {last_name or ''}".strip()
        has_2fa = totp or email_otp or fido

        print(f"User: {email}")
        print(f"Name: {name}")
        print(f"2FA Status: {'Enabled' if has_2fa else 'Not configured'}")
        print(f"Active: {'Yes' if active else 'No'}")
        print()

        if active:
            print("User is already active.")
            return True

        if not has_2fa:
            print("WARNING: This user does not have 2FA configured!")
            print("If REQUIRE_2FA enforcement is active, they may be disabled again.")
            confirm = input("Do you still want to enable this user? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Operation cancelled.")
                return False

        # Enable user
        cur.execute(
            "UPDATE person SET active = TRUE WHERE id = %s",
            (user_id,)
        )
        conn.commit()

        print(f"✓ User {email} has been enabled.")
        return True

    except psycopg2.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Enforce 2FA for Kitsu/Zou users',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--audit', action='store_true',
                      help='Audit users and show 2FA status')
    group.add_argument('--enforce', action='store_true',
                      help='Disable users without 2FA')
    group.add_argument('--enable-user', metavar='EMAIL',
                      help='Re-enable a specific user')

    args = parser.parse_args()

    if args.audit:
        result = audit_users()
        sys.exit(0 if result >= 0 else 1)
    elif args.enforce:
        result = enforce_2fa()
        sys.exit(0 if result >= 0 else 1)
    elif args.enable_user:
        result = enable_user(args.enable_user)
        sys.exit(0 if result else 1)


if __name__ == '__main__':
    main()
