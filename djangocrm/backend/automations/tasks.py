"""
Celery tasks do app automations.

- process_due_routines: Verifica e executa Routines com schedule pendente.
- execute_routine: Executa uma Routine individual.
"""

import logging
import time

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from common.tasks import set_rls_context

logger = logging.getLogger(__name__)

# Máximo de erros consecutivos antes de desativar
MAX_CONSECUTIVE_ERRORS = 10


def _parse_cron_due(config_json, last_run_at):
    """
    Verifica se uma Routine está pendente de execução baseado no schedule_cron.

    config_json.schedule_cron pode ser:
    - Um dict com campos: minute, hour, day_of_week, day_of_month (estilo crontab)
    - Ou um int/string representando intervalo em minutos (simplificado)

    Retorna True se a execução está pendente.
    """
    schedule = config_json.get("schedule_cron")
    if not schedule:
        return False

    now = timezone.now()

    # Modo simplificado: intervalo em minutos
    if isinstance(schedule, (int, float)):
        if not last_run_at:
            return True
        elapsed = (now - last_run_at).total_seconds() / 60
        return elapsed >= schedule

    if isinstance(schedule, str) and schedule.isdigit():
        interval = int(schedule)
        if not last_run_at:
            return True
        elapsed = (now - last_run_at).total_seconds() / 60
        return elapsed >= interval

    # Modo crontab dict: verificar se o minuto atual bate
    if isinstance(schedule, dict):
        minute = schedule.get("minute", "*")
        hour = schedule.get("hour", "*")

        if minute != "*" and now.minute != int(minute):
            return False
        if hour != "*" and now.hour != int(hour):
            return False

        day_of_week = schedule.get("day_of_week", "*")
        if day_of_week != "*" and now.weekday() != int(day_of_week):
            return False

        day_of_month = schedule.get("day_of_month", "*")
        if day_of_month != "*" and now.day != int(day_of_month):
            return False

        # Evitar execução duplicada no mesmo minuto
        if last_run_at:
            same_minute = (
                last_run_at.year == now.year
                and last_run_at.month == now.month
                and last_run_at.day == now.day
                and last_run_at.hour == now.hour
                and last_run_at.minute == now.minute
            )
            if same_minute:
                return False

        return True

    return False


def _execute_action(action_type, action_params, org_id):
    """
    Executa uma ação de Routine.

    action_types suportados:
    - send_email: Envia email via SMTP
    - create_task: Cria uma Task no CRM
    - update_field: Atualiza campo de um model
    - send_notification: Cria notificação in-app (log)
    """
    if action_type == "send_email":
        to_email = action_params.get("to")
        subject = action_params.get("subject", "Automação TalkHub CRM")
        body = action_params.get("body", "")
        template = action_params.get("template")

        if not to_email:
            raise ValueError("Parâmetro 'to' é obrigatório para send_email")

        if template:
            html_content = render_to_string(template, action_params.get("context", {}))
        else:
            html_content = f"<p>{body}</p>"

        msg = EmailMessage(
            subject,
            html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email] if isinstance(to_email, str) else to_email,
        )
        msg.content_subtype = "html"
        msg.send()
        return {"sent_to": to_email}

    elif action_type == "create_task":
        from tasks.models import Task
        from common.models import Org

        org = Org.objects.get(id=org_id)
        title = action_params.get("title", "Tarefa automática")
        description = action_params.get("description", "")
        priority = action_params.get("priority", "Normal")

        task = Task.objects.create(
            org=org,
            title=title,
            status="New",
            priority=priority,
        )
        return {"task_id": str(task.id), "title": title}

    elif action_type == "update_field":
        from django.apps import apps

        app_label = action_params.get("app_label")
        model_name = action_params.get("model_name")
        record_id = action_params.get("record_id")
        field_name = action_params.get("field_name")
        new_value = action_params.get("new_value")

        if not all([app_label, model_name, record_id, field_name]):
            raise ValueError(
                "update_field requer: app_label, model_name, record_id, field_name, new_value"
            )

        Model = apps.get_model(app_label, model_name)
        # Enforce RLS: only update records belonging to the current org
        if hasattr(Model, 'org_id'):
            obj = Model.objects.get(id=record_id, org_id=org_id)
        else:
            raise ValueError(
                f"update_field não suportado para modelo sem org: {model_name}"
            )
        setattr(obj, field_name, new_value)
        obj.save(update_fields=[field_name, "updated_at"])
        return {"updated": f"{model_name}.{field_name}", "record_id": str(record_id)}

    elif action_type == "send_notification":
        # Log-based notification (in-app)
        message = action_params.get("message", "Notificação automática")
        logger.info("Notification [org=%s]: %s", org_id, message)
        return {"notification": message}

    else:
        raise ValueError(f"action_type desconhecido: {action_type}")


