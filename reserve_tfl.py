import threading
import time
import argparse

from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
import pickle
import os

# Login not required for Tock. Leave it as false to decrease reservation delay
ENABLE_LOGIN = True
TOCK_USERNAME = "ilyakatz@gmail.com"
TOCK_PASSWORD = "PASSWORD"

# Set your specific reservation month and days
RESERVATION_MONTH = 'May'
RESERVATION_DAY = '14'
RESERVATION_YEAR = '2024'
RESERVATION_TIME_FORMAT = "%I:%M %p"

RESERVATION_URI_PROD = "https://www.exploretock.com/tfl"
RESERVATION_URI_TEST = "https://www.exploretock.com/persona-san-francisco"

# Set the time range for acceptable reservation times.
# I.e., any available slots between 5:00 PM and 8:30 PM
EARLIEST_TIME = "3:00 PM"
LATEST_TIME = "10:30 PM"
RESERVATION_TIME_MIN = datetime.strptime(EARLIEST_TIME, RESERVATION_TIME_FORMAT)
RESERVATION_TIME_MAX = datetime.strptime(LATEST_TIME, RESERVATION_TIME_FORMAT)

# Set the party size for the reservation
RESERVATION_SIZE = 5

# Multithreading configurations
NUM_THREADS = 1
THREAD_DELAY_SEC = 1
RESERVATION_FOUND = False

# Time between each page refresh in milliseconds. Decrease this time to
# increase the number of reservation attempts
REFRESH_DELAY_MSEC = 500

# Chrome extension configurations that are used with Luminati.io proxy.
# Enable proxy to avoid getting IP potentially banned. This should be enabled only if the REFRESH_DELAY_MSEC
# is extremely low (sub hundred) and NUM_THREADS > 1.
ENABLE_PROXY = False
USER_DATA_DIR = '~/Library/Application Support/Google/Chrome'
PROFILE_DIR = 'Default'
# https://chrome.google.com/webstore/detail/luminati/efohiadmkaogdhibjbmeppjpebenaool
EXTENSION_PATH = USER_DATA_DIR + '/' + PROFILE_DIR + '/Extensions/efohiadmkaogdhibjbmeppjpebenaool/1.149.316_0'

# Delay for how long the browser remains open so that the reservation can be finalized. Tock holds the reservation
# for 10 minutes before releasing.
BROWSER_CLOSE_DELAY_SEC = 600

WEBDRIVER_TIMEOUT_DELAY_MS = 3000

MONTH_NUM = {
    'january':   '01',
    'february':  '02',
    'march':     '03',
    'april':     '04',
    'may':       '05',
    'june':      '06',
    'july':      '07',
    'august':    '08',
    'september': '09',
    'october':   '10',
    'november':  '11',
    'december':  '12'
}


