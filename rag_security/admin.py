from django.contrib import admin

from .models import RagDocument, RagEvalCase, RagKnowledgeBase


admin.site.register(RagKnowledgeBase)
admin.site.register(RagDocument)
admin.site.register(RagEvalCase)

