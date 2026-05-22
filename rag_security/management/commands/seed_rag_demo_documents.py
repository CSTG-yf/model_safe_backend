from django.core.management.base import BaseCommand, CommandError

from projects.models import Project
from rag_security.services import RagDemoDataService


class Command(BaseCommand):
    help = "Seed normal, poisoned, and sensitive documents for RAG security demos."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, required=True)
        parser.add_argument("--name", default="RAG 安全评测演示知识库")

    def handle(self, *args, **options):
        project = Project.objects.filter(id=options["project_id"]).first()
        if not project:
            raise CommandError(f"Project {options['project_id']} does not exist.")
        kb, stats = RagDemoDataService.seed(project, name=options["name"])
        self.stdout.write(self.style.SUCCESS(f"Seeded knowledge_base_id={kb.id}: {stats}"))

