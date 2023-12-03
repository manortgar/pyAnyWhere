
import random
import string
from django.http import HttpResponse
from django.urls import reverse

import stripe
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponseRedirect
from datetime import datetime


from .forms import CheckoutForm, CouponForm, OpinionCreateForm, RefundForm, PaymentForm, CustomSignupForm, ResponseCreateForm, UpdateUserForm, ItemEditForm
from .models import Item, Opinion, OrderItem, Order, Address, Payment, Response, UserProfile

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

@login_required
def admin_item(request, slug):
    # Obtén el artículo usando el slug
    item = get_object_or_404(Item, slug=slug)

    # Verifica si el usuario es un administrador
    if not request.user.is_staff:
        # Si no es un administrador, puedes redirigirlo o mostrar un mensaje
        return render(request, 'no_permission.html')

    # Lógica para manejar el formulario de edición si se envió
    if request.method == 'POST':
        form = ItemEditForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect('core:product', slug=slug)
    else:
        # Cargar el formulario con los datos actuales del artículo
        form = ItemEditForm(instance=item)

    # Renderiza la plantilla con el formulario de edición
    return render(request, 'admin_item.html', {'item': item, 'form': form})

@login_required
def admin_user(request, user):
    userProfile = get_object_or_404(UserProfile, user=user)

    if not request.user.is_staff:
        return render(request, 'no_permission.html')
    
    if request.method == 'POST':
        form = UpdateUserForm(request.POST, instance=userProfile)
        if form.is_valid():
            form.save()
            return redirect('core:user-list')
    else:
        form = UpdateUserForm(instance=userProfile)

    return render(request, 'admin_user.html', {'userProfile': userProfile, 'form': form})

def user_list(request):
    if request.user.is_staff:
        users = UserProfile.objects.all()
        return render(request, 'user_list.html', {'users': users})
    else:
        return render(request, 'no_permission.html')
    
def order_list(request):
    if request.user.is_staff:
        orders = Order.objects.all()
        order1 = orders[1]
        item =order1.items.all()
        orderitem = OrderItem.objects.all()
        print("esto esAAAAAAAAAAAAAAAAAAAA" + str(orders[1].items.all()) + str(item))
        return render(request, 'order_list.html', {'orders': orders}, {'items': orderitem})
    else:
        return render(request, 'no_permission.html')


def products(request):
    queryset = request.GET.get("search")
    products = Item.objects.all()
    if queryset:
        products = Item.objects.filter(
           Q(title__icontains = queryset)
        ).distinct
    context = {
        'object_list': products
    }
    return render(request, "home.html", context)



def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid



from allauth.account.views import SignupView
from .forms import CustomSignupForm

class CustomSignupView(SignupView):
    form_class = CustomSignupForm

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Puedes realizar acciones adicionales aquí si es necesario
        self.user.profile.dni = form.cleaned_data['dni']
        self.user.profile.telefono = form.cleaned_data['telefono']
        self.user.profile.direccion_envio = form.cleaned_data['direccion_envio']
        self.user.profile.save()

        return response

