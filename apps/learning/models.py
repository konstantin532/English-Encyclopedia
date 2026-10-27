from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.drills.models import Exercise
from apps.lexicon.models import LexicalUnit

# Интервалы повторения (раздел 11): сразу, через день, 3–4 дня, неделя, две недели.
REVIEW_INTERVALS_DAYS = (0, 1, 3, 7, 14)


class Status(models.TextChoices):
    NEW = "new", "Новое"
    RECOGNITION = "recognition", "Узнаю"
    GUIDED_USE = "guided_use", "С подсказкой"
    INDEPENDENT_USE = "independent_use", "Сам"
    ACTIVE = "active", "Активный словарь"
    REVIEW_DUE = "review_due", "Пора повторить"


STATUS_LADDER = [Status.NEW, Status.RECOGNITION, Status.GUIDED_USE, Status.INDEPENDENT_USE, Status.ACTIVE]


class UnitProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unit_progress")
    unit = models.ForeignKey(LexicalUnit, on_delete=models.PROTECT, related_name="progress")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    stage = models.PositiveSmallIntegerField(default=0, help_text="Ступень интервала 0–4")
    next_review_at = models.DateTimeField(null=True, blank=True)
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    contexts_used = models.JSONField(default=list, blank=True, help_text="Разные конструкции, где единица употреблена")
    # Модуль «Память слов» (apps/learning/memory.py). Пусто — слово ещё не в модуле памяти.
    # Не меняет stage/next_review_at: прежнее повторение работает как раньше.
    memory_stability = models.FloatField(null=True, blank=True,
                                         help_text="Прочность в днях: за сколько рейтинг опускается до 90%")
    memory_reviewed_at = models.DateTimeField(null=True, blank=True)
    memory_evidence = models.JSONField(default=dict, blank=True,
                                       help_text="Дни и семейства верных ответов, серия ошибок, подсказки")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "unit"], name="uniq_progress_per_unit"),
            models.CheckConstraint(condition=models.Q(stage__lte=len(REVIEW_INTERVALS_DAYS) - 1),
                                   name="unit_progress_stage_in_range"),
        ]
        indexes = [models.Index(fields=["user", "next_review_at"])]

    def register(self, correct: bool, context: str = "", *, mode: str = "partial") -> None:
        now = timezone.now()
        self._register_memory(correct, context, mode, now)
        if correct:
            self.correct_count += 1
            # A correct replay of the SAME exercise (or a lemma-only recall)
            # is not fresh evidence of independently using this word.
            new_context = bool(context) and context not in self.contexts_used
            if new_context:
                self.contexts_used = [*self.contexts_used, context]
            # Replaying early cannot manufacture spaced repetition: the
            # interval advances only when a review is actually due (or new).
            if self.next_review_at is None or self.next_review_at <= now:
                self.stage = min(self.stage + 1, len(REVIEW_INTERVALS_DAYS) - 1)
                self.next_review_at = now + timedelta(days=REVIEW_INTERVALS_DAYS[self.stage])
            if self.status == Status.NEW:
                self.status = Status.RECOGNITION
            elif new_context and self.status == Status.RECOGNITION:
                # A model-matched drill is guided practice, even with several
                # distinct sentence contexts. It cannot demonstrate unaided
                # transfer or independent production. Those require separate
                # human-reviewed evidence; do not award higher statuses here.
                self.status = Status.GUIDED_USE
        else:
            self.wrong_count += 1
            self.stage = max(self.stage - 1, 0)
            if self.status == Status.ACTIVE:
                self.status = Status.INDEPENDENT_USE
            self.next_review_at = now + timedelta(days=REVIEW_INTERVALS_DAYS[self.stage])


    def _register_memory(self, correct, context, mode, now):
        from . import memory

        if not memory.enabled():
            return
        family = (context or "").split("#", 1)[0] or "recall"
        memory.apply(self, correct=correct, mode=mode, error="wrong", family=f"lesson:{family}", now=now)


class ExerciseAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="attempts")
    answer = models.CharField(max_length=200)
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]


class WeekGoal(models.Model):
    """Самооценка ученика по цели недели «Я смогу…»."""

    class GoalStatus(models.TextChoices):
        DONE = "done", "Получилось"
        NOT_YET = "not_yet", "Ещё нет"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="week_goals")
    week = models.ForeignKey("curriculum.Week", on_delete=models.PROTECT, related_name="goals")
    status = models.CharField(max_length=8, choices=GoalStatus.choices)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "week"], name="uniq_goal_per_week")]

# Устная практика — отдельная от знания лексики самооценка. Аудио не хранится.
SPEECH_REVIEW_INTERVALS_DAYS = (0, 1, 3, 7, 14)


class SpeechPracticeProgress(models.Model):
    """Интервальное повторение фрагмента по *самооценке* ученика.

    Ключи стабильны между повторными загрузками content/:
    lesson:<slug>, twister:<number>, poem:<number>.
    """

    class Result(models.TextChoices):
        AGAIN = "again", "Повторить сейчас"
        HARD = "hard", "С подсказкой"
        GOOD = "good", "Самостоятельно"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="speech_practice")
    content_key = models.CharField(max_length=110)
    fragment = models.PositiveSmallIntegerField()
    stage = models.PositiveSmallIntegerField(default=0)
    result = models.CharField(max_length=5, choices=Result.choices, default=Result.AGAIN)
    attempts = models.PositiveIntegerField(default=0)
    next_review_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_key", "fragment"], name="uniq_speech_progress_per_fragment"
            ),
            models.CheckConstraint(condition=models.Q(stage__lte=4), name="speech_progress_stage_in_range"),
        ]
        indexes = [models.Index(fields=["user", "next_review_at"], name="speech_due_by_user_idx")]
        ordering = ["next_review_at", "content_key", "fragment"]

    def register(self, rating: str, now=None) -> None:
        if rating not in self.Result.values:
            raise ValueError("Неизвестная оценка самостоятельного воспроизведения")
        now = now or timezone.now()
        # A first evaluation is always eligible. After that, repeating
        # "good" before its scheduled date is practice, NOT spaced recall.
        due = self.attempts == 0 or self.next_review_at <= now
        self.attempts += 1
        self.result = rating
        if rating == self.Result.AGAIN:
            self.stage = 0
            self.next_review_at = now
        elif rating == self.Result.HARD:
            self.stage = max(self.stage - 1, 0)
            self.next_review_at = now + timedelta(days=1)
        elif due:
            self.stage = min(self.stage + 1, len(SPEECH_REVIEW_INTERVALS_DAYS) - 1)
            self.next_review_at = now + timedelta(days=SPEECH_REVIEW_INTERVALS_DAYS[self.stage])
        # Early GOOD ratings must not extend the deadline or increase stage.


