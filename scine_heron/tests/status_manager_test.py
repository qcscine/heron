#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__copyright__ = """ This code is licensed under the 3-clause BSD license.
Copyright ETH Zurich, Laboratory of Physical Chemistry, Reiher Group.
See LICENSE.txt for details.
"""
"""
Contains tests for the status_manager module.
"""


import operator
import pytest
from scine_heron.status_manager import (
    StatusManager,
    Status,
    WriteableStatus,
    lift,
    lift_writeable,
    as_writeable_status,
    as_status,
    and_,
    or_,
    not_,
)


@pytest.fixture(name="manager")  # type: ignore[misc]
def create_manager() -> StatusManager[bool]:
    """
    Returns a StatusManager that contains `False`.
    """
    return StatusManager(False)


class TestStatusManager:
    """
    Tests for the StatusManager class.
    """

    def test_value_can_be_read(self, manager: StatusManager[bool]) -> None:
        """
        Asserts that the manager contains the value
        that was set by the constructor.
        """
        assert not manager.value

    def test_value_can_be_set(self, manager: StatusManager[bool]) -> None:
        """
        Asserts that the manager contains the value
        that has been set.
        """
        manager.value = True

        assert manager.value

    def test_setting_value_notifies(self, manager: StatusManager[bool]) -> None:
        """
        Asserts that setting the value causes the signal to
        be emitted.
        """
        result = 0

        def set_result(value: bool) -> None:
            nonlocal result
            result = 1 if value else 0

        manager.changed_signal.connect(set_result)

        manager.value = True

        assert result == 1

    def test_setting_value_does_not_notify_if_same_value(
        self, manager: StatusManager[bool]
    ) -> None:
        """
        Asserts that setting the value that the manager already contains
        does not cause a signal to be emitted.
        """
        result = 1

        def set_result(value: bool) -> None:
            nonlocal result
            result = 1 if value else 0

        manager.changed_signal.connect(set_result)

        manager.value = False

        assert result == 1


class TestTransformedWriteableStatusManager:
    """
    Tests for the TransformedStatusManager class.
    """

    @staticmethod
    def identity(value: bool) -> bool:
        """
        Returns the parameter.
        """
        return value

    def test_provides_untransformed_value_if_id_transform(
        self, manager: StatusManager[bool]
    ) -> None:
        """
        The value of a transformed status manager is the transform applied
        to the arguments.
        """
        transformed = lift_writeable(self.identity, self.identity)(manager)

        assert transformed.value == manager.value

    def test_provides_transformed_value(self, manager: StatusManager[bool]) -> None:
        """
        The value of a transformed status manager is the transform applied
        to the arguments.
        """
        transformed = lift_writeable(lambda x: 2 if x else 1, lambda x: x == 2)(manager)

        assert transformed.value == 1

    def test_writes_transformed_value(self, manager: StatusManager[bool]) -> None:
        """
        The input value is set via the inverse transform.
        """
        transformed = lift_writeable(lambda x: 2 if x else 1, lambda x: x == 2)(manager)
        transformed.value = 2

        assert manager.value
        assert transformed.value == 2

    def test_modifying_argument_modifies_transformed_value(
        self, manager: StatusManager[bool]
    ) -> None:
        """
        The value of a transformed status manager is the transform applied
        to the arguments.
        """
        transformed = lift_writeable(self.identity, self.identity)(manager)

        manager.value = True

        assert transformed.value == manager.value

    def test_modifying_argument_notifies_if_different_result(
        self, manager: StatusManager[bool]
    ) -> None:
        """
        If the result of the transform changed, then a signal is emitted.
        """
        notified = False

        def slot() -> None:
            nonlocal notified
            notified = True

        transformed = lift_writeable(self.identity, self.identity)(manager)
        transformed.changed_signal.connect(slot)

        manager.value = True

        assert notified

    def test_modifying_argument_does_not_notify_if_same_result(
        self, manager: StatusManager[bool]
    ) -> None:
        """
        If the result of the transform did not change, then a signal does not
        need to be emitted.
        """
        notified = False

        def slot() -> None:
            nonlocal notified
            notified = True

        transformed = lift_writeable(lambda _: True, lambda _: True)(manager)
        transformed.changed_signal.connect(slot)

        manager.value = True

        assert not notified

    def test_emits_value(self, manager: StatusManager[bool]) -> None:
        """
        The signal also provides the current value.
        """
        value = manager.value

        def slot(argument: bool) -> None:
            nonlocal value
            value = argument

        transformed = lift_writeable(self.identity, self.identity)(manager)
        transformed.changed_signal.connect(slot)

        manager.value = True

        assert value

    def test_logical_not_uses_not_of_values(self, manager: StatusManager[bool]) -> None:
        """
        The function `not_` can be used to combine status managers.
        """

        result = not_(manager)

        assert result.value
        manager.value = True
        assert not result.value


class TestTransformedStatusManager:
    """
    Tests for the TransformedStatusManager class.
    """

    @staticmethod
    def identity(value: bool) -> bool:
        """
        Returns the parameter.
        """
        return value

    def test_provides_untransformed_value_if_id_transform(
        self, manager: StatusManager[bool]
    ) -> None:
        """
        The value of a transformed status manager is the transform applied
        to the arguments.
        """

        transformed = lift(self.identity)(manager)

        assert transformed.value == manager.value

    def test_provides_transformed_value(self, manager: StatusManager[bool]) -> None:
        """
        The value of a transformed status manager is the transform applied
        to the arguments.
        """
        transformed = lift(lambda x: 2 if x else 1)(manager)

        assert transformed.value == 1

    def test_modifying_argument_modifies_transformed_value(
        self, manager: StatusManager[bool]
    ) -> None:
        """
        The value of a transformed status manager is the transform applied
        to the arguments.
        """
        transformed = lift(self.identity)(manager)

        manager.value = True

        assert transformed.value == manager.value

    def test_modifying_argument_notifies_if_different_result(
        self, manager: StatusManager[bool]
    ) -> None:
        """
        If the result of the transform changed, then a signal is emitted.
        """
        notified = False

        def slot() -> None:
            nonlocal notified
            notified = True

        transformed = lift(self.identity)(manager)
        transformed.changed_signal.connect(slot)

        manager.value = True

        assert notified

    def test_modifying_argument_does_not_notify_if_same_result(
        self, manager: StatusManager[bool]
    ) -> None:
        """
        If the result of the transform did not change, then a signal does not
        need to be emitted.
        """
        notified = False

        def slot() -> None:
            nonlocal notified
            notified = True

        transformed = lift(lambda _: True)(manager)
        transformed.changed_signal.connect(slot)

        manager.value = True

        assert not notified

    def test_combining_two_arguments_yields_correct_result(self) -> None:
        """
        Transform may take multiple arguments.
        """
        argument_1 = StatusManager[int](1)
        argument_2 = StatusManager[int](2)

        transformed = lift(operator.add)(argument_1, argument_2)

        assert transformed.value == 3

    def test_each_of_the_arguments_may_trigger_update(self) -> None:
        """
        Transform may take multiple arguments.
        """
        notified = False

        def slot() -> None:
            nonlocal notified
            notified = True

        argument_1 = StatusManager(1)
        argument_2 = StatusManager(2)

        transformed = lift(operator.add)(argument_1, argument_2)
        transformed.changed_signal.connect(slot)

        argument_2.value = 4

        assert notified
        assert transformed.value == 1 + 4

    def test_emits_value(self, manager: StatusManager[bool]) -> None:
        """
        The signal also provides the current value.
        """
        value = manager.value

        def slot(argument: bool) -> None:
            nonlocal value
            value = argument

        transformed = lift(self.identity)(manager)
        transformed.changed_signal.connect(slot)

        manager.value = True

        assert value

    def test_decorator_can_be_used_to_create_transformed_status_wrapper(
        self, manager: StatusManager[bool]
    ) -> None:
        """
        The lift can be used to convert a function
        bool -> bool to a function on StatusManagers.
        """

        @lift
        def transform(value: bool) -> str:
            return "a" if value else "b"

        transformed = transform(manager)
        assert transformed.value == "b"  # pylint: disable=no-member

        manager.value = True
        assert transformed.value == "a"  # pylint: disable=no-member

    def test_logical_and_uses_and_of_values(self, manager: StatusManager[bool]) -> None:
        """
        The function `and_` can be used to combine status managers.
        """

        other_manager = StatusManager(True)
        result = and_(manager, other_manager)

        assert not result.value
        manager.value = True
        assert result.value

    def test_logical_or_uses_or_of_values(self, manager: StatusManager[bool]) -> None:
        """
        The function `or_` can be used to combine status managers.
        """

        other_manager = StatusManager(True)
        result = or_(manager, other_manager)

        assert result.value
        other_manager.value = False
        assert not result.value


@pytest.fixture(name="writeable_adapted_manager")  # type: ignore[misc]
def create_writeable_adapted_manager(
    manager: StatusManager[bool],
) -> WriteableStatus[bool]:
    """
    Returns a WriteableStatus that wraps `manager`.
    """
    return as_writeable_status(
        pull=lambda: manager.value,
        push=lambda x: setattr(manager, "value", x),
        signal=manager.changed_signal,
    )


class TestAdaptedWriteableStatusManager:
    """
    Tests for the TransformedWriteableStatusManager class.
    """

    def test_value_can_be_read(
        self,
        manager: StatusManager[bool],
        writeable_adapted_manager: WriteableStatus[bool],
    ) -> None:
        """
        A value can be read from the adapted manager.
        """
        assert writeable_adapted_manager.value == manager.value

    def test_value_can_be_set(
        self,
        manager: StatusManager[bool],
        writeable_adapted_manager: WriteableStatus[bool],
    ) -> None:
        """
        A value can be set via the adapted manager.
        """
        writeable_adapted_manager.value = True
        assert manager.value

    def test_signals_are_forwarded(
        self,
        manager: StatusManager[bool],
        writeable_adapted_manager: WriteableStatus[bool],
    ) -> None:
        """
        The provided signal is forwarded.
        """
        value = manager.value

        def slot(argument: bool) -> None:
            nonlocal value
            value = argument

        writeable_adapted_manager.changed_signal.connect(slot)
        manager.value = True

        assert value


@pytest.fixture(name="adapted_manager")  # type: ignore[misc]
def create_adapted_manager(manager: StatusManager[bool]) -> Status[bool]:
    """
    Returns an AdaptedStatusManager that wraps `manager`.
    """
    return as_status(pull=lambda: manager.value, signal=manager.changed_signal)


class TestAdaptedStatusManager:
    """
    Tests for the TransformedStatusManager class.
    """

    def test_value_can_be_read(
        self, manager: StatusManager[bool], adapted_manager: Status[bool],
    ) -> None:
        """
        A value can be read from the adapted manager.
        """
        assert adapted_manager.value == manager.value

    def test_signals_are_forwarded(
        self, manager: StatusManager[bool], adapted_manager: Status[bool],
    ) -> None:
        """
        The provided signal is forwarded.
        """
        value = manager.value

        def slot(argument: bool) -> None:
            nonlocal value
            value = argument

        adapted_manager.changed_signal.connect(slot)
        manager.value = True

        assert value