class CheckoutView(View):
    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            usuario = self.request.user
        else:
            usuario = User.objects.get(username = 'anonymous')
        try:
            order = Order.objects.get(user=usuario, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'order': order
            }
            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "No puedes realizar la acción seleccionada, no esta activa")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            usuario = self.request.user
        else:
            usuario = User.objects.get(username = 'anonymous')
        #form = CheckoutForm(self.request.POST or None)

        try:
            order = Order.objects.get(user=usuario, ordered=False)
            DNI = self.request.POST.get('DNI')
            telefono = self.request.POST.get('telefono')
            email = self.request.POST.get('email')

            shipping_address = self.request.POST.get('shipping_address')
            shipping_country = self.request.POST.get('shipping_country')
            shipping_zip = self.request.POST.get('shipping_zip')
            shipping_option = self.request.POST.get('shipping_option')

            payment_option = self.request.POST.get('payment_option')

            if is_valid_form([shipping_address, shipping_country, shipping_zip]):
                shipping_address = Address(
                    user=usuario,
                    street_address=shipping_address,
                    apartment_address=shipping_address,
                    country=shipping_country,
                    zip=shipping_zip
                )
                shipping_address.save()
                order.shipping_address = shipping_address
                order.save()

            order.shipping = shipping_option=='D'
            if not(order.shipping):
                shipping_address = Address(
                        user=usuario,
                        street_address="Recogida en tienda",
                        apartment_address="Recogida en tienda",
                        zip="12345")
                shipping_address.save()
                order.shipping_address = shipping_address
                order.save()

            order.email = email
            if payment_option == 'T':
                order.payment_type = False
                order.save()
                return redirect('core:payment', payment_option='card')
            elif payment_option == 'C':
                order.payment_type = True
                order.save()
                return redirect('core:payment', payment_option='cod')
            else:
                messages.warning(
                    self.request, "Opción de pago seleccionada incorrecta")
                return redirect('core:checkout')
                
        except ObjectDoesNotExist:
            messages.warning(self.request, "No puedes realizar la acción seleccionada, no está activa")
            return redirect("core:order-summary")


