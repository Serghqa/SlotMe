from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']
CSRF_TRUSTED_ORIGINS = [
    'http://192.168.9.98:8000',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://192.168.9.1:8000',
]

# Django Debug Toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
# INTERNAL_IPS = ['127.0.0.1']
INTERNAL_IPS = ['*']

# Логирование в консоль
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'root': {
#         'handlers': ['console'],
#         'level': 'INFO',
#     },
#     'loggers': {
#         'django.db.backends': {
#             'handlers': ['console'],
#             'level': 'DEBUG',  # SQL-запросы в консоли
#             'propagate': False,
#         },
#     },
# }