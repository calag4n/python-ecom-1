from django import template
from core.models import Order

register = template.Library()


@register.filter
def cart_item_count(user):
    if user.is_authenticated:
        qs = Order.objects.filter(user=user, ordered=False)
        if qs.exists():
            qt = 0
            for item in qs[0].items.iterator():
                qt += item.quantity
            return qt
    return 0
