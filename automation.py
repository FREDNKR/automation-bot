from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
    NoSuchElementException,
)
import time
import os


# ----------------------------------------------------------------------
# Helper: click an element robustly.
# Tries a normal click, falls back to JS click, falls back to ActionChains.
# Handles the "element covered by an overlay" case that causes silent
# failures or ElementClickInterceptedException.
# ----------------------------------------------------------------------
def robust_click(driver, element):
    try:
        element.click()
        return True
    except ElementClickInterceptedException:
        pass
    except StaleElementReferenceException:
        raise  # caller should re-locate and retry

    # Fallback 1: scroll into view then JS click
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception:
        pass

    # Fallback 2: ActionChains click (handles some overlay/animation cases)
    try:
        ActionChains(driver).move_to_element(element).pause(0.2).click().perform()
        return True
    except Exception:
        return False


# ----------------------------------------------------------------------
# Helper: find a clickable element matching any of several XPath
# candidates, searching main document first, then any iframes.
# Returns (element, frame_context) where frame_context is None for the
# main document or the iframe WebElement if found inside one.
# ----------------------------------------------------------------------
def find_in_page_or_frames(driver, wait, xpaths, timeout=10):
    driver.switch_to.default_content()
    end_time = time.time() + timeout

    while time.time() < end_time:
        # Try main document
        for xp in xpaths:
            try:
                el = driver.find_element(By.XPATH, xp)
                if el.is_displayed():
                    return el, None
            except (NoSuchElementException, StaleElementReferenceException):
                continue

        # Try each iframe
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in frames:
            try:
                driver.switch_to.frame(frame)
                for xp in xpaths:
                    try:
                        el = driver.find_element(By.XPATH, xp)
                        if el.is_displayed():
                            return el, frame
                    except (NoSuchElementException, StaleElementReferenceException):
                        continue
            except Exception:
                pass
            finally:
                driver.switch_to.default_content()

        time.sleep(0.5)

    return None, None


def is_element_disabled(driver, element):
    """
    Returns True if the element looks unclickable: disabled attribute,
    aria-disabled='true', or a class name containing 'disabled'.
    """
    try:
        if element.get_attribute("disabled") is not None:
            return True
        aria = element.get_attribute("aria-disabled")
        if aria and aria.lower() == "true":
            return True
        cls = (element.get_attribute("class") or "").lower()
        if "disabled" in cls:
            return True
        if not element.is_enabled():
            return True
        return False
    except StaleElementReferenceException:
        # Element vanished/re-rendered; treat as "state changed", caller should re-locate.
        return True


def dismiss_close_popup(driver, wait, timeout=6):
    """
    Looks for a generic 'close' button on a popup/modal (an X icon, a
    button/element with aria-label 'close', or a class like 'close' /
    'modal-close' / 'btn-close'). Clicks it if found. Returns True if a
    popup was found and dismissed, False if none was found within timeout.
    This does NOT raise if nothing is found — the popup is optional.
    """
    close_xpaths = [
        "//*[@aria-label='Close']",
        "//*[@aria-label='close']",
        "//button[contains(@class,'close')]",
        "//*[contains(@class,'modal-close')]",
        "//*[contains(@class,'btn-close')]",
        "//*[contains(@class,'close-btn')]",
        "//*[contains(@class,'popup-close')]",
        "//button[normalize-space(text())='×']",
        "//button[normalize-space(text())='X']",
        "//span[normalize-space(text())='×']",
        "//*[@role='button'][normalize-space(text())='×']",
        "//*[name()='svg'][contains(@class,'close')]/..",
    ]

    close_btn, frame_ctx = find_in_page_or_frames(driver, wait, close_xpaths, timeout=timeout)

    if close_btn is None:
        driver.switch_to.default_content()
        return False

    robust_click(driver, close_btn)
    driver.switch_to.default_content()
    print("   ✅ Dismissed popup (clicked close/X button)")
    time.sleep(1.5)
    return True


def run_automation(target_url, numbers_file):
    driver = None
    debug_dir = "debug_output"
    os.makedirs(debug_dir, exist_ok=True)

    try:
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--single-process")
        options.add_argument("--no-zygote")
        options.add_argument("--disable-setuid-sandbox")

        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service

        os.system("rm -rf ~/.wdm")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        wait = WebDriverWait(driver, 15)

        print(f"✅ Started on: {target_url}")

        with open(numbers_file, "r") as f:
            numbers = [line.strip() for line in f if line.strip()]

        for i, num in enumerate(numbers, 1):
            print(f"\n[{i}/{len(numbers)}] Processing: {num}")

            try:
                driver.get(target_url)
                time.sleep(5)

                # === Login ===
                mobile = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='tel'], input[placeholder*='mobile'], input:nth-of-type(1)")))
                mobile.clear()
                mobile.send_keys(num)

                password = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='password'], input[placeholder*='password'], input:nth-of-type(2)")))
                password.clear()
                password.send_keys(num)

                login_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button")))
                robust_click(driver, login_btn)
                print("   Login clicked")

                time.sleep(6)

                # === Dismiss any popup (X/close button) that blocks the Daily coins button ===
                print("   Checking for a popup to close...")
                dismiss_close_popup(driver, wait, timeout=6)

                # === Daily coins button ===
                print("   Looking for 'Daily coins' button...")
                daily_xpaths = [
                    "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'daily coin')]",
                    "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'daily coin')]",
                    "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'dailycoin')]",
                    "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'dailycoin')]",
                    "//*[@role='button'][contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'dailycoin')]",
                ]
                daily_btn, _ = find_in_page_or_frames(driver, wait, daily_xpaths, timeout=15)
                if daily_btn is None:
                    raise TimeoutException("Could not locate 'Daily coins' button")

                robust_click(driver, daily_btn)
                print("   ✅ Clicked 'Daily coins'!")

                # Give the popup time to animate/render fully.
                time.sleep(4)

                # === Sign In (inside popup, possibly inside an iframe) ===
                sign_xpaths = [
                    "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in')]",
                    "//*[@role='button'][contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in')]",
                    "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in')]",
                    "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in')]",
                ]

                sign_btn, frame_ctx = find_in_page_or_frames(driver, wait, sign_xpaths, timeout=12)

                if sign_btn is None:
                    # Save diagnostics so you can see exactly what the popup looked like.
                    shot_path = os.path.join(debug_dir, f"popup_not_found_{num}.png")
                    html_path = os.path.join(debug_dir, f"popup_not_found_{num}.html")
                    driver.switch_to.default_content()
                    driver.save_screenshot(shot_path)
                    with open(html_path, "w", encoding="utf-8") as hf:
                        hf.write(driver.page_source)
                    raise TimeoutException(
                        f"Could not locate 'Sign In' button. Saved {shot_path} and {html_path} for inspection."
                    )

                # If the element was in an iframe, driver context is already
                # switched into that frame by find_in_page_or_frames since it
                # only switches back to default on failure paths.
                success = robust_click(driver, sign_btn)
                driver.switch_to.default_content()

                if not success:
                    raise ElementClickInterceptedException("Sign In click failed after all fallback strategies")

                print("   ✅ Clicked Sign In!")

            except Exception as e:
                print(f"   ❌ Error for {num}: {type(e).__name__}: {e}")
                try:
                    driver.switch_to.default_content()
                    driver.save_screenshot(os.path.join(debug_dir, f"error_{num}.png"))
                except Exception:
                    pass
                continue

        print("\n✅ All done!")
        return "Automation completed successfully!"

    except Exception as e:
        return f"Critical Error: {e}"
    finally:
        if driver:
            driver.quit()