# Understanding Order Status

Every order moves through the following statuses in order:

- **pending** — order received, payment not yet confirmed (usually resolves within
  minutes)
- **processing** — payment confirmed, order is being prepared/fulfilled
- **shipped** — order has left the warehouse; a tracking number is attached at this
  point
- **delivered** — carrier has confirmed delivery
- **cancelled** — order was cancelled either by the customer or automatically due to
  payment failure
- **refunded** — a refund has been issued for this order (see refund policies for
  eligibility)

An order can only move forward through these statuses, except for cancellation or
refund, which can happen from most states. If an order has been stuck in "processing"
for more than 3 business days, this indicates a fulfillment error and should be
escalated to the technical team rather than treated as a normal delay.

Customers can look up their order status at any time using their order ID from the
confirmation email.
