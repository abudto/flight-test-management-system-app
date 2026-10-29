from django.db import models

# Create your models here.
from programs.models import Program
from django.core.exceptions import ValidationError


class EngineeringTestRequirement(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='engineering_requirements',
    )

    document_number = models.CharField(max_length=100)
    document_title = models.CharField(max_length=200)
    purpose = models.TextField()
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f'{self.document_number} - {self.document_title}'


class Test(models.Model):
    engineering_requirement = models.ForeignKey(
        EngineeringTestRequirement,
        on_delete=models.CASCADE,
        related_name='tests',
    )

    test_number = models.CharField(max_length=50)
    test_title = models.CharField(max_length=200)
    objective = models.TextField()

    special_equipment = models.TextField(blank=True)
    special_test_requirement = models.TextField(blank=True)
    test_procedure = models.TextField(blank=True)
    pass_fail_criteria = models.TextField(blank=True)
    related_regulation = models.CharField(
        max_length=200,
        blank=True
    )
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f'{self.test_number} - {self.test_title}'


class TestPoint(models.Model):
    class WeightCategory(models.TextChoices):
        light = 'light', 'LIGHT'
        medium = 'medium', 'MEDIUM'
        heavy = 'heavy', 'HEAVY'

    class CgCategory(models.TextChoices):
        forward = 'Forward', 'FWD'
        mid = 'Mid', 'MID'
        aft = 'Aft', 'AFT'


    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name='test_points',
    )

    test_point_number = models.CharField(max_length=50)
    weight_category = models.CharField(max_length=30, blank=True, choices=WeightCategory.choices)
    cg_category = models.CharField(max_length=30, blank=True, choices=CgCategory.choices)
    target_speed = models.FloatField(null=True, blank=True)
    target_altitude = models.FloatField(null=True, blank=True)
    repetition_required = models.PositiveBigIntegerField(default=1,)
    pass_fail_criteria = models.TextField(blank=True)
    status = models.CharField(max_length=30, default='PLANNED',)

    remarks = models.TextField(blank=True)

    def __str__(self):
        return self.test_point_number


class TestPointCondition(models.Model):
    test_point = models.ForeignKey(
        TestPoint,
        on_delete=models.CASCADE,
        related_name='conditions',
    )

    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    unit = models.CharField(max_length=30, blank=True)
    tolerance = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f'{self.name}: {self.value} {self.unit}'.strip()


class TestCard(models.Model):
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="test_cards",
    )

    card_number = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    revision = models.CharField(max_length=20, default="A")

    preparation = models.TextField(blank=True)
    procedure = models.TextField()
    safety_notes = models.TextField(blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["test", "card_number", "revision"],
                name="unique_card_revision_per_test",
            )
        ]

    def __str__(self):
        return f"{self.card_number} Rev {self.revision}"


class TestSequence(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="test_sequences",
    )

    sequence_number = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    revision = models.CharField(max_length=20, default="A")

    planned_date = models.DateField(null=True, blank=True)
    objective = models.TextField(blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["program", "sequence_number", "revision"],
                name="unique_sequence_revision_per_program",
            )
        ]

    def __str__(self):
        return f"{self.sequence_number} Rev {self.revision}"


class TestSequenceItem(models.Model):
    sequence = models.ForeignKey(
        TestSequence,
        on_delete=models.CASCADE,
        related_name="items",
    )

    order = models.PositiveIntegerField()
    test_point = models.ForeignKey(
        TestPoint,
        on_delete=models.PROTECT,
        related_name="sequence_items",
    )

    test_card = models.ForeignKey(
        TestCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sequence_items",
    )

    estimated_duration_min = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    remarks = models.TextField(blank=True)

    def clean(self):
        super().clean()

        if not self.sequence_id or not self.test_point_id:
            return

        point_program_id = (
            self.test_point.test
            .engineering_requirement.program_id
        )

        if point_program_id != self.sequence.program_id:
            raise ValidationError({
                "test_point": (
                    "The selected test point must belong "
                    "to the same program as the sequence."
                )
            })

        if self.test_card_id:
            if self.test_card.test_id != self.test_point.test_id:
                raise ValidationError({
                    "test_card": (
                        "The selected test card must belong "
                        "to the same test as the test point."
                    )
                })

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["sequence", "order"],
                name="unique_order_per_sequence",
            )
        ]

    def __str__(self):
        return (
            f"{self.sequence.sequence_number} - "
            f"{self.order}: {self.test_point.test_point_number}"
        )