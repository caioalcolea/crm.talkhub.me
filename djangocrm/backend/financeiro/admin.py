from django.contrib import admin

from financeiro.models import (
    FormaPagamento,
    Lancamento,
    Parcela,
    PlanoDeContas,
    PlanoDeContasGrupo,
)


class ParcelaInline(admin.TabularInline):
    model = Parcela
    extra = 0
    readonly_fields = ("numero", "valor_parcela", "data_vencimento", "status")


@admin.register(PlanoDeContasGrupo)
class PlanoDeContasGrupoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "is_active", "org")
    list_filter = ("is_active", "org")
    search_fields = ("codigo", "nome")


@admin.register(PlanoDeContas)
class PlanoDeContasAdmin(admin.ModelAdmin):
    list_display = ("nome", "grupo", "is_active", "org")
    list_filter = ("is_active", "grupo", "org")
    search_fields = ("nome", "grupo__codigo", "grupo__nome")


@admin.register(FormaPagamento)
class FormaPagamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "is_active", "org")
    list_filter = ("is_active", "org")


@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = (
        "descricao",
        "tipo",
        "currency",
        "valor_total",
        "numero_parcelas",
        "status",
        "data_primeiro_vencimento",
        "org",
    )
    list_filter = ("tipo", "status", "currency", "org")
    search_fields = ("descricao",)
    inlines = [ParcelaInline]


@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = (
        "lancamento",
        "numero",
        "valor_parcela",
        "data_vencimento",
        "data_pagamento",
        "status",
    )
    list_filter = ("status", "org")
    search_fields = ("lancamento__descricao",)
