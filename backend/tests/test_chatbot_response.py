import unittest

from app.main import build_local_response, is_out_of_scope


class ChatbotResponseTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "title": "Sample HLDD Template",
            "summary": "Customer relationship management project",
            "technology_stack": ["React", "FastAPI", "PostgreSQL", "Google Cloud", "Docker"],
            "functional_requirements": [
                "Manage customer onboarding workflow",
                "Generate reporting dashboards",
            ],
            "acceptance_criteria": [
                "The onboarding workflow is documented and implemented",
                "Dashboards provide updated metrics",
            ],
            "project_management_tool": "Jira",
            "features": [{"id": "IPMA#001"}],
            "stories": [{"id": "E-CRM#001"}],
            "testing_stories": [{"id": "TEST-E-CRM#001"}],
        }

    def test_local_response_includes_recommended_and_alternative_stack_guidance(self):
        response = build_local_response(
            self.payload,
            "What frontend, backend, and cloud options fit this project?",
        )

        self.assertIn("Recommended setup", response)
        self.assertIn("Alternatives", response)
        self.assertIn("Efficiency", response)
        self.assertIn("Security", response)
        self.assertIn("Turnaround time", response)

    def test_local_response_can_include_cost_breakdown_when_requested(self):
        response = build_local_response(
            self.payload,
            "Show me a cost breakdown and options under a mid-size budget.",
        )

        self.assertIn("Cost breakdown", response)
        self.assertIn("Monthly estimate", response)

    def test_local_response_includes_selected_priority_guidance(self):
        response = build_local_response(
            self.payload,
            "Show me a cost breakdown and options under a mid-size budget.",
            priority="lowest cost",
        )

        self.assertIn("Selected priority", response)
        self.assertIn("Lowest cost", response)
        self.assertIn("Priority lens", response)

    def test_scope_guard_flags_irrelevant_prompts(self):
        self.assertTrue(is_out_of_scope("Tell me a joke"))

    def test_scope_guard_accepts_relevant_project_prompts(self):
        self.assertFalse(is_out_of_scope("How should the repository and architecture fit this HLDD?"))


if __name__ == "__main__":
    unittest.main()
