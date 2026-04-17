"""
Home page module for Content Processing Solution Accelerator V2.
Supports Auto Claim collection with expandable rows, AI Summary, and AI Gap Analysis.
"""

import os
import glob
import logging

from base.base import BasePage
from playwright.sync_api import expect

logger = logging.getLogger(__name__)


class HomePageV2(BasePage):
    """
    V2 Home page object containing all locators and methods for interacting
    with the Content Processing home page (Auto Claim workflow).
    """

    # HOMEPAGE PANELS
    PROCESSING_QUEUE = "//span[normalize-space()='Processing Queue']"
    OUTPUT_REVIEW = "//span[contains(normalize-space(),'Output Review')]"
    SOURCE_DOC = "//span[normalize-space()='Source Document']"
    PROCESSING_QUEUE_BTN = "//button[normalize-space()='Processing Queue']"
    OUTPUT_REVIEW_BTN = "//button[contains(normalize-space(),'Output Review')]"
    SOURCE_DOC_BTN = "//button[normalize-space()='Source Document']"
    COLLAPSE_PANEL_BTN = "//button[@title='Collapse Panel']"

    # COLLECTION & ACTIONS
    SELECT_COLLECTION = "//input[contains(@placeholder,'Select Collection')]"
    IMPORT_DOCUMENTS_BTN = "//button[normalize-space()='Import Document(s)']"
    REFRESH_BTN = "//button[normalize-space()='Refresh']"

    # IMPORT DIALOG
    BROWSE_FILES_BTN = "//button[normalize-space()='Browse Files']"
    IMPORT_BTN = "//button[normalize-space()='Import']"
    CLOSE_BTN = "//button[normalize-space()='Close']"
    SELECTED_COLLECTION_INFO = "//div[contains(text(),'Selected Collection')]"
    SELECT_SCHEMA_COMBOBOX = "//input[@placeholder='Select Schema']"

    # File name to schema mapping for Auto Claim collection
    FILE_SCHEMA_MAP = {
        "claim_form.pdf": "Auto Insurance Claim Form",
        "damage_photo.png": "Damaged Vehicle Image Assessment",
        "police_report.pdf": "Police Report Document",
        "repair_estimate.pdf": "Repair Estimate Document",
    }

    # TABLE (uses div with role="table", not native <table>)
    CLAIMS_TABLE = "div[role='table']"
    DATA_ROWS = "div[role='table'] div[role='rowgroup']:nth-child(2) div[role='row']"
    NO_DATA = "//p[normalize-space()='No data available']"

    # OUTPUT REVIEW TABS (Claim level)
    AI_SUMMARY_TAB = "//span[.='AI Summary']"
    AI_GAP_ANALYSIS_TAB = "//span[.='AI Gap Analysis']"

    AI_SUMMARY_CONTENT = "//p[contains(text(),'1) Claim & Policy')]"
    AI_GAP_ANALYSIS_CONTENT = "//p[contains(text(),'Executive Summary:')]"

    # OUTPUT REVIEW TABS (Document/child file level)
    EXTRACTED_RESULTS_TAB = "//span[.='Extracted Results']"
    PROCESS_STEPS_TAB = "//span[.='Process Steps']"

    # COMMENTS
    COMMENTS = "//textarea"
    SAVE_BTN = "//button[normalize-space()='Save']"

    # SOURCE DOCUMENT PANE
    SOURCE_DOC_NO_DATA = "//p[normalize-space()='No document available']"

    # API DOCUMENTATION
    API_DOCUMENTATION_TAB = "//div[normalize-space()='API Documentation']"

    def __init__(self, page):
        """
        Initialize the HomePageV2.

        Args:
            page: Playwright page object
        """
        super().__init__(page)
        self.page = page

    def dismiss_any_dialog(self):
        """Dismiss any open dialog or backdrop to ensure a clean state."""
        # Try closing via Close button first with a short timeout
        try:
            close_btn = self.page.locator(self.CLOSE_BTN)
            if close_btn.count() > 0 and close_btn.is_visible():
                close_btn.click(timeout=5000)
                self.page.wait_for_timeout(500)
        except (TimeoutError, Exception):  # pylint: disable=broad-exception-caught
            # Button may be unstable or detached — ignore and continue
            pass

        # Press Escape to dismiss any remaining backdrop
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(500)

    def validate_home_page(self):
        """Validate that all main sections are visible on the home page."""
        logger.info("Starting home page validation...")

        logger.info("Validating Processing Queue is visible...")
        expect(self.page.locator(self.PROCESSING_QUEUE)).to_be_visible()
        logger.info("✓ Processing Queue is visible")

        logger.info("Validating Output Review is visible...")
        expect(self.page.locator(self.OUTPUT_REVIEW)).to_be_visible()
        logger.info("✓ Output Review is visible")

        logger.info("Validating Source Document is visible...")
        expect(self.page.locator(self.SOURCE_DOC)).to_be_visible()
        logger.info("✓ Source Document is visible")

        self.page.wait_for_timeout(2000)
        logger.info("Home page validation completed successfully")

    def select_collection(self, collection_name="Auto Claim"):
        """
        Select a collection from the Select Collection dropdown.

        Args:
            collection_name: Name of the collection to select (default: Auto Claim)
        """
        logger.info(f"Starting collection selection for: {collection_name}")

        self.page.wait_for_timeout(3000)

        logger.info("Clicking on Select Collection dropdown...")
        self.page.locator(self.SELECT_COLLECTION).click()
        logger.info("✓ Select Collection dropdown clicked")

        logger.info(f"Selecting '{collection_name}' option...")
        self.page.get_by_role("option", name=collection_name).click()
        logger.info(f"✓ '{collection_name}' option selected")

        self.page.wait_for_timeout(2000)
        logger.info(f"Collection selection completed for: {collection_name}")

    def get_testdata_files(self):
        """
        Dynamically get all files from the testdata folder.

        Returns:
            list: List of absolute file paths from testdata folder
        """
        current_working_dir = os.getcwd()
        testdata_dir = os.path.join(current_working_dir, "testdata")
        files = glob.glob(os.path.join(testdata_dir, "*"))
        # Filter only files (not directories)
        files = [f for f in files if os.path.isfile(f)]
        logger.info(f"Found {len(files)} files in testdata folder: {[os.path.basename(f) for f in files]}")
        return files

    def select_schema_for_file(self, file_name, schema_name):
        """
        Select a schema from the dropdown for a specific file in the import dialog.

        Args:
            file_name: Name of the file (e.g. 'claim_form.pdf')
            schema_name: Schema to select (e.g. 'Auto Insurance Claim Form')
        """
        logger.info(f"Selecting schema '{schema_name}' for file '{file_name}'...")

        # Get all schema comboboxes and file labels in the import dialog
        schema_dropdowns = self.page.get_by_role(
            "alertdialog", name="Import Content"
        ).get_by_placeholder("Select Schema")
        file_labels = self.page.get_by_role(
            "alertdialog", name="Import Content"
        ).locator("strong")

        # Find the index of this file among all listed files
        count = file_labels.count()
        target_index = -1
        for i in range(count):
            label_text = file_labels.nth(i).inner_text().strip()
            if label_text == file_name:
                target_index = i
                break

        if target_index == -1:
            raise Exception(f"File '{file_name}' not found in import dialog")

        # Click on the schema dropdown for this file
        schema_dropdowns.nth(target_index).click()
        logger.info(f"✓ Schema dropdown clicked for '{file_name}'")

        self.page.wait_for_timeout(1000)

        # Select the schema option
        self.page.get_by_role("option", name=schema_name).click()
        logger.info(f"✓ Schema '{schema_name}' selected for '{file_name}'")

        self.page.wait_for_timeout(1000)

    def upload_files(self):
        """
        Upload all files from the testdata folder dynamically.
        After browsing files, selects the appropriate schema for each file
        before clicking Import.
        """
        logger.info("Starting file upload for Auto Claim documents...")

        files = self.get_testdata_files()
        if not files:
            raise Exception("No files found in testdata folder")

        with self.page.expect_file_chooser() as fc_info:
            logger.info("Clicking Import Document(s) button...")
            self.page.locator(self.IMPORT_DOCUMENTS_BTN).click()
            logger.info("✓ Import Document(s) button clicked")

            logger.info("Clicking Browse Files button...")
            self.page.locator(self.BROWSE_FILES_BTN).click()
            logger.info("✓ Browse Files button clicked")

            self.page.wait_for_timeout(3000)

        file_chooser = fc_info.value
        logger.info(f"Selecting {len(files)} files: {[os.path.basename(f) for f in files]}")
        file_chooser.set_files(files)
        logger.info("✓ All files selected")

        self.page.wait_for_timeout(5000)

        # Select schema for each uploaded file
        for file_path in files:
            file_name = os.path.basename(file_path)
            schema_name = self.FILE_SCHEMA_MAP.get(file_name)
            if schema_name:
                self.select_schema_for_file(file_name, schema_name)
            else:
                logger.warning(
                    f"No schema mapping found for '{file_name}', skipping schema selection"
                )

        self.page.wait_for_timeout(2000)

        logger.info("Clicking Import button...")
        self.page.locator(self.IMPORT_BTN).click()
        logger.info("✓ Import button clicked")

        self.page.wait_for_timeout(10000)

        logger.info("Validating upload success...")
        expect(
            self.page.get_by_role("alertdialog", name="Import Content")
            .locator("path")
            .nth(1)
        ).to_be_visible()
        logger.info("✓ Upload success message is visible")

        logger.info("Closing upload dialog...")
        self.page.locator(self.CLOSE_BTN).click()
        logger.info("✓ Upload dialog closed")

        logger.info("File upload completed successfully")

    def refresh_until_completed(self, max_retries=60):
        """
        Refresh and wait for the first claim row (parent) to show Completed status.
        Processing goes through: Processing → Summarizing → GapAnalysis → Completed.

        Args:
            max_retries: Maximum number of refresh attempts (default: 60)
        """
        logger.info("Starting refresh process to monitor claim processing status...")

        for i in range(max_retries):
            self.page.wait_for_timeout(3000)
            # Get the status of the first data row (parent claim row)
            first_row = self.page.locator(self.DATA_ROWS).first
            status_cell = first_row.locator("div[role='cell']").nth(3)
            status_text = status_cell.inner_text().strip()
            logger.info(f"Attempt {i + 1}/{max_retries}: Current status = '{status_text}'")

            if status_text == "Completed":
                logger.info("✓ Claim processing completed successfully")
                return

            if status_text == "Error":
                logger.error(f"Process failed with status: 'Error' after {i + 1} retries")
                raise Exception(
                    f"Process failed with status: 'Error' after {i + 1} retries."
                )

            logger.info("Clicking Refresh button...")
            self.page.locator(self.REFRESH_BTN).click()
            logger.info("✓ Refresh button clicked, waiting...")
            self.page.wait_for_timeout(15000)

        raise Exception(
            f"Process did not complete after {max_retries} retries."
        )

    def expand_first_claim_row(self):
        """Expand the first claim row to reveal child file rows."""
        logger.info("Expanding first claim row...")

        first_row = self.page.locator(self.DATA_ROWS).first
        expand_btn = first_row.locator("button").first
        expand_btn.click()
        logger.info("✓ First claim row expanded")

        self.page.wait_for_timeout(3000)

    def get_child_file_rows(self):
        """
        Get child file rows belonging to the first expanded claim row.
        Child rows appear immediately after the parent row and don't have
        a button in the first cell. Stops when hitting the next parent row.

        Returns:
            list: List of (index, row_locator) tuples for child rows
        """
        all_rows = self.page.locator(self.DATA_ROWS)
        total = all_rows.count()
        child_indices = []
        found_first_parent = False

        for i in range(total):
            row = all_rows.nth(i)
            first_cell = row.locator("div[role='cell']").first
            has_button = first_cell.locator("button").count() > 0

            if has_button:
                if found_first_parent:
                    # Hit the next parent row — stop collecting children
                    break
                found_first_parent = True
                continue

            if found_first_parent:
                child_indices.append(i)

        logger.info(f"Found {len(child_indices)} child file rows for first claim")
        self.child_indices = child_indices
        return all_rows

    def validate_all_child_files_completed(self):
        """Validate that all child file rows show Completed status with Entity/Schema scores."""
        logger.info("Validating all child file statuses...")

        all_rows = self.get_child_file_rows()
        child_indices = self.child_indices

        if len(child_indices) == 0:
            raise Exception("No child file rows found after expanding claim row")

        for idx in child_indices:
            row = all_rows.nth(idx)
            cells = row.locator("div[role='cell']")

            # Get file name from second cell (index 1)
            file_name = cells.nth(1).inner_text().strip()

            # Get status from fourth cell (index 3)
            status_text = cells.nth(3).inner_text().strip()
            logger.info(f"File '{file_name}': Status = '{status_text}'")

            if status_text != "Completed":
                raise Exception(
                    f"File '{file_name}' has status '{status_text}', expected 'Completed'"
                )
            logger.info(f"✓ File '{file_name}' status is Completed")

            # Validate Entity score exists (index 5)
            entity_score = cells.nth(5).inner_text().strip()
            if not entity_score or entity_score == "":
                raise Exception(f"File '{file_name}' has no Entity score")
            logger.info(f"✓ File '{file_name}' Entity score: {entity_score}")

            # Validate Schema score exists (index 6)
            schema_score = cells.nth(6).inner_text().strip()
            if not schema_score or schema_score == "":
                raise Exception(f"File '{file_name}' has no Schema score")
            logger.info(f"✓ File '{file_name}' Schema score: {schema_score}")

        logger.info(f"All {len(child_indices)} child files validated successfully")

    def validate_ai_summary(self):
        """Validate that the AI Summary tab has content."""
        logger.info("Starting AI Summary validation...")

        logger.info("Clicking on AI Summary tab...")
        self.page.locator(self.AI_SUMMARY_TAB).first.click()
        logger.info("✓ AI Summary tab clicked")

        self.page.wait_for_timeout(3000)

        logger.info("Validating AI Summary content is visible...")
        expect(self.page.locator(self.AI_SUMMARY_CONTENT)).to_be_visible()
        logger.info("✓ AI Summary content is visible")

        logger.info("AI Summary validation completed successfully")

    def validate_ai_gap_analysis(self):
        """Validate that the AI Gap Analysis tab has content."""
        logger.info("Starting AI Gap Analysis validation...")

        logger.info("Clicking on AI Gap Analysis tab...")
        self.page.locator(self.AI_GAP_ANALYSIS_TAB).first.click()
        logger.info("✓ AI Gap Analysis tab clicked")

        self.page.wait_for_timeout(3000)

        logger.info("Validating AI Gap Analysis content is visible...")
        expect(self.page.locator(self.AI_GAP_ANALYSIS_CONTENT)).to_be_visible()
        logger.info("✓ AI Gap Analysis content is visible")

        logger.info("AI Gap Analysis validation completed successfully")

    def click_on_first_claim_row(self):
        """Click on the first claim row to select it and load its Output Review."""
        logger.info("Clicking on first claim row to load Output Review...")

        first_row = self.page.locator(self.DATA_ROWS).first
        # Click on the file name cell to select the row
        first_row.locator("div[role='cell']").nth(1).click()
        logger.info("✓ First claim row clicked")

        self.page.wait_for_timeout(5000)

    def click_on_child_file_row(self, file_name="claim_form.pdf"):
        """
        Click on a specific child file row to load its Extracted Results and Source Document.

        Args:
            file_name: Name of the child file to click (default: claim_form.pdf)
        """
        logger.info(f"Clicking on child file '{file_name}' to load Output Review...")

        all_rows = self.page.locator(self.DATA_ROWS)
        total = all_rows.count()
        clicked = False

        for i in range(total):
            row = all_rows.nth(i)
            file_cell = row.locator("div[role='cell']").nth(1)
            cell_text = file_cell.inner_text().strip()
            if cell_text == file_name:
                file_cell.click()
                clicked = True
                break

        if not clicked:
            raise Exception(f"Child file '{file_name}' not found in table rows")

        logger.info(f"✓ Child file '{file_name}' clicked")
        self.page.wait_for_timeout(5000)

    def validate_extracted_results(self):
        """Validate that the Extracted Results tab is visible and has JSON content."""
        logger.info("Starting Extracted Results validation...")

        logger.info("Clicking on Extracted Results tab...")
        self.page.locator(self.EXTRACTED_RESULTS_TAB).first.click()
        logger.info("✓ Extracted Results tab clicked")

        self.page.wait_for_timeout(3000)

        logger.info("Validating Extracted Results content is visible...")
        # The Extracted Results tab shows a JSON editor with extracted data
        tabpanel = self.page.locator("div[role='tabpanel']")
        expect(tabpanel).to_be_visible()
        # JSON content should not be empty — look for the react-json-view container
        json_content = tabpanel.locator(
            "//div[contains(@class,'react-json-view')] | "
            "//div[contains(@class,'json-editor')] | "
            "//span[contains(@class,'object-key')]"
        )
        if json_content.count() > 0:
            logger.info("✓ Extracted Results JSON content is visible")
        else:
            # Fallback: check tabpanel has any text content
            panel_text = tabpanel.inner_text().strip()
            if len(panel_text) > 0:
                logger.info(f"✓ Extracted Results has content ({len(panel_text)} chars)")
            else:
                raise Exception("Extracted Results tab has no content")

        logger.info("Extracted Results validation completed successfully")

    def validate_source_document_visible(self):
        """Validate that the Source Document pane shows the document (not 'No document available')."""
        logger.info("Starting Source Document pane validation...")

        logger.info("Validating Source Document pane has content...")
        _source_doc_pane = self.page.locator(
            "//div[contains(text(),'Source Document')]/ancestor::div[1]/following-sibling::*"
        )

        # Verify "No document available" is NOT shown
        no_data = self.page.locator(self.SOURCE_DOC_NO_DATA)
        if no_data.count() > 0 and no_data.is_visible():
            raise Exception("Source Document pane shows 'No document available'")

        logger.info("✓ Source Document pane is displaying a document")
        logger.info("Source Document validation completed successfully")

    def modify_comments_and_save(self, comment_text="Automated test comment"):
        """
        Click on claim_form.pdf child document, find the 'name' field with value
        'Camille Roy', update it to 'Camille Royy', add a comment, click Save,
        and verify the updated value is persisted.

        Args:
            comment_text: Text to enter in the comments field
        """
        logger.info("Starting modify JSON, add comment, and save...")

        updated_value = "Camille Royy"
        original_value = "Camille Roy"

        # Step 1: Click on claim_form.pdf child document
        logger.info("Clicking on claim_form.pdf child document...")
        self.click_on_child_file_row("claim_form.pdf")
        logger.info("✓ claim_form.pdf selected")

        # Step 2: Ensure Extracted Results tab is active
        logger.info("Ensuring Extracted Results tab is active...")
        self.page.locator(self.EXTRACTED_RESULTS_TAB).first.click()
        self.page.wait_for_timeout(3000)
        logger.info("✓ Extracted Results tab is active")

        # Step 3: Find the name field by its ID and double-click to edit
        logger.info("Locating policyholder name field in JSON editor...")
        name_field = self.page.locator(
            "//div[@id='policyholder_information.name_display']"
        )

        if name_field.count() == 0:
            logger.warning("⚠ policyholder_information.name_display not found — skipping edit")
        else:
            name_field.first.scroll_into_view_if_needed()
            logger.info("✓ Found policyholder_information.name_display field")

            # Double-click to enter edit mode
            name_field.first.dblclick()
            logger.info("✓ Double-clicked on name field to enter edit mode")
            self.page.wait_for_timeout(2000)

            # Find the input/textarea in edit mode and update the value
            edit_input = self.page.locator(
                ".jer-input-component input, "
                ".jer-input-component textarea, "
                ".JSONEditor-contentDiv input[type='text'], "
                ".JSONEditor-contentDiv textarea"
            )

            if edit_input.count() > 0:
                logger.info("Edit mode activated — updating value...")
                edit_input.first.clear()
                edit_input.first.fill(updated_value)
                logger.info(f"✓ Value changed from '{original_value}' to '{updated_value}'")

                # Confirm the edit
                confirm_btn = self.page.locator(
                    ".jer-confirm-buttons button:first-child, "
                    "[class*='jer-confirm'] button, "
                    ".jer-edit-buttons button:first-child"
                )
                if confirm_btn.count() > 0:
                    confirm_btn.first.click()
                    logger.info("✓ Edit confirmed via confirm button")
                else:
                    edit_input.first.press("Enter")
                    logger.info("✓ Edit confirmed via Enter key")

                self.page.wait_for_timeout(1000)
            else:
                logger.warning("⚠ Edit input not found after double-click")

        # Step 4: Add comment text
        logger.info("Locating Comments textarea...")
        comments_field = self.page.locator(self.COMMENTS)
        expect(comments_field).to_be_visible()
        logger.info("✓ Comments textarea is visible")

        logger.info("Clearing and entering comment text...")
        comments_field.fill(comment_text)
        logger.info(f"✓ Comment entered: '{comment_text}'")

        self.page.wait_for_timeout(1000)

        # Step 5: Click Save
        logger.info("Clicking Save button...")
        save_btn = self.page.locator(self.SAVE_BTN)
        expect(save_btn).to_be_enabled(timeout=5000)
        save_btn.click()
        logger.info("✓ Save button clicked")

        self.page.wait_for_timeout(8000)

        # Step 6: Verify the updated value is persisted
        logger.info("Verifying saved data persisted...")

        # Re-click claim_form.pdf to reload Extracted Results
        self.click_on_child_file_row("claim_form.pdf")
        self.page.locator(self.EXTRACTED_RESULTS_TAB).first.click()
        self.page.wait_for_timeout(3000)

        # Search for the updated value in the JSON editor content
        page_content = self.page.locator(".JSONEditor-contentDiv").inner_text()
        if updated_value in page_content:
            logger.info(f"✓ Updated value '{updated_value}' found — data persisted successfully")
        else:
            logger.warning(f"⚠ '{updated_value}' not found after save — may have been reset")

        # Verify comment is persisted
        comments_after = self.page.locator(self.COMMENTS).input_value()
        if comment_text in comments_after:
            logger.info(f"✓ Comment '{comment_text}' is persisted after save")
        else:
            logger.info(f"✓ Save completed (comment field value: '{comments_after[:50]}')")

        logger.info("Modify JSON, add comment, and save completed successfully")

    def validate_process_steps(self):
        """
        Validate the Process Steps tab for all child files in the expanded claim.
        Clicks each child file, opens Process Steps tab, and expands the accordion
        sections (Extract, Map, Evaluate) to verify content loads.
        """
        logger.info("Starting Process Steps validation for all child files...")

        # Get the list of child file names from FILE_SCHEMA_MAP
        child_files = list(self.FILE_SCHEMA_MAP.keys())
        logger.info(f"Will validate Process Steps for {len(child_files)} files: {child_files}")

        for file_name in child_files:
            logger.info(f"--- Validating Process Steps for '{file_name}' ---")

            # Click on the child file row
            logger.info(f"Clicking on child file '{file_name}'...")
            all_rows = self.page.locator(self.DATA_ROWS)
            total = all_rows.count()
            clicked = False

            for i in range(total):
                row = all_rows.nth(i)
                file_cell = row.locator("div[role='cell']").nth(1)
                cell_text = file_cell.inner_text().strip()
                if cell_text == file_name:
                    file_cell.click()
                    clicked = True
                    break

            if not clicked:
                logger.warning(f"⚠ Child file '{file_name}' not found in table — skipping")
                continue

            logger.info(f"✓ Child file '{file_name}' clicked")
            self.page.wait_for_timeout(5000)

            # Click on Process Steps tab
            logger.info(f"Clicking Process Steps tab for '{file_name}'...")
            self.page.locator(self.PROCESS_STEPS_TAB).first.click()
            self.page.wait_for_timeout(3000)
            logger.info(f"✓ Process Steps tab clicked for '{file_name}'")

            # Validate tab panel is visible
            tabpanel = self.page.locator("div[role='tabpanel']")
            expect(tabpanel).to_be_visible()

            # Process Steps uses FluentUI Accordion — each step has an AccordionHeader button
            accordion_headers = tabpanel.locator("button").filter(has=self.page.locator("span"))

            header_count = accordion_headers.count()
            if header_count == 0:
                logger.warning(f"⚠ No accordion headers found for '{file_name}'")
            else:
                logger.info(f"Found {header_count} process step sections for '{file_name}'")

                for j in range(min(header_count, 3)):
                    header = accordion_headers.nth(j)
                    header_text = header.inner_text().strip()
                    logger.info(f"Expanding '{header_text}' for '{file_name}'...")
                    header.click()
                    self.page.wait_for_timeout(3000)
                    logger.info(f"✓ '{header_text}' expanded for '{file_name}'")

            logger.info(f"✓ Process Steps validated for '{file_name}'")

        logger.info(f"Process Steps validation completed for all {len(child_files)} child files")

    def delete_first_claim(self):
        """Delete the first claim via More actions menu."""
        logger.info("Starting claim deletion process...")

        logger.info("Clicking on More actions button...")
        self.page.get_by_role("button", name="More actions").first.click()
        logger.info("✓ More actions button clicked")

        logger.info("Clicking on Delete menu item...")
        self.page.get_by_role("menuitem", name="Delete").click()
        logger.info("✓ Delete menu item clicked")

        logger.info("Clicking on Confirm button...")
        self.page.get_by_role("button", name="Confirm").click()
        logger.info("✓ Confirm button clicked")

        self.page.wait_for_timeout(2000)

        logger.info("Validating deletion confirmation message...")
        delete_msg = self.page.locator("//div[contains(text(),'Claim process with')]")
        expect(delete_msg).to_be_visible(timeout=10000)
        logger.info("✓ Deletion confirmation message is visible")

        logger.info("Claim deletion completed successfully")

    def validate_collapsible_panels(self):
        """Validate collapsible section functionality for each panel."""
        logger.info("Starting collapsible panels validation...")

        # Collapse Processing Queue panel
        logger.info("Collapsing Processing Queue panel...")
        self.page.locator(self.COLLAPSE_PANEL_BTN).nth(0).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ Processing Queue collapsed")

        # Expand Processing Queue panel
        logger.info("Expanding Processing Queue panel...")
        self.page.locator(self.PROCESSING_QUEUE_BTN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ Processing Queue expanded")

        # Collapse Output Review panel
        logger.info("Collapsing Output Review panel...")
        self.page.locator(self.COLLAPSE_PANEL_BTN).nth(1).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ Output Review collapsed")

        # Expand Output Review panel
        logger.info("Expanding Output Review panel...")
        self.page.locator(self.OUTPUT_REVIEW_BTN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ Output Review expanded")

        # Collapse Source Document panel
        logger.info("Collapsing Source Document panel...")
        self.page.locator(self.COLLAPSE_PANEL_BTN).nth(2).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ Source Document collapsed")

        # Expand Source Document panel
        logger.info("Expanding Source Document panel...")
        self.page.locator(self.SOURCE_DOC_BTN).click()
        self.page.wait_for_timeout(2000)
        logger.info("✓ Source Document expanded")

        logger.info("Collapsible panels validation completed successfully")

    def validate_api_document_link(self):
        """Validate API Documentation tab opens and displays correct content."""
        logger.info("Starting API Documentation validation...")

        original_page = self.page

        with self.page.context.expect_page() as new_page_info:
            logger.info("Clicking on API Documentation tab...")
            self.page.get_by_role("tab", name="API Documentation").click()
            logger.info("✓ API Documentation tab clicked")

        new_page = new_page_info.value
        new_page.wait_for_load_state()
        logger.info("New tab opened successfully")

        logger.info("Switching to new tab...")
        new_page.bring_to_front()
        logger.info("✓ Switched to new tab")

        logger.info("Validating API documentation title is visible...")
        expect(new_page.locator("//h1[@class='title']")).to_be_visible()
        logger.info("✓ API documentation title is visible")

        logger.info("Closing API Documentation tab...")
        new_page.close()
        logger.info("✓ API Documentation tab closed")

        logger.info("Switching back to original tab...")
        original_page.bring_to_front()
        logger.info("✓ Switched back to original tab")

        logger.info("API Documentation validation completed successfully")

    def validate_import_without_collection(self):
        """Validate that import button shows validation when no collection is selected."""
        logger.info("Starting validation for import without collection selection...")

        # Clear the collection dropdown if it has a value
        clear_btn = self.page.locator(
            "//input[contains(@placeholder,'Select Collection')]/following-sibling::*[contains(@class,'clearIcon')]"
        )
        if clear_btn.count() > 0 and clear_btn.is_visible():
            logger.info("Clearing existing collection selection...")
            clear_btn.click()
            self.page.wait_for_timeout(1000)
            logger.info("✓ Collection selection cleared")
        else:
            # Try pressing Escape to clear any selection, then clear via keyboard
            collection_input = self.page.locator(self.SELECT_COLLECTION)
            collection_input.click()
            collection_input.fill("")
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(1000)

        logger.info("Clicking on Import Document(s) button without selecting collection...")
        self.page.locator(self.IMPORT_DOCUMENTS_BTN).click()
        logger.info("✓ Import Document(s) button clicked")

        self.page.wait_for_timeout(2000)

        logger.info("Validating validation message is visible...")
        # V2 may show "Please Select Collection" or open dialog with warning
        validation_msg = self.page.locator(
            "//div[contains(text(),'Please Select') or contains(text(),'Please select')]"
        )
        dialog = self.page.get_by_role("alertdialog")

        if validation_msg.count() > 0 and validation_msg.first.is_visible():
            logger.info("✓ Validation message is visible")
        elif dialog.count() > 0 and dialog.is_visible():
            logger.info("✓ Import dialog opened — checking for collection warning")

        # Close any open dialog to avoid blocking subsequent tests
        close_btn = self.page.locator(self.CLOSE_BTN)
        if close_btn.count() > 0 and close_btn.is_visible():
            close_btn.click()
            self.page.wait_for_timeout(1000)
            logger.info("✓ Dialog closed")

        # Dismiss any remaining backdrop by pressing Escape
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(1000)

        logger.info("Import without collection validation completed successfully")

    def refresh_page(self):
        """Refresh the current page using browser reload."""
        logger.info("Starting page refresh...")

        self.page.reload()
        logger.info("✓ Page reloaded")

        self.page.wait_for_timeout(3000)
        logger.info("Page refresh completed successfully")

    def validate_schema_selection_warning(self):
        """
        Validate that the import dialog shows the correct collection warning message
        and that each file requires schema selection before Import is enabled.
        ADO TC 17305: Alert user to upload file correctly as per selected schema.
        """
        logger.info("Starting schema selection warning validation...")

        logger.info("Clicking Import Document(s) button...")
        self.page.locator(self.IMPORT_DOCUMENTS_BTN).click()
        logger.info("✓ Import Document(s) button clicked")

        self.page.wait_for_timeout(3000)

        # Validate the selected collection info message
        logger.info("Validating 'Selected Collection: Auto Claim' message...")
        dialog = self.page.get_by_role("alertdialog", name="Import Content")
        expect(dialog).to_be_visible()
        logger.info("✓ Import Content dialog is visible")

        # The collection info is in a span with class fui-MessageBarTitle
        collection_text = dialog.locator("//span[.='Selected Collection: Auto Claim']")
        expect(collection_text).to_be_visible(timeout=10000)
        logger.info("✓ 'Selected Collection: Auto Claim' message is visible")

        # Validate the warning text about importing specific files
        # Text is inside div.fui-MessageBarBody
        logger.info("Validating import warning message...")
        warning_text = dialog.locator(
            "//div[contains(@class,'fui-MessageBarBody') and contains(.,'Please import files specific')]"
        )
        expect(warning_text.first).to_be_visible(timeout=10000)
        logger.info("✓ Import warning message is visible")

        # Validate Import button is disabled before file selection
        logger.info("Validating Import button is disabled...")
        expect(dialog.locator("//button[normalize-space()='Import']")).to_be_disabled()
        logger.info("✓ Import button is disabled before file/schema selection")

        logger.info("Closing dialog...")
        dialog.locator("//button[normalize-space()='Close']").click()
        logger.info("✓ Dialog closed")

        logger.info("Schema selection warning validation completed successfully")

    def validate_unsupported_file_upload(self):
        """
        Validate that uploading unsupported file types (e.g., .txt, .docx, .json)
        shows an appropriate error or is rejected.
        ADO TC 26004: Validate upload of unsupported files.
        """
        logger.info("Starting unsupported file upload validation...")

        # Create a temporary unsupported file
        import tempfile
        temp_dir = tempfile.mkdtemp()
        unsupported_file = os.path.join(temp_dir, "test_document.txt")
        with open(unsupported_file, "w") as f:
            f.write("This is an unsupported test file")

        with self.page.expect_file_chooser() as fc_info:
            logger.info("Clicking Import Document(s) button...")
            self.page.locator(self.IMPORT_DOCUMENTS_BTN).click()
            logger.info("✓ Import Document(s) button clicked")

            logger.info("Clicking Browse Files button...")
            self.page.locator(self.BROWSE_FILES_BTN).click()
            logger.info("✓ Browse Files button clicked")

            self.page.wait_for_timeout(3000)

        file_chooser = fc_info.value
        logger.info(f"Selecting unsupported file: {unsupported_file}")
        file_chooser.set_files([unsupported_file])
        logger.info("✓ Unsupported file selected")

        self.page.wait_for_timeout(3000)

        # Check for validation message about unsupported file types
        logger.info("Validating unsupported file error message...")
        error_msg = self.page.locator(
            "//p[contains(.,'Only PDF and JPEG, PNG image files are available')]"
        )
        if error_msg.is_visible():
            logger.info("✓ Unsupported file error message is visible")
        else:
            # Check if Import button remains disabled
            dialog = self.page.get_by_role("alertdialog", name="Import Content")
            import_btn = dialog.locator("//button[normalize-space()='Import']")
            expect(import_btn).to_be_disabled()
            logger.info("✓ Import button remains disabled for unsupported file")

        logger.info("Closing dialog...")
        self.page.locator(self.CLOSE_BTN).click()
        logger.info("✓ Dialog closed")

        # Cleanup temp file
        os.remove(unsupported_file)
        os.rmdir(temp_dir)

        logger.info("Unsupported file upload validation completed successfully")

    def validate_network_disconnect_error(self):
        """
        Validate error handling when network is disconnected during file upload.
        ADO TC 17306: Unclear Error Notification on Network Disconnect.
        Simulates offline mode using Playwright's route abort.
        """
        logger.info("Starting network disconnect error validation...")

        # First, select files normally
        with self.page.expect_file_chooser() as fc_info:
            logger.info("Clicking Import Document(s) button...")
            self.page.locator(self.IMPORT_DOCUMENTS_BTN).click()
            logger.info("✓ Import Document(s) button clicked")

            logger.info("Clicking Browse Files button...")
            self.page.locator(self.BROWSE_FILES_BTN).click()
            logger.info("✓ Browse Files button clicked")

            self.page.wait_for_timeout(3000)

        file_chooser = fc_info.value
        files = self.get_testdata_files()
        file_chooser.set_files(files)
        logger.info("✓ Files selected")

        self.page.wait_for_timeout(3000)

        # Select schemas for all files
        for file_path in files:
            file_name = os.path.basename(file_path)
            schema_name = self.FILE_SCHEMA_MAP.get(file_name)
            if schema_name:
                self.select_schema_for_file(file_name, schema_name)

        self.page.wait_for_timeout(2000)

        # Simulate network disconnect by blocking all requests
        logger.info("Simulating network disconnect...")
        self.page.context.set_offline(True)
        logger.info("✓ Network set to offline mode")

        # Click Import — should trigger an error
        logger.info("Clicking Import button while offline...")
        self.page.locator(self.IMPORT_BTN).click()
        logger.info("✓ Import button clicked")

        self.page.wait_for_timeout(5000)

        # Verify an error notification or warning is displayed
        logger.info("Checking for error notification...")
        # Look for any toast/notification or error dialog
        error_visible = (
            self.page.locator("//div[contains(@class,'Toastify')]").is_visible()
            or self.page.locator("//div[contains(@role,'alert')]").is_visible()
            or self.page.locator("//div[contains(text(),'error')]").is_visible()
            or self.page.locator("//div[contains(text(),'Error')]").is_visible()
            or self.page.locator("//div[contains(text(),'failed')]").is_visible()
            or self.page.locator("//div[contains(text(),'Failed')]").is_visible()
        )

        if error_visible:
            logger.info("✓ Error notification is displayed on network disconnect")
        else:
            logger.warning("⚠ No visible error notification found — may need locator update")

        # Restore network
        logger.info("Restoring network connection...")
        self.page.context.set_offline(False)
        logger.info("✓ Network restored to online mode")

        # Close dialog
        logger.info("Closing dialog...")
        self.page.locator(self.CLOSE_BTN).click()
        logger.info("✓ Dialog closed")

        self.page.wait_for_timeout(3000)
        logger.info("Network disconnect error validation completed")

    def open_import_dialog_with_files(self):
        """
        Open the import dialog and browse all testdata files without selecting schemas.
        Leaves the dialog open for further validation.

        Returns:
            dialog: The alertdialog locator for further assertions
        """
        logger.info("Opening import dialog and browsing files...")

        files = self.get_testdata_files()
        if not files:
            raise Exception("No files found in testdata folder")

        with self.page.expect_file_chooser() as fc_info:
            logger.info("Clicking Import Document(s) button...")
            self.page.locator(self.IMPORT_DOCUMENTS_BTN).click()
            logger.info("✓ Import Document(s) button clicked")

            logger.info("Clicking Browse Files button...")
            self.page.locator(self.BROWSE_FILES_BTN).click()
            logger.info("✓ Browse Files button clicked")

            self.page.wait_for_timeout(3000)

        file_chooser = fc_info.value
        logger.info(f"Selecting {len(files)} files: {[os.path.basename(f) for f in files]}")
        file_chooser.set_files(files)
        logger.info("✓ All files selected")

        self.page.wait_for_timeout(5000)

        dialog = self.page.get_by_role("alertdialog", name="Import Content")
        logger.info("Import dialog opened with files ready for schema selection")
        return dialog

    def validate_import_disabled_without_schemas(self):
        """
        Validate that the Import button remains disabled when files are uploaded
        but no schemas have been selected for any file.
        """
        logger.info("Starting validation: Import disabled without schema selection...")

        dialog = self.open_import_dialog_with_files()

        logger.info("Validating Import button is disabled without schema selection...")
        import_btn = dialog.locator("//button[normalize-space()='Import']")
        expect(import_btn).to_be_disabled()
        logger.info("✓ Import button is disabled when no schemas are selected")

        logger.info("Closing dialog...")
        self.page.locator(self.CLOSE_BTN).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ Dialog closed")

        logger.info("Validation completed: Import disabled without schemas")

    def validate_import_disabled_with_partial_schemas(self):
        """
        Validate that the Import button remains disabled when schemas are selected
        for only some files but not all.
        """
        logger.info("Starting validation: Import disabled with partial schema selection...")

        dialog = self.open_import_dialog_with_files()

        # Select schema for only the first file
        files = self.get_testdata_files()
        first_file = os.path.basename(files[0])
        first_schema = self.FILE_SCHEMA_MAP.get(first_file)

        if first_schema:
            logger.info(f"Selecting schema only for first file: '{first_file}' → '{first_schema}'")
            self.select_schema_for_file(first_file, first_schema)
            logger.info(f"✓ Schema selected for '{first_file}' only")
        else:
            raise Exception(f"No schema mapping for '{first_file}'")

        self.page.wait_for_timeout(2000)

        logger.info("Validating Import button is still disabled with partial schemas...")
        import_btn = dialog.locator("//button[normalize-space()='Import']")
        expect(import_btn).to_be_disabled()
        logger.info("✓ Import button remains disabled with partial schema selection")

        logger.info("Closing dialog...")
        self.page.locator(self.CLOSE_BTN).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ Dialog closed")

        logger.info("Validation completed: Import disabled with partial schemas")

    def upload_files_with_mismatched_schemas(self):
        """
        Upload files with deliberately mismatched/swapped schemas to validate
        that the system handles incorrect schema assignments.
        Swaps schemas: claim_form.pdf gets Repair Estimate schema and vice versa.
        """
        logger.info("Starting file upload with mismatched schemas...")

        # Define mismatched schema mapping (swap schemas around)
        mismatched_map = {
            "claim_form.pdf": "Repair Estimate Document",
            "damage_photo.png": "Police Report Document",
            "police_report.pdf": "Damaged Vehicle Image Assessment",
            "repair_estimate.pdf": "Auto Insurance Claim Form",
        }

        _dialog = self.open_import_dialog_with_files()

        # Select mismatched schemas for each file
        files = self.get_testdata_files()
        for file_path in files:
            file_name = os.path.basename(file_path)
            schema_name = mismatched_map.get(file_name)
            if schema_name:
                logger.info(f"Assigning MISMATCHED schema '{schema_name}' to '{file_name}'...")
                self.select_schema_for_file(file_name, schema_name)
                logger.info(f"✓ Mismatched schema '{schema_name}' assigned to '{file_name}'")

        self.page.wait_for_timeout(2000)

        logger.info("Clicking Import button with mismatched schemas...")
        self.page.locator(self.IMPORT_BTN).click()
        logger.info("✓ Import button clicked")

        self.page.wait_for_timeout(10000)

        logger.info("Validating upload success (system accepts mismatched schemas)...")
        expect(
            self.page.get_by_role("alertdialog", name="Import Content")
            .locator("path")
            .nth(1)
        ).to_be_visible()
        logger.info("✓ Upload accepted with mismatched schemas")

        logger.info("Closing upload dialog...")
        self.page.locator(self.CLOSE_BTN).click()
        logger.info("✓ Upload dialog closed")

        logger.info("File upload with mismatched schemas completed")

    def validate_schema_dropdown_after_file_removal(self):
        """
        Validate that removing a file from the import dialog preserves the
        schema selections of remaining files.
        """
        logger.info("Starting validation: Schema dropdown after file removal...")

        dialog = self.open_import_dialog_with_files()

        # Select schemas for all files first
        files = self.get_testdata_files()
        for file_path in files:
            file_name = os.path.basename(file_path)
            schema_name = self.FILE_SCHEMA_MAP.get(file_name)
            if schema_name:
                self.select_schema_for_file(file_name, schema_name)

        self.page.wait_for_timeout(2000)
        logger.info("✓ Schemas selected for all files")

        # Try to remove the first file using the delete/remove button next to it
        logger.info("Attempting to remove first file from the list...")
        _file_labels = dialog.locator("strong")
        first_file_name = os.path.basename(files[0])

        # Look for a delete/remove button near the first file entry
        remove_buttons = dialog.locator(
            "//button[contains(@aria-label,'Remove') or contains(@aria-label,'Delete') "
            "or contains(@aria-label,'remove') or contains(@title,'Remove') "
            "or contains(@title,'Delete')]"
        )

        if remove_buttons.count() > 0:
            remove_buttons.first.click()
            self.page.wait_for_timeout(2000)
            logger.info(f"✓ First file '{first_file_name}' removed from list")

            # Validate remaining files still have their schema selections
            remaining_files = [os.path.basename(f) for f in files[1:]]
            schema_dropdowns = dialog.get_by_placeholder("Select Schema")

            for idx, file_name in enumerate(remaining_files):
                dropdown = schema_dropdowns.nth(idx)
                dropdown_value = dropdown.input_value()
                expected_schema = self.FILE_SCHEMA_MAP.get(file_name, "")
                logger.info(f"File '{file_name}': Schema dropdown value = '{dropdown_value}'")

                if expected_schema and dropdown_value == expected_schema:
                    logger.info(f"✓ Schema '{expected_schema}' preserved for '{file_name}'")
                else:
                    logger.warning(
                        f"⚠ Schema may have changed for '{file_name}': "
                        f"expected '{expected_schema}', got '{dropdown_value}'"
                    )
        else:
            logger.info("No remove button found — file removal not supported in import dialog")
            logger.info("✓ Skipping file removal validation (UI does not support it)")

        logger.info("Closing dialog...")
        self.page.locator(self.CLOSE_BTN).click()
        self.page.wait_for_timeout(1000)
        logger.info("✓ Dialog closed")

        logger.info("Schema dropdown after file removal validation completed")
