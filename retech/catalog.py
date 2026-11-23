CATEGORIES = {
    "phones": ("Phones", 6500),
    "laptops": ("Laptops", 12000),
    "chargers": ("Chargers", 600),
    "batteries": ("Batteries", 450),
    "other": ("Other electronics", 1800),
}

CONDITIONS = {
    "excellent": ("Excellent", 100, "Fully functional with minimal wear."),
    "good": ("Good", 75, "Fully functional with visible wear."),
    "fair": ("Fair", 45, "Functional with significant wear or minor issues."),
    "non-working": ("Non-working", 15, "No longer working. Suitable for parts or recycling."),
}


def estimate_value(category, condition):
    return CATEGORIES[category][1] * CONDITIONS[condition][1] // 100


def money(value):
    digits = str(value)
    head, tail = digits[:-3], digits[-3:]
    while head:
        tail = f"{head[-2:]},{tail}"
        head = head[:-2]
    return f"₹{tail}"
