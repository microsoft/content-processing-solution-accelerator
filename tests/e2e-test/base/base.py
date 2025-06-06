class BasePage:
    def __init__(self, page):
        self.page = page

    def scroll_into_view(self, locator):
        reference_list = locator
        locator.nth(reference_list.count() - 1).scroll_into_view_if_needed()

    def is_visible(self, locator):
        locator.is_visible()
