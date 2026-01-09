from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.defaults import (
    page_not_found, 
    permission_denied,
    server_error
)

handler404 = 'blog.views.custom_page_not_found'
handler403 = 'blog.views.custom_permission_denied'
handler500 = 'blog.views.custom_server_error'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('django.contrib.auth.urls')),
    path('', include('blog.urls')),
    path('pages/', include('pages.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
