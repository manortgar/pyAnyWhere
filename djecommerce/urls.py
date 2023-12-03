from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from core.views import CustomSignupView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('accounts/signup/', CustomSignupView.as_view(), name='account_signup'),  # Incluye la URL de registro personalizada
    path('', include('core.urls', namespace='core'))
]+static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)


if settings.DEBUG:
     import debug_toolbar
     urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
     urlpatterns += static(settings.MEDIA_URL,
                           document_root=settings.MEDIA_ROOT)
     urlpatterns += static(settings.STATIC_URL,
                           document_root=settings.STATIC_ROOT)
