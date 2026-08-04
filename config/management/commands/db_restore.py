import os
import subprocess
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Restores the PostgreSQL database from a chosen backup file."

    def add_arguments(self, parser):
        parser.add_argument(
            'filename', 
            type=str, 
            help='The exact filename of the backup located in the backups/ folder.'
        )

    def handle(self, *args, **options):
        # 1. Fetch DB configurations dynamically
        db_config = settings.DATABASES.get('default')
        
        if not db_config or db_config.get('ENGINE') != 'django.db.backends.postgresql':
            self.stdout.write(self.style.ERROR("Error: This command only supports PostgreSQL databases."))
            return

        db_name = db_config.get('NAME')
        db_user = db_config.get('USER')
        db_password = db_config.get('PASSWORD')
        db_host = db_config.get('HOST', 'localhost')
        db_port = db_config.get('PORT', '5432')

        # 2. Locate the backup file
        backup_file = Path(settings.BASE_DIR) / 'backups' / options['filename']
        if not backup_file.exists():
            self.stdout.write(self.style.ERROR(f"Error: File not found at {backup_file}"))
            return

        # 3. Confirm destructive action with user
        self.stdout.write(self.style.WARNING(f"WARNING: This will completely overwrite database '{db_name}'."))
        confirm = input("Are you absolutely sure you want to proceed? (yes/no): ")
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.ERROR("Restore operation aborted by user."))
            return

        # 4. Setup environment credentials securely
        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = str(db_password)

        self.stdout.write(self.style.WARNING("Dropping active schema connections and restoring..."))

        # 5. Execute destructive pg_restore
        # --clean drops database objects before recreating them
        # --no-owner skips setting object ownership to match production/dev splits
        restore_cmd = f"pg_restore -h {db_host} -p {db_port} -U {db_user} -d {db_name} --clean --no-owner {backup_file}"

        try:
            result = subprocess.run(
                restore_cmd, 
                shell=True, 
                env=env, 
                check=True, 
                stderr=subprocess.PIPE, 
                text=True
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully restored database from: {options['filename']}"))
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR("Restore failed!"))
            if e.stderr:
                self.stdout.write(self.style.ERROR(f"PostgreSQL Error Details: {e.stderr.strip()}"))
