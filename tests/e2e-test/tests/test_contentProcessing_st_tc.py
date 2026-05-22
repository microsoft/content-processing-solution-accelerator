"""
Test module for Content Processing Solution Accelerator V2 end-to-end tests.
"""
# pylint: disable=protected-access,broad-exception-caught

import logging
import pytest
from pages.HomePageV2 import HomePageV2

logger = logging.getLogger(__name__)


@pytest.mark.gp
def test_content_processing_golden_path(login_logout, request):
    """
    Content Processing V2 - Validate Golden path works as expected

    Executes golden path test steps for Content Processing V2 with Auto Claim workflow.
    """
    request.node._nodeid = "Content Processing V2 - Validate Golden path works as expected"

    page = login_logout
    home = HomePageV2(page)

    golden_path_steps = [
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Validate API Documentation link and content", lambda: home.validate_api_document_link()),
        ("03. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("04. Upload Auto Claim documents", lambda: home.upload_files()),
        ("05. Refresh until claim status is Completed", lambda: home.refresh_until_completed()),
        ("06. Expand first claim row", lambda: home.expand_first_claim_row()),
        ("07. Validate all child files are Completed with scores", lambda: home.validate_all_child_files_completed()),
        ("08. Click on child file to load Extracted Results", lambda: home.click_on_child_file_row("claim_form.pdf")),
        ("09. Validate Extracted Results tab has JSON content", lambda: home.validate_extracted_results()),
        ("10. Validate Source Document pane displays the file", lambda: home.validate_source_document_visible()),
        ("11. Edit name value to Camille Royy, add comment, and save", lambda: home.modify_comments_and_save("Automated GP test comment")),
        ("12. Validate Process Steps for all child files", lambda: home.validate_process_steps()),
        ("13. Refresh page before AI Summary validation", lambda: home.refresh_page()),
        ("14. Click on first claim row to load Output Review", lambda: home.click_on_first_claim_row()),
        ("15. Validate AI Summary tab has content", lambda: home.validate_ai_summary()),
        ("16. Validate AI Gap Analysis tab has content", lambda: home.validate_ai_gap_analysis()),
        ("17. Validate user able to delete claim", lambda: home.delete_first_claim()),
    ]

    for description, action in golden_path_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_sections_display(login_logout, request):
    """
    Content Processing V2 - All the sections need to be displayed properly

    Validates that all main sections (Processing Queue, Output Review, Source Document)
    are displayed correctly on the home page.
    """
    request.node._nodeid = "Content Processing V2 - All the sections need to be displayed properly"

    page = login_logout
    home = HomePageV2(page)

    logger.info("Running test: Validate all sections are displayed properly")
    try:
        home.validate_home_page()
        logger.info("Test passed: All sections displayed properly")
    except Exception:
        logger.error("Test failed: All sections display validation", exc_info=True)
        raise


def test_content_processing_file_upload(login_logout, request):
    """
    Content Processing V2 - Files need to be uploaded successfully

    Validates that 4 Auto Claim documents can be uploaded successfully with schema selection.
    """
    request.node._nodeid = "Content Processing V2 - Files need to be uploaded successfully"

    page = login_logout
    home = HomePageV2(page)

    upload_steps = [
        ("01. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("02. Upload Auto Claim documents", lambda: home.upload_files()),
    ]

    for description, action in upload_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_refresh_screen(login_logout, request):
    """
    Content Processing V2 - Refreshing the screen

    Validates that screen refresh works properly after uploading files.
    """
    request.node._nodeid = "Content Processing V2 - Refreshing the screen"

    page = login_logout
    home = HomePageV2(page)

    refresh_steps = [
        ("01. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("02. Upload Auto Claim documents", lambda: home.upload_files()),
        ("03. Refresh until claim status is Completed", lambda: home.refresh_until_completed()),
    ]

    for description, action in refresh_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_expand_and_verify_child_files(login_logout, request):
    """
    Content Processing V2 - Expand claim row and verify child docs processing status

    Uploads docs, waits for completion, expands first row and validates all child files
    show Completed status with Entity and Schema scores.
    """
    request.node._nodeid = "Content Processing V2 - Expand and verify child files completed with scores"

    page = login_logout
    home = HomePageV2(page)

    steps = [
        ("01. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("02. Upload Auto Claim documents", lambda: home.upload_files()),
        ("03. Refresh until claim status is Completed", lambda: home.refresh_until_completed()),
        ("04. Expand first claim row", lambda: home.expand_first_claim_row()),
        ("05. Validate all child files Completed with scores", lambda: home.validate_all_child_files_completed()),
    ]

    for description, action in steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_import_without_collection(login_logout, request):
    """
    Content Processing V2 - Once cleared Select Collection dropdown, import content shows validation

    Validates that when no collection is selected, clicking Import Document(s)
    button displays appropriate validation message.
    """
    request.node._nodeid = "Content Processing V2 - Once cleared Select Collection dropdown, import content shows validation"

    page = login_logout
    home = HomePageV2(page)

    import_validation_steps = [
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Validate import content without collection selection", lambda: home.validate_import_without_collection()),
    ]

    for description, action in import_validation_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_delete_file(login_logout, request):
    """
    Content Processing V2 - Delete File

    Validates that uploaded claims can be successfully deleted from the processing queue.
    """
    request.node._nodeid = "Content Processing V2 - Delete File"

    page = login_logout
    home = HomePageV2(page)

    delete_file_steps = [
        ("00. Dismiss any open dialog", lambda: home.dismiss_any_dialog()),
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Delete uploaded claim", lambda: home.delete_first_claim()),
    ]

    for description, action in delete_file_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_collapsible_panels(login_logout, request):
    """
    Content Processing V2 - Collapsible section for each panel

    Validates that each panel (Processing Queue, Output Review, Source Document) can be
    collapsed and expanded correctly.
    """
    request.node._nodeid = "Content Processing V2 - Collapsible section for each panel"

    page = login_logout
    home = HomePageV2(page)

    collapsible_panels_steps = [
        ("00. Dismiss any open dialog", lambda: home.dismiss_any_dialog()),
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Validate collapsible panels functionality", lambda: home.validate_collapsible_panels()),
    ]

    for description, action in collapsible_panels_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_api_documentation(login_logout, request):
    """
    Content Processing V2 - API Document

    Validates that the API Documentation link opens correctly in a new page and displays
    the correct API documentation content.
    """
    request.node._nodeid = "Content Processing V2 - API Document"

    page = login_logout
    home = HomePageV2(page)

    api_documentation_steps = [
        ("00. Dismiss any open dialog", lambda: home.dismiss_any_dialog()),
        ("01. Validate home page is loaded", lambda: home.validate_home_page()),
        ("02. Validate API Documentation link and content", lambda: home.validate_api_document_link()),
    ]

    for description, action in api_documentation_steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_schema_selection_warning(login_logout, request):
    """
    Content Processing V2 - Alert user to upload file correctly as per the selected schema

    ADO TC 17305: Validates that the import dialog shows 'Selected Collection: Auto Claim'
    warning and that Import button remains disabled until schemas are selected for each file.
    """
    request.node._nodeid = "Content Processing V2 - Alert user to upload file correctly as per selected schema"

    page = login_logout
    home = HomePageV2(page)

    steps = [
        ("00. Dismiss any open dialog", lambda: home.dismiss_any_dialog()),
        ("01. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("02. Validate schema selection warning in import dialog", lambda: home.validate_schema_selection_warning()),
    ]

    for description, action in steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_unsupported_file_upload(login_logout, request):
    """
    Content Processing V2 - Validate upload of unsupported files

    ADO TC 26004: Validates that uploading non-PDF/non-image files (e.g., .txt, .docx)
    is rejected with an appropriate error message or disabled Import button.
    """
    request.node._nodeid = "Content Processing V2 - Validate upload of unsupported files"

    page = login_logout
    home = HomePageV2(page)

    steps = [
        ("00. Dismiss any open dialog", lambda: home.dismiss_any_dialog()),
        ("01. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("02. Validate unsupported file upload is rejected", lambda: home.validate_unsupported_file_upload()),
    ]

    for description, action in steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_import_disabled_without_schema(login_logout, request):
    """
    Content Processing V2 - Import button disabled when no schemas are selected

    Validates that after uploading files into the import dialog, the Import button
    remains disabled until schemas are assigned to every file.
    """
    request.node._nodeid = "Content Processing V2 - Import button disabled when no schemas are selected"

    page = login_logout
    home = HomePageV2(page)

    steps = [
        ("00. Dismiss any open dialog", lambda: home.dismiss_any_dialog()),
        ("01. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("02. Validate Import disabled without schema selection", lambda: home.validate_import_disabled_without_schemas()),
    ]

    for description, action in steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_import_disabled_with_partial_schemas(login_logout, request):
    """
    Content Processing V2 - Import button disabled with partial schema selection

    Validates that assigning schemas to only some files (not all) keeps the
    Import button disabled, preventing incomplete uploads.
    """
    request.node._nodeid = "Content Processing V2 - Import button disabled with partial schema selection"

    page = login_logout
    home = HomePageV2(page)

    steps = [
        ("00. Dismiss any open dialog", lambda: home.dismiss_any_dialog()),
        ("01. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("02. Validate Import disabled with partial schema selection", lambda: home.validate_import_disabled_with_partial_schemas()),
    ]

    for description, action in steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_mismatched_schema_upload(login_logout, request):
    """
    Content Processing V2 - Upload files with deliberately mismatched schemas

    Validates what happens when files are uploaded with wrong schema assignments
    (e.g., claim_form.pdf assigned Repair Estimate schema). The system should accept
    the upload but processing results may differ from correct schema assignments.
    """
    request.node._nodeid = "Content Processing V2 - Upload files with mismatched schemas"

    page = login_logout
    home = HomePageV2(page)

    steps = [
        ("00. Dismiss any open dialog", lambda: home.dismiss_any_dialog()),
        ("01. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("02. Upload files with mismatched schemas", lambda: home.upload_files_with_mismatched_schemas()),
        ("03. Refresh until processing completes", lambda: home.refresh_until_completed()),
        ("04. Expand first claim row", lambda: home.expand_first_claim_row()),
        ("05. Validate child files completed (even with wrong schemas)", lambda: home.validate_all_child_files_completed()),
        ("06. Clean up - delete the claim", lambda: home.delete_first_claim()),
    ]

    for description, action in steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_schema_preserved_after_file_removal(login_logout, request):
    """
    Content Processing V2 - Schema selections preserved after removing a file

    Validates that when a file is removed from the import dialog, the schema
    selections for the remaining files are preserved and not reset.
    """
    request.node._nodeid = "Content Processing V2 - Schema selections preserved after file removal"

    page = login_logout
    home = HomePageV2(page)

    steps = [
        ("00. Dismiss any open dialog", lambda: home.dismiss_any_dialog()),
        ("01. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("02. Validate schema preserved after file removal", lambda: home.validate_schema_dropdown_after_file_removal()),
    ]

    for description, action in steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise


def test_content_processing_network_disconnect(login_logout, request):
    """
    Content Processing V2 - Error notification on network disconnect during file upload

    ADO TC 17306: Validates that when network is disconnected during file upload,
    an appropriate error notification is displayed to the user.
    """
    request.node._nodeid = "Content Processing V2 - Error notification on network disconnect during upload"

    page = login_logout
    home = HomePageV2(page)

    steps = [
        ("00. Dismiss any open dialog", lambda: home.dismiss_any_dialog()),
        ("01. Select Auto Claim collection", lambda: home.select_collection("Auto Claim")),
        ("02. Validate network disconnect error handling", lambda: home.validate_network_disconnect_error()),
    ]

    for description, action in steps:
        logger.info(f"Running test step: {description}")
        try:
            action()
            logger.info(f"Step passed: {description}")
        except Exception:
            logger.error(f"Step failed: {description}", exc_info=True)
            raise
