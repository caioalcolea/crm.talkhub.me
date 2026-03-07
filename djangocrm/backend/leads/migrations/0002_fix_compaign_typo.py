from django.db import migrations


def fix_compaign_typo(apps, schema_editor):
    Lead = apps.get_model("leads", "Lead")
    Lead.objects.filter(source="compaign").update(source="campaign")


def reverse_fix(apps, schema_editor):
    Lead = apps.get_model("leads", "Lead")
    Lead.objects.filter(source="campaign").update(source="compaign")


class Migration(migrations.Migration):

    dependencies = [
        ("leads", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(fix_compaign_typo, reverse_fix),
    ]
