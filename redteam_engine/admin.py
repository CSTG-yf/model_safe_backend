from django.contrib import admin

from .models import AttackStrategy, RedTeamAttempt, StrategyStat


admin.site.register(AttackStrategy)
admin.site.register(RedTeamAttempt)
admin.site.register(StrategyStat)
