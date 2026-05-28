from decouple import config, Csv


ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
