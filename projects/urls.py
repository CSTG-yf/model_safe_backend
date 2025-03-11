from django.urls import path, include
from .views import ProjectListCreateView, ProjectDetailView

urlpatterns = [
    path('', ProjectListCreateView.as_view(), name='project_list_create'),  # 获取所有项目 & 创建项目
    path('<int:project_id>/', ProjectDetailView.as_view(), name='project_detail'),  # 获取 / 更新 / 删除单个项目
    path('<int:project_id>/members/', include('members.urls')),
]
