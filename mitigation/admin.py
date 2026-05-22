from django.contrib import admin

from .models import (
    MitigationRecommendation,
    MitigationTemplate,
    RegressionCase,
    RegressionSet,
)


admin.site.register(MitigationTemplate)
admin.site.register(MitigationRecommendation)
admin.site.register(RegressionSet)
admin.site.register(RegressionCase)
