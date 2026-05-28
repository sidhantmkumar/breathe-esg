from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import ensure_csrf_cookie
import os

@ensure_csrf_cookie
def index(request):
    template_path = os.path.join(settings.BASE_DIR, 'templates', 'index.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return HttpResponse(content, content_type='text/html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('', index),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)