from environ import Env

env = Env()

BASE_URL = env.str("ECL_OAUTH_BASE_URL", default="").strip()

FLOW_LIFETIME_SECONDS = 15 * 60

RESULT_LIFETIME_SECONDS = 5 * 60

CLIENT_LIFETIME_SECONDS = 30 * 24 * 60 * 60
