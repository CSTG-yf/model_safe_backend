from django.contrib import admin

from .models import AppTrace, TraceRisk, TraceStep


admin.site.register(AppTrace)
admin.site.register(TraceStep)
admin.site.register(TraceRisk)
