"""
Django settings for the AI evaluation backend.
"""

from datetime import timedelta
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE pairs without adding a runtime dependency."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = env(name)
    if value is None:
        return default
    return int(value)


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = env(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


load_dotenv(BASE_DIR / ".env")


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]"])


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "trace_analysis",
    "redteam_engine",
    "mitigation",
    "rag_security",
    "protection_strategy",
    "agent_security",
    "question_bank",
    "model_evaluation",
    "report_generation",
    "jailbreak_evaluation",
    "channels",
    "corsheaders",
    "users",
    "projects",
    "members",
    "celery",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ai_evaluation.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ai_evaluation.wsgi.application"
ASGI_APPLICATION = "ai_evaluation.asgi.application"


DATABASES = {
    "default": {
        "ENGINE": env("DB_ENGINE", "django.db.backends.mysql"),
        "NAME": env("DB_NAME", "ai"),
        "USER": env("DB_USER", "root"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "3306"),
    }
}

if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"]["OPTIONS"] = {"charset": "utf8mb4"}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


TIME_ZONE = env("DJANGO_TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

CORS_ORIGIN_WHITELIST = tuple(env_list("CORS_ALLOWED_ORIGINS", [
    "http://localhost:3000",
    "http://localhost:63342",
    "http://localhost:5173",
]))

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=env_int("JWT_ACCESS_TOKEN_HOURS", 1)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_TOKEN_DAYS", 7)),
}

# Platform-internal models are used by the evaluation system itself.
# They must not be treated as the project target model under test.
INTERNAL_ATTACK_MODEL_NAME = env("INTERNAL_ATTACK_MODEL_NAME", env("DEFAULT_MODEL_NAME", "moonshot-v1-8k"))
INTERNAL_JUDGE_MODEL_NAME = env("INTERNAL_JUDGE_MODEL_NAME", env("DEFAULT_EVAL_MODEL_NAME", "deepseek-v3"))
INTERNAL_RECOMMENDATION_MODEL_NAME = env("INTERNAL_RECOMMENDATION_MODEL_NAME", INTERNAL_JUDGE_MODEL_NAME)

# Backward-compatible aliases for older code paths.
DEFAULT_MODEL_NAME = INTERNAL_ATTACK_MODEL_NAME
DEFAULT_EVAL_MODEL_NAME = INTERNAL_JUDGE_MODEL_NAME

REDIS_URL = env("REDIS_URL", "redis://127.0.0.1:6379/0")
REDIS_CACHE_URL = env("REDIS_CACHE_URL", "redis://127.0.0.1:6379/1")

CHROMA_BASE_URL = env("CHROMA_BASE_URL", "http://127.0.0.1:8001")
CHROMA_COLLECTION_NAME = env("CHROMA_COLLECTION_NAME", "ai_evaluation_rag")
CHROMA_COLLECTION_PREFIX = env("CHROMA_COLLECTION_PREFIX", "ai_eval_rag")
CHROMA_TIMEOUT = env_int("CHROMA_TIMEOUT", 30)
RAG_FAIL_OPEN_TO_KEYWORD = env_bool("RAG_FAIL_OPEN_TO_KEYWORD", True)

OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_EMBEDDING_MODEL = env("OLLAMA_EMBEDDING_MODEL", "bge-m3")
OLLAMA_EMBEDDING_TIMEOUT = env_int("OLLAMA_EMBEDDING_TIMEOUT", 120)

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "app.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console", "app_file"],
        "level": env("DJANGO_LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django.request": {
            "handlers": ["console", "app_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "app_file"],
            "level": env("CELERY_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}
