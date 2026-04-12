from __future__ import annotations

from django.db import migrations, models


def fill_category_names(apps, schema_editor) -> None:
    Category = apps.get_model("blog", "Category")
    for category in Category.objects.all():
        updated_fields = []
        if not getattr(category, "name_en", None):
            category.name_en = category.slug
            updated_fields.append("name_en")
        if not getattr(category, "name_ru", None):
            category.name_ru = category.name_en
            updated_fields.append("name_ru")
        if not getattr(category, "name_kk", None):
            category.name_kk = category.name_en
            updated_fields.append("name_kk")
        if updated_fields:
            category.save(update_fields=updated_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0004_alter_comment_author_alter_post_author_and_more"),
    ]

    operations = [
        migrations.RunPython(fill_category_names, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="category",
            name="name_en",
            field=models.CharField(max_length=100, unique=True, verbose_name="name (English)"),
        ),
        migrations.AlterField(
            model_name="category",
            name="name_ru",
            field=models.CharField(max_length=100, unique=True, verbose_name="name (Russian)"),
        ),
        migrations.AlterField(
            model_name="category",
            name="name_kk",
            field=models.CharField(max_length=100, unique=True, verbose_name="name (Kazakh)"),
        ),
    ]
