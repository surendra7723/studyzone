import compileall
import re
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Ahead-of-time (AOT) compiles project files while ignoring templates and environments."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting optimized AOT compilation..."))
        
        # Regex pattern to ignore templates, virtual envs, git, and logs
        ignore_pattern = re.compile(r'(\.git|venv|\.venv|django-app-template|.*\.py-tpl|docs|notes|studyzone\.log)')
        
        success = compileall.compile_dir(
            settings.BASE_DIR,
            maxlevels=10,
            force=True,
            quiet=1,
            legacy=True,  # Keeps .pyc files next to .py files
            rx=ignore_pattern  # Applies the exclusion filter
        )

        if success:
            self.stdout.write(self.style.SUCCESS("Successfully compiled active apps and configurations!"))
        else:
            self.stdout.write(self.style.ERROR("Compilation completed with errors in unignored files."))
