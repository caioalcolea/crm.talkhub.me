from django.urls import include, path
from rest_framework.routers import DefaultRouter

from financeiro.api_views import (
    DashboardReportView,
    EntityFinancialReportView,
    FluxoPlanoContasReportView,
    FormaPagamentoViewSet,
    FormOptionsView,
    LancamentoViewSet,
    ParcelaViewSet,
    PaymentTransactionViewSet,
    PixGenerateView,
    PlanoDeContasGrupoViewSet,
    PlanoDeContasViewSet,
    RelatorioMensalReportView,
)

app_name = "financeiro"

router = DefaultRouter()
router.register(
    r"plano-de-contas/grupos", PlanoDeContasGrupoViewSet, basename="plano-grupo"
)
router.register(r"plano-de-contas", PlanoDeContasViewSet, basename="plano-contas")
router.register(r"formas-pagamento", FormaPagamentoViewSet, basename="forma-pagamento")
router.register(r"lancamentos", LancamentoViewSet, basename="lancamento")
router.register(r"parcelas", ParcelaViewSet, basename="parcela")
router.register(r"pix/transactions", PaymentTransactionViewSet, basename="pix-transaction")

urlpatterns = [
    path("", include(router.urls)),
    # PIX
    path("pix/generate/", PixGenerateView.as_view(), name="pix-generate"),
    # Reports
    path("reports/dashboard/", DashboardReportView.as_view(), name="report-dashboard"),
    path(
        "reports/fluxo-plano-contas/",
        FluxoPlanoContasReportView.as_view(),
        name="report-fluxo-plano-contas",
    ),
    path(
        "reports/relatorio-mensal/",
        RelatorioMensalReportView.as_view(),
        name="report-mensal",
    ),
    path(
        "reports/by-entity/<uuid:pk>/",
        EntityFinancialReportView.as_view(),
        name="report-entity",
    ),
    # Form options
    path("form-options/", FormOptionsView.as_view(), name="form-options"),
]
