from django.urls import path
from . import grading_views, teaching_views, views

urlpatterns = [
    path("notas/", grading_views.book_list, name="book_list"),
    path("notas/novo/", grading_views.book_form, name="book_create"),
    path("notas/<int:pk>/", grading_views.book_detail, name="book_detail"),
    path("notas/<int:pk>/regras/", grading_views.book_form, name="book_edit"),
    path("notas/<int:book_pk>/avaliacao/nova/", grading_views.assessment_form, name="assessment_create"),
    path("avaliacoes/<int:pk>/editar/", grading_views.assessment_form, name="assessment_edit"),
    path("avaliacoes/<int:pk>/notas/", grading_views.grade_form, name="grade_form"),
    path("avaliacoes/<int:pk>/cancelar/", grading_views.assessment_cancel, name="assessment_cancel"),
    path("", views.dashboard, name="dashboard"),
    path("criar-conta/", views.register, name="register"),
    path("turmas/<int:pk>/", views.classroom_detail, name="classroom_detail"),
    path("aulas/", teaching_views.lesson_list, name="lesson_list"),
    path("aulas/nova/", teaching_views.lesson_choose, name="lesson_choose"),
    path("turmas/<int:classroom_pk>/aulas/nova/", teaching_views.lesson_form, name="lesson_create"),
    path("aulas/<int:pk>/", teaching_views.lesson_detail, name="lesson_detail"),
    path("aulas/<int:pk>/editar/", teaching_views.lesson_form, name="lesson_edit"),
    path("aulas/<int:pk>/chamada/", teaching_views.attendance_form, name="attendance_form"),
    path("aulas/<int:pk>/cancelar/", teaching_views.lesson_cancel, name="lesson_cancel"),
    path("turmas/<int:pk>/frequencia/", teaching_views.classroom_frequency, name="classroom_frequency"),
    path("cadastros/<slug:kind>/", views.record_list, name="record_list"),
    path("cadastros/<slug:kind>/novo/", views.record_form, name="record_create"),
    path("cadastros/<slug:kind>/<int:pk>/editar/", views.record_form, name="record_edit"),
]

