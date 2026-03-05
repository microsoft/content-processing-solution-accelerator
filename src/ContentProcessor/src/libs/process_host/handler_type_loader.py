# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Dynamic handler class loader for pipeline steps.

Resolves a step name (e.g. ``'extract'``) to its corresponding handler
class (``ExtractHandler``) via importlib convention-based lookup.
"""

import importlib

from libs.pipeline.queue_handler_base import HandlerBase


def load(process_step: str) -> HandlerBase:
    """Import and return the handler class for a pipeline step.

    Follows the naming convention ``libs.pipeline.handlers.<step>_handler``
    containing a class ``<Step>Handler``.

    Args:
        process_step: Lower-case step name (e.g. 'extract', 'map').

    Returns:
        The handler *class* (not an instance).

    Raises:
        Exception: If the module or class cannot be found.
    """

    module_name = f"libs.pipeline.handlers.{process_step}_handler"
    class_name = f"{process_step.capitalize()}Handler"

    try:
        module = importlib.import_module(module_name)
        dynamic_class = getattr(module, class_name)
        return dynamic_class
    except (ModuleNotFoundError, AttributeError) as e:
        raise Exception(f"Error loading processor {class_name}: {e}")
