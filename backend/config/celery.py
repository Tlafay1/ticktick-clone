"""Application Celery du clone TickTick.

Worker + beat pour le déclenchement des rappels et la purge de corbeille.
Lancement : `celery -A config worker` et `celery -A config beat`.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("ticktick")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
