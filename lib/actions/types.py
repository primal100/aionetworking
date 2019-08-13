from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .protocols import ParallelAction, OneWaySequentialAction, ActionProtocol


ActionType = TypeVar('ActionType', bound='ActionProtocol')
ParallelActionType = TypeVar('ParallelActionType', bound='ParallelAction')
OneWaySequentialActionType = TypeVar('OneWaySequentialActionType', bound='OneWaySequentialAction')
