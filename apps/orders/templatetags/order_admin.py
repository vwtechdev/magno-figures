from django import template

register = template.Library()


@register.filter
def move_first(value, app_label):
    value = list(value)
    target = app_label.lower()
    match = [item for item in value if str(item.get("app_label", "")).lower() == target]
    rest = [item for item in value if str(item.get("app_label", "")).lower() != target]
    return match + rest