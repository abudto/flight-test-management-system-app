from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from testing.models import Test, TestCard, TestPoint, TestSequence, TestSequenceItem
from testing.test_support import ConstraintAssertionsMixin, PlanningDataMixin


class SequenceItemValidationTests(PlanningDataMixin, TestCase):
    def item(self, **overrides):
        values = dict(sequence=self.sequence_a, order=1,
                      test_point=self.point_a, test_card=self.card_a)
        values.update(overrides)
        return TestSequenceItem(**values)

    def test_matching_point_and_card_are_valid(self):
        item = self.item()
        item.full_clean()
        item.save()
        self.assertEqual(self.sequence_a.items.get(), item)

    def test_second_program_has_its_own_valid_sequence(self):
        item = self.item(sequence=self.sequence_b, test_point=self.point_b,
                         test_card=self.card_b)
        item.full_clean()
        item.save()
        self.assertFalse(self.sequence_a.items.exists())
        self.assertEqual(self.sequence_b.items.get(), item)

    def test_point_from_another_program_is_rejected(self):
        with self.assertRaises(ValidationError) as error:
            self.item(test_point=self.point_b, test_card=None).full_clean()
        self.assertIn("test_point", error.exception.message_dict)

    def test_cross_program_point_is_rejected_even_with_matching_card(self):
        with self.assertRaises(ValidationError) as error:
            self.item(test_point=self.point_b, test_card=self.card_b).full_clean()
        self.assertIn("test_point", error.exception.message_dict)

    def test_card_from_another_program_is_rejected(self):
        with self.assertRaises(ValidationError) as error:
            self.item(test_card=self.card_b).full_clean()
        self.assertIn("test_card", error.exception.message_dict)

    def test_card_from_another_test_in_same_program_is_rejected(self):
        other_test = Test.objects.create(
            engineering_requirement=self.requirement_a, test_number="TEST-02",
            test_title="Another synthetic test", objective="Check card compatibility",
        )
        other_card = TestCard.objects.create(
            test=other_test, card_number="CARD-02", title="Another card",
            procedure="Synthetic procedure",
        )
        with self.assertRaises(ValidationError) as error:
            self.item(test_card=other_card).full_clean()
        self.assertIn("test_card", error.exception.message_dict)

    def test_card_and_duration_are_optional(self):
        item = self.item(test_card=None, estimated_duration_min=None)
        item.full_clean()
        item.save()
        item.refresh_from_db()
        self.assertIsNone(item.test_card)
        self.assertIsNone(item.estimated_duration_min)

    def test_existing_item_cannot_be_validated_with_foreign_point(self):
        item = self.item()
        item.save()
        item.test_point = self.point_b
        item.test_card = None
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_negative_order_and_duration_are_rejected(self):
        for field in ["order", "estimated_duration_min"]:
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as error:
                    self.item(**{field: -1}).full_clean()
                self.assertIn(field, error.exception.message_dict)


class PlanningConstraintTests(ConstraintAssertionsMixin, PlanningDataMixin, TestCase):
    def test_card_revision_duplicate_is_rejected(self):
        self.assert_duplicate_rejected(TestCard(
            test=self.test_a, card_number=self.card_a.card_number,
            revision=self.card_a.revision, title="Duplicate", procedure="Synthetic",
        ))

    def test_card_number_can_have_another_revision(self):
        card = TestCard(test=self.test_a, card_number=self.card_a.card_number,
                        revision="B", title="Revised", procedure="Synthetic")
        card.full_clean()
        card.save()
        self.assertEqual(self.test_a.test_cards.count(), 2)

    def test_card_identity_is_scoped_to_test(self):
        self.card_a.full_clean()
        self.card_b.full_clean()
        self.assertEqual(self.card_a.card_number, self.card_b.card_number)
        self.assertEqual(self.card_a.revision, self.card_b.revision)
        self.assertNotEqual(self.card_a.test_id, self.card_b.test_id)

    def test_sequence_revision_duplicate_is_rejected(self):
        self.assert_duplicate_rejected(TestSequence(
            program=self.program_a, sequence_number=self.sequence_a.sequence_number,
            revision=self.sequence_a.revision, title="Duplicate",
        ))

    def test_sequence_number_can_have_another_revision(self):
        sequence = TestSequence(
            program=self.program_a, sequence_number=self.sequence_a.sequence_number,
            revision="B", title="Revised",
        )
        sequence.full_clean()
        sequence.save()
        self.assertEqual(self.program_a.test_sequences.count(), 2)

    def test_sequence_identity_is_scoped_to_program(self):
        self.sequence_a.full_clean()
        self.sequence_b.full_clean()
        self.assertEqual(self.sequence_a.sequence_number, self.sequence_b.sequence_number)
        self.assertEqual(self.sequence_a.revision, self.sequence_b.revision)

    def test_duplicate_item_order_is_rejected(self):
        TestSequenceItem.objects.create(
            sequence=self.sequence_a, order=1, test_point=self.point_a,
        )
        self.assert_duplicate_rejected(TestSequenceItem(
            sequence=self.sequence_a, order=1, test_point=self.point_a,
        ))

    def test_item_order_can_repeat_in_different_sequences(self):
        for sequence, point in [(self.sequence_a, self.point_a),
                                (self.sequence_b, self.point_b)]:
            item = TestSequenceItem(sequence=sequence, order=1, test_point=point)
            item.full_clean()
            item.save()
        self.assertEqual(TestSequenceItem.objects.count(), 2)

    def test_items_are_returned_in_execution_order(self):
        for order in [3, 1, 2]:
            TestSequenceItem.objects.create(
                sequence=self.sequence_a, order=order, test_point=self.point_a,
            )
        self.assertEqual(list(self.sequence_a.items.values_list("order", flat=True)),
                         [1, 2, 3])


class PlanningDeletionTests(PlanningDataMixin, TestCase):
    def test_assigned_test_point_is_protected(self):
        item = TestSequenceItem.objects.create(
            sequence=self.sequence_a, order=1, test_point=self.point_a,
        )
        with self.assertRaises(ProtectedError) as error:
            self.point_a.delete()
        self.assertIn(item, error.exception.protected_objects)
        self.assertTrue(TestPoint.objects.filter(pk=self.point_a.pk).exists())
        item.refresh_from_db()
        self.assertEqual(item.test_point_id, self.point_a.pk)

    def test_deleting_card_preserves_item_and_clears_optional_reference(self):
        item = TestSequenceItem.objects.create(
            sequence=self.sequence_a, order=1, test_point=self.point_a,
            test_card=self.card_a,
        )
        self.card_a.delete()
        item.refresh_from_db()
        self.assertIsNone(item.test_card_id)
        self.assertEqual(item.test_point_id, self.point_a.pk)
