from django.urls import path

from .views import EvaluableModelListView, ModelPingView


urlpatterns = [
    path("evaluable/", EvaluableModelListView.as_view(), name="evaluable_models"),
    path("ping/", ModelPingView.as_view(), name="model_ping"),
]
