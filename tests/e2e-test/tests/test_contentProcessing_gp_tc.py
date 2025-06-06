import logging

import pytest
from pages.HomePage import HomePage

logger = logging.getLogger(__name__)


@pytest.mark.testcase_id("TC001")
def test_ContentProcessing_Golden_path_test(login_logout):
    """Validate Golden path test case for Content Processing Accelerator"""
    page = login_logout
    home_page = HomePage(page)
    logger.info("Step 1: Validate home page is loaded.")
    home_page.validate_home_page()
    logger.info("Step 2: Select Invoice Schema.")
    home_page.select_schema("Invoice")
    logger.info("Step 3: Upload Invoice documents.")
    home_page.upload_files("Invoice")
    logger.info("Step 4: Refresh page till status is updated to Completed.")
    home_page.refresh()
    logger.info("Step 5: Validate extracted result for Invoice.")
    home_page.validate_invoice_extracted_result()
    logger.info("Step 6: Modify Extracted Data JSON & submit comments.")
    home_page.modify_and_submit_extracted_data()
    logger.info("Step 7: Validate process steps for Invoice")
    home_page.validate_process_steps()
    logger.info("Step 8: Select Property Loss Damage Claim Form Schema.")
    home_page.select_schema("Property")
    logger.info("Step 9: Upload Property Loss Damage Claim Form documents.")
    home_page.upload_files("Property")
    logger.info("Step 10: Refresh page till status is updated to Completed.")
    home_page.refresh()
    logger.info(
        "Step 11: Validate extracted result for Property Loss Damage Claim Form."
    )
    home_page.validate_property_extracted_result()
    logger.info("Step 12: Validate process steps for Property Loss Damage Claim Form.")
    home_page.validate_process_steps()
    logger.info("Step 13: Validate Delete files.")
    home_page.delete_files()
