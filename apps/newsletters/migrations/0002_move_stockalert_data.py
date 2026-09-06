from django.db import migrations


def copy_stock_alerts(apps, schema_editor):
    OldAlert = apps.get_model("figures", "StockAlert")
    NewAlert = apps.get_model("newsletters", "StockAlert")
    for old in OldAlert.objects.all().iterator():
        new, created = NewAlert.objects.get_or_create(
            figure_id=old.figure_id,
            email=old.email,
            defaults={
                "is_notified": old.is_notified,
                "is_active": old.is_active,
            },
        )
        if created:
            NewAlert.objects.filter(pk=new.pk).update(
                created_at=old.created_at, updated_at=old.updated_at
            )


def copy_stock_alerts_back(apps, schema_editor):
    NewAlert = apps.get_model("newsletters", "StockAlert")
    OldAlert = apps.get_model("figures", "StockAlert")
    for new in NewAlert.objects.all().iterator():
        old, created = OldAlert.objects.get_or_create(
            figure_id=new.figure_id,
            email=new.email,
            defaults={
                "is_notified": new.is_notified,
                "is_active": new.is_active,
            },
        )
        if created:
            OldAlert.objects.filter(pk=old.pk).update(
                created_at=new.created_at, updated_at=new.updated_at
            )


class Migration(migrations.Migration):
    dependencies = [
        ("figures", "0006_stockalert"),
        ("newsletters", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_stock_alerts, copy_stock_alerts_back),
    ]
