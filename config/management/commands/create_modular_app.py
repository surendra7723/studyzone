from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Deprecated alias for startmoduleapp."

    def add_arguments(self, parser):
        parser.add_argument("app_name", help="Name of the app to create.")
        parser.add_argument(
            "directory",
            nargs="?",
            default="apps",
            help="Destination namespace directory (default: apps).",
        )

    def handle(self, *args, **options):
        app_name = options["app_name"]
        destination = options["directory"]
        self.stdout.write(
            self.style.WARNING("create_modular_app is deprecated; use startmoduleapp.")
        )
        call_command(
            "startmoduleapp",
            app_name,
            dest=destination,
        )
