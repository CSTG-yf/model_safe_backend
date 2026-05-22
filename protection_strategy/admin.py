from django.contrib import admin

from .models import ModelProtectionStrategy, ProtectionPolicySource, ProtectionPolicyVersion


@admin.register(ModelProtectionStrategy)
class ModelProtectionStrategyAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "target_model_name", "name", "status", "active_version", "updated_at")
    list_filter = ("status", "target_model_name")
    search_fields = ("name", "target_model_name", "project__name")


@admin.register(ProtectionPolicyVersion)
class ProtectionPolicyVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "strategy", "version", "status", "created_at", "activated_at")
    list_filter = ("status",)
    search_fields = ("strategy__name", "strategy__target_model_name")


@admin.register(ProtectionPolicySource)
class ProtectionPolicySourceAdmin(admin.ModelAdmin):
    list_display = ("id", "policy_version", "source_type", "weight", "created_at")
    list_filter = ("source_type",)