class MistakeReview(models.Model):
    """Five authored practice questions appear two days after a verified A1 error.

    Free responses that merely differ from the model are NOT scheduled.
    Progress here is separate from CEFR and vocabulary mastery.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mistake_reviews",
    )
    exercise = models.ForeignKey(
        Exercise, on_delete=models.PROTECT, related_name="delayed_reviews",
    )
    due_at = models.DateTimeField()
    current_index = models.PositiveSmallIntegerField(default=0)
    correct_count = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "exercise"], name="unique_mistake_review"),
            # Пять отложенных вопросов: счётчики не выходят за пределы пакета.
            models.CheckConstraint(condition=models.Q(current_index__lte=5, correct_count__lte=5),
                                   name="mistake_review_counts_in_range"),
        ]
        indexes = [
            models.Index(fields=["user", "completed_at", "due_at"], name="mistake_review_due_idx"),
        ]
        ordering = ["due_at", "pk"]



class IndependentAttempt(models.Model):
    """Evidence for an A1 no-options check, NOT a CEFR certificate.

    Model-key agreement is distinguished from human validation; free transfer
    can only be self-assessed until a teacher checks it.
    """
    class Outcome(models.TextChoices):
        MODEL_MATCH = "model_match", "Совпало с образцом"
        NEEDS_REVIEW = "needs_review", "Нужна проверка"
        SELF_REPORTED = "self_reported", "Самооценка ученика"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="independent_attempts")
    lesson = models.ForeignKey("lessons.Lesson", on_delete=models.PROTECT, related_name="independent_attempts")
    skill = models.CharField(max_length=12)
    submitted = models.CharField(max_length=400)
    # Exact exercise shown when this response was created. Newer content edits
    # must never silently change what a human reviewer thinks was asked.
    prompt_snapshot = models.TextField(blank=True, default="")
    model_snapshot = models.TextField(blank=True, default="")
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    self_rating = models.CharField(max_length=16, blank=True)

    class Assistance(models.TextChoices):
        NOT_STATED = "not_stated", "Не указано (старая попытка)"
        NO_HELP = "no_help", "Без конспекта и переводчика"
        NOTES = "notes", "С конспектом или объяснением"
        TRANSLATOR = "translator", "С онлайн-переводчиком или готовым ответом"

    # Learner-declared conditions, not proof of actual independent competence.
    assistance = models.CharField(
        max_length=16, choices=Assistance.choices, default=Assistance.NOT_STATED
    )
    # A documented alternative task, chosen server-side; 0 is the original.
    task_variant = models.PositiveSmallIntegerField(default=0)
    # Empty only for historic/legacy attempts. Modern four-answer POSTs carry
    # a one-time form token, allowing DB-level protection against race retries.
    batch_token = models.CharField(max_length=64, blank=True, default="")
    # Learner reflection, never a machine-scored CEFR or speech grade.
    self_rubric = models.JSONField(default=dict, blank=True)

    class TeacherVerdict(models.TextChoices):
        UNREVIEWED = "unreviewed", "Не проверено преподавателем"
        MEETS_TASK = "meets_task", "Смысл и форма подходят"
        NEEDS_WORK = "needs_work", "Нужна доработка"
        UNCLEAR = "unclear", "Неоднозначно, обсудить"

    # Independent evidence stays unverified until a staff reviewer assesses it.
    teacher_verdict = models.CharField(
        max_length=16, choices=TeacherVerdict.choices,
        default=TeacherVerdict.UNREVIEWED,
    )
    teacher_rubric = models.JSONField(default=dict, blank=True)
    teacher_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_independent_attempts",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Empty/default values preserve the meaning of historical lesson evidence.
    origin = models.CharField(max_length=16, default="lesson")
    target = models.ForeignKey(LexicalUnit, on_delete=models.PROTECT, null=True, blank=True,
                               related_name="independent_attempts")
    trainer_session = models.ForeignKey("TrainerSession", on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name="attempts")
    trainer_sequence = models.PositiveSmallIntegerField(default=0)
    evidence = models.JSONField(default=dict, blank=True)

    @staticmethod
    def redact_export_rows(rows, *, user):
        trainer_rows = [row for row in rows if row['origin'] == 'trainer']
        if trainer_rows:
            completed = set(TrainerSession.objects.filter(
                user=user, phase='complete',
                pk__in=[row['trainer_session_id'] for row in trainer_rows],
            ).values_list('pk', flat=True))
            for row in trainer_rows:
                if row['trainer_session_id'] not in completed:
                    # Keep submitted text and server evidence, but do not make
                    # an unfinished assessment's answer key an export shortcut.
                    row.pop('model_snapshot', None)
        return rows

    class Meta:
        indexes = [models.Index(fields=["user", "lesson", "-created_at"], name="independent_user_lesson_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "lesson", "skill", "batch_token"],
                condition=~models.Q(batch_token=""),
                name="unique_independent_batch_skill_token",
            ),
            models.UniqueConstraint(
                fields=["user", "lesson", "skill", "task_variant"],
                condition=models.Q(skill="transfer", task_variant__in=[100, 101, 102]),
                name="unique_pilot_stage_per_learner",
            ),
            models.UniqueConstraint(
                fields=["trainer_session", "skill", "trainer_sequence"],
                condition=models.Q(trainer_session__isnull=False),
                name="unique_trainer_logical_attempt",
            ),
        ]
        ordering = ["-created_at"]


def trainer_token():
    import uuid
    return uuid.uuid4().hex


class TrainerEnrollment(models.Model):
    """Opt-in preferences, never an additional vocabulary progress ledger."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trainer_enrollments')
    enabled = models.BooleanField(default=True)
    prerequisites_confirmed = models.BooleanField(default=False)
    timezone_name = models.CharField(max_length=64, default='Europe/Moscow')
    daily_limit = models.PositiveSmallIntegerField(default=10)
    rate_window_at = models.DateTimeField(null=True, blank=True)
    rate_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_trainer_enrollment'),
            models.CheckConstraint(condition=models.Q(daily_limit__gte=1, daily_limit__lte=10),
                                   name='trainer_daily_limit_range'),
        ]


