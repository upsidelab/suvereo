"""Configuration for the integration OAuth handshake.

Kept with the feature rather than in Django settings, since nothing outside it reads these. Values
are resolved once at import, so they behave like settings and tests can override them in place.
"""

from environ import Env

env = Env()

#: Public base URL this API is reached at, e.g. https://api.example.com. Needed only for redirect
#: URIs: behind TLS termination the request reports plain HTTP, and a URI built from that would not
#: match the one registered with the provider. Empty means "derive it from the request".
BASE_URL = env.str("ECL_OAUTH_BASE_URL", default="").strip()

#: Long enough to sign in and consent, short enough that an abandoned flow cannot be resumed.
FLOW_LIFETIME_SECONDS = 15 * 60

#: The outcome only has to survive between the callback and the form collecting it.
RESULT_LIFETIME_SECONDS = 5 * 60
