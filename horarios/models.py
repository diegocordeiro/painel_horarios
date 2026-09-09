from django.db import models

from .slug import url_slug, versao_slug


class Versao(models.Model):
    """Uma versão/histórico do quadro de horários (equivale a siteVersions.json)."""

    versao = models.CharField("Versão", max_length=40, unique=True)
    inicio = models.DateField("Início")
    fim = models.DateField("Fim", null=True, blank=True)
    atual = models.BooleanField("Versão atual", default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    @property
    def slug(self) -> str:
        return versao_slug(self.versao)

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "Versão"
        verbose_name_plural = "Versões"

    def __str__(self) -> str:
        return self.versao


class Curso(models.Model):
    """Um curso do campus (equivale a docs/cursos/*.mdx)."""

    TIPO_CHOICES = [
        ("Técnico Integrado", "Técnico Integrado"),
        ("Técnico Subsequente", "Técnico Subsequente"),
        ("Técnico (PROEJA)", "Técnico (PROEJA)"),
        ("Licenciatura", "Licenciatura"),
        ("Tecnologia", "Tecnologia"),
    ]

    nome = models.CharField("Nome", max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    tipo = models.CharField("Tipo", max_length=40, choices=TIPO_CHOICES, blank=True)
    modalidade = models.CharField("Modalidade", max_length=200, blank=True)
    turno = models.CharField("Turno", max_length=200, blank=True)
    carga_horaria = models.CharField("Carga horária", max_length=200, blank=True)
    duracao = models.CharField("Duração", max_length=200, blank=True)
    coordenador = models.CharField("Coordenador(a)", max_length=200, blank=True)
    email = models.EmailField("E-mail", blank=True)
    lattes = models.URLField("Lattes", blank=True)
    posicao = models.IntegerField("Posição", default=9999)
    ppcs = models.JSONField("PPCs", default=list, blank=True)

    class Meta:
        ordering = ["posicao", "nome"]
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = url_slug(self.nome)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.nome


class Professor(models.Model):
    """Um professor (equivale a docs/professor/*.mdx)."""

    nome = models.CharField("Nome", max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = url_slug(self.nome)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.nome


class Sala(models.Model):
    """Uma sala/laboratório (equivale a docs/sala/*.mdx)."""

    nome = models.CharField("Nome", max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    predio = models.CharField("Prédio", max_length=200, blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Sala"
        verbose_name_plural = "Salas"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = url_slug(self.nome)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.nome


class Turma(models.Model):
    """Uma turma (equivale a docs/turma/<curso>/t_*.mdx)."""

    curso = models.ForeignKey(Curso, related_name="turmas", on_delete=models.CASCADE)
    nome_completo = models.CharField("Nome completo", max_length=300, unique=True)
    slug = models.SlugField(max_length=300, blank=True)
    rotulo = models.CharField("Rótulo", max_length=200, blank=True)

    class Meta:
        ordering = ["curso__posicao", "nome_completo"]
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = url_slug(self.nome_completo)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.nome_completo


class Aula(models.Model):
    """Um bloco de aula (equivale a uma célula do Grid, já com slots contíguos unidos)."""

    versao = models.ForeignKey(Versao, related_name="aulas", on_delete=models.CASCADE)
    atividade_id = models.CharField("Activity Id", max_length=50, blank=True)
    disciplina = models.CharField("Disciplina", max_length=200)
    dia_semana = models.CharField("Dia da semana", max_length=30)
    hora_inicio = models.CharField("Hora início", max_length=5)
    hora_fim = models.CharField("Hora fim", max_length=5)
    tag = models.CharField("Tag", max_length=30, blank=True)
    sala = models.ForeignKey(
        Sala, related_name="aulas", null=True, blank=True, on_delete=models.SET_NULL
    )
    professores = models.ManyToManyField(Professor, related_name="aulas", blank=True)
    turmas = models.ManyToManyField(Turma, related_name="aulas", blank=True)

    class Meta:
        ordering = ["dia_semana", "hora_inicio"]
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"

    def __str__(self) -> str:
        return f"{self.disciplina} ({self.hora_inicio}-{self.hora_fim})"