class PaymentView(View):
    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            usuario = self.request.user
        else:
            usuario = User.objects.get(username = 'anonymous')
        order = Order.objects.get(user=usuario, ordered=False)
        context = {
            'order': order,
            'payment_option': order.payment_type
        }
        userprofile = usuario.userprofile
        if userprofile.one_click_purchasing:
            # fetch the users card list
            cards = stripe.Customer.list_sources(
                userprofile.stripe_customer_id,
                limit=3,
                object='card'
            )
            card_list = cards['data']
            if len(card_list) > 0:
                # update the context with the default card
                context.update({
                    'card': card_list[0]
                })
        return render(self.request, "payment.html", context)

    def post(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            usuario = self.request.user
        else:
            usuario = User.objects.get(username = 'anonymous')
        order = Order.objects.get(user=usuario, ordered=False)
        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=usuario)
        if form.is_valid():
            if order.payment_type:
                try:
                    payment = Payment()
                    payment.user = usuario
                    payment.amount = order.get_total()
                    payment.save()

                    # assign the payment to the order

                    order_items = order.items.all()
                    order_items.update(ordered=True)
                    for item in order_items:
                        item.save()

                    order.ordered = True
                    order.payment = payment
                    order.ref_code = create_ref_code()
                    order.save()

                    email = order.user.email
                    template = get_template('invoice.html')

                    # Se renderiza el template y se envias parametros
                    content = template.render({'email': email,'order': order})

                    # Se crea el correo (titulo, mensaje, emisor, destinatario)
                    try:
                        msg = EmailMultiAlternatives(
                        'Gracias por tu compra',
                        'Hola, te enviamos un correo con tu factura',
                        settings.EMAIL_HOST_USER,
                        [email]
                        )

                        msg.attach_alternative(content, 'text/html')
                        msg.send()
                        messages.success(self.request, "¡Tu pedido fue un éxito! Recibirás un correo con los datos del envío, tu número de referencia del pedido es " + order.ref_code)
                        return redirect("/")
                    except Exception as email_exception:
                        messages.warning(
                            self.request, "Error al enviar el email. Hemos registrado la incidencia")
                        return redirect("/")
                    
                except Exception as e:
                    # send an email to ourselves
                    messages.warning(
                        self.request, "Ha ocurrido un problema grave. Hemos registrado la incidencia")
                    return redirect("/")
            else:
                token = form.cleaned_data.get('stripeToken')
                save = form.cleaned_data.get('save')
                use_default = form.cleaned_data.get('use_default')

                if save:
                    if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                        customer = stripe.Customer.retrieve(
                            userprofile.stripe_customer_id)
                        customer.sources.create(source=token)

                    else:
                        customer = stripe.Customer.create(
                            email=usuario.email,
                        )
                        customer.sources.create(source=token)
                        userprofile.stripe_customer_id = customer['id']
                        userprofile.one_click_purchasing = True
                        userprofile.save()

                amount = int(order.get_total() * 100)

                try:

                    if use_default or save:
                        # charge the customer because we cannot charge the token more than once
                        charge = stripe.Charge.create(
                            amount=amount,  # cents
                            currency="usd",
                            customer=userprofile.stripe_customer_id
                        )
                    else:
                        # charge once off on the token
                        charge = stripe.Charge.create(
                            amount=amount,  # cents
                            currency="usd",
                            source=token
                        )

                    # create the payment
                    payment = Payment()
                    payment.stripe_charge_id = charge['id']
                    payment.user = usuario
                    payment.amount = order.get_total()
                    payment.save()

                    # assign the payment to the order

                    order_items = order.items.all()
                    order_items.update(ordered=True)
                    for item in order_items:
                        item.save()

                    order.ordered = True
                    order.payment = payment
                    order.ref_code = create_ref_code()
                    order.save()

                    email = order.user.email

                    template = get_template('invoice.html')

                    # Se renderiza el template y se envias parametros
                    content = template.render({'email': email,'order': order})

                    # Se crea el correo (titulo, mensaje, emisor, destinatario)
                    try:
                        msg = EmailMultiAlternatives(
                        'Gracias por tu compra',
                        'Hola, te enviamos un correo con tu factura',
                        settings.EMAIL_HOST_USER,
                        [email]
                        )

                        msg.attach_alternative(content, 'text/html')
                        msg.send()
                        messages.success(self.request, "¡Tu pedido fue un éxito! Recibirás un correo con los datos del envío, tu número de referencia del pedido es " + order.ref_code)
                        return redirect("/")
                    except Exception as email_exception:
                        messages.warning(
                            self.request, "Error al enviar el email. Hemos registrado la incidencia")
                        return redirect("/")

                except stripe.error.CardError as e:
                    body = e.json_body
                    err = body.get('error', {})
                    messages.warning(self.request, f"{err.get('message')}")
                    return redirect("/")

                except stripe.error.RateLimitError as e:
                    # Too many requests made to the API too quickly
                    messages.warning(self.request, "Rate limit error")
                    return redirect("/")

                except stripe.error.InvalidRequestError as e:
                    # Invalid parameters were supplied to Stripe's API
                    print(e)
                    messages.warning(self.request, "Invalid parameters")
                    return redirect("/")

                except stripe.error.AuthenticationError as e:
                    # Authentication with Stripe's API failed
                    # (maybe you changed API keys recently)
                    messages.warning(self.request, "Not authenticated")
                    return redirect("/")

                except stripe.error.APIConnectionError as e:
                    # Network communication with Stripe failed
                    messages.warning(self.request, "Network error")
                    return redirect("/")

                except stripe.error.StripeError as e:
                    # Display a very generic error to the user, and maybe send
                    # yourself an email
                    messages.warning(
                        self.request, "Algo ha ido mal, no se le ha cobrado. Por favor inténtelo de nuevo")
                    return redirect("/")

                except Exception as e:
                    # send an email to ourselves
                    messages.warning(
                        self.request, "Ha ocurrido un problema grave. Hemos registrado la incidencia ")
                    return redirect("/")

        messages.warning(self.request, "Invalid data received")
        return redirect("/payment/stripe/")


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"

    def get_queryset(self):
        category = self.kwargs.get('category', None)
        queryset = super().get_queryset()
        
        if category:
            queryset = queryset.filter(category=category)

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Item.category  # Reemplaza con el nombre de tu campo de categoría
        return context