def _validate_routine_config(config_json):
    """Valida config_json para tipo routine."""
    if not isinstance(config_json, dict):
        return False, "config_json deve ser um dicionário"

    if "schedule_cron" not in config_json:
        return False, "Campo 'schedule_cron' é obrigatório"

    if "action_type" not in config_json:
        return False, "Campo 'action_type' é obrigatório"

    valid_actions = ["send_email", "create_task", "update_field", "send_notification"]
    if config_json["action_type"] not in valid_actions:
        return False, f"action_type inválido. Opções: {', '.join(valid_actions)}"

    return True, None


@shared_task(name="automations.tasks.execute_routine")
def execute_routine(automation_id, org_id):
    """Executa uma Routine individual."""
    set_rls_context(org_id)

    from automations.models import Automation, AutomationLog

    start = time.monotonic()

    try:
        automation = Automation.objects.get(id=automation_id, org_id=org_id)
    except Automation.DoesNotExist:
        logger.error("Routine %s not found for org %s", automation_id, org_id)
        return

    if not automation.is_active:
        return

    config = automation.config_json
    action_type = config.get("action_type")
    action_params = config.get("action_params", {})

    try:
        result = _execute_action(action_type, action_params, org_id)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Sucesso: resetar error_count, incrementar run_count
        automation.last_run_at = timezone.now()
        automation.run_count += 1
        automation.error_count = 0
        automation.save(update_fields=["last_run_at", "run_count", "error_count", "updated_at"])

        AutomationLog.objects.create(
            org_id=org_id,
            automation=automation,
            status="success",
            trigger_data={"schedule": config.get("schedule_cron")},
            result_data=result or {},
            execution_time_ms=elapsed_ms,
        )

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        error_msg = str(exc)
        logger.exception("Routine %s failed: %s", automation_id, error_msg)

        automation.last_run_at = timezone.now()
        automation.error_count += 1
        automation.save(update_fields=["last_run_at", "error_count", "updated_at"])

        AutomationLog.objects.create(
            org_id=org_id,
            automation=automation,
            status="error",
            trigger_data={"schedule": config.get("schedule_cron")},
            error_detail=error_msg,
            execution_time_ms=elapsed_ms,
        )

        # Desativar após MAX_CONSECUTIVE_ERRORS erros consecutivos
        if automation.error_count >= MAX_CONSECUTIVE_ERRORS:
            automation.is_active = False
            automation.save(update_fields=["is_active", "updated_at"])
            logger.warning(
                "Routine %s desativada após %d erros consecutivos",
                automation.name,
                MAX_CONSECUTIVE_ERRORS,
            )
            _notify_admin_deactivation(automation, org_id)


