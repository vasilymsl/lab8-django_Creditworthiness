from django.contrib import admin
from django.urls import path

from app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    # ЛР8: один HTTP метод async-сервиса
    path("set_result", views.set_result, name="set-result"),
    path("set_result/", views.set_result, name="set-result-slash"),
    path("health", views.health, name="health"),
    path("health/", views.health, name="health-slash"),
]