@login_required
class Home_login(ListView):
    model = Item
    paginate_by = 10
    template_name = "home_login.html"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            usuario = self.request.user
        else:
            usuario = User.objects.get(username = 'anonymous')
        try:
            order = Order.objects.get(user=usuario, ordered=False)
            context = {
                    'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "No tienes activo la orden")
            return redirect("/")


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"



def add_to_cart(request, slug):
    if request.user.is_authenticated:
            usuario = request.user
    else:
        usuario = User.objects.get(username = 'anonymous')
  
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
            item=item,
            user=usuario,
            ordered=False
        )
    order_qs = Order.objects.filter(user=usuario, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
            # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
                order_item.quantity += 1
                order_item.save()
                messages.info(request, "El objeto ha sido actualizado.")
                return redirect("core:order-summary")
        else:
                order.items.add(order_item)
                messages.info(request, "El objeto ha sido añadido a tu carrito")
                return redirect("core:order-summary")
    else:
            ordered_date = timezone.now()
            order = Order.objects.create(
                user=usuario, ordered_date=ordered_date)
            order.items.add(order_item)
            messages.info(request, "El objeto ya estaba añadido en tu carrito")
            return redirect("core:order-summary")


def remove_from_cart(request, slug):
    if request.user.is_authenticated:
            usuario = request.user
    else:
            usuario = User.objects.get(username = 'anonymous')
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=usuario,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=usuario,
                ordered=False
            )[0]
            order.items.remove(order_item)
            messages.info(request, "El objeto ha sido borrado de tu carrito")
            return redirect("core:order-summary")
        else:
            messages.info(request, "Este objeto no estaba en tu cesta")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "No tienes ningún pedido activo")
        return redirect("core:product", slug=slug)


def remove_single_item_from_cart(request, slug):
    if request.user.is_authenticated:
            usuario = request.user
    else:
            usuario = User.objects.get(username = 'anonymous')
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=usuario,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=usuario,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "La cantidad del producto ha sido modificada.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "El producto no se encuentra en el carrito")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "No tienes activa la orden")
        return redirect("core:product", slug=slug)
    

    
def condiciones(request):
    context = {}
    return render(request, "condiciones.html", context)

def aboutUs(request):
    context = {}
    return render(request, "about-us.html", context)
    
def politica(request):
    context = {}
    return render(request, "politica.html", context)

@login_required
def opinions(request):
    context = {
        'opinions' : Opinion.objects.all()
    }       
    return render(request,'opinions2.html', context)


@login_required
def opinions_details(request, opinion_id):
    opinion = Opinion.objects.get(id = opinion_id)
    responses = Response.objects.filter(opinion = opinion)
    context = {
        'opinion' : opinion,
        'responses' : responses
    }       
    return render(request,'opinionDetails.html', context)

@login_required
def create_opinion(request):
    if request.method == 'POST':
        opinion_form = OpinionCreateForm(request.POST)
        if opinion_form.is_valid():
            try:
                title = opinion_form.cleaned_data.get('title')
                description = opinion_form.cleaned_data.get('description')
                user = request.user
                opinion = Opinion(title = title, description = description, user = user)
                opinion.save()
                messages.success(request, 'La opinión fue añadida con éxito')
                return redirect('/opinions/')
            except:
                messages.error(request, 'La opinión no se ha podido añadir')
                return redirect('/opinions/create')
    else:
        opinion_form = OpinionCreateForm()
        context = {
            'form' : opinion_form
        }
        return render(request,'createOpinion.html',context)


@login_required
def createResponse(request, opinion_id):
    if request.method == 'POST':
        response_form = ResponseCreateForm(request.POST)
        
        if response_form.is_valid():
            try:
                description = response_form.cleaned_data.get('description')
                user = request.user
                opinion = Opinion.objects.get(id=opinion_id)
                response = Response(description = description, user = user,opinion=opinion)
                response.save()
                messages.success(request, 'La respuesta se ha añadido correctamente')
                return redirect('/opinions/%s/' %(opinion_id))
            except:
                messages.error(request, 'La creación de la respuesta ha fallado')
                return redirect('/opinions/%s/addResponse' %(opinion_id))
    else:
        response_form = ResponseCreateForm()
        context = {
            'form' : response_form
        }
        return render(request,'createResponse.html',context)


