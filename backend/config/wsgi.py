"""
WSGI config for the backend project.

This is mostly boilerplate, but it is required so Django can expose the
application object to WSGI servers.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

