import os
from django.core.urlresolvers import reverse_lazy

CONF_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CONF_DIR)
PROJECT_NAME = "Owliver"
CONF_DIR_NAME = os.path.relpath(CONF_DIR,BASE_DIR)

LOGIN_URL = reverse_lazy("accounts:login")
LOGOUT_URL = reverse_lazy("accounts:logout")
LOGIN_REDIRECT_URL = reverse_lazy("main:index")
LOGOUT_REDIRECT_URL = LOGIN_REDIRECT_URL

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '$_nu@^oulpl25@7y$yoxqotale9zx2^znm)reu+nr%oqxp8-5k'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'main',
	'accounts',
)

MIDDLEWARE_CLASSES = (
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = CONF_DIR_NAME+'.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [os.path.join(BASE_DIR,"templates")],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
				'main.context_processors.settings_processor'
			],
		},
	},
]

WSGI_APPLICATION = CONF_DIR_NAME+'.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': os.path.join(BASE_DIR, 'sqlite3.db'),
	}
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (os.path.join(BASE_DIR,'static'),)

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR,'media')
