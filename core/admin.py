from django.contrib import admin
from .models import Item, Order, OrderItem, Payment, Coupon, Refund, Address


def make_refund_accepted(modeladmin, request, queryset):
    queryset.update(refund_requested=False, refund_granted=True)


make_refund_accepted.short_description = 'Update orders to refund granted'


class OrderAdmin(admin.ModelAdmin):
    list_display = [
        '__str__',
        'ordered_date',
        'ordered',
        'being_delivered',
        'received',
        'refund_requested',
        'refund_granted',
        'billing_address',
        'shipping_address',
        'payment',
        'coupon',
    ]
    list_display_links = [
        '__str__',
        'billing_address',
        'shipping_address',
        'payment',
        'coupon',
    ]
    list_filter = [
        'ordered_date',
        'ordered',
        'being_delivered',
        'received',
        'refund_requested',
        'refund_granted', ]
    search_fields = [
        'user__username',
        'ref_code'
    ]
    actions = [make_refund_accepted]


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'user', 'ordered', 'order_id']


class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'address',
        'address_2',
        'country',
        'zipcode',
        'address_type',
        'save_info',
    ]
    list_filter = [
        'address_type',
        'save_info',
        'country',
    ]
    search_fields = [
        'user',
        'address',
        'zipcode',
    ]


admin.site.register(Item)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Payment)
admin.site.register(Coupon)
admin.site.register(Address, AddressAdmin)
