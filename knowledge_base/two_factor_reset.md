# Resetting Two-Factor Authentication (2FA)

If a customer is locked out because they lost access to their 2FA device (lost phone,
uninstalled authenticator app, etc.), follow this process:

1. Verify the customer's identity using two of the following: full name on account,
   billing zip code, last 4 digits of the payment method on file, or the answer to
   their account security question.
2. Once verified, send a 2FA reset link to the email address on file. This link is
   valid for 1 hour only.
3. The customer must set up 2FA again from scratch after using the reset link — their
   old authenticator codes will no longer work.

2FA cannot be disabled permanently for accounts on the Enterprise plan, since it is
required by their organization's security policy. For these accounts, only an org
admin can perform a 2FA reset for a member, not support staff directly.

Never reset 2FA based on identity claims made only in a chat message with no
verification — this is a common social engineering vector.
