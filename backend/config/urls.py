"""
Root URL configuration for the backend project.

We keep it short and simply include the URLs from the `core` app.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # All API endpoints related to equipment live under /api/
    path("api/", include("core.urls")),
]

# In development it is convenient to serve media files (like generated PDFs)
# directly from Django.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

