"""Rule-based intent layer for the /api/chat assistant (level 1).

Each rule pairs trigger keywords with a handler that reads live data and
returns a natural-language answer. Handlers take the db as an argument so
the module stays independent of the Flask app. A model layer (level 2)
will sit behind these rules once a rule misses.
"""
import re

FALLBACK = ("I can help with stock levels and low-stock alerts. "
            "Try asking what's running low or how much of an item is in stock.")

def _find_named_item(items, text):
    """Match an item by full name, then by a name word (allowing plural/prefix)."""
    for item in items:
        if item["item_name"].lower() in text:
            return item
    words = [w for w in re.findall(r"[a-z0-9]+", text) if len(w) >= 3]
    for item in items:
        name_words = [w for w in re.findall(r"[a-z0-9]+", item["item_name"].lower()) if len(w) >= 3]
        for name_word in name_words:
            if any(w == name_word or w.startswith(name_word) or name_word.startswith(w) for w in words):
                return item
    return None

def _intent_low_stock(db, message):
    """Report every item at or below its configured threshold."""
    items = list(db.inventory_items.find(
        {"minimum_threshold": {"$ne": None}}, {"_id": 0}
    ))
    low = [
        item for item in items
        if item.get("quantity") is not None
        and item["quantity"] <= item["minimum_threshold"]
    ]
    if not low:
        return "Everything is above its minimum threshold right now."
    names = ", ".join(item["item_name"] for item in low)
    return f"{len(low)} item(s) at or below threshold: {names}."

def _intent_item_quantity(db, message):
    """Report the current quantity of an item named in the message."""
    item = _find_named_item(list(db.inventory_items.find({}, {"_id": 0})), message)
    if item:
        return f"{item['item_name']}: {item['quantity']} in stock."
    return None

def _intent_expiring_soon(db, message):
    """List the items with the nearest expiry dates."""
    items = list(db.inventory_items.find({"expiry_date": {"$ne": None}}, {"_id": 0}))
    dated = [item for item in items if item.get("expiry_date")]
    if not dated:
        return "No items have an expiry date set."
    dated.sort(key=lambda item: item["expiry_date"])
    parts = []
    for item in dated[:5]:
        when = item["expiry_date"]
        when = when.date().isoformat() if hasattr(when, "date") else str(when)
        parts.append(f"{item['item_name']} ({when})")
    return f"Expiring soonest: {', '.join(parts)}."

def _intent_cheapest_supplier(db, message):
    """Find the lowest-priced supplier for an item named in the message."""
    item = _find_named_item(list(db.inventory_items.find({}, {"_id": 0})), message)
    if not item:
        return None
    prices = list(db.supplier_prices.find({"item_id": item["item_id"]}, {"_id": 0}))
    if not prices:
        return f"No supplier prices recorded for {item['item_name']} yet."
    best = min(prices, key=lambda price: price["price"])
    supplier = db.suppliers.find_one({"supplier_id": best["supplier_id"]}, {"_id": 0})
    name = supplier["supplier_name"] if supplier else "Unknown Supplier"
    return f"Cheapest {item['item_name']}: {name} at ${best['price']}."

def _intent_supplier_list(db, message):
    """List every registered supplier."""
    suppliers = list(db.suppliers.find({}, {"_id": 0, "supplier_name": 1}))
    if not suppliers:
        return "No suppliers are registered yet."
    names = ", ".join(supplier["supplier_name"] for supplier in suppliers)
    return f"Suppliers: {names}."

def _intent_waste_report(db, message):
    """Report the total recorded waste across the historical data."""
    records = list(db.historical_data.find({}, {"_id": 0, "quantity_wasted": 1}))
    total = sum(record.get("quantity_wasted", 0) or 0 for record in records)
    return f"Total recorded waste is {round(total, 2)} units across {len(records)} record(s)."

def _intent_items_by_category(db, message):
    """List the items belonging to a category named in the message."""
    for category in db.inventory_items.distinct("category"):
        if category and category.lower() in message:
            items = list(db.inventory_items.find({"category": category}, {"_id": 0, "item_name": 1}))
            names = ", ".join(item["item_name"] for item in items)
            return f"{category}: {names}."
    return None

def _intent_list_categories(db, message):
    """List the distinct inventory categories."""
    categories = [c for c in db.inventory_items.distinct("category") if c]
    if not categories:
        return "No categories are defined yet."
    return f"Categories: {', '.join(categories)}."

def _intent_count_items(db, message):
    """Report how many items are in the inventory."""
    count = db.inventory_items.count_documents({})
    return f"There are {count} item(s) in inventory."

def _intent_list_items(db, message):
    """List the names of every inventory item."""
    items = list(db.inventory_items.find({}, {"_id": 0, "item_name": 1}))
    if not items:
        return "There are no items in inventory yet."
    names = ", ".join(item["item_name"] for item in items)
    return f"Inventory items: {names}."

def _intent_greeting(db, message):
    """Greet the user and hint at what the assistant covers."""
    return "Hi! Ask me about stock levels, suppliers, expiry dates, or waste."

def _intent_help(db, message):
    """Explain what the assistant can answer."""
    return ("I can help with low stock, item quantity, item count, listing "
            "items or categories, suppliers, cheapest price, expiring items, "
            "and waste totals.")

# Ordered rules: first keyword hit whose handler returns an answer wins.
# More specific intents come first; a handler that returns None lets the
# next rule try (e.g. "how many items" falls through to count_items).
CHAT_RULES = [
    (("low", "out of stock", "running out", "threshold", "alert"), _intent_low_stock),
    (("how much", "how many", "quantity", "stock of"), _intent_item_quantity),
    (("expiring", "expire", "expires", "expiry", "going bad", "shelf life"), _intent_expiring_soon),
    (("cheapest", "best price", "lowest price", "best deal"), _intent_cheapest_supplier),
    (("suppliers", "vendors", "supplier list", "who supplies"), _intent_supplier_list),
    (("waste", "wasted", "discarded", "thrown out", "spoilage"), _intent_waste_report),
    (("what's in", "items in", "show me", "category"), _intent_items_by_category),
    (("categories", "category list", "what categories"), _intent_list_categories),
    (("how many items", "how many products", "item count", "number of items", "total items", "count"), _intent_count_items),
    (("list items", "list inventory", "what items", "show inventory", "all items", "what do we have", "what's in stock"), _intent_list_items),
    (("hi", "hello", "hey", "good morning", "good afternoon", "greetings"), _intent_greeting),
    (("help", "what can you do", "commands", "how do you work"), _intent_help),
]

def _match_rule(db, message):
    text = message.lower()
    # Single-word keywords match whole words; multi-word keywords match phrases.
    words = set(re.findall(r"[a-z0-9]+", text))
    for keywords, handler in CHAT_RULES:
        for keyword in keywords:
            hit = keyword in text if " " in keyword else keyword in words
            if hit:
                reply = handler(db, text)
                if reply:
                    return reply
                break
    return None

def answer(db, message):
    """Return the assistant reply for a user message as a response dict."""
    reply = _match_rule(db, message)
    if reply:
        return {"response": reply, "source": "rules"}
    return {"response": FALLBACK, "source": "fallback"}
