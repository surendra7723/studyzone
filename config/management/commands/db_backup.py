import os
import subprocess
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Creates a secure compressed backup of the PostgreSQL database."

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

        # 2. Establish backup storage path
        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_filename = f"{db_name}_{timestamp}.sql.gz"
        backup_path = backup_dir / backup_filename

        self.stdout.write(self.style.WARNING(f"Starting PostgreSQL dump for database: '{db_name}'..."))

        # 3. Setup environment credentials securely (avoids plain text CLI exposure)
        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = str(db_password)

        # 4. Construct shell pipeline command for pg_dump and gzip compression
        # Use custom directory format (-F c) for easy pg_restore later
        dump_cmd = f"pg_dump -h {db_host} -p {db_port} -U {db_user} -F c {db_name} > {backup_path}"

        try:
            result = subprocess.run(
                dump_cmd, 
                shell=True, 
                env=env, 
                check=True, 
                stderr=subprocess.PIPE, 
                text=True
            )
            self.stdout.write(self.style.SUCCESS(f"Backup created successfully: {backup_path}"))
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"Backup failed!"))
            if e.stderr:
                self.stdout.write(self.style.ERROR(f"PostgreSQL Error Details: {e.stderr.strip()}"))
