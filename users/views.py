from django.contrib.auth import authenticate
from rest_framework import status, views, generics, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer


def get_tokens_for_user(user):
    """ 生成 JWT Token """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class RegisterView(views.APIView):
    """ 用户注册并返回 JWT Token """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({
                "result": "success",
                "message": "注册成功",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username
                },
                "access": tokens["access"],
                "refresh": tokens["refresh"]
            }, status=status.HTTP_201_CREATED)

        return Response({
            "result": "error",
            "message": "注册失败",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(views.APIView):
    """ 用户登录并返回 JWT Token """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(email=serializer.validated_data['email'],
                                password=serializer.validated_data['password'])
            if user:
                tokens = get_tokens_for_user(user)
                return Response({
                    "result": "success",
                    "message": "登录成功",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "username": user.username
                    },
                    "access": tokens["access"],
                    "refresh": tokens["refresh"]
                })
            return Response({"result": "error", "message": "邮箱或密码错误"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "result": "error",
            "message": "登录失败",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(views.APIView):
    """ 获取 & 修改当前用户信息 """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """ 获取当前用户信息 """
        serializer = UserSerializer(request.user)
        return Response({
            "result": "success",
            "message": "用户信息获取成功",
            "user": serializer.data
        })

    def put(self, request):
        """ 修改当前用户的用户名 """
        new_username = request.data.get("username")
        print(f"Received username: {new_username} (type: {type(new_username)})")

        if not new_username:
            return Response({"result": "error", "message": "请提供新的用户名"}, status=status.HTTP_400_BAD_REQUEST)

        request.user.username = new_username
        request.user.save()

        return Response({
            "result": "success",
            "message": "用户名修改成功",
            "user": {
                "id": request.user.id,
                "email": request.user.email,
                "username": request.user.username
            }
        }, status=status.HTTP_200_OK)


class SearchUserView(views.APIView):
    """ 搜索用户 """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        email = request.query_params.get("email")
        if not email:
            return Response({"result": "error", "message": "请提供邮箱"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if user:
            return Response({
                "result": "success",
                "message": "用户信息获取成功",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username
                }
            })
        return Response({"result": "error", "message": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)

