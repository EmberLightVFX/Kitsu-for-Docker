/**
 * Kitsu 2FA Enforcement - Client-side Modal
 *
 * This script runs after Kitsu loads and shows a blocking modal
 * if the user doesn't have 2FA configured.
 */

(function() {
    'use strict';

    console.log('[2FA Enforcer] Script loaded');

    let modalShown = false;
    let checkAttempts = 0;
    const MAX_ATTEMPTS = 50; // Try for ~5 seconds
    let lastKnownUserStatus = null; // Track user's 2FA status

    /**
     * Check if user is authenticated and has 2FA enabled
     */
    async function check2FAStatus() {
        try {
            // Get current user data from API
            const response = await fetch('/api/data/user/context', {
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                // User not authenticated yet
                return null;
            }

            const data = await response.json();
            console.log('[2FA Enforcer] User context:', data);

            // Extract user data from context
            const userData = data.user || data;

            // Check if any 2FA method is enabled
            const has2FA = userData.totp_enabled ||
                          userData.email_otp_enabled ||
                          userData.fido_enabled;

            return {
                email: userData.email,
                has2FA: has2FA,
                user: userData
            };

        } catch (error) {
            console.error('[2FA Enforcer] Error checking 2FA status:', error);
            return null;
        }
    }

    /**
     * Check if user is on a page where they can configure 2FA
     */
    function isOn2FAConfigPage() {
        const path = window.location.pathname;
        const hash = window.location.hash;

        // Check if on profile page or 2FA configuration pages
        const allowed2FAPages = [
            '/profile',
            '/settings',
            '/account',
            '#/profile',
            '#/settings',
            '#/account'
        ];

        return allowed2FAPages.some(page => path.includes(page) || hash.includes(page));
    }

    /**
     * Create and show the blocking modal
     */
    function showBlockingModal(userEmail) {
        if (modalShown) return;

        // Don't show modal if user is already on the 2FA config page
        if (isOn2FAConfigPage()) {
            console.log('[2FA Enforcer] User on 2FA config page, not showing modal');
            return;
        }

        modalShown = true;

        console.log('[2FA Enforcer] Showing blocking modal for:', userEmail);

        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = '2fa-enforcer-overlay';
        overlay.innerHTML = `
            <div class="2fa-enforcer-modal">
                <div class="2fa-enforcer-icon">🔐</div>
                <h1>Two-Factor Authentication Required</h1>
                <p class="2fa-enforcer-subtitle">Your account must have 2FA enabled to continue</p>

                <div class="2fa-enforcer-warning">
                    <strong>⚠️ Action Required</strong>
                    <p>For security reasons, all users must enable two-factor authentication before using Kitsu.</p>
                </div>

                <div class="2fa-enforcer-steps">
                    <h3>How to enable 2FA:</h3>
                    <ol>
                        <li>Click the button below to go to your profile</li>
                        <li>Navigate to the "Security" or "Authentication" section</li>
                        <li>Enable TOTP (recommended), Email OTP, or FIDO authentication</li>
                        <li>Complete the setup process</li>
                        <li>Refresh this page to continue</li>
                    </ol>
                </div>

                <button class="2fa-enforcer-button" onclick="window.location.href='/profile'">
                    Configure 2FA Now
                </button>

                <div class="2fa-enforcer-footer">
                    <p>Logged in as: <strong>${userEmail}</strong></p>
                    <a href="/api/auth/logout" class="2fa-enforcer-logout">Logout</a>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Prevent scrolling on the page behind
        document.body.style.overflow = 'hidden';

        // Prevent closing with ESC key
        document.addEventListener('keydown', preventEscape, true);

        // Try to disable all other interactions
        disablePageInteractions();
    }

    /**
     * Prevent ESC key from closing anything
     */
    function preventEscape(e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    }

    /**
     * Disable interactions with the page behind the modal
     */
    function disablePageInteractions() {
        // Add CSS to disable pointer events on the app
        const style = document.createElement('style');
        style.id = '2fa-enforcer-disable-style';
        style.textContent = `
            #app {
                pointer-events: none !important;
                filter: blur(5px) !important;
            }
            #2fa-enforcer-overlay {
                pointer-events: auto !important;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Main check function - runs periodically until user is authenticated
     */
    async function performCheck() {
        checkAttempts++;

        if (checkAttempts > MAX_ATTEMPTS) {
            console.log('[2FA Enforcer] Max attempts reached, stopping checks');
            return;
        }

        const status = await check2FAStatus();

        if (status === null) {
            // User not authenticated yet, check again
            setTimeout(performCheck, 200);
            return;
        }

        // Save user status
        lastKnownUserStatus = status;

        if (!status.has2FA) {
            // User authenticated but no 2FA - show modal
            showBlockingModal(status.email);
        } else {
            console.log('[2FA Enforcer] User has 2FA enabled, no action needed');
        }
    }

    // Inject CSS styles
    const styles = document.createElement('style');
    styles.textContent = `
        #2fa-enforcer-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(10px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 999999;
            animation: fadeIn 0.3s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .2fa-enforcer-modal {
            background: white;
            padding: 3rem;
            border-radius: 1rem;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            max-width: 600px;
            width: 90%;
            text-align: center;
            animation: slideIn 0.4s ease-out;
        }

        @keyframes slideIn {
            from {
                transform: translateY(-50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        .2fa-enforcer-icon {
            font-size: 5rem;
            margin-bottom: 1rem;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }

        .2fa-enforcer-modal h1 {
            color: #333;
            margin-bottom: 0.5rem;
            font-size: 2rem;
            font-weight: 700;
        }

        .2fa-enforcer-subtitle {
            color: #666;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }

        .2fa-enforcer-warning {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 0.5rem;
            padding: 1.5rem;
            margin-bottom: 2rem;
            text-align: left;
        }

        .2fa-enforcer-warning strong {
            display: block;
            color: #856404;
            margin-bottom: 0.5rem;
            font-size: 1.1rem;
        }

        .2fa-enforcer-warning p {
            color: #856404;
            margin: 0;
            line-height: 1.5;
        }

        .2fa-enforcer-steps {
            text-align: left;
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin-bottom: 2rem;
        }

        .2fa-enforcer-steps h3 {
            color: #333;
            margin-top: 0;
            margin-bottom: 1rem;
            font-size: 1.2rem;
        }

        .2fa-enforcer-steps ol {
            margin: 0;
            padding-left: 1.5rem;
        }

        .2fa-enforcer-steps li {
            margin: 0.75rem 0;
            color: #555;
            line-height: 1.6;
        }

        .2fa-enforcer-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 1rem 3rem;
            font-size: 1.1rem;
            font-weight: 600;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }

        .2fa-enforcer-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }

        .2fa-enforcer-button:active {
            transform: translateY(0);
        }

        .2fa-enforcer-footer {
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px solid #e0e0e0;
            color: #666;
            font-size: 0.9rem;
        }

        .2fa-enforcer-footer p {
            margin: 0.5rem 0;
        }

        .2fa-enforcer-logout {
            color: #dc3545;
            text-decoration: none;
            font-weight: 500;
        }

        .2fa-enforcer-logout:hover {
            text-decoration: underline;
        }
    `;
    document.head.appendChild(styles);

    /**
     * Remove the modal if user navigates to 2FA config page
     */
    function removeModalIfOn2FAPage() {
        if (modalShown && isOn2FAConfigPage()) {
            console.log('[2FA Enforcer] User navigated to 2FA config page, removing modal');
            const overlay = document.getElementById('2fa-enforcer-overlay');
            const disableStyle = document.getElementById('2fa-enforcer-disable-style');

            if (overlay) {
                overlay.remove();
            }
            if (disableStyle) {
                disableStyle.remove();
            }

            // Re-enable scrolling
            document.body.style.overflow = '';
            document.removeEventListener('keydown', preventEscape, true);

            modalShown = false;
        }
    }

    /**
     * Check if user left 2FA config page without configuring 2FA
     */
    async function checkIfLeftConfigPage(lastUserStatus) {
        // If modal is not shown and user is not on config page anymore
        if (!modalShown && lastUserStatus && !lastUserStatus.has2FA && !isOn2FAConfigPage()) {
            console.log('[2FA Enforcer] User left config page, re-checking 2FA status...');

            // ALWAYS re-check 2FA status from API (user may have just configured it)
            const status = await check2FAStatus();

            if (status) {
                // Update last known status
                lastKnownUserStatus = status;

                if (!status.has2FA) {
                    // Still no 2FA, show modal again
                    console.log('[2FA Enforcer] User still has no 2FA, showing modal');
                    showBlockingModal(status.email);
                } else {
                    // User has configured 2FA!
                    console.log('[2FA Enforcer] ✓ User has configured 2FA, no modal needed');
                }
            }
        }
    }

    // Monitor URL changes (for SPA navigation)
    let lastUrl = location.href;
    new MutationObserver(() => {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            removeModalIfOn2FAPage();
            // Check if user left config page without enabling 2FA
            checkIfLeftConfigPage(lastKnownUserStatus);
        }
    }).observe(document, {subtree: true, childList: true});

    // Also check on hash change
    window.addEventListener('hashchange', () => {
        removeModalIfOn2FAPage();
        checkIfLeftConfigPage(lastKnownUserStatus);
    });

    // Start checking after a small delay to let the app initialize
    setTimeout(() => {
        console.log('[2FA Enforcer] Starting authentication check...');
        performCheck();
    }, 500);

})();
