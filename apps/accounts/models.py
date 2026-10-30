from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Нужен адрес почты")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True)
        return self._create(email, password, **extra)


class User(AbstractUser):
    """Ученик. Вход по почте, имя — для обращения в уроках."""

    username = None
    email = models.EmailField("почта", unique=True)
    display_name = models.CharField("как к вам обращаться", max_length=60, blank=True)
    current_level = models.ForeignKey(
        "curriculum.Level", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    markers_enabled = models.BooleanField("маркеры в тексте", default=False, db_default=False)
    markers_in_color = models.BooleanField("маркеры в цвете", default=True)
    # Роль «учитель» назначает только владелец (суперпользователь) в админке.
    is_teacher = models.BooleanField("учитель", default=False, db_default=False,
                                     help_text="Открывает кабинет учителя. Назначает только владелец.")
    teacher_sees_all = models.BooleanField(
        "видит всех учеников", default=False, db_default=False,
        help_text="Выключено — учитель видит только учеников своих групп.")
    teacher_access_requested = models.BooleanField(
        "заявка на доступ учителя", default=False, db_default=False,
        help_text="Заявка не даёт прав. Для одобрения владелец включает «учитель»; для отказа снимает заявку.")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []
    objects = UserManager()

    def save(self, *args, **kwargs):
        # Почта без учёта регистра: Anna@Mail.ru и anna@mail.ru — один аккаунт.
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    @property
    def is_owner(self) -> bool:
        return self.is_superuser

    @property
    def is_learner(self) -> bool:
        return not (self.is_teacher or self.is_staff or self.is_superuser)

    def __str__(self) -> str:
        return self.display_name or self.email
