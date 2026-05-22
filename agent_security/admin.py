from django.contrib import admin

from .models import AgentTool, AgentToolCall


@admin.register(AgentTool)
class AgentToolAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "name", "tool_type", "risk_level", "requires_confirmation", "enabled")
    list_filter = ("tool_type", "risk_level", "requires_confirmation", "enabled")
    search_fields = ("name", "display_name", "project__name")


@admin.register(AgentToolCall)
class AgentToolCallAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "run", "planned_tool_name", "decision", "risk_code", "risk_level", "created_at")
    list_filter = ("decision", "risk_code", "risk_level")
    search_fields = ("planned_tool_name", "trace_id", "case_id", "project__name")
