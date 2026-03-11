"""
Add production indexes for conversations:
- GIN index on metadata_json for is_group filtering
- Composite index on (org, assigned_to) for agent filtering
- Composite index on (org, -updated_at) for polling endpoint
"""

from django.conf import settings
from django.db import migrations, models

try:
    from django.contrib.postgres.indexes import GinIndex
except ImportError:
    GinIndex = None


class Migration(migrations.Migration):

    dependencies = [
        ("conversations", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="conversation",
            index=(
                GinIndex(fields=["metadata_json"], name="conv_metadata_gin")
                if GinIndex
                else models.Index(fields=["metadata_json"], name="conv_metadata_gin")
            ),
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["org", "assigned_to"], name="conv_org_assigned"
            ),
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["org", "-updated_at"], name="conv_org_updated"
            ),
        ),
    ]
