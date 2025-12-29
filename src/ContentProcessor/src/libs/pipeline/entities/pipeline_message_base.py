# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import traceback
from abc import abstractmethod
from typing import Optional

from pydantic import PrivateAttr

from libs.base.application_models import AppModelBase


class SerializableException(AppModelBase):
    """
    Exception model to make serializable.
    """

    exception: Optional[str] = None
    exception_details: Optional[str] = None
    exception_stack_trace: Optional[str] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    exception_inner_exception: Optional[str] = None
    exception_source: Optional[str] = None


class PipelineMessageBase(AppModelBase):
    """
    Base class for pipeline messages, providing a structure for handling exceptions and enforcing the implementation of
    methods for saving data to persistent storage and databases.

    Attributes:
        _exception (Optional[SerializableException]): Private attribute to store exception details.

    Properties:
        exception (Optional[SerializableException]): Property to get or set the exception details.

    Methods:
        add_exception(exception: BaseException): Adds an exception to the message, converting it to a SerializableException.
        save_to_persistent_storage(): Abstract method to save the message to persistent storage. Must be implemented by subclasses.
        save_to_database(): Abstract method to save the message to a database. Must be implemented by subclasses.

    Config:
        arbitrary_types_allowed (bool): Allows arbitrary types for attributes.
        populate_by_name (bool): Allows population of attributes by name.
    """

    _exception: Optional[SerializableException] = PrivateAttr(default=None)

    @property
    def exception(self) -> Optional[SerializableException]:
        return self._exception

    @exception.setter
    def exception(self, exception: BaseException):
        self.add_exception(exception)

    def add_exception(self, exception: BaseException):
        self._exception = SerializableException(
            exception=exception.__class__.__name__,
            exception_details=str(exception),
            exception_stack_trace="".join(traceback.format_tb(exception.__traceback__)),
            exception_type=exception.__class__.__name__,
            exception_message=str(exception),
            exception_inner_exception=str(exception.__cause__)
            if exception.__cause__
            else None,
            exception_source=str(exception.__traceback__),
        )

    @abstractmethod
    def save_to_persistent_storage(self, account_url: str, container_name: str):
        raise NotImplementedError("Method not implemented")

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
