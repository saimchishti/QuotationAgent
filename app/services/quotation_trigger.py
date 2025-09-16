# app/services/quotation_trigger.py
import time
from datetime import datetime, timezone
from app.db.session import get_collection

CHECK_INTERVAL = 5  # seconds


class QuotationTrigger:
    def __init__(self):
        self.collection = get_collection("order_drafts")

    def fetch_new_drafts(self):
        """Fetch order drafts with status=draft"""
        cursor = self.collection.find({"status": "draft"})
        return list(cursor)

    def mark_in_progress(self, draft_id):
        self.collection.update_one(
            {"_id": draft_id},
            {"$set": {"status": "in_progress", "picked_at": datetime.now(timezone.utc)}},
        )

    def watch_loop(self, handler):
        """Poll in a loop (sync version)"""
        while True:
            drafts = self.fetch_new_drafts()
            for draft in drafts:
                print(f"🔔 Found draft order: {draft['_id']}")
                self.mark_in_progress(draft["_id"])
                handler(draft)
            time.sleep(CHECK_INTERVAL)


# Example handler
def print_handler(order):
    print("📋 Draft Order Details:")
    print(f"  Customer ID: {order.get('customer_id')}")
    print(f"  Phone: {order.get('phone_number')}")
    print(f"  Items: {order.get('items')}")
    print(f"  Notes: {order.get('notes')}")
    print(f"  Status: {order.get('status')}")


if __name__ == "__main__":
    trigger = QuotationTrigger()
    trigger.watch_loop(print_handler)
