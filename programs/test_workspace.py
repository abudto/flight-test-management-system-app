"""Synthetic HTTP workflows, permissions, validation, and deletion safety."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from programs.models import Program
from programs.workspace import RESOURCES
from testing.models import TestSequenceItem
from testing.test_support import PlanningDataMixin


class WorkspaceTests(PlanningDataMixin, TestCase):
    def url(self, name, key, pk=None):
        return reverse(name, args=[key] + ([pk] if pk is not None else []))

    def test_every_resource_has_list_and_create_pages(self):
        for key in RESOURCES:
            with self.subTest(key=key):
                for name in ("record_list", "record_create"):
                    self.assertEqual(self.client.get(self.url(name, key)).status_code, 200)

    def test_complete_create_read_edit_delete_workflow_for_all_resources(self):
        created = {}
        payloads = [
            ("programs", {"name": "New synthetic program", "status": "Active"}),
            ("aircraft", {"program": "@programs", "aircraft_number": "AC-NEW", "aircraft_type": "Synthetic"}),
            ("requirements", {"program": "@programs", "document_number": "SPEC-NEW", "document_title": "New specification", "purpose": "Synthetic"}),
            ("tests", {"engineering_requirement": "@requirements", "test_number": "T-NEW", "test_title": "New test", "objective": "Synthetic"}),
            ("points", {"test": "@tests", "test_point_number": "PT-NEW", "repetition_required": 1, "status": "PLANNED"}),
            ("conditions", {"test_point": "@points", "name": "Speed", "value": "100", "unit": "kt"}),
            ("cards", {"test": "@tests", "card_number": "C-NEW", "title": "New card", "revision": "A", "procedure": "Synthetic procedure"}),
            ("sequences", {"program": "@programs", "sequence_number": "S-NEW", "title": "New sequence", "revision": "A", "planned_date": "2026-11-03"}),
            ("items", {"sequence": "@sequences", "order": 1, "test_point": "@points", "test_card": "@cards", "estimated_duration_min": 5}),
            ("hazards", {"program": "@programs", "test": "@tests", "hazard_id": "H-NEW", "description": "Synthetic hazard", "mitigation": "Synthetic mitigation"}),
            ("units", {"quantity": "speed", "name": "Synthetic knot", "symbol": "kt-demo", "to_si_factor": "0.5144444444"}),
            ("measurements", {"name": "Synthetic speed", "code": "SPD-NEW", "quantity": "speed", "default_unit": "@units"}),
            ("regulations", {"code": "REG-NEW", "title": "Synthetic regulation", "authority": "Synthetic"}),
            ("regulatory-requirements", {"regulation": "@regulations", "section": "1", "description": "Synthetic requirement"}),
            ("crew", {"full_name": "Synthetic Engineer", "active": "on"}),
        ]
        for key, payload in payloads:
            with self.subTest(key=key):
                payload = {k: created[v[1:]].pk if isinstance(v, str) and v.startswith("@") else v for k, v in payload.items()}
                response = self.client.post(self.url("record_create", key), payload)
                self.assertEqual(response.status_code, 302, getattr(response, "context", None))
                obj = RESOURCES[key].model.objects.latest("pk")
                created[key] = obj
                self.assertRedirects(response, self.url("record_detail", key, obj.pk))
                self.assertEqual(self.client.get(self.url("record_edit", key, obj.pk)).status_code, 200)
                self.assertEqual(self.client.post(self.url("record_edit", key, obj.pk), payload).status_code, 302)
        for key, obj in reversed(list(created.items())):
            with self.subTest(delete=key):
                self.assertEqual(self.client.get(self.url("record_delete", key, obj.pk)).status_code, 200)
                self.assertEqual(self.client.post(self.url("record_delete", key, obj.pk)).status_code, 302)
                self.assertFalse(RESOURCES[key].model.objects.filter(pk=obj.pk).exists())

    def test_anonymous_users_are_redirected_including_exports(self):
        self.client.logout()
        urls = [reverse("home"), self.url("record_list", "programs"),
                self.url("record_create", "tests"), self.url("record_detail", "cards", self.card_a.pk),
                reverse("test_matrix", args=[self.program_a.pk]),
                reverse("export_test_matrix", args=[self.program_a.pk]),
                reverse("export_card_pdf", args=[self.card_a.pk]),
                reverse("export_sequence_pdf", args=[self.sequence_a.pk])]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse("login")))
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)

    def test_read_only_user_cannot_write_even_with_forged_post(self):
        user = get_user_model().objects.create_user("reader", password="synthetic-password")
        user.user_permissions.add(Permission.objects.get(codename="view_program"))
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url("record_list", "programs")).status_code, 200)
        for name, pk in [("record_create", None), ("record_edit", self.program_a.pk), ("record_delete", self.program_a.pk)]:
            response = self.client.post(self.url(name, "programs", pk), {"name": "Forged"})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get(self.url("record_list", "hazards")).status_code, 403)
        self.assertEqual(self.client.get(reverse("export_card_pdf", args=[self.card_a.pk])).status_code, 403)
        self.program_a.refresh_from_db()
        self.assertEqual(self.program_a.name, "Synthetic Alpha")

    def test_program_filter_search_and_invalid_parameters(self):
        response = self.client.get(self.url("record_list", "points"), {"program": self.program_a.pk})
        self.assertEqual(response.context["page"].paginator.count, 1)
        self.assertEqual(response.context["page"][0], self.point_a)
        response = self.client.get(self.url("record_list", "programs"), {"q": "Bravo"})
        self.assertEqual(list(response.context["page"]), [self.program_b])
        self.assertEqual(self.client.get(self.url("record_list", "points"), {"program": "bad"}).status_code, 404)
        self.assertEqual(self.client.get(self.url("record_list", "unknown")).status_code, 404)

    def test_parent_assignment_is_fixed_and_cannot_be_forged(self):
        response = self.client.post(self.url("record_edit", "tests", self.test_a.pk), {
            "engineering_requirement": self.requirement_b.pk, "test_number": "T-EDIT",
            "test_title": "Updated", "objective": "Synthetic",
        })
        self.assertEqual(response.status_code, 302)
        self.test_a.refresh_from_db()
        self.assertEqual(self.test_a.engineering_requirement_id, self.requirement_a.pk)
        url = self.url("record_create", "points") + f"?parent={self.test_a.pk}"
        response = self.client.post(url, {"test": self.test_b.pk, "test_point_number": "NEW", "repetition_required": 1, "status": "PLANNED"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.test_a.test_points.filter(test_point_number="NEW").exists())

    def test_cross_program_sequence_and_hazard_are_rejected(self):
        response = self.client.post(self.url("record_create", "items"), {
            "sequence": self.sequence_a.pk, "order": 1, "test_point": self.point_b.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(TestSequenceItem.objects.exists())
        response = self.client.post(self.url("record_create", "hazards"), {
            "program": self.program_a.pk, "test": self.test_b.pk, "hazard_id": "BAD",
            "description": "Synthetic", "mitigation": "Synthetic",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_parent_deletion_blocked_and_get_never_deletes(self):
        url = self.url("record_delete", "programs", self.program_a.pk)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 409)
        self.assertTrue(Program.objects.filter(pk=self.program_a.pk).exists())
        leaf = Program.objects.create(name="Disposable synthetic")
        self.client.get(self.url("record_delete", "programs", leaf.pk))
        self.assertTrue(Program.objects.filter(pk=leaf.pk).exists())

    def test_csrf_protects_writes_and_logout(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.workspace_user)
        self.assertEqual(client.post(self.url("record_create", "programs"), {"name": "Forged"}).status_code, 403)
        self.assertEqual(client.get(reverse("logout")).status_code, 405)
        self.assertEqual(client.post(reverse("logout")).status_code, 403)

    def test_login_logout_and_account_pages(self):
        for name in ["password_change", "password_change_done"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.client.post(reverse("logout"))
        response = self.client.post(reverse("login"), {"username": "synthetic-engineer", "password": "synthetic-password"})
        self.assertRedirects(response, reverse("home"))
