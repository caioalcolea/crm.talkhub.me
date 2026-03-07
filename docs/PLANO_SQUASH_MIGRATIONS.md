# 🗜️ Plano de Squash (Concatenação) de Migrations — TalkHub CRM

> Data: 2026-03-05
> Objetivo: Consolidar todas as migrations de cada app Django em uma única `0001_initial.py`, eliminando o histórico incremental e simplificando o desenvolvimento.

---

## 1. INVENTÁRIO ATUAL

| App | Migrations | Arquivos |
|-----|-----------|----------|
| **common** | 23 | `0001_initial` → `0023_enable_rls_missing_tables` |
| **accounts** | 7 | `0001_initial` → `0007_alter_account_currency_max_length` |
| **contacts** | 14 | `0001_initial` → `0014_add_omni_correlation_fields` |
| **leads** | 14 | `0001_initial` → `0014_add_omni_ticket_fields` |
| **cases** | 11 | `0001_initial` → `0011_add_omni_ticket_fields` |
| **tasks** | 12 | `0001_initial` → `0012_boardcolumn_talkhub_stage_id` |
| **opportunity** | 12 | `0001_initial` → `0012_goalbreakdown` |
| **invoices** | 8 | `0001_initial` → `0008_alter_currency_max_length` |
| **orders** | 4 | `0001_initial` → `0004_alter_order_currency_max_length` |
| **financeiro** | 2 | `0001_initial` → `0002_paymenttransaction` |
| **integrations** | 4 | `0001_initial` → `0004_add_sync_interval_minutes` |
| **talkhub_omni** | 4 | `0001_initial` → `0004_enable_rls_phase6` |
| **channels** | 1 | `0001_initial` |
| **conversations** | 1 | `0001_initial` |
| **automations** | 1 | `0001_initial` |
| **campaigns** | 1 | `0001_initial` |
| **TOTAL** | **119 arquivos** | 16 apps |

### Apps que já estão limpas (1 migration só)
- channels, conversations, automations, campaigns → **nenhuma ação necessária**

### Apps que precisam de squash (12 apps, 115 migrations → 12)
- common (23→1), contacts (14→1), leads (14→1), tasks (12→1), opportunity (12→1), cases (11→1), invoices (8→1), accounts (7→1), orders (4→1), integrations (4→1), talkhub_omni (4→1), financeiro (2→1)

---

## 2. ESTRATÉGIA: RESET COMPLETO (Nuclear)

Como o usuário confirmou que **pode perder todos os dados**, a estratégia mais limpa e segura é:

### Por que NÃO usar `squashmigrations`?
- O comando `squashmigrations` do Django gera migrations "squashed" que mantêm referência às originais
- Migrations com `RunSQL` (RLS policies) e `RunPython` não são otimizadas pelo squash
- O resultado ainda é confuso e requer limpeza manual
- Com 119 migrations e dependências cruzadas entre apps, o squash incremental é frágil

### Estratégia escolhida: Fresh `makemigrations`
1. Deletar TODAS as migrations existentes
2. Rodar `makemigrations` do zero — Django gera migrations limpas baseadas no estado atual dos models
3. Adicionar migrations customizadas de RLS após as iniciais
4. Recriar o banco do zero (migrate em banco limpo)

---

## 3. PRÉ-REQUISITOS

### 3.1 Backup de Produção (obrigatório)
```bash
# No servidor de produção
BACKEND=$(docker ps -q -f name=djangocrm_crm_backend)
DB=$(docker ps -q -f name=djangocrm_crm_db)

# Dump completo do banco
docker exec $DB pg_dump -U crm_user -d crm_db -F c -f /tmp/crm_backup_pre_squash.dump
docker cp $DB:/tmp/crm_backup_pre_squash.dump ./backups/

# Backup dos arquivos de migration atuais (git já tem, mas por segurança)
tar czf backups/migrations_backup.tar.gz $(find djangocrm/backend -path "*/migrations/*.py" -not -name "__pycache__")
```

### 3.2 Verificar estado atual
```bash
cd djangocrm/backend
python manage.py showmigrations  # Confirmar que todas estão aplicadas
python manage.py check           # Zero erros
python manage.py manage_rls --status  # Documentar estado RLS
```

### 3.3 Garantir que o código está commitado
```bash
git add -A
git commit -m "chore: snapshot antes do squash de migrations"
git tag pre-squash-v1
```

---

## 4. EXECUÇÃO — PASSO A PASSO

### ETAPA 1: Deletar todas as migrations existentes

Deletar todos os arquivos de migration (exceto `__init__.py`) de todas as 16 apps:

