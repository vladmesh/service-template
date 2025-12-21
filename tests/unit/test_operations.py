"""Tests for framework.spec.operations module."""

import pytest

from framework.spec.operations import EventsConfig, OperationSpec, RestConfig


class TestEventsConfig:
    """Tests for EventsConfig."""

    def test_subscribe_only(self) -> None:
        """EventsConfig with subscribe only is valid."""
        config = EventsConfig(subscribe="user.import.requested")
        assert config.subscribe == "user.import.requested"
        assert config.publish_on_success is None

    def test_publish_only(self) -> None:
        """EventsConfig with publish_on_success only is valid."""
        config = EventsConfig(publish_on_success="user.created")
        assert config.publish_on_success == "user.created"

    def test_both_subscribe_and_publish(self) -> None:
        """EventsConfig with both subscribe and publish is valid."""
        config = EventsConfig(
            subscribe="user.import.requested",
            publish_on_success="user.import.completed",
        )
        assert config.subscribe is not None
        assert config.publish_on_success is not None

    def test_neither_subscribe_nor_publish_fails(self) -> None:
        """EventsConfig with neither subscribe nor publish fails."""
        with pytest.raises(ValueError, match="subscribe.*or.*publish_on_success"):
            EventsConfig()

    def test_publish_on_error_optional(self) -> None:
        """publish_on_error is optional and works with subscribe."""
        config = EventsConfig(
            subscribe="user.import.requested",
            publish_on_error="user.import.failed",
        )
        assert config.publish_on_error == "user.import.failed"

    def test_message_model_override(self) -> None:
        """message_model overrides default input/output."""
        config = EventsConfig(
            subscribe="user.import.requested",
            message_model="CustomBatchPayload",
        )
        assert config.message_model == "CustomBatchPayload"

    def test_all_fields_together(self) -> None:
        """All EventsConfig fields work together."""
        config = EventsConfig(
            subscribe="user.import.requested",
            publish_on_success="user.import.completed",
            publish_on_error="user.import.failed",
            message_model="CustomPayload",
        )
        assert config.subscribe == "user.import.requested"
        assert config.publish_on_success == "user.import.completed"
        assert config.publish_on_error == "user.import.failed"
        assert config.message_model == "CustomPayload"


class TestOperationSpecValidation:
    """Tests for OperationSpec validation."""

    def test_subscribe_requires_input_model(self) -> None:
        """Operation with events.subscribe must have input model."""
        with pytest.raises(ValueError, match="must have 'input' model"):
            OperationSpec(
                name="process_import",
                events=EventsConfig(subscribe="user.import.requested"),
            )

    def test_subscribe_with_input_valid(self) -> None:
        """Operation with events.subscribe and input model is valid."""
        op = OperationSpec(
            name="process_import",
            input_model="UserImportBatch",
            events=EventsConfig(subscribe="user.import.requested"),
        )
        assert op.events is not None
        assert op.events.subscribe == "user.import.requested"
        assert op.input_model == "UserImportBatch"

    def test_publish_only_no_input_valid(self) -> None:
        """Operation with only publish_on_success doesn't require input."""
        op = OperationSpec(
            name="create_user",
            output_model="UserRead",
            rest=RestConfig(method="POST"),
            events=EventsConfig(publish_on_success="user.created"),
        )
        assert op.events is not None
        assert op.events.publish_on_success == "user.created"

    def test_operation_must_have_transport(self) -> None:
        """Operation without transport fails."""
        with pytest.raises(ValueError, match="at least one transport"):
            OperationSpec(name="orphan_op", input_model="SomeModel")

    def test_rest_only_operation(self) -> None:
        """REST-only operation is valid."""
        op = OperationSpec(
            name="get_user",
            output_model="UserRead",
            rest=RestConfig(method="GET", path="/{user_id}"),
        )
        assert op.rest is not None
        assert op.events is None

    def test_events_only_operation(self) -> None:
        """Events-only operation is valid."""
        op = OperationSpec(
            name="process_import",
            input_model="ImportBatch",
            output_model="ImportResult",
            events=EventsConfig(
                subscribe="import.requested",
                publish_on_success="import.completed",
            ),
        )
        assert op.events is not None
        assert op.rest is None

    def test_dual_transport_operation(self) -> None:
        """Operation with both REST and Events is valid."""
        op = OperationSpec(
            name="create_user",
            input_model="UserCreate",
            output_model="UserRead",
            rest=RestConfig(method="POST", status=201),
            events=EventsConfig(publish_on_success="user.created"),
        )
        assert op.rest is not None
        assert op.events is not None
