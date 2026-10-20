from django.urls import path

from . import views

app_name = "subscriptions"
urlpatterns = [
    path("subscribe/", views.subscribe, name="subscribe"),
    path("confirm/<uuid:token>/", views.confirm, name="confirm"),
    path("unsubscribe/<uuid:token>/", views.unsubscribe, name="unsubscribe"),
    path("one-click/<uuid:token>/", views.one_click_unsubscribe, name="one_click"),
]
