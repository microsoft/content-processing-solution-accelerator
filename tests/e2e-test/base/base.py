"""
Base page module providing common functionality for all page objects.
"""


class BasePage:
    """Base class for all page objects with common methods."""

    def __init__(self, page):
        """
        Initialize the BasePage with a Playwright page instance.

        Args:
            page: Playwright page object
        """
        self.page = page

    def scroll_into_view(self, locator):
        """
        Scroll the last element matching the locator into view.

        Args:
            locator: Playwright locator object
        """
        reference_list = locator
        locator.nth(reference_list.count() - 1).scroll_into_view_if_needed()

    def is_visible(self, locator):
        """
        Check if an element is visible on the page.

        Args:
            locator: Playwright locator object

        Returns:
            bool: True if visible, False otherwise
        """
        return locator.is_visible()