```bash
cd djangocrm/backend

# Lista de todas as apps com migrations
APPS=(
  common accounts contacts leads cases tasks opportunity
  invoices orders financeiro integrations talkhub_omni
  channels conversations automations campaigns
)

for app in "${APPS[@]}"; do
  # Remove todos os .py exceto __init__.py
  find "$app/migrations" -name "*.py" -not -name "__init__.py" -delete
  # Remove todos os .pyc
  find "$app/migrations" -name "*.pyc" -delete
  # Remove __pycache__
  rm -rf "$app/migrations/__pycache__"
  echo "✅ Limpo: $app/migrations/"
done
```

### ETAPA 2: Gerar migrations frescas

```bash
cd djangocrm/backend

# Gerar todas as migrations do zero
python manage.py makemigrations
```

Isso vai gerar um `0001_initial.py` para cada app, com o estado final dos models.

**Verificar**: cada app deve ter exatamente 1 arquivo de migration.

```bash
for app in "${APPS[@]}"; do
  count=$(find "$app/migrations" -name "*.py" -not -name "__init__.py" | wc -l)
  echo "$app: $count migrations"
done
```

### ETAPA 3: Criar migration de RLS

Após as migrations iniciais, criar uma migration customizada para habilitar RLS em todas as tabelas org-scoped.

Criar o arquivo `common/migrations/0002_enable_rls_all_tables.py`:

```python
"""
Enable Row-Level Security on all org-scoped tables.
Single consolidated migration replacing all previous RLS migrations.
"""
from django.db import migrations
from common.rls import ORG_SCOPED_TABLES, get_enable_policy_sql, get_disable_policy_sql


def enable_rls(apps, schema_editor):
    """Enable RLS on all org-scoped tables."""
    if schema_editor.connection.vendor != 'postgresql':
        return

    cursor = schema_editor.connection.cursor()
    for table in ORG_SCOPED_TABLES:
        # Check if table exists before enabling RLS
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table]
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_enable_policy_sql(table))


def disable_rls(apps, schema_editor):
    """Disable RLS on all org-scoped tables (reverse)."""
    if schema_editor.connection.vendor != 'postgresql':
        return

    cursor = schema_editor.connection.cursor()
    for table in ORG_SCOPED_TABLES:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s)",
            [table]
        )
        if cursor.fetchone()[0]:
            cursor.execute(get_disable_policy_sql(table))


class Migration(migrations.Migration):

    dependencies = [
        # Depende de TODAS as 0001_initial de todas as apps
        # (para garantir que todas as tabelas existem)
        ("common", "0001_initial"),
        ("accounts", "0001_initial"),
        ("contacts", "0001_initial"),
        ("leads", "0001_initial"),
        ("cases", "0001_initial"),
        ("tasks", "0001_initial"),
        ("opportunity", "0001_initial"),
        ("invoices", "0001_initial"),
        ("orders", "0001_initial"),
        ("financeiro", "0001_initial"),
        ("integrations", "0001_initial"),
        ("talkhub_omni", "0001_initial"),
        ("channels", "0001_initial"),
        ("conversations", "0001_initial"),
        ("automations", "0001_initial"),
        ("campaigns", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
```

### ETAPA 4: Dropar e recriar o banco de dados

```bash
# ATENÇÃO: Isso APAGA todos os dados!

# Opção A: Docker (produção)
docker stack rm djangocrm
sleep 15
docker volume rm crm_db
# Redeploy vai recriar o volume e rodar migrations
./redeploy.sh

# Opção B: Local (desenvolvimento)
cd djangocrm/backend
# Dropar e recriar o banco
psql -U postgres -c "DROP DATABASE IF EXISTS crm_db;"
psql -U postgres -c "CREATE DATABASE crm_db OWNER crm_user;"

# Aplicar migrations do zero
python manage.py migrate

# Recriar superadmin
python manage.py create_default_admin
```

### ETAPA 5: Verificação pós-squash

```bash
cd djangocrm/backend

# 1. Confirmar migrations aplicadas
python manage.py showmigrations

# 2. Verificar integridade dos models
python manage.py check

# 3. Verificar RLS
python manage.py manage_rls --status
python manage.py manage_rls --verify-user

# 4. Rodar testes
pytest --no-cov -x

# 5. Contar migrations (deve ser 17 total: 16x 0001_initial + 1x 0002_enable_rls)
find . -path "*/migrations/0*.py" | wc -l
```

### ETAPA 6: Commit e tag

```bash
git add -A
git commit -m "chore: squash all migrations — fresh 0001_initial per app + consolidated RLS"
git tag post-squash-v1
```

---

