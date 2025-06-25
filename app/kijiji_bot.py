"""
Kijiji Bot - Selenium automation for Kijiji posting.

This module provides the KijijiBot class for automated posting to Kijiji.
It handles login, navigation, ad posting, and error management.
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logger = logging.getLogger(__name__)

# Constants for Kijiji navigation
KIJIJI_BASE_URL = "https://www.kijiji.ca"
KIJIJI_LOGIN_URL = "https://www.kijiji.ca/t-login.html"
KIJIJI_POST_URL = "https://www.kijiji.ca/p-post-ad.html"

# Wait timeouts (in seconds)
DEFAULT_WAIT_TIMEOUT = 10
LONG_WAIT_TIMEOUT = 20
SHORT_WAIT_TIMEOUT = 5

# Hard-coded navigation path: Ontario → Toronto (GTA) → Markham / York Region
NAVIGATION_PATH = {
    'province': 'Ontario',
    'city_area': 'Toronto (GTA)',
    'specific_area': 'Markham / York Region'
}


class KijijiBot:
    """
    Selenium-based bot for automated Kijiji posting.
    
    Handles login, navigation, ad posting with explicit waits and error handling.
    """
    
    def __init__(self, email: str, password: str, driver: Optional[webdriver.Chrome] = None, headless: bool = False):
        """
        Initialize the KijijiBot.
        
        Args:
            email: Kijiji account email
            password: Kijiji account password  
            driver: Optional pre-configured WebDriver instance
            headless: Whether to run Chrome in headless mode
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.driver = driver
        self.wait = None
        self.long_wait = None
        self.short_wait = None
        
        # Initialize driver if not provided
        if self.driver is None:
            self._setup_driver()
        else:
            self._setup_waits()
            
        logger.info(f"KijijiBot initialized for email: {email[:3]}***{email[-10:]}")
    
    def _setup_driver(self) -> None:
        """
        Set up Chrome WebDriver using webdriver-manager.
        """
        try:
            # Chrome options
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Auto-fetch Chrome driver
            service = Service(ChromeDriverManager().install())
            
            # Create driver
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Setup waits
            self._setup_waits()
            
            logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise WebDriverException(f"WebDriver setup failed: {str(e)}")
    
    def _setup_waits(self) -> None:
        """
        Setup WebDriverWait instances for different timeout scenarios.
        """
        self.wait = WebDriverWait(self.driver, DEFAULT_WAIT_TIMEOUT)
        self.long_wait = WebDriverWait(self.driver, LONG_WAIT_TIMEOUT)
        self.short_wait = WebDriverWait(self.driver, SHORT_WAIT_TIMEOUT)
    
    def login(self) -> Dict[str, Any]:
        """
        Log into Kijiji using provided credentials.
        
        Returns:
            Dict with success status, message, and optional error details
        """
        try:
            logger.info("Starting Kijiji login process")
            
            # Navigate to login page
            self.driver.get(KIJIJI_LOGIN_URL)
            logger.debug(f"Navigated to: {KIJIJI_LOGIN_URL}")
            
            # Wait for and find email field
            email_field = self.wait.until(
                EC.element_to_be_clickable((By.ID, "emailOrNickname"))
            )
            email_field.clear()
            email_field.send_keys(self.email)
            logger.debug("Email entered")
            
            # Wait for and find password field
            password_field = self.wait.until(
                EC.element_to_be_clickable((By.ID, "password"))
            )
            password_field.clear()
            password_field.send_keys(self.password)
            logger.debug("Password entered")
            
            # Find and click login button
            login_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit'][@aria-label='Sign In']"))
            )
            login_button.click()
            logger.debug("Login button clicked")
            
            # Wait for successful login - check for profile or account elements
            try:
                # Multiple possible indicators of successful login
                success_indicators = [
                    (By.XPATH, "//span[contains(text(), 'My Kijiji')]"),
                    (By.XPATH, "//a[contains(@href, '/m-my-ads.html')]"),
                    (By.CLASS_NAME, "user-profile"),
                    (By.XPATH, "//button[contains(text(), 'Post Ad')]"),
                ]
                
                login_success = False
                for by_type, selector in success_indicators:
                    try:
                        self.short_wait.until(EC.presence_of_element_located((by_type, selector)))
                        login_success = True
                        logger.info(f"Login successful - found indicator: {selector}")
                        break
                    except TimeoutException:
                        continue
                
                if not login_success:
                    # Check for error messages
                    try:
                        error_element = self.short_wait.until(
                            EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
                        )
                        error_text = error_element.text
                        logger.error(f"Login failed with error: {error_text}")
                        return {
                            'success': False,
                            'message': f"Login failed: {error_text}",
                            'ad_url': None
                        }
                    except TimeoutException:
                        logger.error("Login failed - no success indicators found")
                        return {
                            'success': False,
                            'message': "Login failed - unable to verify successful login",
                            'ad_url': None
                        }
            
            except TimeoutException:
                logger.error("Login verification timed out")
                return {
                    'success': False,
                    'message': "Login verification timed out",
                    'ad_url': None
                }
            
            logger.info("Login completed successfully")
            return {
                'success': True,
                'message': "Login successful",
                'ad_url': None
            }
            
        except TimeoutException as e:
            logger.error(f"Login timeout: {str(e)}")
            return {
                'success': False,
                'message': f"Login timeout: Element not found within timeout period",
                'ad_url': None
            }
        except Exception as e:
            logger.error(f"Login failed with exception: {str(e)}")
            return {
                'success': False,
                'message': f"Login failed: {str(e)}",
                'ad_url': None
            }
    
    def post_ad(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post an ad using the provided record data.
        
        Args:
            record: Dictionary containing ad details (title, description, price, etc.)
            
        Returns:
            Dict with success status, message, and optional ad_url
        """
        try:
            logger.info(f"Starting ad posting for: {record.get('title', 'Unknown')}")
            
            # Navigate to post ad page
            self.driver.get(KIJIJI_POST_URL)
            logger.debug(f"Navigated to: {KIJIJI_POST_URL}")
            
            # Step 1: Select category - assume it's for vehicles/heavy equipment
            category_result = self._select_category()
            if not category_result['success']:
                return category_result
            
            # Step 2: Fill location - hard-coded navigation path
            location_result = self._select_location()
            if not location_result['success']:
                return location_result
            
            # Step 3: Fill ad details
            details_result = self._fill_ad_details(record)
            if not details_result['success']:
                return details_result
            
            # Step 4: Upload image if provided
            if record.get('image_filename'):
                upload_result = self._upload_image(record)
                if not upload_result['success']:
                    return upload_result
            
            # Step 5: Submit the ad
            submit_result = self._submit_ad()
            if not submit_result['success']:
                return submit_result
            
            # Step 6: Get the ad URL if possible
            ad_url = self._get_posted_ad_url()
            
            logger.info(f"Ad posted successfully: {record.get('title')}")
            return {
                'success': True,
                'message': f"Ad '{record.get('title')}' posted successfully",
                'ad_url': ad_url
            }
            
        except Exception as e:
            logger.error(f"Ad posting failed: {str(e)}")
            return {
                'success': False,
                'message': f"Ad posting failed: {str(e)}",
                'ad_url': None
            }
    
    def _select_category(self) -> Dict[str, Any]:
        """
        Select appropriate category for heavy equipment/bucket trucks.
        """
        try:
            # Wait for category selection page
            logger.debug("Selecting category for heavy equipment")
            
            # Look for Business & Industrial or similar category
            category_selectors = [
                "//a[contains(text(), 'Business & Industrial')]",
                "//span[contains(text(), 'Business & Industrial')]",
                "//div[contains(text(), 'Business & Industrial')]"
            ]
            
            category_clicked = False
            for selector in category_selectors:
                try:
                    category_element = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    category_element.click()
                    category_clicked = True
                    logger.debug("Business & Industrial category selected")
                    break
                except (TimeoutException, ElementClickInterceptedException):
                    continue
            
            if not category_clicked:
                # Fallback to general category if specific one not found
                try:
                    general_category = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'category')][1]"))
                    )
                    general_category.click()
                    logger.debug("Fallback category selected")
                except TimeoutException:
                    return {
                        'success': False,
                        'message': "Could not select any category",
                        'ad_url': None
                    }
            
            # Continue to subcategory if needed
            try:
                subcategory_selectors = [
                    "//a[contains(text(), 'Heavy Equipment')]",
                    "//span[contains(text(), 'Heavy Equipment')]",
                    "//div[contains(text(), 'Heavy Equipment')]",
                    "//a[contains(text(), 'Other')]"
                ]
                
                for selector in subcategory_selectors:
                    try:
                        subcategory_element = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        subcategory_element.click()
                        logger.debug(f"Subcategory selected: {selector}")
                        break
                    except (TimeoutException, ElementClickInterceptedException):
                        continue
            except Exception:
                # Subcategory selection is optional
                pass
            
            return {'success': True, 'message': 'Category selected', 'ad_url': None}
                
        except Exception as e:
            logger.error(f"Category selection failed: {str(e)}")
            return {
                'success': False,
                'message': f"Category selection failed: {str(e)}",
                'ad_url': None
            }
    
    def _select_location(self) -> Dict[str, Any]:
        """
        Select location using hard-coded navigation path:
        Ontario → Toronto (GTA) → Markham / York Region
        """
        try:
            logger.debug("Selecting location: Ontario → Toronto (GTA) → Markham / York Region")
            
            # Step 1: Select Ontario
            ontario_selectors = [
                "//option[contains(text(), 'Ontario')]",
                "//a[contains(text(), 'Ontario')]",
                "//span[contains(text(), 'Ontario')]"
            ]
            
            for selector in ontario_selectors:
                try:
                    ontario_element = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    ontario_element.click()
                    logger.debug("Ontario selected")
                    break
                except (TimeoutException, ElementClickInterceptedException):
                    continue
            
            # Wait a moment for location options to load
            time.sleep(2)
            
            # Step 2: Select Toronto (GTA)
            toronto_selectors = [
                "//option[contains(text(), 'Toronto (GTA)')]",
                "//a[contains(text(), 'Toronto (GTA)')]",
                "//span[contains(text(), 'Toronto')]"
            ]
            
            for selector in toronto_selectors:
                try:
                    toronto_element = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    toronto_element.click()
                    logger.debug("Toronto (GTA) selected")
                    break
                except (TimeoutException, ElementClickInterceptedException):
                    continue
            
            # Wait a moment for sub-location options to load
            time.sleep(2)
            
            # Step 3: Select Markham / York Region
            markham_selectors = [
                "//option[contains(text(), 'Markham')]",
                "//option[contains(text(), 'York Region')]",
                "//a[contains(text(), 'Markham')]",
                "//a[contains(text(), 'York Region')]"
            ]
            
            for selector in markham_selectors:
                try:
                    markham_element = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    markham_element.click()
                    logger.debug("Markham / York Region selected")
                    break
                except (TimeoutException, ElementClickInterceptedException):
                    continue
            
            return {'success': True, 'message': 'Location selected', 'ad_url': None}
                
        except Exception as e:
            logger.error(f"Location selection failed: {str(e)}")
            return {
                'success': False,
                'message': f"Location selection failed: {str(e)}",
                'ad_url': None
            }
    
    def _fill_ad_details(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fill in the ad details form with record data.
        """
        try:
            logger.debug("Filling ad details form")
            
            # Title field
            title_selectors = [
                "//input[@name='title']",
                "//input[@id='title']",
                "//input[contains(@placeholder, 'title')]"
            ]
            
            for selector in title_selectors:
                try:
                    title_field = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    title_field.clear()
                    title_field.send_keys(record.get('title', ''))
                    logger.debug(f"Title entered: {record.get('title')}")
                    break
                except (TimeoutException, ElementClickInterceptedException):
                    continue
            
            # Description field
            description_selectors = [
                "//textarea[@name='description']",
                "//textarea[@id='description']",
                "//textarea[contains(@placeholder, 'description')]"
            ]
            
            for selector in description_selectors:
                try:
                    description_field = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    description_field.clear()
                    description_field.send_keys(record.get('description', ''))
                    logger.debug("Description entered")
                    break
                except (TimeoutException, ElementClickInterceptedException):
                    continue
            
            # Price field
            price_selectors = [
                "//input[@name='price']",
                "//input[@id='price']",
                "//input[contains(@placeholder, 'price')]"
            ]
            
            for selector in price_selectors:
                try:
                    price_field = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    price_field.clear()
                    price_field.send_keys(str(record.get('price', '')))
                    logger.debug(f"Price entered: {record.get('price')}")
                    break
                except (TimeoutException, ElementClickInterceptedException):
                    continue
            
            # Additional fields if available
            self._fill_optional_fields(record)
            
            return {'success': True, 'message': 'Ad details filled', 'ad_url': None}
                
        except Exception as e:
            logger.error(f"Failed to fill ad details: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to fill ad details: {str(e)}",
                'ad_url': None
            }
    
    def _fill_optional_fields(self, record: Dict[str, Any]) -> None:
        """
        Fill optional fields like fuel type, equipment type, tags.
        """
        try:
            # Fuel type dropdown
            fuel_type = record.get('fuel_type', '')
            if fuel_type:
                fuel_selectors = [
                    f"//option[contains(text(), '{fuel_type}')]",
                    f"//select[@name='fuel']//option[contains(text(), '{fuel_type}')]"
                ]
                
                for selector in fuel_selectors:
                    try:
                        fuel_option = self.short_wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        fuel_option.click()
                        logger.debug(f"Fuel type selected: {fuel_type}")
                        break
                    except (TimeoutException, ElementClickInterceptedException):
                        continue
            
            # Equipment type
            equipment_type = record.get('equipment_type', '')
            if equipment_type:
                equipment_selectors = [
                    f"//option[contains(text(), '{equipment_type}')]",
                    f"//select[@name='equipment']//option[contains(text(), '{equipment_type}')]"
                ]
                
                for selector in equipment_selectors:
                    try:
                        equipment_option = self.short_wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        equipment_option.click()
                        logger.debug(f"Equipment type selected: {equipment_type}")
                        break
                    except (TimeoutException, ElementClickInterceptedException):
                        continue
            
            # Tags field
            tags = record.get('tags', '')
            if tags:
                tag_selectors = [
                    "//input[@name='tags']",
                    "//input[@id='tags']",
                    "//input[contains(@placeholder, 'tag')]"
                ]
                
                for selector in tag_selectors:
                    try:
                        tags_field = self.short_wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        tags_field.clear()
                        tags_field.send_keys(tags)
                        logger.debug(f"Tags entered: {tags}")
                        break
                    except (TimeoutException, ElementClickInterceptedException):
                        continue
                        
        except Exception as e:
            logger.warning(f"Some optional fields could not be filled: {str(e)}")
    
    def _upload_image(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload image file for the ad.
        """
        try:
            # Import here to avoid circular imports
            try:
                from . import data_io
            except ImportError:
                import data_io
            
            # Get image path
            image_path = data_io.get_image_path(record)
            logger.debug(f"Uploading image: {image_path}")
            
            # Find file upload input
            upload_selectors = [
                "//input[@type='file']",
                "//input[@name='image']",
                "//input[@id='image']"
            ]
            
            for selector in upload_selectors:
                try:
                    upload_input = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    upload_input.send_keys(str(image_path))
                    logger.debug(f"Image uploaded: {image_path}")
                    
                    # Wait for upload to complete
                    time.sleep(3)
                    return {'success': True, 'message': 'Image uploaded', 'ad_url': None}
                    
                except (TimeoutException, WebDriverException):
                    continue
            
            # If no upload field found, continue without image
            logger.warning("No image upload field found, continuing without image")
            return {'success': True, 'message': 'No image upload field found', 'ad_url': None}
                
        except Exception as e:
            logger.warning(f"Image upload failed: {str(e)}")
            # Don't fail the entire posting process for image upload issues
            return {'success': True, 'message': f'Image upload failed: {str(e)}', 'ad_url': None}
    
    def _submit_ad(self) -> Dict[str, Any]:
        """
        Submit the completed ad form.
        """
        try:
            logger.debug("Submitting ad")
            
            # Find submit button
            submit_selectors = [
                "//button[contains(text(), 'Post')]",
                "//button[contains(text(), 'Submit')]",
                "//input[@type='submit']",
                "//button[@type='submit']"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    submit_button.click()
                    logger.debug("Submit button clicked")
                    
                    # Wait for submission to complete
                    time.sleep(5)
                    return {'success': True, 'message': 'Ad submitted', 'ad_url': None}
                    
                except (TimeoutException, ElementClickInterceptedException):
                    continue
            
            return {
                'success': False,
                'message': "Could not find submit button",
                'ad_url': None
            }
                
        except Exception as e:
            logger.error(f"Ad submission failed: {str(e)}")
            return {
                'success': False,
                'message': f"Ad submission failed: {str(e)}",
                'ad_url': None
            }
    
    def _get_posted_ad_url(self) -> Optional[str]:
        """
        Try to extract the URL of the posted ad.
        """
        try:
            # Look for success page indicators or ad URL
            current_url = self.driver.current_url
            
            # If we're on a success page or ad page, return the URL
            if 'kijiji.ca' in current_url and 'v-' in current_url:
                logger.debug(f"Ad URL detected: {current_url}")
                return current_url
            
            # Look for success message with ad link
            ad_link_selectors = [
                "//a[contains(@href, '/v-')]",
                "//a[contains(text(), 'View your ad')]"
            ]
            
            for selector in ad_link_selectors:
                try:
                    ad_link = self.short_wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    ad_url = ad_link.get_attribute('href')
                    if ad_url:
                        logger.debug(f"Ad URL found: {ad_url}")
                        return ad_url
                except TimeoutException:
                    continue
            
            return None
                
        except Exception as e:
            logger.warning(f"Could not extract ad URL: {str(e)}")
            return None
    
    def close(self) -> None:
        """
        Close the WebDriver and clean up resources.
        """
        try:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error closing WebDriver: {str(e)}")


# Utility function for testing
def test_kijiji_bot(email: str, password: str, sample_record: Dict[str, Any] = None) -> None:
    """
    Test function for KijijiBot.
    
    Args:
        email: Test email
        password: Test password
        sample_record: Optional sample record for testing
    """
    if sample_record is None:
        sample_record = {
            'title': 'Test Bucket Truck',
            'description': 'Test description for bucket truck',
            'price': 50000,
            'tags': 'test,bucket,truck',
            'fuel_type': 'Diesel',
            'equipment_type': 'Bucket Truck',
            'image_filename': 'truck1.jpg'
        }
    
    bot = None
    try:
        # Initialize bot
        bot = KijijiBot(email, password, headless=False)
        
        # Test login
        login_result = bot.login()
        print(f"Login result: {login_result}")
        
        if login_result['success']:
            # Test posting
            post_result = bot.post_ad(sample_record)
            print(f"Post result: {post_result}")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
    finally:
        if bot:
            bot.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 3:
        test_email = sys.argv[1]
        test_password = sys.argv[2]
        test_kijiji_bot(test_email, test_password)
    else:
        print("Usage: python kijiji_bot.py <email> <password>")
        print("Note: This will run a test with sample data")
