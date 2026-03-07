from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accountemail",
            name="recipients",
            field=models.ManyToManyField(
                related_name="received_email", to="contacts.contact"
            ),
        ),
    ]
