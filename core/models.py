from django.db.models.signals import post_save
from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.shortcuts import reverse
from django_countries.fields import CountryField

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
        email = models.EmailField(unique=True)
        USERNAME_FIELD = 'email'
        REQUIRED_FIELDS = ['username']

CATEGORY_CHOICES = (
    ('MP', 'Maquinaria Pesada'),
    ('MS', 'Maquinaria Semipesada'),
    ('ML', 'Maquinaria Ligera')
)

FABRICANTE_CHOICES = (
    ('CAT', 'Caterpillar'),
    ('KMT', 'Komatsu'),
    ('X', 'XCMG'),
    ('JD', 'John Deere'),
    ('S', 'Sany'),

)

DISPONIBILITY_CHOICES = (
    ('D', 'Disponible'),
    ('ND', 'No disponible')
)

LABEL_CHOICES = (
    ('P', 'primary'),
    ('S', 'secondary'),
    ('D', 'danger')
)

ADDRESS_CHOICES = (
    ('B', 'Billing'),
    ('S', 'Shipping'),
)

STATE_CHOICES = (
    ('CF', 'Confirmado'),
    ('EV', 'Enviado'),
    ('EP', 'En preparacion'),
    ('RB', 'Recibido'),
    ('AN', 'Anulado'),
    
)








class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)
    one_click_purchasing = models.BooleanField(default=False)
    DNI = models.CharField(max_length=9, blank=True, null=True)
    telefono = models.CharField(max_length=9, blank=True, null=True)
    
    primary_address = models.ForeignKey(
        'Address', related_name='primary_address', on_delete=models.SET_NULL, blank=True, null=True)
    
    card_number = models.BigIntegerField(blank=True, null=True)
    card_expiry = models.PositiveIntegerField(blank=True, null=True)
    card_expiry_month = models.PositiveSmallIntegerField(blank=True, null=True)
    card_expiry_year = models.PositiveIntegerField(blank=True, null=True)
    card_cvc = models.PositiveSmallIntegerField(blank=True, null=True)
    has_card_details = models.BooleanField(default=False)


    def __str__(self):
        return self.user.username


class Item(models.Model):
    title = models.CharField(max_length=100)
    price = models.FloatField()
    fabricante = models.CharField(choices=FABRICANTE_CHOICES, max_length=3)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=2)
    label = models.CharField(choices=LABEL_CHOICES, max_length=1)
    slug = models.SlugField()
    description = models.TextField()
    image = models.ImageField()
    disponibility = models.CharField(choices=DISPONIBILITY_CHOICES, max_length=2,null=True)
    selected = models.BooleanField(default = False)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:product", kwargs={
            'slug': self.slug
        })

    def get_add_to_cart_url(self):
        return reverse("core:add-to-cart", kwargs={
            'slug': self.slug
        })

    def get_remove_from_cart_url(self):
        return reverse("core:remove-from-cart", kwargs={
            'slug': self.slug
        })
    
    def get_admin_item_panel(self):
        return reverse("core:admin-item", kwargs={
            'slug': self.slug
        })


class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.item.title}"

    def get_total_item_price(self):
        return self.quantity * self.item.price

    def get_final_price(self):
        return self.get_total_item_price()


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    ref_code = models.CharField(max_length=20, blank=True, null=True)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField()
    ordered = models.BooleanField(default=False)
    shipping_address = models.ForeignKey(
        'Address', related_name='shipping_address', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey(
        'Payment', on_delete=models.SET_NULL, blank=True, null=True)
    being_delivered = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    statement = models.CharField(choices=STATE_CHOICES, max_length=2,null=True, default='Confirmado')
    payment_type = models.BooleanField(default=False)
    shipping = models.BooleanField(default=True, blank=True, null=True)

    '''
    1. Item added to cart
    2. Adding a billing address
    (Failed checkout)
    3. Payment
    (Preprocessing, processing, packaging etc.)
    4. Being delivered
    5. Received
    6. Refunds
    '''

    def __str__(self):
        return self.user.username

    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
      
        return total


    def is_shipping_cost(self):
        return not(self.shipping) or self.get_total() > 50
    
    def get_final_price(self):
        if self.is_shipping_cost():
            return self.get_total()
        else:
            return self.get_total() + 3.99    


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_addresses')
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    zip = models.CharField(max_length=100)
    address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICES)
    default = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = 'Addresses'


class Payment(models.Model):
    stripe_charge_id = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET_NULL, blank=True, null=True)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

class Response(models.Model):
    description = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    opinion = models.ForeignKey('Opinion', related_name='opinion', on_delete=models.CASCADE, blank=True, null=True)                         

class Opinion(models.Model):
    title = models.CharField(max_length = 20)
    description = models.CharField(max_length = 100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    
    
    def get_absolute_url(self):
        return '/opinions/%s' %(self.id)

def userprofile_receiver(sender, instance, created, *args, **kwargs):
    if created:
        userprofile = UserProfile.objects.create(user=instance)


post_save.connect(userprofile_receiver, sender=settings.AUTH_USER_MODEL)
