"""
Home page module for Content Processing Solution Accelerator.
"""

import os.path
import logging

from base.base import BasePage
from playwright.sync_api import expect

logger = logging.getLogger(__name__)


class HomePage(BasePage):
    """
    Home page object containing all locators and methods for interacting
    with the Content Processing home page.
    """
    # HOMEPAGE
    PROCESSING_QUEUE = "//span[normalize-space()='Processing Queue']"
    OUTPUT_REVIEW = "//span[normalize-space()='Output Review']"
    SOURCE_DOC = "//span[normalize-space()='Source Document']"
    PROCESSING_QUEUE_BTN = "//button[normalize-space()='Processing Queue']"
    OUTPUT_REVIEW_BTN = "//button[normalize-space()='Output Review']"
    SOURCE_DOC_BTN = "//button[normalize-space()='Source Document']"
    INVOICE_SELECTED_SCHEMA = "//span[.='Selected Schema  : Invoice ']"
    PROP_SELECTED_SCHEMA = "//span[.='Selected Schema  : Property Loss Damage Claim Form ']"
    INVOICE_SELECT_VALIDATION = "//div[contains(text(),'Please Select Schema')]"
    SEARCH_BOX = "//input[@placeholder='Search']"
    PROCESSING_QUEUE_CP = "//div[@class='panelLeft']//button[@title='Collapse Panel']"
    COLLAPSE_PANEL_BTN = "//button[@title='Collapse Panel']"
    API_DOCUMENTATION = "//span[.='API Documentation']"
    INVALID_FILE_VALIDATION = "//p[contains(.,'Only PDF and JPEG, PNG image files are available.')]"

    TITLE_TEXT = "//span[normalize-space()='Processing Queue']"
    SELECT_SCHEMA = "//input[@placeholder='Select Schema']"
    IMPORT_CONTENT = "//button[normalize-space()='Import Content']"
    REFRESH = "//button[normalize-space()='Refresh']"
    BROWSE_FILES = "//button[normalize-space()='Browse Files']"
    UPLOAD_BTN = "//button[normalize-space()='Upload']"
    SUCCESS_MSG = "/div[@class='file-item']//*[name()='svg']"
    UPLOAD_WARNING_MESSAGE = "//div[contains(text(),'Please upload files specific to')]"
    SCHEMA_NAME_IN_WARNING = "//div[contains(text(),'Invoice')]"

    CLOSE_BTN = "//button[normalize-space()='Close']"
    STATUS = "//div[@role='cell']"
    PROCESS_STEPS = "//button[@value='process-history']"
    EXTRACT = "//span[normalize-space()='extract']"
    MAP = "//span[normalize-space()='map']"
    EVALUATE = "//span[normalize-space()='evaluate']"
    EXTRACTED_RESULT = "//button[@value='extracted-results']"
    COMMENTS = "//textarea"
    SAVE_BTN = "//button[normalize-space()='Save']"
    EDIT_CONFIRM = "//div[@class='jer-confirm-buttons']//div[1]"
    SHIPPING_ADD_STREET = "//textarea[@id='shipping_address.street_textarea']"
    DELETE_FILE = "//button[@aria-haspopup='menu']"

    # INVOICE_JSON_ENTITIES
    CUSTOMER_NAME = "//div[@id='customer_name_display']"
    CUSTOMER_STREET = "//div[@id='customer_address.street_display']"
    CUSTOMER_CITY = "//div[@id='customer_address.city_display']"
    CUSTOMER_ZIP_CODE = "//div[@id='customer_address.postal_code_display']"
    CUSTOMER_COUNTRY = "//div[@id='customer_address.country_display']"
    SHIPPING_STREET = "//div[@id='shipping_address.street_display']"
    SHIPPING_CITY = "//div[@id='shipping_address.city_display']"
    SHIPPING_POSTAL_CODE = "//div[@id='shipping_address.postal_code_display']"
    SHIPPING_COUNTRY = "//div[@id='shipping_address.country_display']"
    PURCHASE_ORDER = "//div[@id='purchase_order_display']"
    INVOICE_ID = "//div[@id='invoice_id_display']"
    INVOICE_DATE = "//div[@id='invoice_date_display']"
    payable_by = "//div[@id='payable_by_display']"
    vendor_name = "//div[@id='vendor_name_display']"
    v_street = "//div[@id='vendor_address.street_display']"
    v_city = "//div[@id='vendor_address.city_display']"
    v_state = "//div[@id='vendor_address.state_display']"
    v_zip_code = "//div[@id='vendor_address.postal_code_display']"
    vendor_tax_id = "//div[@id='vendor_tax_id_display']"
    SUBTOTAL = "//span[normalize-space()='16859.1']"
    TOTAL_TAX = "//span[normalize-space()='11286']"
    INVOICE_TOTAL = "//span[normalize-space()='22516.08']"
    PAYMENT_TERMS = "//div[@id='payment_terms_display']"
    product_code1 = "//div[@id='items.0.product_code_display']"
    p1_description = "//div[@id='items.0.description_display']"
    p1_quantity = "//span[normalize-space()='163']"
    p1_tax = "//span[normalize-space()='2934']"
    p1_unit_price = "//span[normalize-space()='2.5']"
    p1_total = "//span[normalize-space()='407.5']"

    # PROPERTY_JSON_DATA

    first_name = "//div[@id='policy_claim_info.first_name_display']"
    last_name = "//div[@id='policy_claim_info.last_name_display']"
    tel_no = "//div[@id='policy_claim_info.telephone_number_display']"
    policy_no = "//div[@id='policy_claim_info.policy_number_display']"
    coverage_type = "//div[@id='policy_claim_info.coverage_type_display']"
    claim_number = "//div[@id='policy_claim_info.claim_number_display']"
    policy_effective_date = (
        "//div[@id='policy_claim_info.policy_effective_date_display']"
    )
    policy_expiration_date = (
        "//div[@id='policy_claim_info.policy_expiration_date_display']"
    )
    damage_deductible = "//span[normalize-space()='1000']"
    damage_deductible_currency = (
        "//div[@id='policy_claim_info.damage_deductible_currency_display']"
    )
    date_of_damage_loss = "//div[@id='policy_claim_info.date_of_damage_loss_display']"
    time_of_loss = "//div[@id='policy_claim_info.time_of_loss_display']"
    date_prepared = "//div[@id='policy_claim_info.date_prepared_display']"
    item = "//div[@id='property_claim_details.0.item_display']"
    description = "//div[@id='property_claim_details.0.description_display']"
    date_acquired = "//div[@id='property_claim_details.0.date_acquired_display']"
    cost_new = "//body[1]/div[1]/div[1]/div[1]/div[1]/main[1]/div[1]/div[2]/div[2]/div[2]/div[3]/div[1]/div[1]/div[2]/div[1]/div[1]/div[3]/div[2]/div[1]/div[3]/div[1]/div[1]/div[3]/div[4]/div[1]/div[1]/div[1]/div[1]/span[1]"
    cost_new_currency = (
        "//div[@id='property_claim_details.0.cost_new_currency_display']"
    )
    replacement_repair = "//span[normalize-space()='350']"
    replacement_repair_currency = (
        "//div[@id='property_claim_details.0.replacement_repair_currency_display']"
    )

    def __init__(self, page):
        """
        Initialize the HomePage.

        Args:
            page: Playwright page object
        """
        super().__init__(page)
        self.page = page

    def validate_home_page(self):
        """Validate that the home page elements are visible."""
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

    def select_schema(self, SchemaName):
        """Select a schema from the dropdown."""
        logger.info(f"Starting schema selection for: {SchemaName}")

        self.page.wait_for_timeout(5000)

        logger.info("Clicking on Select Schema dropdown...")
        self.page.locator(self.SELECT_SCHEMA).click()
        logger.info("✓ Select Schema dropdown clicked")

        if SchemaName == "Invoice":
            logger.info("Selecting 'Invoice' option...")
            self.page.get_by_role("option", name="Invoice").click()
            logger.info("✓ 'Invoice' option selected")
        else:
            logger.info("Selecting 'Property Loss Damage Claim' option...")
            self.page.get_by_role("option", name="Property Loss Damage Claim").click()
            logger.info("✓ 'Property Loss Damage Claim' option selected")

        logger.info(f"Schema selection completed for: {SchemaName}")

    def upload_files(self, schemaType):
        """Upload files based on schema type."""
        logger.info(f"Starting file upload for schema type: {schemaType}")

        with self.page.expect_file_chooser() as fc_info:
            logger.info("Clicking Import Content button...")
            self.page.locator(self.IMPORT_CONTENT).click()
            logger.info("✓ Import Content button clicked")

            logger.info("Clicking Browse Files button...")
            self.page.locator(self.BROWSE_FILES).click()
            logger.info("✓ Browse Files button clicked")

            self.page.wait_for_timeout(5000)
            # self.page.wait_for_load_state('networkidle')

        file_chooser = fc_info.value
        current_working_dir = os.getcwd()
        file_path1 = os.path.join(
            current_working_dir, "testdata", "FabrikamInvoice_1.pdf"
        )
        file_path2 = os.path.join(current_working_dir, "testdata", "ClaimForm_1.pdf")

        if schemaType == "Invoice":
            logger.info(f"Selecting file: {file_path1}")
            file_chooser.set_files([file_path1])
            logger.info("✓ Invoice file selected")
        else:
            logger.info(f"Selecting file: {file_path2}")
            file_chooser.set_files([file_path2])
            logger.info("✓ Claim form file selected")

        self.page.wait_for_timeout(5000)
        self.page.wait_for_load_state("networkidle")

        logger.info("Clicking Upload button...")
        self.page.locator(self.UPLOAD_BTN).click()
        logger.info("✓ Upload button clicked")

        self.page.wait_for_timeout(10000)

        logger.info("Validating success message is visible...")
        expect(
            self.page.get_by_role("alertdialog", name="Import Content")
            .locator("path")
            .nth(1)
        ).to_be_visible()
        logger.info("✓ Success message is visible")

        logger.info("Closing upload dialog...")
        self.page.locator(self.CLOSE_BTN).click()
        logger.info("✓ Upload dialog closed")

        logger.info(f"File upload completed successfully for schema type: {schemaType}")

    def refresh(self):
        """Refresh and wait for processing to complete."""
        logger.info("Starting refresh process to monitor file processing status...")

        status_ele = self.page.locator(self.STATUS).nth(2)
        max_retries = 20

        for i in range(max_retries):
            status_text = status_ele.inner_text().strip()
            logger.info(f"Attempt {i + 1}/{max_retries}: Current status = '{status_text}'")

            if status_text == "Completed":
                logger.info("✓ Processing completed successfully")
                break
            elif status_text == "Error":
                logger.error(f"Process failed with status: 'Error' after {i + 1} retries")
                raise Exception(
                    f"Process failed with status: 'Error' after {i + 1} retries."
                )

            logger.info("Clicking Refresh button...")
            self.page.locator(self.REFRESH).click()
            logger.info("✓ Refresh button clicked, waiting 5 seconds...")
            self.page.wait_for_timeout(5000)
        else:
            # Executed only if the loop did not break (i.e., status is neither Completed nor Error)
            logger.error(f"Process did not complete. Final status was '{status_text}' after {max_retries} retries")
            raise Exception(
                f"Process did not complete. Final status was '{status_text}' after {max_retries} retries."
            )

        logger.info("Refresh process completed successfully")

    def validate_invoice_extracted_result(self):
        """Validate all extracted invoice data fields."""
        logger.info("Starting invoice extracted result validation...")

        logger.info("Validating Customer Name...")
        expect(self.page.locator(self.CUSTOMER_NAME)).to_contain_text(
            "Paris Fashion Group SARL"
        )
        logger.info("✓ Customer Name validated: Paris Fashion Group SARL")

        logger.info("Validating Customer Street...")
        expect(self.page.locator(self.CUSTOMER_STREET)).to_contain_text(
            "10 Rue de Rivoli"
        )
        logger.info("✓ Customer Street validated: 10 Rue de Rivoli")

        logger.info("Validating Customer City...")
        expect(self.page.locator(self.CUSTOMER_CITY)).to_contain_text("Paris")
        logger.info("✓ Customer City validated: Paris")

        logger.info("Validating Customer Zip Code...")
        expect(self.page.locator(self.CUSTOMER_ZIP_CODE)).to_contain_text("75001")
        logger.info("✓ Customer Zip Code validated: 75001")

        logger.info("Validating Customer Country...")
        expect(self.page.locator(self.CUSTOMER_COUNTRY)).to_contain_text("France")
        logger.info("✓ Customer Country validated: France")

        logger.info("Validating Shipping Street...")
        expect(self.page.locator(self.SHIPPING_STREET)).to_contain_text(
            "25 Avenue Montaigne"
        )
        logger.info("✓ Shipping Street validated: 25 Avenue Montaigne")

        logger.info("Validating Shipping City...")
        expect(self.page.locator(self.SHIPPING_CITY)).to_contain_text("Paris")
        logger.info("✓ Shipping City validated: Paris")

        logger.info("Validating Shipping Postal Code...")
        expect(self.page.locator(self.SHIPPING_POSTAL_CODE)).to_contain_text("75008")
        logger.info("✓ Shipping Postal Code validated: 75008")

        logger.info("Validating Shipping Country...")
        expect(self.page.locator(self.SHIPPING_COUNTRY)).to_contain_text("France")
        logger.info("✓ Shipping Country validated: France")

        logger.info("Validating Purchase Order...")
        expect(self.page.locator(self.PURCHASE_ORDER)).to_contain_text("PO-34567")
        logger.info("✓ Purchase Order validated: PO-34567")

        logger.info("Validating Invoice ID...")
        expect(self.page.locator(self.INVOICE_ID)).to_contain_text("INV-20231005")
        logger.info("✓ Invoice ID validated: INV-20231005")

        logger.info("Validating Invoice Date...")
        expect(self.page.locator(self.INVOICE_DATE)).to_contain_text("2023-10-05")
        logger.info("✓ Invoice Date validated: 2023-10-05")

        logger.info("Validating Payable By Date...")
        expect(self.page.locator(self.payable_by)).to_contain_text("2023-11-04")
        logger.info("✓ Payable By Date validated: 2023-11-04")

        logger.info("Validating Vendor Name...")
        expect(self.page.locator(self.vendor_name)).to_contain_text(
            "Fabrikam Unlimited Company"
        )
        logger.info("✓ Vendor Name validated: Fabrikam Unlimited Company")

        logger.info("Validating Vendor Street...")
        expect(self.page.locator(self.v_street)).to_contain_text("Wilton Place")
        logger.info("✓ Vendor Street validated: Wilton Place")

        logger.info("Validating Vendor City...")
        expect(self.page.locator(self.v_city)).to_contain_text("Brooklyn")
        logger.info("✓ Vendor City validated: Brooklyn")

        logger.info("Validating Vendor State...")
        expect(self.page.locator(self.v_state)).to_contain_text("NY")
        logger.info("✓ Vendor State validated: NY")

        logger.info("Validating Vendor Zip Code...")
        expect(self.page.locator(self.v_zip_code)).to_contain_text("22345")
        logger.info("✓ Vendor Zip Code validated: 22345")

        logger.info("Validating Vendor Tax ID...")
        expect(self.page.locator(self.vendor_tax_id)).to_contain_text("FR123456789")
        logger.info("✓ Vendor Tax ID validated: FR123456789")

        logger.info("Validating Subtotal...")
        expect(self.page.locator(self.SUBTOTAL)).to_contain_text("16859.1")
        logger.info("✓ Subtotal validated: 16859.1")

        logger.info("Validating Total Tax...")
        expect(self.page.locator(self.TOTAL_TAX)).to_contain_text("11286")
        logger.info("✓ Total Tax validated: 11286")

        logger.info("Validating Invoice Total...")
        expect(self.page.locator(self.INVOICE_TOTAL)).to_contain_text("22516.08")
        logger.info("✓ Invoice Total validated: 22516.08")

        logger.info("Validating Payment Terms...")
        expect(self.page.locator(self.PAYMENT_TERMS)).to_contain_text("Net 30")
        logger.info("✓ Payment Terms validated: Net 30")

        logger.info("Validating Product Code...")
        expect(self.page.locator(self.product_code1)).to_contain_text("EM032")
        logger.info("✓ Product Code validated: EM032")

        logger.info("Validating Product Description...")
        expect(self.page.locator(self.p1_description)).to_contain_text(
            "Item: Terminal Lug"
        )
        logger.info("✓ Product Description validated: Item: Terminal Lug")

        logger.info("Validating Product Quantity...")
        expect(self.page.locator(self.p1_quantity)).to_contain_text("163")
        logger.info("✓ Product Quantity validated: 163")

        logger.info("Validating Product Tax...")
        expect(self.page.locator(self.p1_tax)).to_contain_text("2934")
        logger.info("✓ Product Tax validated: 2934")

        logger.info("Validating Product Unit Price...")
        expect(self.page.locator(self.p1_unit_price)).to_contain_text("2.5")
        logger.info("✓ Product Unit Price validated: 2.5")

        logger.info("Validating Product Total...")
        expect(self.page.locator(self.p1_total)).to_contain_text("407.5")
        logger.info("✓ Product Total validated: 407.5")

        logger.info("Invoice extracted result validation completed successfully")

    def modify_and_submit_extracted_data(self):
        """Modify shipping address and submit the changes."""
        logger.info("Starting modification of extracted data...")

        logger.info("Double-clicking on Shipping Street field...")
        self.page.get_by_text('"25 Avenue Montaigne"').dblclick()
        logger.info("✓ Shipping Street field double-clicked")

        logger.info("Updating Shipping Street to '25 Avenue Montaigne updated'...")
        self.page.locator(self.SHIPPING_ADD_STREET).fill("25 Avenue Montaigne updated")
        logger.info("✓ Shipping Street updated")

        logger.info("Clicking Edit Confirm button...")
        self.page.locator(self.EDIT_CONFIRM).click()
        logger.info("✓ Edit Confirm button clicked")

        logger.info("Adding comment: 'Updated Shipping street address'...")
        self.page.locator(self.COMMENTS).fill("Updated Shipping street address")
        logger.info("✓ Comment added")

        logger.info("Clicking Save button...")
        self.page.locator(self.SAVE_BTN).click()
        logger.info("✓ Save button clicked")

        self.page.wait_for_timeout(6000)
        logger.info("Data modification and submission completed successfully")

    def validate_process_steps(self):
        """Validate all process steps (extract, map, evaluate)."""
        logger.info("Starting process steps validation...")

        logger.info("Clicking on Process Steps tab...")
        self.page.locator(self.PROCESS_STEPS).click()
        logger.info("✓ Process Steps tab clicked")

        # Extract Step
        logger.info("Validating Extract step...")
        self.page.locator(self.EXTRACT).click()
        self.page.wait_for_timeout(3000)

        logger.info("Checking 'extract' text is visible...")
        expect(self.page.get_by_text('"extract"')).to_be_visible()
        logger.info("✓ 'extract' text is visible")

        logger.info("Checking 'Succeeded' status is visible...")
        expect(self.page.get_by_text('"Succeeded"')).to_be_visible()
        logger.info("✓ 'Succeeded' status is visible for Extract step")

        self.page.locator(self.EXTRACT).click()
        self.page.wait_for_timeout(3000)

        # Map Step
        logger.info("Validating Map step...")
        self.page.locator(self.MAP).click()
        self.page.wait_for_timeout(3000)

        logger.info("Checking 'map' text is visible...")
        expect(self.page.get_by_text('"map"')).to_be_visible()
        logger.info("✓ 'map' text is visible for Map step")

        self.page.locator(self.MAP).click()
        self.page.wait_for_timeout(3000)

        # Evaluate Step
        logger.info("Validating Evaluate step...")
        self.page.locator(self.EVALUATE).click()
        self.page.wait_for_timeout(3000)

        logger.info("Checking 'evaluate' text is visible...")
        expect(self.page.get_by_text('"evaluate"')).to_be_visible()
        logger.info("✓ 'evaluate' text is visible for Evaluate step")

        self.page.locator(self.EVALUATE).click()
        self.page.wait_for_timeout(3000)

        logger.info("Clicking on Extracted Result tab...")
        self.page.locator(self.EXTRACTED_RESULT).click()
        self.page.wait_for_timeout(3000)
        logger.info("✓ Extracted Result tab clicked")

        logger.info("Process steps validation completed successfully")

    def validate_property_extracted_result(self):
        """Validate all extracted property claim data fields."""
        logger.info("Starting property extracted result validation...")

        logger.info("Validating First Name...")
        expect(self.page.locator(self.first_name)).to_contain_text("Sophia")
        logger.info("✓ First Name validated: Sophia")

        logger.info("Validating Last Name...")
        expect(self.page.locator(self.last_name)).to_contain_text("Kim")
        logger.info("✓ Last Name validated: Kim")

        logger.info("Validating Telephone Number...")
        expect(self.page.locator(self.tel_no)).to_contain_text("646-555-0789")
        logger.info("✓ Telephone Number validated: 646-555-0789")

        logger.info("Validating Policy Number...")
        expect(self.page.locator(self.policy_no)).to_contain_text("PH5678901")
        logger.info("✓ Policy Number validated: PH5678901")

        logger.info("Validating Coverage Type...")
        expect(self.page.locator(self.coverage_type)).to_contain_text("Homeowners")
        logger.info("✓ Coverage Type validated: Homeowners")

        logger.info("Validating Claim Number...")
        expect(self.page.locator(self.claim_number)).to_contain_text("CLM5432109")
        logger.info("✓ Claim Number validated: CLM5432109")

        logger.info("Validating Policy Effective Date...")
        expect(self.page.locator(self.policy_effective_date)).to_contain_text(
            "2022-07-01"
        )
        logger.info("✓ Policy Effective Date validated: 2022-07-01")

        logger.info("Validating Policy Expiration Date...")
        expect(self.page.locator(self.policy_expiration_date)).to_contain_text(
            "2023-07-01"
        )
        logger.info("✓ Policy Expiration Date validated: 2023-07-01")

        logger.info("Validating Damage Deductible...")
        expect(self.page.locator(self.damage_deductible)).to_contain_text("1000")
        logger.info("✓ Damage Deductible validated: 1000")

        logger.info("Validating Damage Deductible Currency...")
        expect(self.page.locator(self.damage_deductible_currency)).to_contain_text(
            "USD"
        )
        logger.info("✓ Damage Deductible Currency validated: USD")

        logger.info("Validating Date of Damage/Loss...")
        expect(self.page.locator(self.date_of_damage_loss)).to_contain_text(
            "2023-05-10"
        )
        logger.info("✓ Date of Damage/Loss validated: 2023-05-10")

        logger.info("Validating Time of Loss...")
        expect(self.page.locator(self.time_of_loss)).to_contain_text("13:20")
        logger.info("✓ Time of Loss validated: 13:20")

        logger.info("Validating Date Prepared...")
        expect(self.page.locator(self.date_prepared)).to_contain_text("2023-05-11")
        logger.info("✓ Date Prepared validated: 2023-05-11")

        logger.info("Validating Item...")
        expect(self.page.locator(self.item)).to_contain_text("Apple")
        logger.info("✓ Item validated: Apple")

        logger.info("Validating Description...")
        expect(self.page.locator(self.description)).to_contain_text(
            '"High-performance tablet with a large, vibrant display'
        )
        logger.info("✓ Description validated")

        logger.info("Validating Date Acquired...")
        expect(self.page.locator(self.date_acquired)).to_contain_text("2022-01-20")
        logger.info("✓ Date Acquired validated: 2022-01-20")

        logger.info("Validating Cost New...")
        expect(self.page.locator(self.cost_new)).to_contain_text("1100")
        logger.info("✓ Cost New validated: 1100")

        logger.info("Validating Cost New Currency...")
        expect(self.page.locator(self.cost_new_currency)).to_contain_text("USD")
        logger.info("✓ Cost New Currency validated: USD")

        logger.info("Validating Replacement/Repair...")
        expect(self.page.locator(self.replacement_repair)).to_contain_text("350")
        logger.info("✓ Replacement/Repair validated: 350")

        logger.info("Validating Replacement/Repair Currency...")
        expect(self.page.locator(self.replacement_repair_currency)).to_contain_text(
            "USD"
        )
        logger.info("✓ Replacement/Repair Currency validated: USD")

        logger.info("Property extracted result validation completed successfully")

    def delete_files(self):
        """Delete uploaded files from the processing queue."""
        logger.info("Starting file deletion process...")

        logger.info("Clicking on Delete File menu button...")
        self.page.locator(self.DELETE_FILE).nth(0).click()
        logger.info("✓ Delete File menu button clicked")

        logger.info("Clicking on Delete menu item...")
        self.page.get_by_role("menuitem", name="Delete").click()
        logger.info("✓ Delete menu item clicked")

        logger.info("Clicking on Confirm button...")
        self.page.get_by_role("button", name="Confirm").click()
        logger.info("✓ Confirm button clicked")

        self.page.wait_for_timeout(6000)
        logger.info("File deletion completed successfully")

    def validate_import_without_schema(self):
        """Validate import content validation when no schema is selected."""
        logger.info("Starting validation for import without schema selection...")

        logger.info("Clicking on Import Content button without selecting schema...")
        self.page.locator(self.IMPORT_CONTENT).click()
        logger.info("✓ Import Content button clicked")

        logger.info("Validating 'Please Select Schema' message is visible...")
        expect(self.page.locator(self.INVOICE_SELECT_VALIDATION)).to_be_visible()
        logger.info("✓ 'Please Select Schema' validation message is visible")

        logger.info("Import without schema validation completed successfully")

    def validate_invoice_schema_selected(self):
        """Validate that Invoice schema is selected and visible."""
        logger.info("Starting validation for Invoice schema selection...")

        logger.info("Clicking on Import Content button...")
        self.page.locator(self.IMPORT_CONTENT).click()
        logger.info("✓ Import Content button clicked")

        logger.info("Validating 'Selected Schema : Invoice' message is visible...")
        expect(self.page.locator(self.INVOICE_SELECTED_SCHEMA)).to_be_visible()
        logger.info("✓ 'Selected Schema : Invoice' is visible")

        logger.info("Invoice schema selection validation completed successfully")

    def validate_property_schema_selected(self):
        """Validate that Property Loss Damage Claim Form schema is selected and visible."""
        logger.info("Starting validation for Property Loss Damage Claim Form schema selection...")

        logger.info("Clicking on Import Content button...")
        self.page.locator(self.IMPORT_CONTENT).click()
        logger.info("✓ Import Content button clicked")

        logger.info("Validating 'Selected Schema : Property Loss Damage Claim Form' message is visible...")
        expect(self.page.locator(self.PROP_SELECTED_SCHEMA)).to_be_visible()
        logger.info("✓ 'Selected Schema : Property Loss Damage Claim Form' is visible")

        logger.info("Property Loss Damage Claim Form schema selection validation completed successfully")

    def close_upload_popup(self):
        """Close the upload popup dialog."""
        logger.info("Starting to close upload popup...")

        logger.info("Clicking on Close button...")
        self.page.locator(self.CLOSE_BTN).click()
        logger.info("✓ Close button clicked")

        logger.info("Upload popup closed successfully")

    def refresh_page(self):
        """Refresh the current page using browser reload."""
        logger.info("Starting page refresh...")

        logger.info("Reloading the page...")
        self.page.reload()
        logger.info("✓ Page reloaded")

        self.page.wait_for_timeout(3000)
        logger.info("Page refresh completed successfully")

    def validate_search_functionality(self):
        """Validate search functionality in extracted results."""
        logger.info("Starting search functionality validation...")

        logger.info("Entering search text 'Fabrikam' in Search Box...")
        self.page.locator(self.SEARCH_BOX).fill("Fabrikam")
        logger.info("✓ Search text 'Fabrikam' entered")

        self.page.wait_for_timeout(2000)

        logger.info("Validating vendor name contains 'Fabrikam'...")
        expect(self.page.locator("//div[@id='vendor_name_display']")).to_contain_text("Fabrikam")
        logger.info("✓ Vendor name contains 'Fabrikam'")

        logger.info("Search functionality validation completed successfully")

    def validate_api_document_link(self):
        """Validate API Documentation link opens and displays correct content."""
        logger.info("Starting API Documentation link validation...")

        # Store reference to original page
        original_page = self.page
        logger.info("Stored reference to original page/tab")

        with self.page.context.expect_page() as new_page_info:
            logger.info("Clicking on API Documentation link...")
            self.page.locator(self.API_DOCUMENTATION).nth(0).click()
            logger.info("✓ API Documentation link clicked")

        new_page = new_page_info.value
        new_page.wait_for_load_state()
        logger.info("New tab/page opened successfully")

        # Switch to new tab
        logger.info("Switching to new tab...")
        new_page.bring_to_front()
        logger.info("✓ Switched to new tab")

        logger.info("Validating title heading is visible...")
        expect(new_page.locator("//h1[@class='title']")).to_be_visible()
        logger.info("✓ Title heading is visible")

        logger.info("Validating 'contentprocessor' text is visible...")
        expect(new_page.locator("//span[normalize-space()='contentprocessor']")).to_be_visible()
        logger.info("✓ 'contentprocessor' text is visible")

        logger.info("Validating 'schemavault' text is visible...")
        expect(new_page.locator("//span[normalize-space()='schemavault']")).to_be_visible()
        logger.info("✓ 'schemavault' text is visible")

        logger.info("Validating 'default' text is visible...")
        expect(new_page.locator("//span[normalize-space()='default']")).to_be_visible()
        logger.info("✓ 'default' text is visible")

        logger.info("Validating 'Schemas' text is visible...")
        expect(new_page.locator("//span[normalize-space()='Schemas']")).to_be_visible()
        logger.info("✓ 'Schemas' text is visible")

        logger.info("Closing API Documentation tab...")
        new_page.close()
        logger.info("✓ API Documentation tab closed")

        # Switch back to original tab
        logger.info("Switching back to original tab...")
        original_page.bring_to_front()
        logger.info("✓ Switched back to original tab")

        logger.info("API Documentation link validation completed successfully")

    def validate_collapsible_panels(self):
        """Validate collapsible section functionality for each panel (Processing Queue, Output Review, Source Document)."""
        logger.info("Starting collapsible panels validation...")

        # Collapse Processing Queue panel
        logger.info("Collapsing Processing Queue panel...")
        self.page.locator(self.COLLAPSE_PANEL_BTN).nth(0).click()
        logger.info("✓ Collapse button for Processing Queue clicked")

        self.page.wait_for_timeout(2000)
        logger.info("Waited 2 seconds after collapsing Processing Queue")

        # Expand Processing Queue panel
        logger.info("Expanding Processing Queue panel...")
        self.page.locator(self.PROCESSING_QUEUE_BTN).click()
        logger.info("✓ Processing Queue clicked to expand")

        self.page.wait_for_timeout(2000)

        # Collapse Output Review panel
        logger.info("Collapsing Output Review panel...")
        self.page.locator(self.COLLAPSE_PANEL_BTN).nth(1).click()
        logger.info("✓ Collapse button for Output Review clicked")

        self.page.wait_for_timeout(2000)
        logger.info("Waited 2 seconds after collapsing Output Review")

        # Expand Output Review panel
        logger.info("Expanding Output Review panel...")
        self.page.locator(self.OUTPUT_REVIEW_BTN).click()
        logger.info("✓ Output Review clicked to expand")

        self.page.wait_for_timeout(2000)

        # Collapse Source Document panel
        logger.info("Collapsing Source Document panel...")
        self.page.locator(self.COLLAPSE_PANEL_BTN).nth(2).click()
        logger.info("✓ Collapse button for Source Document clicked")

        self.page.wait_for_timeout(2000)
        logger.info("Waited 2 seconds after collapsing Source Document")

        # Expand Source Document panel
        logger.info("Expanding Source Document panel...")
        self.page.locator(self.SOURCE_DOC_BTN).click()
        logger.info("✓ Source Document clicked to expand")

        self.page.wait_for_timeout(2000)

        logger.info("Collapsible panels validation completed successfully")
