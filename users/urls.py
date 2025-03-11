from django.urls import path
from .views import RegisterView, LoginView, UserProfileView, SearchUserView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('me/', UserProfileView.as_view(), name='user_profile'),
    path('search/', SearchUserView.as_view(), name='search_user'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

]
