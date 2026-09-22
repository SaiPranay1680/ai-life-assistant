from unittest import TestCase

from app.modules.documents.folders import guess_folder, normalize_folder


class FolderGuessTests(TestCase):
    def test_health_insurance(self) -> None:
        self.assertEqual(
            guess_folder("01_family_health_insurance.pdf", "health_insurance", "health_insurance_policy"),
            ("Health", "Insurance"),
        )

    def test_health_appointment(self) -> None:
        self.assertEqual(guess_folder("clinic_appointment.pdf", "generic", "appointment"), ("Health", "Appointment"))

    def test_vehicle_licence(self) -> None:
        self.assertEqual(guess_folder("driving_licence.pdf", "generic", ""), ("Vehicle", "Driving licence"))

    def test_vehicle_insurance(self) -> None:
        self.assertEqual(guess_folder("car_policy.pdf", "car_insurance", ""), ("Vehicle", "Insurance"))

    def test_normalize_unknown_subcategory(self) -> None:
        self.assertEqual(normalize_folder("Health", "something else"), ("Health", "Insurance"))