class Send(View):
    def get(self, request):
        return render(request, 'send.html')
    
    def post(self, request):
        email = request.POST.get('email')
        print(email)

        template = get_template('email-order-success.html')

        # Se renderiza el template y se envias parametros
        content = template.render({'email': email})

        # Se crea el correo (titulo, mensaje, emisor, destinatario)
        msg = EmailMultiAlternatives(
            'Gracias por tu compra',
            'Hola, te enviamos un correo con tu factura',
            settings.EMAIL_HOST_USER,
            [email]
        )

        msg.attach_alternative(content, 'text/html')
        msg.send()

        return render(request, 'send.html')


    def delete_carrito(request):
        if request.user.is_authenticated:
            usuario = request.user
        else:
            usuario = User.objects.get(username = 'anonymous')
        user = usuario
        user.delete()
        messages.success(request, 'El perfil ha sido borrado con éxito')
        return redirect('/', foo='bar')
    
@login_required
def profile(request):
    usuario = request.user
    usuario_profile, created = UserProfile.objects.get_or_create(user=usuario)

    if request.method == 'POST':
        user_form = UpdateUserForm(request.POST, instance=usuario_profile)
        if user_form.is_valid():
            # Actualizar la información del perfil
            user_form.save()


             # Actualizar el correo electrónico en el modelo User
            usuario.email = user_form.cleaned_data.get('email')
            usuario.username = user_form.cleaned_data.get('username')
            usuario.telefono = user_form.cleaned_data.get('telefono')
            usuario.dni = user_form.cleaned_data.get('dni')
            usuario.save()

            
            # Actualizar la información de la tarjeta
            card_number = user_form.cleaned_data.get('card_number')
            #card_expiry = user_form.cleaned_data.get('card_expiry')
            card_expiry_month = user_form.cleaned_data.get('card_expiry_month')
            card_expiry_year = user_form.cleaned_data.get('card_expiry_year')
            card_cvc = user_form.cleaned_data.get('card_cvc')

            if card_number and card_expiry_month and card_expiry_year and card_cvc:
                # Convertir mes y año a un formato de fecha
                card_expiry = f"{card_expiry_month}/{card_expiry_year}"
                try:
                    card_expiry_date = datetime.strptime(card_expiry, '%m/%Y')
                except ValueError:
                    messages.warning(request, 'Formato de fecha de expiración inválido')
                    return redirect('edit_profile')

                usuario_profile.card_number = card_number
                #usuario_profile.card_expiry = card_expiry
                usuario_profile.card_expiry_month  = card_expiry_month
                usuario_profile.card_expiry_year  = card_expiry_year
                usuario_profile.card_cvc = card_cvc
                usuario_profile.has_card_details = True
                usuario_profile.save()

                messages.success(request, 'Información de la tarjeta guardada con éxito')
            else:
                messages.warning(request, 'Por favor, completa todos los campos de la tarjeta')
            
            if usuario_profile.primary_address:
                street_address = user_form.cleaned_data.get('street_address')
                apartment_address = user_form.cleaned_data.get('apartment_address')
                country = user_form.cleaned_data.get('country')
                zip_code = user_form.cleaned_data.get('zip')

                usuario_profile.primary_address.street_address = street_address
                usuario_profile.primary_address.apartment_address = apartment_address
                usuario_profile.primary_address.country = country
                usuario_profile.primary_address.zip = zip_code
                
                # Puedes actualizar otros campos de dirección aquí según sea necesario

                usuario_profile.primary_address.save()
            else:
                # Crea una dirección principal si no existe
                street_address = user_form.cleaned_data.get('street_address')
                apartment_address = user_form.cleaned_data.get('apartment_address')
                country = user_form.cleaned_data.get('country')
                zip_code = user_form.cleaned_data.get('zip')

                new_address = Address.objects.create(
                    user=request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip_code,
                    address_type='B',
                    default=True
                )
                
                usuario_profile.primary_address = new_address
                usuario_profile.save()
                messages.success(request, 'Información de la dirección guardada con éxito')

            
            
    else:
        # Crear una instancia de formulario vacía
        user_form = UpdateUserForm()

        # Actualizar valores solo si existen en la instancia UserProfile
        if usuario_profile:
            user_form.fields['username'].initial = usuario_profile.user.username
            user_form.fields['email'].initial = usuario_profile.user.email
            user_form.fields['telefono'].initial = usuario_profile.telefono
            user_form.fields['DNI'].initial = usuario_profile.DNI
        if usuario_profile.primary_address:
            user_form.fields['street_address'].initial = usuario_profile.primary_address.street_address
            user_form.fields['apartment_address'].initial = usuario_profile.primary_address.apartment_address
            user_form.fields['country'].initial = usuario_profile.primary_address.country
            user_form.fields['zip'].initial = usuario_profile.primary_address.zip
                
        user_form.fields['card_number'].initial = usuario_profile.card_number
       # user_form.fields['card_expiry'].initial = usuario_profile.card_expiry
        user_form.fields['card_expiry_month'].initial = usuario_profile.card_expiry_month
        user_form.fields['card_expiry_year'].initial = usuario_profile.card_expiry_year

        user_form.fields['card_cvc'].initial = usuario_profile.card_cvc
            
    if request.user.is_staff:
        # Si el usuario es administrador, redirige al panel de administración
        return HttpResponseRedirect(reverse('admin:index'))

    return render(request, 'profile.html', {'user_form': user_form})

