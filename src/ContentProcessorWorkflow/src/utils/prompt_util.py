# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Prompt/template rendering utilities.

This module wraps a minimal subset of Jinja2 usage to render text prompts from
either an in-memory template string or a template file.

Operational expectations:
    - Callers pass only non-sensitive runtime values.
    - Rendering is synchronous; keep templates small to avoid blocking.
"""

from jinja2 import Template


class TemplateUtility:
    """Render Jinja2 templates from strings or files."""

    @staticmethod
    def render_from_file(file_path: str, **kwargs) -> str:
        """Render a Jinja2 template from a UTF-8 text file.

        Args:
            file_path: Path to a text file containing a Jinja2 template.
            **kwargs: Variables made available to the template during rendering.

        Returns:
            Rendered template string.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            template_content = file.read()

        template = Template(template_content)
        return template.render(**kwargs)

    @staticmethod
    def render(template_str: str, **kwargs) -> str:
        """Render a Jinja2 template from an in-memory string.

        Args:
            template_str: Jinja2 template source.
            **kwargs: Variables made available to the template during rendering.

        Returns:
            Rendered template string.
        """
        template = Template(template_str)
        return template.render(**kwargs)
