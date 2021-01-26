# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views
from django.conf.urls.static import static
from .forms import AuthForm
from engine.views import *
from .views import *

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'', include('engine.urls')),
    url(r'^login/$', views.login, {'template_name': 'engine/login.html', 'authentication_form': AuthForm},
        name="login"),
    url(r'^register/$', RegisterView.as_view(), name="register"),
    url(r'^profile/(?P<pk>[0-9]+)$', ProfileView.as_view(), name='profile'),
    url(r'^profile/(?P<pk>[0-9]+)/update_password$', ProfileUpdatePasswordView.as_view(), name='update-password'),
    url(r'^profile/(?P<pk>[0-9]+)/history/(?P<type>[a-z]+)$', ProfileShowRankingHistoryView.as_view(), name='show-history'),
    url(r'^profile/(?P<pk>[0-9]+)/load_data$', ProfileLoadData.as_view(), name='profile-load-data'),
    url(r'^profile/(?P<pk>[0-9]+)/(?P<update_type>[a-z]+)/(?P<key>[a-zA-Z0-9_]+)/(?P<value>[a-zA-Z0-9_ -]+)$',
        ProfileUpdateKeyView.as_view(), name='profile-update-key'),
    url(r'^logout/$', views.logout, {'next_page': '/login'}, name='logout')
]
