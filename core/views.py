from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.utils import timezone
from .forms import CheckoutForm, CouponForm, RefundForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund

import random
import string
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'order': order,
                'couponform': CouponForm()
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                save_info=True
            )
            if shipping_address_qs.exists():
                context.update({
                    'default_shipping_address': shipping_address_qs[0]
                })

                # billing_address_qs = Address.objects.filter(
                #     user=self.request.user,
                #     address_type='B',
                # )
                # if billing_address_qs.exists():
                #     context.update({
                #         'default_billing_address': billing_address_qs[0]
                #     })

            return render(self.request, 'checkout.html', context)

        except ObjectDoesNotExist:
            messages.warning(
                self.request, "Vous n'avez pas de commande en cours")
            return redirect('core:checkout')

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                shipping_address = form.cleaned_data.get('shipping_address')
                shipping_address_2 = form.cleaned_data.get(
                    'shipping_address2')
                shipping_country = form.cleaned_data.get('shipping_country')
                shipping_zipcode = form.cleaned_data.get('shipping_zipcode')

                # billing_address = form.cleaned_data.get('billing_address')
                # billing_address_2 = form.cleaned_data.get('billing_address2')
                # billing_country = form.cleaned_data.get('billing_country')
                # billing_zipcode = form.cleaned_data.get('billing_zipcode')

                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                save_info = form.cleaned_data.get('save_info')
                payment_option = form.cleaned_data.get('payment_option')

                shipping_address_block = Address(
                    user=self.request.user,
                    address=shipping_address,
                    address_2=shipping_address_2,
                    country=shipping_country,
                    zipcode=shipping_zipcode,
                    address_type='S'
                )

                # if same_billing_address:
                # billing_address_block = Address(
                #     user=self.request.user,
                #     address=shipping_address,
                #     address_2=shipping_address_2,
                #     country=shipping_country,
                #     zipcode=shipping_zipcode,
                #     address_type='B'
                # )
                # else:
                #     billing_address = Address(
                #         user=self.request.user,
                #         address=billing_address,
                #         address_2=billing_address_2,
                #         country=billing_country,
                #         zipcode=billing_zipcode,
                #         address_type='B'
                #     )

                shipping_address_block.save()
                # order.billing_address = billing_address_block
                order.shipping_address = shipping_address_block

                print(self.request)
                print(order)
                print(order.shipping_address)

                # billing_address_block.save()
                order.save()

                if payment_option == 'S':
                    return redirect('core:payment-opt', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment-opt', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, 'Option de paiement invalide')
                    return redirect('core:checkout')

        except ObjectDoesNotExist:
            messages.warning(self.request, "You don't have an order yet.")
            return redirect('core:order-summary')

        # if form.is_valid():
        #     address = form.cleaned_data.get('address')
        #     address_2 = form.cleaned_data.get('address_2')
        #     country = form.cleaned_data.get('country')
        #     zipcode = form.cleaned_data.get('zipcode')
        #     same_billing_address = form.cleaned_data.get(
        #         'same_billing_address')
        #     save_info = form.cleaned_data.get('save_info')
        #     payment_option = form.cleaned_data.get('payment_option')
        #     billing_address = Address(
        #         user=self.request.user,
        #         address=address,
        #         address_2=address_2,
        #         country=country,
        #         zipcode=zipcode,
        #     )
        #     billing_address.save()
        #     return redirect('core:checkout')
        messages.warning(self.request, 'Echec')
        return redirect('core:checkout')


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        print(self.request)
        print(order)
        print(order.shipping_address)

        if order.shipping_address:
            context = {
                'order': order
            }
            return render(self.request, 'payment.html', context)
        else:
            messages.warning(
                self.request, "Vous n'avez pas enregistré d'adresse de facturation")
            return redirect('core:checkout')

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken')
        amount = int(order.get_total() * 100),
        amount = int(amount[0])  # cents

        try:
          # Use Stripe's library to make requests...
            charge = stripe.Charge.create(
                amount=amount,
                currency="eur",
                source=token,
            )

          # create the payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

          # assign the payment to the order
            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.order_id = order
                item.save()

            order.ordered = True
            order.ordered_date = timezone.now()
            order.payment = payment
            order.ref_code = create_ref_code()
            order.save()

            messages.success(self.request, 'Merci de votre commande !')
            return redirect('/')

        except stripe.error.CardError as e:
          # Since it's a decline, stripe.error.CardError will be caught
            messages.warning(self.request, f'Error: {e.error.message}')
            return redirect('/')
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.warning(self.request, f'Error: {e.error.message}')
            return redirect('/')
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.warning(self.request, f'Error: {e.error.message}')
            return redirect('/')
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.warning(self.request, f'Error: {e.error.message}')
            return redirect('/')
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.warning(self.request, f'Error: {e.error.message}')
            return redirect('/')
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.warning(self.request, f'Error: {e.error.message}')
            return redirect('/')
        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            return redirect('/')


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = 'home.html'


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order,
                'couponform': CouponForm()
            }
            return render(self.request, 'order-summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You don't have an order yet.")
            return redirect('/')


class ItemDetailView(DetailView):
    model = Item
    template_name = 'product.html'


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )

    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, 'This item quantity was updated.')
            return redirect('core:order-summary')
        else:
            order.items.add(order_item)
            messages.info(request, 'This item was added to your cart.')
            return redirect('core:order-summary')
    else:
        order = Order.objects.create(
            user=request.user)
        order.items.add(order_item)
        messages.info(request, 'This item was added to your cart.')
        return redirect('core:order-summary')


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order_item.quantity = 1
            order_item.save()

            order.items.remove(order_item)
            messages.info(request, 'This item was removed from your cart.')
            return redirect('core:product', slug=slug)
        else:
            messages.info(request, 'This item was not in your cart.')
            return redirect('core:product', slug=slug)
    else:
        # add message saying the order doesn't exist
        messages.info(request, 'You do not have an active order.')
        return redirect('core:product', slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, 'Quantité mise à jour.')
            return redirect('core:order-summary')
        else:
            messages.info(request, 'This item was not in your cart.')
            return redirect('core:product', slug=slug)
    else:
        # add message saying the order doesn't exist
        messages.info(request, 'You do not have an active order.')
        return redirect('core:product', slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.warning(
            request, "Ce coupon n'existe pas ou n'est plus valide")
        return None


class AddCoupon(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                coupon = get_coupon(self.request, code)

                if isinstance(coupon, Coupon):
                    order.coupon = get_coupon(self.request, code)
                    order.save()
                    messages.success(self.request, "Le coupon a été appliqué")
                    return redirect('core:checkout')

            except ObjectDoesNotExist:
                messages.warning(
                    self.request, "Vous n'avez pas de commande en cours")
                return redirect('core:checkout')


class RequestRefundView(View):

    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, 'request_refund.html', context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                refund = Refund()
                refund.order = order
                refund.reason = message,
                refund.email = email
                refund.save()

                messages.info(
                    self.request, "Votre requête est prise en compte")
                return redirect('/')

            except ObjectDoesNotExist:
                messages.info(self.request, "Cette commande n'existe pas")
                return redirect('core:request-refund')
