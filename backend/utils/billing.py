from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

# Keep the structure, but we'll ignore it in logic
SUBSCRIPTION_TIERS = {
    'price_1RGJ9GG6l1KZGqIroxSqgphC': {'name': 'free', 'minutes': 10},
    'price_1RGJ9LG6l1KZGqIrd9pwzeNW': {'name': 'base', 'minutes': 300},
    'price_1RGJ9JG6l1KZGqIrVUU4ZRv6': {'name': 'extra', 'minutes': 2400},
}

UNLIMITED_SUBSCRIPTION = {
    'price_id': 'UNLIMITED',
    'plan_name': 'Unlimited',
    'status': 'active'
}

async def get_account_subscription(client, account_id: str) -> Optional[Dict]:
    """
    Return a synthetic Unlimited subscription for everyone.
    If you ever want to re-enable real billing, replace this with the original DB query.
    """
    return UNLIMITED_SUBSCRIPTION

async def calculate_monthly_usage(client, account_id: str) -> float:
    """
    Billing disabled: always report zero usage.
    """
    return 0.0

async def check_billing_status(client, account_id: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Billing disabled: always allow runs.
    """
    subscription = await get_account_subscription(client, account_id)
    # Always green-light
    return True, "OK", subscription

# Helper function to get account ID from thread (unchanged)
async def get_account_id_from_thread(client, thread_id: str) -> Optional[str]:
    result = await client.table('threads') \
        .select('account_id') \
        .eq('thread_id', thread_id) \
        .limit(1) \
        .execute()
    if result.data and len(result.data) > 0:
        return result.data[0]['account_id']
    return None
