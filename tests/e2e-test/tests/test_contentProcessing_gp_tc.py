"""
Test module for Content Processing Solution Accelerator end-to-end tests.
"""

import logging
import pytest
from pages.HomePage import HomePage

logger = logging.getLogger(__name__)


@pytest.mark.gp
def test_content_processing_golden_path(login_logout, request):
    """
    Content Processing - Validate Golden path works as expected

    Executes golden path test steps for Content Processing Solution Accelerator with detailed logging.
    """
    request.node._nodeid = "Content Processing - Validate Golden path works as expected"

    page = login_logout
    home = HomePage(page)

    # Define step-wise test actions for Golden Path
    golden_path_steps = [
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Select Invoice Schema", lambda: home.select_schema("Invoice")),
        ("03. Upload Invoice documents", lambda: home.upload_files("Invoice")),
        ("04. Refresh until Invoice file status is Completed", lambda: home.refresh()),
        ("05. Validate extracted result for Invoice", lambda: home.validate_invoice_extracted_result()),
        ("06. Modify Extracted Data JSON & submit comments", lambda: home.modify_and_submit_extracted_data()),
        ("07. Validate process steps for Invoice", lambda: home.validate_process_steps()),
        ("08. Select Property Loss Damage Claim Form Schema", lambda: home.select_schema("Property")),
        ("09. Upload Property Loss Damage Claim Form documents", lambda: home.upload_files("Property")),
        ("10. Refresh until Claim Form status is Completed", lambda: home.refresh()),
        ("11. Validate extracted result for Property Loss Damage Claim Form", lambda: home.validate_property_extracted_result()),
        ("12. Validate process steps for Property Loss Damage Claim Form", lambda: home.validate_process_steps()),
        ("13. Validate user able to delete file", lambda: home.delete_files()),
    ]

    # Execute all steps sequentially
    for description, action in golden_path_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_sections_display(login_logout, request):
    """
    Content Processing - All the sections need to be displayed properly

    Validates that all main sections (Processing Queue, Output Review, Source Document)
    are displayed correctly on the home page.
    """
    request.node._nodeid = "Content Processing - All the sections need to be displayed properly"

    page = login_logout
    home = HomePage(page)

    logger.info("Running test: Validate all sections are displayed properly")
    try:
        home.validate_home_page()
        logger.info("Test passed: All sections displayed properly")
    except Exception:  # pylint: disable=broad-exception-caught
        logger.error("Test failed: All sections display validation", exc_info=True)
        raise


