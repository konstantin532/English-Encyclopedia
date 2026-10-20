# Learner history can no longer disappear in a cascade when course content changes:
# links to content are PROTECT. Account deletion (user FK) still removes a learner's data.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0011_pilot_stage_idempotency"),
        ("drills", "0003_exercise_uid_archive"),
        ("lexicon", "0005_longer_ipa_and_verification_note"),
        ("curriculum", "0004_twister_method"),
        ("lessons", "0003_lesson_contractions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="unitprogress", name="unit",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="progress",
                                    to="lexicon.lexicalunit"),
        ),
        migrations.AlterField(
            model_name="exerciseattempt", name="exercise",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attempts",
                                    to="drills.exercise"),
        ),
        migrations.AlterField(
            model_name="weekgoal", name="week",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="goals",
                                    to="curriculum.week"),
        ),
        migrations.AlterField(
            model_name="mistakereview", name="exercise",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="delayed_reviews",
                                    to="drills.exercise"),
        ),
        migrations.AlterField(
            model_name="independentattempt", name="lesson",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="independent_attempts",
                                    to="lessons.lesson"),
        ),
        migrations.AddConstraint(
            model_name="unitprogress",
            constraint=models.CheckConstraint(condition=models.Q(stage__lte=4), name="unit_progress_stage_in_range"),
        ),
        migrations.AddConstraint(
            model_name="speechpracticeprogress",
            constraint=models.CheckConstraint(condition=models.Q(stage__lte=4), name="speech_progress_stage_in_range"),
        ),
        migrations.AddConstraint(
            model_name="mistakereview",
            constraint=models.CheckConstraint(condition=models.Q(current_index__lte=5, correct_count__lte=5),
                                              name="mistake_review_counts_in_range"),
        ),
    ]
