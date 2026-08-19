# Failed Payment Retry Policy

When a scheduled payment fails (for example, due to insufficient funds or an expired
card), the system automatically retries the charge up to 3 times over 7 days:

1. First retry: 2 days after the initial failure
2. Second retry: 4 days after the initial failure
3. Third retry: 7 days after the initial failure

The customer's account remains fully active during this retry window. An email
notification is sent after each failed attempt explaining the reason for the failure
and providing a link to update payment details.

If all three retries fail, the account is downgraded to a read-only "past due" state.
Access is restored automatically within minutes of a successful payment.

Accounts that remain unpaid for more than 30 days are suspended and may be subject to
data deletion after 90 days, per our data retention policy.
