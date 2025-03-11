from django.urls import path
from .views import ProjectMemberView

urlpatterns = [
    path('', ProjectMemberView.as_view(), name='manage_members'),  # 获取 & 邀请成员
    path('<int:user_id>/', ProjectMemberView.as_view(), name='remove_member'),  # 删除成员
]
