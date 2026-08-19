"""Mock data structures for the customer support triage agent.

These stand in for a real orders/CRM database. Tools in the notebook read from
these structures instead of returning hardcoded strings.
"""

from datetime import date

CUSTOMERS = {
    "cust_1001": {
        "customer_id": "cust_1001",
        "name": "Maria Chen",
        "email": "maria.chen@example.com",
        "plan": "Pro (monthly)",
        "signup_date": "2024-02-14",
        "dispute_count": 2,
        "enterprise": False,
    },
    "cust_1002": {
        "customer_id": "cust_1002",
        "name": "Devon Walker",
        "email": "devon.walker@example.com",
        "plan": "Starter (monthly)",
        "signup_date": "2025-06-01",
        "dispute_count": 0,
        "enterprise": False,
    },
    "cust_1003": {
        "customer_id": "cust_1003",
        "name": "Priya Natarajan",
        "email": "priya.n@example.com",
        "plan": "Enterprise (annual)",
        "signup_date": "2022-09-30",
        "dispute_count": 0,
        "enterprise": True,
    },
    "cust_1004": {
        "customer_id": "cust_1004",
        "name": "Jonas Berg",
        "email": "jonas.berg@example.com",
        "plan": "Pro (annual)",
        "signup_date": "2023-11-05",
        "dispute_count": 1,
        "enterprise": False,
    },
}

ORDERS = {
    "ord_5001": {
        "order_id": "ord_5001",
        "customer_id": "cust_1001",
        "product": "Pro Plan - Monthly Renewal",
        "amount_usd": 49.00,
        "status": "delivered",
        "order_date": "2026-07-19",
    },
    "ord_5002": {
        "order_id": "ord_5002",
        "customer_id": "cust_1001",
        "product": "Pro Plan - Monthly Renewal",
        "amount_usd": 49.00,
        "status": "delivered",
        "order_date": "2026-08-19",
    },
    "ord_5003": {
        "order_id": "ord_5003",
        "customer_id": "cust_1002",
        "product": "Starter Plan - Monthly Renewal",
        "amount_usd": 15.00,
        "status": "processing",
        "order_date": "2026-08-17",
    },
    "ord_5004": {
        "order_id": "ord_5004",
        "customer_id": "cust_1003",
        "product": "Enterprise Plan - Annual Renewal",
        "amount_usd": 4800.00,
        "status": "delivered",
        "order_date": "2026-01-10",
    },
    "ord_5005": {
        "order_id": "ord_5005",
        "customer_id": "cust_1004",
        "product": "Pro Plan - Annual Renewal",
        "amount_usd": 499.00,
        "status": "cancelled",
        "order_date": "2026-05-22",
    },
}


def get_customer(customer_id: str) -> dict | None:
    return CUSTOMERS.get(customer_id)


def get_order(order_id: str) -> dict | None:
    return ORDERS.get(order_id)


def today() -> date:
    return date(2026, 8, 19)