def test_content_processing_file_upload(login_logout, request):
    """
    Content Processing - Files need to be uploaded successfully

    Validates that files can be uploaded successfully for both Invoice and Property schemas.
    """
    request.node._nodeid = "Content Processing - Files need to be uploaded successfully"

    page = login_logout
    home = HomePage(page)

    # Define file upload test steps
    upload_steps = [
        ("01. Select Invoice Schema", lambda: home.select_schema("Invoice")),
        ("02. Upload Invoice documents", lambda: home.upload_files("Invoice")),
        ("03. Select Property Loss Damage Claim Form Schema", lambda: home.select_schema("Property")),
        ("04. Upload Property Loss Damage Claim Form documents", lambda: home.upload_files("Property")),
    ]

    # Execute all upload steps sequentially
    for description, action in upload_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_refresh_screen(login_logout, request):
    """
    Content Processing - Refreshing the screen

    Validates that screen refresh works properly after uploading files.
    """
    request.node._nodeid = "Content Processing - Refreshing the screen"

    page = login_logout
    home = HomePage(page)

    # Define refresh test steps
    refresh_steps = [
        ("01. Select Invoice Schema", lambda: home.select_schema("Invoice")),
        ("02. Upload Invoice documents", lambda: home.upload_files("Invoice")),
        ("03. Refresh until file status is Completed", lambda: home.refresh()),
    ]

    # Execute all refresh steps sequentially
    for description, action in refresh_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_schema_validation(login_logout, request):
    """
    Content Processing - Validate Content Processing - Alert user to upload file correctly as per the selected schema

    Validates that the system correctly displays the selected schema and alerts users to upload
    files specific to the selected schema (Invoice and Property Loss Damage Claim Form).
    """
    request.node._nodeid = "Content Processing - Validate Content Processing - Alert user to upload file correctly as per the selected schema"

    page = login_logout
    home = HomePage(page)

    # Define schema validation test steps
    schema_validation_steps = [
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Select Invoice Schema", lambda: home.select_schema("Invoice")),
        ("03. Validate Invoice schema is selected correctly", lambda: home.validate_invoice_schema_selected()),
        ("04. Close upload popup", lambda: home.close_upload_popup()),
        ("05. Select Property Loss Damage Claim Form Schema", lambda: home.select_schema("Property")),
        ("06. Validate Property schema is selected correctly", lambda: home.validate_property_schema_selected()),
        ("07. Close upload popup", lambda: home.close_upload_popup()),
        ("08: Refresh screen", lambda: home.refresh_page())
    ]

    # Execute all schema validation steps sequentially
    for description, action in schema_validation_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_import_without_schema(login_logout, request):
    """
    Content Processing - Once cleared Select Schema dropdown, import content shows validation

    Validates that when no schema is selected (or schema is cleared), clicking Import Content
    button displays appropriate validation message prompting user to select a schema first.
    """
    request.node._nodeid = "Content Processing - Once cleared Select Schema dropdown, import content shows validation"

    page = login_logout
    home = HomePage(page)

    # Define import without schema validation test steps
    import_validation_steps = [
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Validate import content without schema selection", lambda: home.validate_import_without_schema()),
    ]

    # Execute all import validation steps sequentially
    for description, action in import_validation_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_delete_file(login_logout, request):
    """
    Content Processing - Delete File

    Validates that uploaded files can be successfully deleted from the processing queue.
    Uploads a file first, then verifies the delete functionality works correctly.
    """
    request.node._nodeid = "Content Processing - Delete File"

    page = login_logout
    home = HomePage(page)

    # Define delete file test steps
    delete_file_steps = [
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Delete uploaded file", lambda: home.delete_files()),
    ]

    # Execute all delete file steps sequentially
    for description, action in delete_file_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_search_functionality(login_logout, request):
    """
    Content Processing - Search box inside extracted results

    Validates that the search functionality works correctly in the extracted results section.
    Uploads an Invoice file, waits for processing to complete, and then validates search functionality.
    """
    request.node._nodeid = "Content Processing - Search box inside extracted results"

    page = login_logout
    home = HomePage(page)

    # Define search functionality test steps
    search_functionality_steps = [
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Select Invoice Schema", lambda: home.select_schema("Invoice")),
        ("03. Upload Invoice documents", lambda: home.upload_files("Invoice")),
        ("04. Refresh until file status is Completed", lambda: home.refresh()),
        ("05. Validate search functionality in extracted results", lambda: home.validate_search_functionality()),
    ]

    # Execute all search functionality steps sequentially
    for description, action in search_functionality_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_collapsible_panels(login_logout, request):
    """
    Content Processing - Collapsible section for each panel

    Validates that each panel (Processing Queue, Output Review, Source Document) can be
    collapsed and expanded correctly, ensuring the UI controls work as expected.
    """
    request.node._nodeid = "Content Processing - Collapsible section for each panel"

    page = login_logout
    home = HomePage(page)

    # Define collapsible panels test steps
    collapsible_panels_steps = [
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Validate collapsible panels functionality", lambda: home.validate_collapsible_panels()),
    ]

    # Execute all collapsible panels steps sequentially
    for description, action in collapsible_panels_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_api_documentation(login_logout, request):
    """
    Content Processing - API Document

    Validates that the API Documentation link opens correctly in a new page and displays
    all required API documentation sections including contentprocessor, schemavault, and Schemas.
    """
    request.node._nodeid = "Content Processing - API Document"

    page = login_logout
    home = HomePage(page)

    # Define API documentation test steps
    api_documentation_steps = [
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Validate API Documentation link and content", lambda: home.validate_api_document_link()),
    ]

    # Execute all API documentation steps sequentially
    for description, action in api_documentation_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_expandable_process_steps(login_logout, request):
    """
    Content Processing - Expandable section under each process

    Validates that each process step (extract, map, evaluate) can be expanded and collapsed correctly,
    and displays the expected content and status information.
    """
    request.node._nodeid = "Content Processing - Expandable section under each process"

    page = login_logout
    home = HomePage(page)

    # Define expandable process steps test steps
    expandable_process_steps = [
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Select Invoice Schema", lambda: home.select_schema("Invoice")),
        ("03. Upload Invoice documents", lambda: home.upload_files("Invoice")),
        ("04. Refresh until file status is Completed", lambda: home.refresh()),
        ("05. Validate expandable process steps functionality", lambda: home.validate_process_steps()),
    ]

    # Execute all expandable process steps sequentially
    for description, action in expandable_process_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(f"Step failed: {description}", exc_info=True)
            raise
