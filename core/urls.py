from core import views
from django.urls import path
from core import views
from .views import (
    ItemDetailView,
    CheckoutView,
    HomeView,
    OrderSummaryView,
    add_to_cart,
    admin_user,
    order_list,
    remove_from_cart,
    remove_single_item_from_cart,
    PaymentView,
    aboutUs,
    admin_item,
    user_list,
    
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('all-products/', views.products, name='products'),
    path('home/<str:category>/', HomeView.as_view(), name='home-category'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('product/<slug>/', ItemDetailView.as_view(), name='product'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('admin-item/<slug>/', admin_item, name='admin-item'),
    path('admin-user/<userProfile>/', admin_user, name='admin-user'),
    path('user-list/', user_list, name='user-list'),
    path('order-list/', order_list, name='order-list'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart,
         name='remove-single-item-from-cart'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
    path('opinions/' ,views.opinions,name='opinions'),
    path('opinions/<int:opinion_id>/', views.opinions_details,name="opinionDetails"),
    path('opinions/create/', views.create_opinion,name="opinionCreate"),
    path('opinions/<int:opinion_id>/addResponse/', views.createResponse,name="responseCreate"),
    path('profile/',views.profile),
    path('about-us/' ,aboutUs,name='about-us'),
    path('condiciones/' ,views.condiciones,name='condiciones'),
    path('politica/' ,views.politica,name='politica'),
]


