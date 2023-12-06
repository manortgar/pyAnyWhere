import os
import sys

path = '/home/ARGProject/pyAnyWhere'
if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djecommerce.settings.production')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
