DEMO_EMAIL = "demo-listings@retech.example"
DEMO_NAME = "RETECH Demo"

# Keys are the titles placed in the database by seed-demo.
DEMO_LISTINGS = {
    "Rechargeable battery pack": (
        "batteries", "fair", "A used rechargeable battery pack with reduced capacity.", "battery-pack",
    ),
    "USB-C charger and cable": (
        "chargers", "excellent", "A working USB-C wall charger with a braided cable.", "chargers",
    ),
    "ThinkPad T480": (
        "laptops", "good", "A working ThinkPad with light wear on the lid.", "laptops",
    ),
    "Samsung Galaxy A52": (
        "phones", "good", "A working phone with minor scratches. Charger included.", "phones",
    ),
    "USB-rechargeable AA batteries": (
        "batteries", "fair", "Two AA cells with built-in USB charging. They hold a shorter charge now.", "usb-batteries",
    ),
    "Logitech K260 wireless keyboard": (
        "other", "good", "Working wireless keyboard with its USB receiver. Some keycaps show wear.", "keyboard",
    ),
    "iPad 2": (
        "other", "non-working", "The tablet no longer powers on. The casing is intact.", "tablet",
    ),
    "Logitech M185 wireless mouse": (
        "other", "good", "The buttons and scroll wheel work. USB receiver included.", "other",
    ),
    "iPhone 8": (
        "phones", "fair", "64 GB phone that powers on. The screen has scratches and the battery runs down quickly.", "iphone-8",
    ),
    "MacBook Air 13-inch": (
        "laptops", "good", "Starts up and runs on mains power. Light wear on the case. Charger included.", "macbook-air",
    ),
    "Anker PowerPort 5-port charger": (
        "chargers", "excellent", "All five USB-A ports work. Mains cable included.", "anker-charger",
    ),
    "Wired over-ear headphones": (
        "other", "good", "Both earcups work. The pads show wear and the 3.5 mm plug is intact.", "headphones",
    ),
}


def listing_photo(listing):
    sample = DEMO_LISTINGS.get(listing["title"]) if listing.get("sample") else None
    return sample[3] if sample else listing["category"]
