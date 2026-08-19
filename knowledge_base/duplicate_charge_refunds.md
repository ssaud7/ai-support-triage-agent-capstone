# Duplicate Charge Refunds

Duplicate charges happen occasionally when a payment retry overlaps with a manual
payment, or when a customer submits a card update form twice. These are treated as
billing errors, not standard refund requests.

If two identical charges appear on a customer's account within a 24-hour window for
the same subscription, the second charge should be refunded in full automatically,
with no eligibility window restriction — the standard 30-day rule does not apply to
confirmed duplicate charges.

Before refunding, confirm the duplicate by checking that both charges share the same
amount, same payment method, and occurred within 24 hours of each other. If the
charges are for different amounts or different products, treat it as a standard
refund or billing dispute instead.

Duplicate charge refunds under $100 do not require supervisor approval, since the
error is unambiguous and confirmed programmatically.
