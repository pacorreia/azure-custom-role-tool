"""Tests for subscription management functionality."""

from click.testing import CliRunner
import pytest

from azure_custom_role_tool import cli
from azure_custom_role_tool.azure_client import SubscriptionManager


class DummySubscriptionClient:
    """Mock subscription client."""

    def __init__(self, credential):
        self.credential = credential
        self.subscriptions = DummySubscriptions()


class DummySubscriptions:
    """Mock subscriptions list."""

    def list(self):
        return [
            DummySubscription("sub-123", "Production", "Enabled"),
            DummySubscription("sub-456", "Development", "Enabled"),
            DummySubscription("sub-789", "Staging", "Disabled"),
        ]


class DummySubscription:
    """Mock subscription."""

    def __init__(self, subscription_id, display_name, state):
        self.subscription_id = subscription_id
        self.display_name = display_name
        self.state = state


def test_subscriptions_command(monkeypatch):
    """Test subscriptions command lists all subscriptions."""
    runner = CliRunner()

    def mock_subscription_manager_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_subscription_manager_init)

    result = runner.invoke(cli.cli, ["subscriptions"])
    assert result.exit_code == 0
    assert "Production" in result.output
    assert "Development" in result.output
    assert "Staging" in result.output
    assert "sub-123" in result.output


def test_use_subscription_by_id_option(monkeypatch):
    """Test switching subscription by ID using --id flag."""
    runner = CliRunner()

    def mock_subscription_manager_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_subscription_manager_init)

    result = runner.invoke(cli.cli, ["use-subscription", "--id", "sub-456"])
    assert result.exit_code == 0
    assert "Development" in result.output
    assert "sub-456" in result.output


def test_use_subscription_by_id_positional(monkeypatch):
    """Test switching subscription by ID using positional argument."""
    runner = CliRunner()

    def mock_subscription_manager_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_subscription_manager_init)

    result = runner.invoke(cli.cli, ["use-subscription", "sub-456"])
    assert result.exit_code == 0
    assert "Development" in result.output
    assert "sub-456" in result.output


def test_use_subscription_by_name_option(monkeypatch):
    """Test switching subscription by name using --name flag."""
    runner = CliRunner()

    def mock_subscription_manager_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_subscription_manager_init)

    result = runner.invoke(cli.cli, ["use-subscription", "--name", "Production"])
    assert result.exit_code == 0
    assert "Switched to subscription" in result.output
    assert "Production" in result.output


def test_use_subscription_by_name_positional(monkeypatch):
    """Test switching subscription by name using positional argument."""
    runner = CliRunner()

    def mock_subscription_manager_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_subscription_manager_init)

    result = runner.invoke(cli.cli, ["use-subscription", "Production"])
    assert result.exit_code == 0
    assert "Switched to subscription" in result.output
    assert "Production" in result.output


def test_use_subscription_case_insensitive_option(monkeypatch):
    """Test subscription name matching with --name flag is case-insensitive."""
    runner = CliRunner()

    def mock_subscription_manager_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_subscription_manager_init)

    result = runner.invoke(cli.cli, ["use-subscription", "--name", "DEVELOPMENT"])
    assert result.exit_code == 0
    assert "Development" in result.output


def test_use_subscription_case_insensitive_positional(monkeypatch):
    """Test subscription name matching with positional arg is case-insensitive."""
    runner = CliRunner()

    def mock_subscription_manager_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_subscription_manager_init)

    result = runner.invoke(cli.cli, ["use-subscription", "DEVELOPMENT"])
    assert result.exit_code == 0
    assert "Development" in result.output


def test_use_subscription_not_found_option(monkeypatch):
    """Test error when subscription not found using --id flag."""
    runner = CliRunner()

    def mock_subscription_manager_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_subscription_manager_init)

    result = runner.invoke(cli.cli, ["use-subscription", "--id", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_use_subscription_not_found_positional(monkeypatch):
    """Test error when subscription not found using positional argument."""
    runner = CliRunner()

    def mock_subscription_manager_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_subscription_manager_init)

    result = runner.invoke(cli.cli, ["use-subscription", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_use_subscription_requires_argument(monkeypatch):
    """Test error when neither positional argument nor flags provided."""
    runner = CliRunner()

    def mock_subscription_manager_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_subscription_manager_init)

    result = runner.invoke(cli.cli, ["use-subscription"])
    assert result.exit_code != 0
    assert "Specify a subscription ID or name" in result.output


def test_subscription_manager_list_subscriptions(monkeypatch):
    """Test SubscriptionManager.list_subscriptions()."""

    def mock_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_init)

    manager = SubscriptionManager()
    subs = manager.list_subscriptions()

    assert len(subs) == 3
    assert subs[0]["display_name"] == "Production"
    assert subs[1]["display_name"] == "Development"
    assert subs[2]["display_name"] == "Staging"


def test_subscription_manager_get_by_id(monkeypatch):
    """Test SubscriptionManager.get_subscription_by_id()."""

    def mock_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_init)

    manager = SubscriptionManager()
    sub = manager.get_subscription_by_id("sub-456")

    assert sub is not None
    assert sub["display_name"] == "Development"


def test_subscription_manager_get_by_name(monkeypatch):
    """Test SubscriptionManager.get_subscription_by_name()."""

    def mock_init(self):
        self.credential = None
        self.subscription_client = DummySubscriptionClient(None)

    monkeypatch.setattr(SubscriptionManager, "__init__", mock_init)

    manager = SubscriptionManager()
    sub = manager.get_subscription_by_name("Staging")

    assert sub is not None
    assert sub["subscription_id"] == "sub-789"
