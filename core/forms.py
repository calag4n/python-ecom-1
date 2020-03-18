from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget


PAYMENT_CHOICES = (
    ('S', 'Stripe'),
    ('P', 'Paypal')
)


class CheckoutForm(forms.Form):
    shipping_address = forms.CharField()
    shipping_address2 = forms.CharField()
    shipping_zipcode = forms.CharField()
    shipping_country = CountryField(
        blank_label='(select country)').formfield(
            widget=CountrySelectWidget(attrs={
                'class': 'custom-select d-block w-100'
            })
    )

    billing_address = forms.CharField(required=False)
    billing_address2 = forms.CharField(required=False)
    billing_zipcode = forms.CharField(required=False)
    billing_country = CountryField(
        blank_label='(select country)').formfield(
            required=False,
            widget=CountrySelectWidget(attrs={
                'class': 'custom-select d-block w-100'
            })
    )

    same_billing_address = forms.BooleanField(
        widget=forms.CheckboxInput(), label='Addresse de facturation identique', required=False)
    save_info = forms.BooleanField(
        widget=forms.CheckboxInput(), label='Conserver ces informations', required=False)
    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES)


class CouponForm(forms.Form):
    code = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={
        'class': "form-control",
        'placeholder': "Code PROMO",
        'aria-label': "Recipient's username",
        'aria-describedby': "basic-addon2"
    }))


class RefundForm(forms.Form):
    ref_code = forms.CharField()
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 4
    }))
