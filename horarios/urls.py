from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("introducao/", views.intro, name="intro"),
    path("versoes/", views.versoes, name="versoes"),
    path("turma/", views.turma_list, name="turma_list"),
    path("turma/<slug:curso_slug>/<slug:turma_slug>/", views.turma_detail, name="turma_detail"),
    path("professor/", views.professor_list, name="professor_list"),
    path("professor/<slug>/", views.professor_detail, name="professor_detail"),
    path("sala/", views.sala_list, name="sala_list"),
    path("sala/<slug>/", views.sala_detail, name="sala_detail"),
    path("carga-horaria/", views.carga_horaria, name="carga_horaria"),
    path("cursos/", views.curso_list, name="curso_list"),
    path("curso/<slug>/", views.curso_detail, name="curso_detail"),
    path("campus/administracao/", views.campus_administracao, name="campus_administracao"),
    path("campus/calendario-academico/", views.campus_calendario, name="campus_calendario"),
    path("campus/setor-de-saude/", views.campus_saude, name="campus_saude"),
]
