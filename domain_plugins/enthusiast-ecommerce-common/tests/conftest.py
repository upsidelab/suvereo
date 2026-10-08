"""Minimal Django bootstrap so this plugin's tests can run on their own.

Nothing in this plugin touches Django, but importing ``enthusiast_common`` pulls in
``enthusiast_common.indexing``, which declares an abstract Django model - and declaring a
model requires the app registry to be ready. Configuring empty settings is enough: the model
is abstract, so it never needs an app label or a database.
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(INSTALLED_APPS=[], DATABASES={})
    django.setup()
