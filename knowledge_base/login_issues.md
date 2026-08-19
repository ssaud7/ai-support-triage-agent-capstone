# Troubleshooting Login Issues

If a customer cannot log in, walk through these steps in order:

1. **Confirm the email address** — customers sometimes have multiple accounts under
   different email addresses (personal vs. work).
2. **Password reset** — send a password reset link. Links expire after 30 minutes.
3. **Check account status** — a "past due" or "suspended" account (see
   failed_payment_retry.md) will block login with a specific error banner rather than
   a generic "invalid credentials" message.
4. **Check for repeated failed attempts** — after 5 failed login attempts within 15
   minutes, the account is temporarily locked for 30 minutes as a security measure.
5. **Browser/cache issues** — ask the customer to try an incognito/private window or
   clear cookies for our domain, since stale session cookies are a common cause of
   silent login failures.

If none of the above resolves it, escalate to the technical team with the customer's
account email, approximate time of the failed attempt, and browser/device details.
