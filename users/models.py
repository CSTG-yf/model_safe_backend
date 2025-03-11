import random
import string
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.timezone import now

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, company_name="", username=None, **extra_fields):
        """ 创建普通用户 """
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)

        # 如果没有提供用户名，生成随机用户名
        if not username:
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            username = f"用户_{random_suffix}"

        user = self.model(email=email, username=username, company_name=company_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        """ 创建超级用户 """
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    """ 自定义用户模型 """
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)  # 唯一的邮箱作为登录字段
    username = models.CharField(max_length=150, unique=True)  # 用户名
    company_name = models.CharField(max_length=255, blank=True, null=True)  # 公司名称（可选）
    is_active = models.BooleanField(default=True)  # 是否激活
    is_staff = models.BooleanField(default=False)  # 是否是管理员
    created_at = models.DateTimeField(default=now)  # 记录创建时间

    objects = UserManager()

    USERNAME_FIELD = 'email'  # 以 email 作为唯一登录字段
    REQUIRED_FIELDS = []  # 其他必填字段为空

    class Meta:
        db_table = 'users'  # 指定数据库表名

    def __str__(self):
        return self.email
