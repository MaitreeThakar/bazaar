from django import forms
from .models import Product,CartItem
from django.contrib.auth.models import User



class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = ['name', 'description', 'price']

    def clean_price(self):
        price = self.cleaned_data['price']

        if price <= 0:
            raise forms.ValidationError(
                'Price must be greater than 0.'
            )

        return price


class CartItemForm(forms.ModelForm):

    class Meta:
        model = CartItem
        fields = ['quantity']

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']

        if quantity <= 0:
            raise forms.ValidationError(
                'Quantity must be greater than 0.'
            )

        return quantity


class SignUpForm(forms.Form):
    username = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    phone = forms.CharField()
    role = forms.ChoiceField(
        choices=[
            ('customer', 'Customer'),
            ('supplier', 'Supplier'),
        ]
    )
    def clean_username(self):
        username = self.cleaned_data['username'].strip()

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")

        return username

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data