@login_required
def opinions(request):
    context = {
        'opinions' : Opinion.objects.all()
    }       
    return render(request,'opinions2.html', context)


@login_required
def opinions_details(request, opinion_id):
    opinion = Opinion.objects.get(id = opinion_id)
    responses = Response.objects.filter(opinion = opinion)
    context = {
        'opinion' : opinion,
        'responses' : responses
    }       
    return render(request,'opinionDetails.html', context)

@login_required
def create_opinion(request):
    if request.method == 'POST':
        opinion_form = OpinionCreateForm(request.POST)
        if opinion_form.is_valid():
            try:
                title = opinion_form.cleaned_data.get('title')
                description = opinion_form.cleaned_data.get('description')
                user = request.user
                opinion = Opinion(title = title, description = description, user = user)
                opinion.save()
                messages.success(request, 'La opinión fue añadida con éxito')
                return redirect('/opinions/')
            except:
                messages.error(request, 'La opinión no se ha podido añadir')
                return redirect('/opinions/create')
    else:
        opinion_form = OpinionCreateForm()
        context = {
            'form' : opinion_form
        }
        return render(request,'createOpinion.html',context)


@login_required
def createResponse(request, opinion_id):
    if request.method == 'POST':
        response_form = ResponseCreateForm(request.POST)
        
        if response_form.is_valid():
            try:
                description = response_form.cleaned_data.get('description')
                user = request.user
                opinion = Opinion.objects.get(id=opinion_id)
                response = Response(description = description, user = user,opinion=opinion)
                response.save()
                messages.success(request, 'La respuesta se ha añadido correctamente')
                return redirect('/opinions/%s/' %(opinion_id))
            except:
                messages.error(request, 'La creación de la respuesta ha fallado')
                return redirect('/opinions/%s/addResponse' %(opinion_id))
    else:
        response_form = ResponseCreateForm()
        context = {
            'form' : response_form
        }
        return render(request,'createResponse.html',context)