def _notify_admin_deactivation(automation, org_id):
    """Notifica admin da org que uma Routine foi desativada por erros."""
    try:
        from common.models import Org

        org = Org.objects.get(id=org_id)
        # Buscar admins da org
        from common.models import Profile

        admins = Profile.objects.filter(
            org=org, role="ADMIN", is_active=True
        ).select_related("user")

        if not admins.exists():
            return

        admin_emails = [p.user.email for p in admins if p.user.email]
        if not admin_emails:
            return

        subject = f"Automação desativada: {automation.name}"
        html_content = render_to_string(
            "automations/routine_deactivated.html",
            {
                "automation_name": automation.name,
                "error_count": automation.error_count,
                "org_name": org.name,
            },
        )

        msg = EmailMessage(
            subject,
            html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        msg.content_subtype = "html"
        msg.send()
    except Exception:
        logger.exception("Failed to notify admin about routine deactivation")


@shared_task(name="automations.tasks.process_due_routines")
def process_due_routines():
    """
    Verifica todas as Routines ativas e despacha execução para as pendentes.
    Roda a cada minuto via Celery Beat.
    """
    from automations.models import Automation
    from common.models import Org

    # Buscar todas as orgs que têm routines ativas
    org_ids = (
        Automation.objects.filter(
            automation_type="routine",
            is_active=True,
        )
        .values_list("org_id", flat=True)
        .distinct()
    )

    dispatched = 0
    for org_id in org_ids:
        set_rls_context(org_id)

        routines = Automation.objects.filter(
            org_id=org_id,
            automation_type="routine",
            is_active=True,
        )

        for routine in routines:
            # Validar config
            valid, error = _validate_routine_config(routine.config_json)
            if not valid:
                logger.warning(
                    "Routine %s config inválida: %s", routine.name, error
                )
                continue

            # Verificar se está pendente
            if _parse_cron_due(routine.config_json, routine.last_run_at):
                execute_routine.delay(str(routine.id), str(org_id))
                dispatched += 1

    if dispatched:
        logger.info("Dispatched %d routines for execution", dispatched)


@shared_task(name="automations.tasks.execute_logic_rule")
def execute_logic_rule(automation_id, org_id, instance_data=None, event_name=""):
    """Executa as ações de uma LogicRule."""
    set_rls_context(org_id)

    from automations.models import Automation, AutomationLog

    start = time.monotonic()

    try:
        automation = Automation.objects.get(id=automation_id, org_id=org_id)
    except Automation.DoesNotExist:
        logger.error("LogicRule %s not found for org %s", automation_id, org_id)
        return

    if not automation.is_active:
        return

    config = automation.config_json
    actions = config.get("actions", [])
    results = []
    errors = []

    # Isolamento de falha: executar cada ação independentemente
    for action in actions:
        action_type = action.get("action_type")
        action_params = action.get("action_params", {})
        try:
            result = _execute_action(action_type, action_params, org_id)
            results.append({"action_type": action_type, "status": "success", "result": result})
        except Exception as exc:
            error_msg = str(exc)
            logger.exception(
                "LogicRule %s action %s failed: %s",
                automation.name, action_type, error_msg,
            )
            errors.append({"action_type": action_type, "error": error_msg})

    elapsed_ms = int((time.monotonic() - start) * 1000)

    # Atualizar contadores
    automation.last_run_at = timezone.now()
    automation.run_count += 1
    if errors and not results:
        automation.error_count += 1
    else:
        automation.error_count = 0
    automation.save(update_fields=["last_run_at", "run_count", "error_count", "updated_at"])

    # Determinar status do log
    if errors and not any(r["status"] == "success" for r in results):
        log_status = "error"
    elif errors:
        log_status = "success"  # Parcial — pelo menos uma ação funcionou
    else:
        log_status = "success"

    AutomationLog.objects.create(
        org_id=org_id,
        automation=automation,
        status=log_status,
        trigger_data={"event": event_name, "instance": instance_data or {}},
        result_data={"actions": results, "errors": errors},
        error_detail="; ".join(e["error"] for e in errors) if errors else "",
        execution_time_ms=elapsed_ms,
    )


def _execute_social_action(action_type, action_params, org_id, webhook_data):
    """
    Executa uma ação de SocialAutomation.

    action_types suportados:
    - auto_reply: Responder automaticamente via canal
    - assign_to_user: Atribuir conversa a um usuário
    - create_lead: Criar lead a partir do contato
    - add_tag: Adicionar tag ao contato
    - send_to_automation_router: Despachar via AutomationRouter
    """
    if action_type == "auto_reply":
        message = action_params.get("message", "")
        if not message:
            raise ValueError("Parâmetro 'message' é obrigatório para auto_reply")

        # Enviar via TalkHub Omni client
        subscriber_id = webhook_data.get("subscriber_id") or webhook_data.get("from_id")
        if subscriber_id:
            try:
                from talkhub_omni.client import TalkHubClient
                from talkhub_omni.models import TalkHubConnection
                from common.models import Org

                org = Org.objects.get(id=org_id)
                conn = TalkHubConnection.objects.filter(org=org, is_active=True).first()
                if conn:
                    client = TalkHubClient(conn)
                    client.send_message(subscriber_id, message)
                    return {"replied_to": subscriber_id, "message": message}
            except Exception as exc:
                logger.warning("auto_reply failed: %s", exc)
                raise
        return {"status": "no_subscriber_id"}

    elif action_type == "assign_to_user":
        user_id = action_params.get("user_id")
        if not user_id:
            raise ValueError("Parâmetro 'user_id' é obrigatório para assign_to_user")
        # Lógica de atribuição depende do contexto (conversa, ticket, etc.)
        return {"assigned_to": user_id}

    elif action_type == "create_lead":
        from leads.models import Lead
        from common.models import Org

        org = Org.objects.get(id=org_id)
        subscriber_name = webhook_data.get("subscriber_name", "")
        subscriber_email = webhook_data.get("subscriber_email", "")

        title = action_params.get("title", f"Lead via {webhook_data.get('channel', 'social')}")
        lead = Lead.objects.create(
            org=org,
            title=title,
            first_name=subscriber_name.split(" ")[0] if subscriber_name else "",
            last_name=" ".join(subscriber_name.split(" ")[1:]) if subscriber_name else "",
            email=subscriber_email,
            status="assigned",
            source="social",
        )
        return {"lead_id": str(lead.id), "title": title}

    elif action_type == "add_tag":
        tag_name = action_params.get("tag_name")
        if not tag_name:
            raise ValueError("Parâmetro 'tag_name' é obrigatório para add_tag")
        # Criar ou buscar tag e associar ao contato
        from common.models import Tags, Org

        org = Org.objects.get(id=org_id)
        tag, _ = Tags.objects.get_or_create(org=org, name=tag_name)
        return {"tag_id": str(tag.id), "tag_name": tag_name}

    elif action_type == "send_to_automation_router":
        # Delegar ao AutomationRouter (Task 23)
        channel = action_params.get("channel", "internal")
        message = action_params.get("message", "")
        recipient = action_params.get("recipient", {})

        from automations.router import dispatch

        result = dispatch(
            org_id=org_id,
            channel=channel,
            recipient=recipient,
            message=message,
            metadata={"source": "social_automation", "webhook_data": webhook_data},
        )
        return result

    else:
        raise ValueError(f"Social action_type desconhecido: {action_type}")


@shared_task(name="automations.tasks.execute_social_automation")
def execute_social_automation(
    automation_id, org_id, webhook_data=None, social_event="", channel_type=""
):
    """Executa as ações de uma SocialAutomation."""
    set_rls_context(org_id)

    from automations.models import Automation, AutomationLog

    start = time.monotonic()

    try:
        automation = Automation.objects.get(id=automation_id, org_id=org_id)
    except Automation.DoesNotExist:
        logger.error("SocialAutomation %s not found for org %s", automation_id, org_id)
        return

    if not automation.is_active:
        return

    config = automation.config_json
    actions = config.get("actions", [])
    results = []
    errors = []

    for action in actions:
        action_type = action.get("action_type")
        action_params = action.get("action_params", {})
        try:
            result = _execute_social_action(
                action_type, action_params, org_id, webhook_data or {}
            )
            results.append({"action_type": action_type, "status": "success", "result": result})
        except Exception as exc:
            error_msg = str(exc)
            logger.exception(
                "SocialAutomation %s action %s failed: %s",
                automation.name, action_type, error_msg,
            )
            errors.append({"action_type": action_type, "error": error_msg})

    elapsed_ms = int((time.monotonic() - start) * 1000)

    automation.last_run_at = timezone.now()
    automation.run_count += 1
    if errors and not results:
        automation.error_count += 1
    else:
        automation.error_count = 0
    automation.save(update_fields=["last_run_at", "run_count", "error_count", "updated_at"])

    log_status = "error" if (errors and not any(r["status"] == "success" for r in results)) else "success"

    AutomationLog.objects.create(
        org_id=org_id,
        automation=automation,
        status=log_status,
        trigger_data={
            "social_event": social_event,
            "channel_type": channel_type,
            "webhook_data": webhook_data or {},
        },
        result_data={"actions": results, "errors": errors},
        error_detail="; ".join(e["error"] for e in errors) if errors else "",
        execution_time_ms=elapsed_ms,
    )