class ReserveTFL():
    def __init__(self):
        self.driver = self.create_driver()

    def create_driver(self):
        options = Options()
        if ENABLE_PROXY:
            options.add_argument('--load-extension={}'.format(EXTENSION_PATH))
            options.add_argument('--user-data-dir={}'.format(USER_DATA_DIR))
            options.add_argument('--profile-directory=Default')

        return webdriver.Chrome(options=options)

    def teardown(self):
        self.driver.quit()

    def reserve(self):
        global RESERVATION_FOUND
        print("Looking for availability on month: %s, days: %s, between times: %s and %s" % (RESERVATION_MONTH, RESERVATION_DAY, EARLIEST_TIME, LATEST_TIME))

        if ENABLE_LOGIN:
            self.check_cookies_and_login()

        while not RESERVATION_FOUND:
            time.sleep(REFRESH_DELAY_MSEC / 1000)
            url = RESERVATION_URI + "/search?date=%s-%s-02&size=%s&time=%s" % (RESERVATION_YEAR, month_num(RESERVATION_MONTH), RESERVATION_SIZE, "19%3A00")
            print("Refreshing page: %s" % url)
            self.driver.get(url)
            # self.driver.get("https://www.exploretock.com/tfl/search?date=%s-%s-02&size=%s&time=%s" % (RESERVATION_YEAR, month_num(RESERVATION_MONTH), RESERVATION_SIZE, "22%3A00"))
            WebDriverWait(self.driver, WEBDRIVER_TIMEOUT_DELAY_MS).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "div.ConsumerCalendar-month")))

            if not self.search_month():
                print("No available days found. Continuing next search iteration")
                continue

            WebDriverWait(self.driver, WEBDRIVER_TIMEOUT_DELAY_MS).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "button.Consumer-resultsListItem.is-available")))

            print("Found availability. Sleeping for 10 minutes to complete reservation...")
            RESERVATION_FOUND = True
            time.sleep(BROWSER_CLOSE_DELAY_SEC)

    def login_tock(self):
        self.driver.get("https://www.exploretock.com/tfl/login")
        WebDriverWait(self.driver, WEBDRIVER_TIMEOUT_DELAY_MS).until(expected_conditions.presence_of_element_located((By.NAME, "email")))
        print("Logging into Tock")
        self.driver.find_element(By.NAME, "email").send_keys(TOCK_USERNAME)
        print("Email entered")
        self.driver.find_element(By.NAME, "password").send_keys(TOCK_PASSWORD)
        print("Password entered")
        # self.driver.find_element(By.CSS_SELECTOR, "button.MuiButtonBase-root").click()
        data_testid_value = 'login-form'
        css_selector = f'[data-testid="{data_testid_value}"]'
        wait = WebDriverWait(self.driver, 2)
        form = wait.until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
        form.submit()

        print("Login form submitted")
        css_selector = f'[aria-label="Toggle menu open"]'
        WebDriverWait(self.driver, WEBDRIVER_TIMEOUT_DELAY_MS).until(expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))

    def save_cookies(self):
        print("Saving cookies")
        pickle.dump(self.driver.get_cookies(), open("cookies.pkl", "wb"))

    def load_cookies(self):
        print("Loading cookies")
        cookies = pickle.load(open("cookies.pkl", "rb"))
        for cookie in cookies:
            self.driver.add_cookie(cookie)

    def check_cookies_and_login(self):
        self.driver.get("https://www.exploretock.com/tfl/login")
        WebDriverWait(self.driver, WEBDRIVER_TIMEOUT_DELAY_MS).until(expected_conditions.presence_of_element_located((By.NAME, "email")))
        print("Checking cookies")
        if len(self.driver.get_cookies()) == 0:
            print("No cookies found. Logging in")
            self.login_tock()
        else:
            if os.path.exists("cookies.pkl"):
                print("Cookies found. Loading cookies")
                self.load_cookies()
            else:
                print("No cookies file found. Logging in")
                self.login_tock()
                self.save_cookies()


    def search_month(self):
        month_object = None

        print("Searching for month", RESERVATION_MONTH)
        for month in self.driver.find_elements(By.CSS_SELECTOR, "div.ConsumerCalendar-month"):
            header = month.find_element(By.CSS_SELECTOR, "div.ConsumerCalendar-monthHeading")
            span = header.find_element(By.CSS_SELECTOR, "span.MuiTypography-root")
            print("Encountered month", span.text)

            if RESERVATION_MONTH in span.text:
                month_object = month
                print("Month", RESERVATION_MONTH, "found")
                break

        if month_object is None:
            print("Month", RESERVATION_MONTH, "not found. Ending search")
            return False

        for day in month_object.find_elements(By.CSS_SELECTOR, "button.ConsumerCalendar-day.is-in-month.is-available"):
            span = day.find_element(By.CSS_SELECTOR, "span.MuiTypography-root")
            print("Encountered day: " + span.text)
            if span.text == RESERVATION_DAY:
                print("Day %s found. Clicking button" % span.text)
                day.click()

                self.see_more_times()
                if self.search_time():
                    print("Time found")
                    return True
                else:
                    print("No available times found. ")
                    # TODO: we need to break out of the loop since see_more_times() will refresh the page
                    # and it will break self.driver
                    break

        return False

    def see_more_times(self):
        try:
            print("Checking for more times")
            more_time = self.driver.find_element("xpath", "//*[contains(text(), 'more times')]")
            print("See if 'more times' are available", more_time.text)
            if more_time:
                print("More times found", more_time.text)
                more_time.click()

                # Wait for the page content to potentially change
                WebDriverWait(self.driver, 10).until(EC.staleness_of(more_time))

                # Re-locate the "more times" element after the page content refreshes
                more_time = self.driver.find_element("xpath", "//*[contains(text(), 'more times')]")
                more_time.click()
        except StaleElementReferenceException:
             print("StaleElementReferenceException occurred ... retrying")
             # If StaleElementReferenceException occurs, retry the operation
            #  self.driver = self.create_driver()
             self.see_more_times()
        except NoSuchElementException:
            print("No more times found")
            return

    def search_time(self):

        data_testid_value="search-result"
        css_selector = f'[data-testid="{data_testid_value}"]'
        for item in self.driver.find_elements(By.CSS_SELECTOR, css_selector):
            print("Encountered time item", item.text)
            span = item.find_element(By.CSS_SELECTOR, "span.Consumer-resultsListItemTime")
            span2 = span.find_element(By.CSS_SELECTOR, "span")
            print("Encountered time", span2.text)

            available_time = datetime.strptime(span2.text, RESERVATION_TIME_FORMAT)
            if RESERVATION_TIME_MIN <= available_time <= RESERVATION_TIME_MAX:
                print("Time %s found. Clicking button" % span2.text)
                item.click()
                return True

        return False


def month_num(month):
    # TODO error handling
    return MONTH_NUM[month.lower()]


def run_reservation():
    r = ReserveTFL()
    r.reserve()
    r.teardown()


def execute_reservations():
    threads = []
    for _ in range(NUM_THREADS):
        t = threading.Thread(target=run_reservation)
        threads.append(t)
        t.start()
        time.sleep(THREAD_DELAY_SEC)

    for t in threads:
        t.join()


def continuous_reservations():
    while True:
        execute_reservations()


parser = argparse.ArgumentParser(description='Description of your program')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
parser.add_argument('--day', type=str, help='Specify the day to search for')
args = parser.parse_args()

if args.debug:
    RESERVATION_URI = RESERVATION_URI_TEST
else:
    RESERVATION_URI = RESERVATION_URI_PROD

if args.day:
    RESERVATION_DAY = args.day

continuous_reservations()