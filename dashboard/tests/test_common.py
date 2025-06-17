from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.models import Pond, PondControl, WiFiConfig


class DashboardTestCase(TestCase):
    """
    Base test case with common setup for dashboard tests
    """

    @classmethod
    @override_settings(
        SYSTEM_USERNAME="system_test", SYSTEM_EMAIL="system_test@example.com"
    )
    def setUpTestData(cls):
        """Set up data for the whole TestCase"""
        super().setUpTestData()

        # Define common URLs
        cls.login_url = reverse("token_obtain_pair")
        cls.register_url = reverse("register")
        cls.profile_url = reverse("user_profile")
        cls.update_profile_url = reverse("update_profile")
        cls.pond_list_url = reverse("pond_list")
        cls.register_pond_url = reverse("register_pond")

        # Create test users
        cls.test_password = "TestPassword123!"

        cls.test_user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=cls.test_password,
            first_name="Test",
            last_name="User",
        )

        cls.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password=cls.test_password,
            first_name="Other",
            last_name="User",
        )

        # Create system user
        cls.system_user = User.objects.create_user(
            username=settings.SYSTEM_USERNAME,
            email=settings.SYSTEM_EMAIL,
            password="SystemPassword123!",
            first_name="System",
            last_name="User",
        )

    def setUp(self):
        """Set up before each test method"""
        self.client = APIClient()

        # Default to being logged in as test_user
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": self.test_password},
            format="json",
        )

        self.access_token = response.data["access"]
        self.refresh_token = response.data["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")


class PondTestUtils:
    """
    Utility methods for pond-related tests
    """

    @staticmethod
    def create_test_pond(
        owner, name, device_id, is_active=True, with_wifi=False, with_control=True
    ):
        """
        Create a test pond with optional related objects

        Args:
            owner: User who owns the pond
            name: Name of the pond
            device_id: Unique device ID
            is_active: Whether the pond is active
            with_wifi: Whether to create WiFi config
            with_control: Whether to create pond control

        Returns:
            The created Pond instance
        """
        pond = Pond.objects.create(
            name=name, owner=owner, device_id=device_id, is_active=is_active
        )

        if with_control:
            PondControl.objects.create(pond=pond)

        if with_wifi:
            WiFiConfig.objects.create(
                pond=pond,
                ssid=f"WiFi-{device_id}",
                password="TestPassword",
                is_config_synced=True,
            )

        return pond


class TestDataMixin:
    """
    Mixin to add standard test data setup methods
    """

    def create_user_with_ponds(self, username, email, num_ponds=2):
        """
        Create a user with the specified number of ponds

        Args:
            username: Username for the new user
            email: Email for the new user
            num_ponds: Number of ponds to create

        Returns:
            Tuple of (user, ponds)
        """
        user = User.objects.create_user(
            username=username,
            email=email,
            password="UserPassword123!",
            first_name=f"{username.title()}",
            last_name="User",
        )

        ponds = []
        for i in range(num_ponds):
            pond = PondTestUtils.create_test_pond(
                owner=user,
                name=f"{username.title()} Pond {i+1}",
                device_id=f"{username}-device-{i+1}",
                with_wifi=(i % 2 == 0),  # Add WiFi to every other pond
            )
            ponds.append(pond)

        return user, ponds

    def login_as(self, username, password=None):
        """
        Log in as the specified user

        Args:
            username: Username to log in as
            password: Password (defaults to TestPassword123!)

        Returns:
            The access token
        """
        if password is None:
            password = (
                "TestPassword123!"
                if username in ["testuser", "otheruser"]
                else "UserPassword123!"
            )

        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": username, "password": password},
            format="json",
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')
        return response.data["access"]
