from django.core.management.base import BaseCommand
from django.db.models import Count, Min

from apps.tasks.models import Task


class Command(BaseCommand):
    help = "Supprime les tâches en double (même utilisateur, projet, titre)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Affiche les doublons sans les supprimer.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        groups = list(
            Task.objects
            .values("user_id", "project_id", "title")
            .annotate(cnt=Count("id"), min_id=Min("id"))
            .filter(cnt__gt=1)
            .order_by()
        )

        total = 0
        for group in groups:
            dup_ids = list(
                Task.objects
                .filter(
                    user_id=group["user_id"],
                    project_id=group["project_id"],
                    title=group["title"],
                )
                .exclude(id=group["min_id"])
                .values_list("id", flat=True)
            )
            for dup_id in dup_ids:
                try:
                    dup = Task.objects.get(id=dup_id)
                except Task.DoesNotExist:
                    # Déjà supprimé en cascade par un parent dédupliqué.
                    total += 1
                    continue
                child_count = Task.objects.filter(parent=dup).count()
                self.stdout.write(
                    f"  Doublon : « {dup.title} » (id={dup.id}"
                    + (f", {child_count} enfant(s) réassigné(s)" if child_count else "")
                    + ")"
                )
                if not dry_run:
                    # Rattacher les enfants à la tâche canonique avant suppression.
                    Task.objects.filter(parent=dup).update(parent_id=group["min_id"])
                    dup.delete()
                total += 1

        suffix = " (--dry-run, rien supprimé)" if dry_run else ""
        style = self.style.WARNING if dry_run else self.style.SUCCESS
        self.stdout.write(style(f"{total} doublon(s) trouvé(s){suffix}."))
