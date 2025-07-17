import os.path

from base.base import BasePage
from playwright.sync_api import expect


class HomePage(BasePage):
    TITLE_TEXT = "//span[normalize-space()='Processing Queue']"
    SELECT_SCHEMA = "//input[@placeholder='Select Schema']"
    IMPORT_CONTENT = "//button[normalize-space()='Import Content']"
    REFRESH = "//button[normalize-space()='Refresh']"
    BROWSE_FILES = "//button[normalize-space()='Browse Files']"
    UPLOAD_BTN = "//button[normalize-space()='Upload']"
    SUCCESS_MSG = "/div[@class='file-item']//*[name()='svg']"
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
        self.page = page

    def validate_home_page(self):
        expect(self.page.locator(self.TITLE_TEXT)).to_be_visible()
        self.page.wait_for_timeout(2000)

    def select_schema(self, SchemaName):
        self.page.wait_for_timeout(5000)
        self.page.locator(self.SELECT_SCHEMA).click()
        if SchemaName == "Invoice":
            self.page.get_by_role("option", name="Invoice").click()
        else:
            self.page.get_by_role("option", name="Property Loss Damage Claim").click()

    def upload_files(self, schemaType):
        with self.page.expect_file_chooser() as fc_info:
            self.page.locator(self.IMPORT_CONTENT).click()
            self.page.locator(self.BROWSE_FILES).click()
            self.page.wait_for_timeout(5000)
            # self.page.wait_for_load_state('networkidle')
        file_chooser = fc_info.value
        current_working_dir = os.getcwd()
        file_path1 = os.path.join(
            current_working_dir, "testdata", "FabrikamInvoice_1.pdf"
        )
        file_path2 = os.path.join(current_working_dir, "testdata", "ClaimForm_1.pdf")

        if schemaType == "Invoice":
            file_chooser.set_files([file_path1])
        else:
            file_chooser.set_files([file_path2])
        self.page.wait_for_timeout(5000)
        self.page.wait_for_load_state("networkidle")
        self.page.locator(self.UPLOAD_BTN).click()
        self.page.wait_for_timeout(10000)
        expect(
            self.page.get_by_role("alertdialog", name="Import Content")
            .locator("path")
            .nth(1)
        ).to_be_visible()
        self.page.locator(self.CLOSE_BTN).click()

    def refresh(self):
        status_ele = self.page.locator(self.STATUS).nth(2)
        max_retries = 15

        for i in range(max_retries):
            status_text = status_ele.inner_text().strip()

            if status_text == "Completed":
                break
            elif status_text == "Error":
                raise Exception(
                    f"Process failed with status: 'Error' after {i + 1} retries."
                )

            self.page.locator(self.REFRESH).click()
            self.page.wait_for_timeout(5000)
        else:
            # Executed only if the loop did not break (i.e., status is neither Completed nor Error)
            raise Exception(
                f"Process did not complete. Final status was '{status_text}' after {max_retries} retries."
            )

    def validate_invoice_extracted_result(self):
        expect(self.page.locator(self.CUSTOMER_NAME)).to_contain_text(
            "Paris Fashion Group SARL"
        )
        expect(self.page.locator(self.CUSTOMER_STREET)).to_contain_text(
            "10 Rue de Rivoli"
        )
        expect(self.page.locator(self.CUSTOMER_CITY)).to_contain_text("Paris")
        expect(self.page.locator(self.CUSTOMER_ZIP_CODE)).to_contain_text("75001")
        expect(self.page.locator(self.CUSTOMER_COUNTRY)).to_contain_text("France")
        expect(self.page.locator(self.SHIPPING_STREET)).to_contain_text(
            "25 Avenue Montaigne"
        )
        expect(self.page.locator(self.SHIPPING_CITY)).to_contain_text("Paris")
        expect(self.page.locator(self.SHIPPING_POSTAL_CODE)).to_contain_text("75008")
        expect(self.page.locator(self.SHIPPING_COUNTRY)).to_contain_text("France")
        expect(self.page.locator(self.PURCHASE_ORDER)).to_contain_text("PO-34567")
        expect(self.page.locator(self.INVOICE_ID)).to_contain_text("INV-20231005")
        expect(self.page.locator(self.INVOICE_DATE)).to_contain_text("2023-10-05")
        expect(self.page.locator(self.INVOICE_DATE)).to_contain_text("2023-10-05")
        expect(self.page.locator(self.payable_by)).to_contain_text("2023-11-04")
        expect(self.page.locator(self.vendor_name)).to_contain_text(
            "Fabrikam Unlimited Company"
        )
        expect(self.page.locator(self.v_street)).to_contain_text("Wilton Place")
        expect(self.page.locator(self.v_city)).to_contain_text("Brooklyn")
        expect(self.page.locator(self.v_state)).to_contain_text("NY")
        expect(self.page.locator(self.v_zip_code)).to_contain_text("22345")
        expect(self.page.locator(self.vendor_tax_id)).to_contain_text("FR123456789")
        expect(self.page.locator(self.SUBTOTAL)).to_contain_text("16859.1")
        expect(self.page.locator(self.TOTAL_TAX)).to_contain_text("11286")
        expect(self.page.locator(self.INVOICE_TOTAL)).to_contain_text("22516.08")
        expect(self.page.locator(self.PAYMENT_TERMS)).to_contain_text("Net 30")
        expect(self.page.locator(self.product_code1)).to_contain_text("EM032")
        expect(self.page.locator(self.p1_description)).to_contain_text(
            "Item: Terminal Lug"
        )
        expect(self.page.locator(self.p1_quantity)).to_contain_text("163")
        expect(self.page.locator(self.p1_tax)).to_contain_text("2934")
        expect(self.page.locator(self.p1_unit_price)).to_contain_text("2.5")
        expect(self.page.locator(self.p1_total)).to_contain_text("407.5")

    def modify_and_submit_extracted_data(self):
        self.page.get_by_text('"25 Avenue Montaigne"').dblclick()
        self.page.locator(self.SHIPPING_ADD_STREET).fill("25 Avenue Montaigne updated")
        self.page.locator(self.EDIT_CONFIRM).click()
        self.page.locator(self.COMMENTS).fill("Updated Shipping street address")
        self.page.locator(self.SAVE_BTN).click()
        self.page.wait_for_timeout(6000)

    def validate_process_steps(self):
        self.page.locator(self.PROCESS_STEPS).click()
        self.page.locator(self.EXTRACT).click()
        self.page.wait_for_timeout(3000)
        expect(self.page.get_by_text('"extract"')).to_be_visible()
        expect(self.page.get_by_text('"Succeeded"')).to_be_visible()
        self.page.locator(self.EXTRACT).click()
        self.page.wait_for_timeout(3000)
        self.page.locator(self.MAP).click()
        self.page.wait_for_timeout(3000)
        expect(self.page.get_by_text('"map"')).to_be_visible()
        self.page.locator(self.MAP).click()
        self.page.wait_for_timeout(3000)
        self.page.locator(self.EVALUATE).click()
        self.page.wait_for_timeout(3000)
        expect(self.page.get_by_text('"evaluate"')).to_be_visible()
        self.page.locator(self.EVALUATE).click()
        self.page.wait_for_timeout(3000)
        self.page.locator(self.EXTRACTED_RESULT).click()
        self.page.wait_for_timeout(3000)

    def validate_property_extracted_result(self):
        expect(self.page.locator(self.first_name)).to_contain_text("Sophia")
        expect(self.page.locator(self.last_name)).to_contain_text("Kim")
        expect(self.page.locator(self.tel_no)).to_contain_text("646-555-0789")
        expect(self.page.locator(self.policy_no)).to_contain_text("PH5678901")
        expect(self.page.locator(self.coverage_type)).to_contain_text("Homeowners")
        expect(self.page.locator(self.claim_number)).to_contain_text("CLM5432109")
        expect(self.page.locator(self.policy_effective_date)).to_contain_text(
            "2022-07-01"
        )
        expect(self.page.locator(self.policy_expiration_date)).to_contain_text(
            "2023-07-01"
        )
        expect(self.page.locator(self.damage_deductible)).to_contain_text("1000")
        expect(self.page.locator(self.damage_deductible_currency)).to_contain_text(
            "USD"
        )
        expect(self.page.locator(self.date_of_damage_loss)).to_contain_text(
            "2023-05-10"
        )
        expect(self.page.locator(self.time_of_loss)).to_contain_text("13:20")
        expect(self.page.locator(self.date_prepared)).to_contain_text("2023-05-11")
        expect(self.page.locator(self.item)).to_contain_text("Apple")
        expect(self.page.locator(self.description)).to_contain_text(
            '"High-performance tablet with a large, vibrant display'
        )
        expect(self.page.locator(self.date_acquired)).to_contain_text("2022-01-20")
        expect(self.page.locator(self.cost_new)).to_contain_text("1100")
        expect(self.page.locator(self.cost_new_currency)).to_contain_text("USD")
        expect(self.page.locator(self.replacement_repair)).to_contain_text("350")
        expect(self.page.locator(self.replacement_repair_currency)).to_contain_text(
            "USD"
        )

    def delete_files(self):
        self.page.locator(self.DELETE_FILE).nth(0).click()
        self.page.get_by_role("menuitem", name="Delete").click()
        self.page.get_by_role("button", name="Confirm").click()
        self.page.wait_for_timeout(6000)
