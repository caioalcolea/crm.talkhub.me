"""
Management command to seed default Centro de Custo and Formas de Pagamento for organizations.

Usage:
    python manage.py seed_org_defaults --all-orgs
    python manage.py seed_org_defaults --org-id UUID
    python manage.py seed_org_defaults --all-orgs --force   # Re-create even if already exist
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from common.models import Org
from common.rls import get_set_context_sql


# 12 default Centro de Custo groups with sub-contas
DEFAULT_GRUPOS = [
    {
        "codigo": "REC-01",
        "nome": "Receita de Vendas",
        "applies_to": "RECEBER",
        "color": "#10B981",
        "ordem": 1,
        "contas": ["Produtos", "Serviços", "Assinaturas"],
    },
    {
        "codigo": "REC-02",
        "nome": "Receita Financeira",
        "applies_to": "RECEBER",
        "color": "#34D399",
        "ordem": 2,
        "contas": ["Juros", "Rendimentos", "Descontos Obtidos"],
    },
    {
        "codigo": "REC-03",
        "nome": "Outras Receitas",
        "applies_to": "RECEBER",
        "color": "#6EE7B7",
        "ordem": 3,
        "contas": ["Reembolsos", "Bonificações"],
    },
    {
        "codigo": "DESP-01",
        "nome": "Pessoal",
        "applies_to": "PAGAR",
        "color": "#F87171",
        "ordem": 4,
        "contas": ["Salários", "Benefícios", "FGTS/INSS", "Vale Transporte/Alimentação"],
    },
    {
        "codigo": "DESP-02",
        "nome": "Infraestrutura",
        "applies_to": "PAGAR",
        "color": "#FB923C",
        "ordem": 5,
        "contas": ["Aluguel", "Energia", "Internet/Telefone", "Água", "Condomínio"],
    },
    {
        "codigo": "DESP-03",
        "nome": "Tecnologia",
        "applies_to": "PAGAR",
        "color": "#A78BFA",
        "ordem": 6,
        "contas": ["Software/SaaS", "Hardware", "Hospedagem/Cloud"],
    },
    {
        "codigo": "DESP-04",
        "nome": "Marketing",
        "applies_to": "PAGAR",
        "color": "#F472B6",
        "ordem": 7,
        "contas": ["Anúncios", "Eventos", "Material Gráfico"],
    },
    {
        "codigo": "DESP-05",
        "nome": "Administrativo",
        "applies_to": "PAGAR",
        "color": "#FBBF24",
        "ordem": 8,
        "contas": ["Material Escritório", "Contabilidade", "Jurídico"],
    },
    {
        "codigo": "DESP-06",
        "nome": "Impostos e Taxas",
        "applies_to": "PAGAR",
        "color": "#EF4444",
        "ordem": 9,
        "contas": ["ISS", "ICMS", "PIS/COFINS", "IRPJ/CSLL", "Taxas Bancárias"],
    },
    {
        "codigo": "DESP-07",
        "nome": "Transporte e Logística",
        "applies_to": "PAGAR",
        "color": "#F97316",
        "ordem": 10,
        "contas": ["Combustível", "Manutenção Veículos", "Frete"],
    },
    {
        "codigo": "DESP-08",
        "nome": "Comercial",
        "applies_to": "PAGAR",
        "color": "#818CF8",
        "ordem": 11,
        "contas": ["Comissões", "Viagens", "Entretenimento Clientes"],
    },
    {
        "codigo": "GER-01",
        "nome": "Sem Centro de Custo",
        "applies_to": "AMBOS",
        "color": "#6B7280",
        "ordem": 99,
        "contas": ["Geral"],
    },
]

# 8 active default payment methods
DEFAULT_FORMAS_PAGAMENTO = [
    "Pix",
    "Pix Automático",
    "Boleto",
    "Cartão de Crédito",
    "Cartão de Débito",
    "TED",
    "Débito Automático",
    "Dinheiro",
]


def seed_for_org(org, force=False, stdout=None):
    """
    Seed default Centro de Custo groups/contas and Formas de Pagamento for a single org.
    Uses get_or_create to be idempotent. Safe to run multiple times.

    Args:
        org: Org instance
        force: If True, recreate inactive items as active
        stdout: Optional output stream for logging
    """
    from financeiro.models import FormaPagamento, PlanoDeContas, PlanoDeContasGrupo

    # Set RLS context
    with connection.cursor() as cursor:
        cursor.execute(get_set_context_sql(), [str(org.id)])

    grupos_created = 0
    contas_created = 0

    for grupo_data in DEFAULT_GRUPOS:
        grupo, created = PlanoDeContasGrupo.objects.get_or_create(
            codigo=grupo_data["codigo"],
            org=org,
            defaults={
                "nome": grupo_data["nome"],
                "descricao": "",
                "is_active": True,
                "ordem": grupo_data["ordem"],
                "color": grupo_data["color"],
                "applies_to": grupo_data["applies_to"],
                "is_system_default": True,
            },
        )
        if created:
            grupos_created += 1
        elif force:
            # Update fields if force mode
            grupo.is_active = True
            grupo.is_system_default = True
            grupo.color = grupo_data["color"]
            grupo.applies_to = grupo_data["applies_to"]
            grupo.ordem = grupo_data["ordem"]
            grupo.save(update_fields=[
                "is_active", "is_system_default", "color", "applies_to", "ordem", "updated_at",
            ])

        # Create contas within this grupo
        for idx, conta_nome in enumerate(grupo_data["contas"]):
            conta, c_created = PlanoDeContas.objects.get_or_create(
                grupo=grupo,
                nome=conta_nome,
                org=org,
                defaults={
                    "descricao": "",
                    "is_active": True,
                    "is_system_default": True,
                    "sort_order": idx,
                },
            )
            if c_created:
                contas_created += 1
            elif force:
                conta.is_active = True
                conta.is_system_default = True
                conta.sort_order = idx
                conta.save(update_fields=["is_active", "is_system_default", "sort_order", "updated_at"])

    # Formas de Pagamento
    formas_created = 0
    for nome in DEFAULT_FORMAS_PAGAMENTO:
        _, created = FormaPagamento.objects.get_or_create(
            nome=nome,
            org=org,
            defaults={"is_active": True},
        )
        if created:
            formas_created += 1

    if stdout:
        stdout.write(
            f"  Org {org.name}: {grupos_created} grupos, {contas_created} contas, "
            f"{formas_created} formas de pagamento criados"
        )

    return grupos_created, contas_created, formas_created


class Command(BaseCommand):
    help = "Seed default Centro de Custo and Formas de Pagamento for organizations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-id",
            type=str,
            help="UUID of specific organization to seed",
        )
        parser.add_argument(
            "--all-orgs",
            action="store_true",
            help="Seed all active organizations",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-activate and update existing items",
        )

    def handle(self, *args, **options):
        org_id = options.get("org_id")
        all_orgs = options.get("all_orgs")
        force = options.get("force", False)

        if not org_id and not all_orgs:
            raise CommandError("Specify --org-id UUID or --all-orgs")

        if org_id:
            try:
                orgs = [Org.objects.get(id=org_id)]
            except Org.DoesNotExist:
                raise CommandError(f"Organization {org_id} not found")
        else:
            orgs = list(Org.objects.filter(is_active=True))

        self.stdout.write(f"Seeding defaults for {len(orgs)} organization(s)...")

        total_g, total_c, total_f = 0, 0, 0
        for org in orgs:
            g, c, f = seed_for_org(org, force=force, stdout=self.stdout)
            total_g += g
            total_c += c
            total_f += f

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created {total_g} grupos, {total_c} contas, {total_f} formas de pagamento"
        ))
