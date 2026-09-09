"""Views de desenvolvimento (o site final é estático; estas servem para prévia local)."""
from django.shortcuts import render, get_object_or_404

from .models import Aula, Curso, Professor, Sala, Turma, Versao
from .static_site import build_grid


def _versao():
    return Versao.objects.filter(atual=True).first() or Versao.objects.order_by("-inicio").first()


def _aulas_filter(versao, **filters):
    return list(
        Aula.objects.filter(versao=versao, **filters).prefetch_related("professores", "turmas", "sala")
    )


def home(request):
    return render(request, "horarios/home.html")


def intro(request):
    versao = _versao()
    history = list(Versao.objects.exclude(id=versao.id) if versao else Versao.objects.none())
    history.sort(key=lambda v: v.inicio, reverse=True)
    return render(request, "horarios/intro.html", {"versao_atual": versao, "history": history})


def versoes(request):
    versao = _versao()
    history = list(Versao.objects.exclude(id=versao.id) if versao else Versao.objects.none())
    history.sort(key=lambda v: v.inicio, reverse=True)
    return render(request, "horarios/versoes.html", {"versao_atual": versao, "history": history})


def turma_list(request):
    versao = _versao()
    cursos = Curso.objects.order_by("posicao", "nome").prefetch_related("turmas")
    return render(request, "horarios/turma_list.html", {"cursos": cursos, "versao": versao})


def turma_detail(request, curso_slug, turma_slug):
    curso = get_object_or_404(Curso, slug=curso_slug)
    turma = get_object_or_404(Turma, slug=turma_slug, curso=curso)
    versao = _versao()
    aulas = [a for a in _aulas_filter(versao) if a.turmas.filter(id=turma.id).exists()]
    return render(
        request,
        "horarios/turma_detail.html",
        {"curso": curso, "turma": turma, "versao": versao, "grid": build_grid(aulas), "kind": "turma"},
    )


def professor_list(request):
    return render(request, "horarios/professor_list.html", {"professores": Professor.objects.all()})


def professor_detail(request, slug):
    prof = get_object_or_404(Professor, slug=slug)
    versao = _versao()
    aulas = [a for a in _aulas_filter(versao) if a.professores.filter(id=prof.id).exists()]
    return render(
        request,
        "horarios/professor_detail.html",
        {"professor": prof, "versao": versao, "grid": build_grid(aulas), "kind": "professor"},
    )


def sala_list(request):
    return render(request, "horarios/sala_list.html", {"salas": Sala.objects.all()})


def sala_detail(request, slug):
    sala = get_object_or_404(Sala, slug=slug)
    versao = _versao()
    aulas = _aulas_filter(versao, sala=sala)
    return render(
        request,
        "horarios/sala_detail.html",
        {"sala": sala, "versao": versao, "grid": build_grid(aulas), "kind": "sala"},
    )


def curso_list(request):
    return render(request, "horarios/curso_list.html", {"cursos": Curso.objects.all()})


def curso_detail(request, slug):
    curso = get_object_or_404(Curso, slug=slug)
    return render(request, "horarios/curso_detail.html", {"curso": curso})


def campus_administracao(request):
    return render(request, "horarios/campus/administracao.html")


def campus_calendario(request):
    return render(request, "horarios/campus/calendario_academico.html")


def campus_saude(request):
    return render(request, "horarios/campus/setor_de_saude.html")
