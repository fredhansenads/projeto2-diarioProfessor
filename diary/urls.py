from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("criar-conta/", views.register, name="register"),
    path("turmas/<int:pk>/", views.classroom_detail, name="classroom_detail"),
    path("cadastros/<slug:kind>/", views.record_list, name="record_list"),
    path("cadastros/<slug:kind>/novo/", views.record_form, name="record_create"),
    path("cadastros/<slug:kind>/<int:pk>/editar/", views.record_form, name="record_edit"),
]

