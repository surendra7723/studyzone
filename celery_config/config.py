import os
from kombu import Queue

# Core Broker Settings
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://:password@redis-prod:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://:password@redis-prod:6379/1')

# Data Serialization Safety
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Timezone Alignment
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task Routing (Prevents long-running tasks from choking fast tasks)
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = (
    Queue('default', routing_key='default.#'),
    Queue('high_priority', routing_key='high.#'),
    Queue('low_priority', routing_key='low.#'),
)

# Task Execution Controls
CELERY_TASK_ACKS_LATE = True          # Task acknowledged AFTER execution (prevents lost tasks if worker crashes)
CELERY_WORKER_PREFETCH_LIMIT = 1       # Worker takes 1 task at a time (ideal for heavy/unpredictable tasks)
CELERY_TASK_TIME_LIMIT = 30 * 60       # Hard kill task after 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # Raise Exception in task after 25 minutes to allow clean exit