class TrainerSession(models.Model):
    """One frozen encounter. Private keys never enter the assessment projection."""
    # Data rights exports retain all learner submissions via IndependentAttempt.
    # Neither private future keys nor transport receipts are a user submission.
    export_excluded_fields = {'snapshot', 'receipts'}

    @staticmethod
    def redact_export_rows(rows, *, user):
        evidence_keys = {'outcome', 'goal_achieved', 'target_used', 'task_id',
                         'family_id', 'evidence_kind', 'scheduling', 'schedule_eligible'}
        for row in rows:
            if row['phase'] != 'complete':
                # Feedback can name the withheld target too; export only its
                # non-model evidence until this encounter has been completed.
                row['result'] = {key: value for key, value in row['result'].items()
                                 if key in evidence_keys}
        return rows

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trainer_sessions')
    unit = models.ForeignKey(LexicalUnit, on_delete=models.PROTECT, related_name='trainer_sessions')
    phase = models.CharField(max_length=20, default='intro')
    revision = models.PositiveIntegerField(default=0)
    token = models.CharField(max_length=32, default=trainer_token, unique=True)
    snapshot = models.JSONField(default=dict)
    content_version = models.CharField(max_length=32)
    assessment_revision = models.CharField(max_length=32)
    task_id = models.CharField(max_length=100)
    family_id = models.CharField(max_length=100)
    application_index = models.PositiveSmallIntegerField(default=0)
    is_initial = models.BooleanField(default=True)
    assistance = models.JSONField(default=list)
    recall_tries = models.PositiveSmallIntegerField(default=0)
    result = models.JSONField(default=dict)
    schedule_applied = models.BooleanField(default=False)
    receipts = models.JSONField(default=dict)
    draft = models.CharField(max_length=400, blank=True, default='')
    draft_updated_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    last_material_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'unit'], condition=models.Q(completed_at__isnull=True),
                                    name='unique_open_trainer_session'),
            models.CheckConstraint(condition=models.Q(recall_tries__lte=2), name='trainer_max_two_recalls'),
        ]
        indexes = [models.Index(fields=['user', 'started_at'], name='trainer_user_started_idx')]


class PersonalMnemonic(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personal_mnemonics')
    unit = models.ForeignKey(LexicalUnit, on_delete=models.PROTECT, related_name='personal_mnemonics')
    text = models.CharField(max_length=300)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'unit'], name='unique_personal_mnemonic')]


class PhraseStats(models.Model):
    """Счётчик верных фраз ученика за всё время: от него зависит доля пазлов."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="phrase_stats")
    correct_total = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} · верных фраз: {self.correct_total}"
