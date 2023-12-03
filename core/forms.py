from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from allauth.account.forms import SignupForm
#from localflavor.es.forms import ESIdentityCardNumberField
from .models import CATEGORY_CHOICES, DISPONIBILITY_CHOICES, LABEL_CHOICES, UserProfile, Item, FABRICANTE_CHOICES

SHIPPING_CHOICES = (
    ('D', 'Envío a domicilio'),
    ('R', 'Recogida en tienda: Avda. de los Tractores, 13')
)

PAYMENT_CHOICES = (
    ('T', 'Tarjeta de crédito'),
    ('C', 'Contrareembolso')
)

class ItemEditForm(forms.ModelForm):
    title = forms.CharField(max_length=100)
    fabricante = forms.ChoiceField(choices=FABRICANTE_CHOICES)
    price = forms.FloatField()
    category = forms.ChoiceField(choices=CATEGORY_CHOICES)
    label = forms.ChoiceField(choices=LABEL_CHOICES)
    description = forms.CharField()
    image = forms.ImageField()
    disponibility = forms.ChoiceField(choices=DISPONIBILITY_CHOICES)
    selected = forms.BooleanField()

    class Meta:
        model = Item
        fields = ['title', 'fabricante', 'price', 'category', 'label', 'description', 'image', 'disponibility', 'selected']


class CustomSignupForm(SignupForm):
    dni = forms.CharField(max_length=9, label="DNI")
    telefono = forms.CharField(max_length=9, label="Teléfono")
    direccion_envio = forms.CharField(max_length=255, label='Dirección de Envío')

class CheckoutForm(forms.Form):
    DNI = forms.CharField(max_length=9,required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    telefono = forms.CharField(max_length=9,required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    shipping_address = forms.CharField(required=False)
    shipping_country = CountryField(blank_label='Selecciona un país').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    shipping_zip = forms.CharField(required=False)
    shipping_option = forms.ChoiceField(widget=forms.RadioSelect, choices=SHIPPING_CHOICES)
    
    payment_option = forms.ChoiceField(widget=forms.RadioSelect, choices=PAYMENT_CHOICES)

class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Promo code',
        'aria-label': 'Recipient\'s username',
        'aria-describedby': 'basic-addon2'
    }))


class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 4
    }))
    email = forms.EmailField()


class PaymentForm(forms.Form):
    stripeToken = forms.CharField(required=False)
    save = forms.BooleanField(required=False)
    use_default = forms.BooleanField(required=False)

class OpinionCreateForm(forms.Form):
    title = forms.CharField(required=True, label='Título', max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(required=True, label='Descripción',max_length=200, widget=forms.Textarea(attrs={'class': 'form-control'}))

class ResponseCreateForm(forms.Form):
    description = forms.CharField(required=True, label='Ponga aqui su respuesta', max_length=200, widget=forms.Textarea(attrs={'class': 'form-control'}))

class UpdateUserForm(forms.ModelForm):
    # username = forms.CharField(max_length=100,
    #                            required=True,
    #                            widget=forms.TextInput(attrs={'class': 'form-control'}))
    username = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    email = forms.EmailField(required=True,
                             widget=forms.TextInput(attrs={'class': 'form-control'}))
    telefono = forms.CharField(max_length=9,
                               required=False,
                               widget=forms.TextInput(attrs={'class': 'form-control'}))
    DNI = forms.CharField(max_length=9,
                          required=False,
                          widget=forms.TextInput(attrs={'class': 'form-control'}))

    street_address = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    apartment_address = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    country = CountryField(blank_label='(select country)').formfield(
        required=False, widget=CountrySelectWidget(attrs={'class': 'custom-select d-block w-100'}))
    zip = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))


    # Añade opciones para los campos de mes y año
    MONTH_CHOICES = [(i, f"{i:02d}") for i in range(1, 13)]
    YEAR_CHOICES = [(i, str(i)) for i in range(2022, 2030)]  # Puedes ajustar el rango según sea necesario

    card_expiry_month = forms.ChoiceField(choices=MONTH_CHOICES)
    card_expiry_year = forms.ChoiceField(choices=YEAR_CHOICES)


    card_number = forms.CharField(max_length=16, required=False)
    card_expiry_month = forms.ChoiceField(choices=MONTH_CHOICES)
    card_expiry_year = forms.ChoiceField(choices=YEAR_CHOICES)
    card_cvc = forms.CharField(max_length=4, required=False)

    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'telefono', 'DNI', 'street_address', 'apartment_address', 'country', 'zip', 'card_number', 'card_expiry_month','card_expiry_year', 'card_cvc']

    def clean_card_expiry(self):
        card_expiry_month = self.cleaned_data['card_expiry_month']
        card_expiry_year = self.cleaned_data['card_expiry_year']

        # Combinar mes y año para formar la fecha completa
        card_expiry = f"{card_expiry_month}/{card_expiry_year}"

        try:
            # Intentar convertir la fecha a un objeto datetime
            datetime.strptime(card_expiry, '%m/%Y')
        except ValueError:
            raise ValidationError('Formato de fecha inválido. Utilice MM/YYYY.')

        return card_expiry
