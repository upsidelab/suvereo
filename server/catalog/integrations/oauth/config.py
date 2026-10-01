"""Configuration for the integration OAuth handshake.

Kept with the feature rather than in Django settings, since nothing outside it reads these. Values
are resolved once at import, so they behave like settings and tests can override them in place.
"""

from environ import Env

env = Env()

BASE_URL = env.str("ECL_OAUTH_BASE_URL", default="").strip()

FLOW_LIFETIME_SECONDS = 15 * 60

RESULT_LIFETIME_SECONDS = 5 * 60

CLIENT_LIFETIME_SECONDS = 30 * 24 * 60 * 60
