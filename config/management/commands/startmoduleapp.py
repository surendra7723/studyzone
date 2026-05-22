from pathlib import Path

from django.conf import settings
from django.core.management.commands.startapp import Command as StartAppCommand


class Command(StartAppCommand):
    help = "Creates a modular app inside apps/ using django-app-template."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--dest",
            default="apps",
            help="Parent namespace directory (default: apps)",
        )

    def handle(self, **options):
        app_name = options["name"]
        dest = options.get("dest") or "apps"

        template_path = Path(settings.BASE_DIR) / "django-app-template"
        if not template_path.exists():
            self.stderr.write(
                self.style.ERROR(f"Template directory not found: {template_path}")
            )
            return

        dest_dir = Path(settings.BASE_DIR) / dest
        target_dir = dest_dir / app_name

        if target_dir.exists():
            self.stderr.write(
                self.style.ERROR(f"Target app directory already exists: {target_dir}")
            )
            return

        dest_dir.mkdir(parents=True, exist_ok=True)

        options["template"] = str(template_path)
        options["extension"] = ["py-tpl"]
        options["directory"] = str(target_dir)

        super().handle(**options)

        apps_file = target_dir / "apps.py"
        if apps_file.exists():
            content = apps_file.read_text(encoding="utf-8")
            content = content.replace(
                f'name = "{app_name}"',
                f'name = "{dest}.{app_name}"',
            )
            apps_file.write_text(content, encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Created modular app: {target_dir}"))
        self.stdout.write(f'Add to INSTALLED_APPS: "{dest}.{app_name}"')