## 5. ORDEM DE DEPENDÊNCIAS ENTRE APPS

O Django resolve dependências automaticamente no `makemigrations`, mas para referência:

```
common (User, Org, Profile, Tags, Teams — base de tudo)
  ├── accounts (Account → Org, Profile, Tags, Teams)
  ├── contacts (Contact → Org, Profile, Account, Tags, Teams)
  ├── leads (Lead → Org, Profile, Contact, Tags, Teams, LeadStage)
  ├── cases (Case → Org, Profile, Account, Contact, Tags, Teams, CaseStage)
  ├── tasks (Task → Org, Profile, Account, Contact, Lead, Case, Opportunity, Tags, Teams)
  ├── opportunity (Opportunity → Org, Profile, Account, Contact, Lead, Tags, Teams)
  ├── invoices (Invoice → Org, Profile, Account, Contact, Opportunity, Tags, Teams)
  ├── orders (Order → Org, Account, Contact, Opportunity, Product)
  ├── financeiro (Lancamento → Org, Account, Contact, Opportunity, Invoice)
  ├── integrations (IntegrationConnection → Org)
  ├── talkhub_omni (TalkHubConnection → Org, Profile)
  ├── channels (ChannelConfig → Org)
  ├── conversations (Conversation → Org, Contact, Profile, Tags)
  ├── automations (Automation → Org)
  └── campaigns (Campaign → Org, Contact)
```

---

## 6. RISCOS E MITIGAÇÕES

| Risco | Mitigação |
|-------|-----------|
| Dependências circulares no `makemigrations` | Django resolve automaticamente; se falhar, usar `--name` por app |
| RLS não aplicado após migrate | Migration `0002_enable_rls_all_tables` com verificação de existência |
| Testes falham pós-squash | Testes usam banco in-memory; migrations frescas são compatíveis |
| Produção com dados | Backup obrigatório; reset total do volume `crm_db` |
| `automations` e `campaigns` não em INSTALLED_APPS | Incluir temporariamente para gerar migrations, ou gerar separadamente |

---

## 7. RESULTADO FINAL (EXECUTADO)

### Antes
```
16 apps × N migrations = 119 arquivos de migration
Múltiplas migrations de RLS espalhadas (0002, 0004, 0008, 0010, 0011, 0013, 0020, 0023)
Dependências cruzadas complexas
```

### Depois
```
9 apps com 1 migration (0001_initial.py)
7 apps com 2 migrations (0001_initial.py + 0002_initial.py — split por FKs cross-app)
1 migration consolidada de RLS (common/0002_enable_rls_all_tables.py)
Total: 24 arquivos de migration
Redução: 119 → 24 (80% menos)
82 models criados, 77 tabelas com RLS
Zero conflitos, zero ciclos no grafo
```

### Apps com 2 migrations (split automático do Django por dependências cross-app)
- accounts, cases, invoices, financeiro, channels, automations, campaigns

---

## 8. CHECKLIST DE EXECUÇÃO

- [x] **Pré-requisito**: Backup do banco de produção
- [x] **Pré-requisito**: Código commitado e taggeado (`pre-squash-v1`)
- [x] **Pré-requisito**: `showmigrations` e `check` sem erros
- [x] **Etapa 1**: Deletar todas as migrations existentes (119 arquivos removidos)
- [x] **Etapa 2**: `makemigrations` — gerar migrations frescas (24 arquivos gerados)
- [x] **Etapa 3**: Criar `0002_enable_rls_all_tables.py` (77 tabelas, depende de todas as apps)
- [ ] **Etapa 4**: Dropar e recriar banco + `migrate`
- [ ] **Etapa 5**: Verificação (`showmigrations`, `check`, `manage_rls --status`, `pytest`)
- [ ] **Etapa 6**: Commit e tag (`post-squash-v1`)
- [ ] **Produção**: Redeploy com volume limpo

---

## 9. NOTAS SOBRE `automations` E `campaigns`

Essas apps **não estão em INSTALLED_APPS** mas têm migrations e models. Duas opções:

### Opção A (Recomendada): Adicionar ao INSTALLED_APPS antes do squash
- Adicionar `"automations"` e `"campaigns"` ao `INSTALLED_APPS` em `settings.py`
- Isso permite que `makemigrations` gere as migrations corretamente
- As tabelas serão criadas no banco e o RLS será aplicado

### Opção B: Manter fora e gerar separadamente
- Gerar migrations manualmente: `python manage.py makemigrations automations campaigns`
- Risco: dependências podem não ser resolvidas corretamente

**Recomendação**: Opção A — aproveitar o squash para regularizar essas apps.
