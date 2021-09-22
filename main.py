#!/usr/bin/env python3

# -*- -*- -*- -*- -*- -*- -*- -*- -*- -*-
#
# Copyright (c) 2021 Gianni Favilli @fvlgnn
# MIT License.
#
# Description: SPID Test Automation
#
# Date: 14/06/2021
#
# Update: 22/09/2021
#
# coding: utf-8
#
# -*- -*- -*- -*- -*- -*- -*- -*- -*- -*-

import sys, urllib3, os, chromedriver_binary

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import TimeoutException

from time import sleep
from datetime import datetime

import argparse
from dotenv import load_dotenv

urllib3.disable_warnings()

yep = ['true', '1', 't', 'y', 'yes', 'yep', 'ok', 'si', 'sì', 's', 'vero', 'vera', 'v', 'de', 'dè']

#NOTE CONFIG WITH ARGS ----

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('--first', type=int, default=1, help="Test di partenza", required=False)
parser.add_argument('--last', type=int, default=111, help="Test di arrivo", required=False)
parser.add_argument('--exclude', type=int, default=[5,6,7,50,101,102], nargs='+', help="Test da escludere (es. 5 6 7). Di default i test che AgID non verifica", required=False)
parser.add_argument('--custom-test', type=int, nargs='+', help="Esegue solo i test nella lista (es. 1 32 94 95 96 111)", required=False)

parser.add_argument('--url', type=str, default='https://localhost:8443', help="URL di partenza, la webapp con integrato il login con SPID", required=False)
parser.add_argument('--meta', type=str, default='https://localhost:8443/spid-sp-metadata', help="URL del metadata del tuo SP", required=False)
parser.add_argument('--target', type=str, default='TestSpidWebAppLoggedIn', help="HTML <title> della pagina di destinazione", required=False)

parser.add_argument('--custom-user', type=str, default='false', help="True modifica CF e Email nella Response come --cf e --email, False come da test.json", required=False)
parser.add_argument('--fiscal-number', type=str, default='TINIT-GDASDV00A01H501J', help="Codice fiscale con prefisso TINIT- dell'utente di test", required=False)
parser.add_argument('--email', type=str, default='spid.tech@agid.gov.it', help="Email dell'utente di test", required=False)
parser.add_argument('--level', type=int, default=1, help="Livello SPID. Usa 1, 2 o 3", required=False)

parser.add_argument('--delay', type=float, default=0.4, help="Tempo tra un'azione e l'altra", required=False)
parser.add_argument('--logout', type=str, default='true', help="True, forza il logout se la sessione è attiva", required=False)
parser.add_argument('--container', type=str, default='true', help="True se eseguito da dentro un container, False visualizza il browser all'utente per debug", required=False)
parser.add_argument('--logs', type=str, default='false', help="False per live usa stdout, True per debug scrive logs su FS", required=False)

args = parser.parse_args()

write_logs = args.logs.lower() in yep
is_container = args.container.lower() in yep
is_custom_user  = args.custom_user.lower() in yep
logout  = args.logout.lower() in yep

test_first = args.first
test_last = args.last
test_exclude = args.exclude
test_custom = args.custom_test

siteurl = args.url
metadata = args.meta
target_page_title = args.target

spid_level = args.level

fiscal_number = args.fiscal_number
email = args.email

delay = args.delay

#  ----

#NOTE CONFIG WITH DOT-ENV or SYSTEM ENVIRONMENT (Questo potrebbe sovrascrive alcuni ARGS) ----

load_dotenv()

if "USE_ENV_VAR" in os.environ:

    use_env_var = os.getenv('USE_ENV_VAR').lower() in yep

    if use_env_var:

        write_logs = os.getenv('LOGS').lower() in yep
        is_container = os.getenv('CONTAINER').lower() in yep
        is_custom_user  = os.getenv('CUSTOM_USER').lower() in yep
        logout  = os.getenv('LOGOUT').lower() in yep

        test_first = int(os.getenv('FIRST'))
        test_last = int(os.getenv('LAST'))
        test_exclude = [int(x) for x in os.getenv('EXCLUDE').split()]
        test_custom = [int(x) for x in os.getenv('CUSTOM_TEST').split()]

        siteurl = os.getenv('URL')
        metadata = os.getenv('META')
        target_page_title = os.getenv('TARGET')

        spid_level = int(os.getenv('LEVEL'))

        fiscal_number = os.getenv('FISCAL_NUMBER')
        email = os.getenv('EMAIL')

        delay = int(float(os.getenv('DELAY')))

#  ----

# LOGS or STDOUT

if write_logs:
    import logging, logging.handlers
    scriptPath = os.path.dirname(__file__)
    logDir = os.path.join(scriptPath, 'logs')
    logsFile = os.path.join(logDir, 'reports.log')
    formatter = logging.Formatter('%(message)s')
    handler = logging.handlers.TimedRotatingFileHandler(logsFile, when='midnight', interval=1, backupCount=8)
    handler.suffix = "%y%m%d" + ".log"
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def logme(message, level = 'info'):
    if write_logs:
        log = str(level.upper()) + ' - ' + str(message)
        logger.info(log)
    else:
        log = str(datetime.now()) + ': ' + str(level.upper()) + ' - ' + str(message)        
    print(log)
    # if is_container:
    #     # sys.stdout = open(1, 'w', encoding='utf-8', closed=False)
    #     sys.stdout.flush()

# ----

# NOTE MAIN ----

def main():       

    try:

        next = True

        if test_custom is None or test_custom != 0:
            tests = [i for i in range(test_first, test_last + 1) if i not in test_exclude]
        else:
            tests = test_custom

        if is_container:
            logme("Integration Tests Configurations\n")
            logme(f"tests: {tests}")
            logme(f"siteurl: {siteurl}")
            logme(f"metadata: {metadata}")
            logme(f"target_page_title: {target_page_title}")
            logme(f"spid_level: {spid_level}\n")
            logme("End Show Configurations\n")

        logme(f"TEST Started ({datetime.now()}) **** ---- **** ---- **** ---- **** ----\n")           

        for test in tests:

            if next:

                chrome_options = webdriver.ChromeOptions()
                chrome_options.add_argument("incognito")
                chrome_options.add_argument("disable-web-security")
                chrome_options.add_argument("start-maximized")
                chrome_options.add_argument("ignore-certificate-errors-spki-list")
                chrome_options.add_argument("ignore-certificate-errors")
                    
                if is_container:
                                  
                    chrome_options.add_argument("disable-gpu")
                    chrome_options.add_argument("no-sandbox")
                    chrome_options.add_argument("disable-dev-shm-usage")
                    chrome_options.add_argument("headless")
                    chrome_options.add_argument("window-size=1920,1080")

                driver = webdriver.Chrome(options=chrome_options)

                try:

                    driver.get(siteurl)
                    sleep(delay)

                    #NOTE PERSONALIZZAZIONE. Da modificare in base alla propria webapp
                    sleep(delay)
                    driver.find_element_by_xpath("//html").click()
                    sleep(delay)
                    driver.find_element_by_xpath('//a[@href="#spid"]').click()
                    sleep(delay * 2)
                    driver.find_element_by_partial_link_text("Entra con SPID").click()
                    sleep(delay)
                    driver.find_element_by_id("zocial-spid-tester").click()
                    sleep(delay)
                    #NOTE fine PERSONALIZZAZIONE.

                    try:
                        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//input[@placeholder="Username"]')))
                    except TimeoutException:
                       logme(f"TEST {test} - Timeout SPID Validator IdP", "error")
                       next = False

                    sleep(delay)
                    driver.find_element_by_xpath('//input[@placeholder="Username"]').click()
                    sleep(delay)
                    driver.find_element_by_xpath('//input[@placeholder="Username"]').send_keys("validator")
                    sleep(delay)
                    driver.find_element_by_xpath('//input[@placeholder="Password"]').click()
                    sleep(delay)
                    driver.find_element_by_xpath('//input[@placeholder="Password"]').send_keys("validator")
                    sleep(delay)
                    driver.find_element_by_xpath("//button[text()='Login']").click()
                    sleep(delay)

                    #NOTE Aggiornamento del Metadata SP
                    try:
                        driver.find_element_by_id("Worksave").is_displayed()                
                        if test == 1:
                            driver.find_element_by_class_name("worksave-img-new").click()
                            sleep(delay * 2)
                            driver.switch_to.alert.accept()
                            sleep(delay * 3)
                            driver.find_element_by_xpath("//a[text()='Metadata SP']").click()
                            sleep(delay * 3)
                            driver.find_element_by_partial_link_text("Download").click()
                            sleep(delay)
                            driver.find_element_by_xpath('//input[@class="metadata"]').send_keys(metadata)
                            sleep(delay)
                            driver.find_element_by_xpath("//button[text()='Download']").click()
                        else:
                            driver.find_element_by_class_name("worksave-img-continue").click() 
                    except NoSuchElementException:
                        sleep(delay * 3)
                        driver.find_element_by_xpath("//a[text()='Metadata SP']").click()
                        sleep(delay * 3)
                        driver.find_element_by_partial_link_text("Download").click()
                        sleep(delay)
                        driver.find_element_by_xpath('//input[@class="metadata"]').send_keys(metadata)
                        sleep(delay)
                        driver.find_element_by_xpath("//button[text()='Download']").click()
                        pass

                    sleep(delay * 3)
                    driver.find_element_by_xpath("//a[text()='Response']").click()
                    sleep(delay * 3)
                    driver.find_element_by_partial_link_text("Check Response").click()
                    sleep(delay)

                    sleep(delay)
                    driver.find_element_by_id("react-select-2--value").click()
                    sleep(delay)
                    driver.find_element_by_xpath('//input[@id="response-select"]').send_keys(f"{test}.")
                    sleep(delay)
                    driver.find_element_by_xpath('//input[@id="response-select"]').send_keys(Keys.TAB)
                    sleep(delay * 2)
                    expected_result = driver.find_element_by_class_name("test-description").text
                    key_result = expected_result.split(" ")[-1].lower()
                    sleep(delay)

                    #TODO aggiungere azione per premre il pulsante di test eseguito

                    if is_custom_user:

                        driver.execute_script("window.scrollTo(0, 1800)")
                        sleep(delay)
                        driver.find_element_by_xpath('//input[@placeholder="fiscalNumber"]').click()
                        sleep(delay)
                        driver.find_element_by_xpath('//input[@placeholder="fiscalNumber"]').clear()
                        sleep(delay)
                        driver.find_element_by_xpath('//input[@placeholder="fiscalNumber"]').send_keys(fiscal_number)
                        sleep(delay * 2)

                        driver.execute_script("window.scrollTo(0, 1800)")
                        sleep(delay)
                        driver.find_element_by_xpath('//input[@placeholder="email"]').click()
                        sleep(delay)
                        driver.find_element_by_xpath('//input[@placeholder="email"]').clear()
                        sleep(delay)
                        driver.find_element_by_xpath('//input[@placeholder="email"]').send_keys(email)
                        sleep(delay * 2)

                        driver.execute_script("window.scrollTo(0, 0)")
                        sleep(delay)

                    sleep(delay)
                    driver.find_element_by_xpath('//input[@type="submit"]').click()
                    sleep(delay)

                    sleep(delay * 4)                

                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[1])
                    sleep(delay)
                    title_page = driver.title
                    
                    try:
                        spid_log_msg = ""
                        if test in range(94,97):
                            spid_log_msg = f"\nSPID Level set for test: {spid_level}"
                        if key_result == "ok" or key_result == "request.":
                            if title_page == target_page_title or title_page == "Error - Utente Non Autorizzato":
                                logme(f"TEST_{test:03}\nTest description: {expected_result}{spid_log_msg}\nResult: Web App (Title page: {title_page})\n", "passed")
                                #NOTE PERSONALIZZAZIONE. Da modificare in base alla propria webapp
                                if title_page == target_page_title and logout:
                                    try:
                                        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '//button[@id="dropdownMenuButton"]')))
                                        sleep(delay)
                                        driver.find_element_by_xpath('//button[@id="dropdownMenuButton"]').click()
                                        sleep(delay)
                                        driver.find_element_by_xpath("//a[text()='Logout']").click()
                                        sleep(delay * 2)
                                    except TimeoutException:
                                        pass
                                #NOTE fine PERSONALIZZAZIONE.
                            else:
                                logme(f"TEST_{test:03}\nTest description: {expected_result}{spid_log_msg}\nTitle page: {title_page}\n", 'not passed')
                        else:
                            error_message = driver.find_element_by_id("kc-error-message").text.splitlines()[0]
                            logme(f"TEST_{test:03}\nTest description: {expected_result}{spid_log_msg}\nResult description: {error_message}\n", "passed")
                    except NoSuchElementException:
                        print("sono qui")
                        logme(f"TEST_{test:03}\nTest description: {expected_result}{spid_log_msg}\n{spid_log_msg}Incorrect expected page (Title page: {title_page})\n", "not passed")

                except NoSuchElementException as err:
                    logme("TEST " + str(test) + " " + str(err).splitlines()[0], "error")
                    next = False
            
                driver.quit()

    except Exception as e:
        logme(e, 'error')
    finally:
        # driver.quit()
        logme(f"TEST Finished ({datetime.now()}) **** ---- **** ---- **** ---- **** ----\n\n")
        sleep(delay * 2)
        sys.exit()

if __name__ == '__main__':
    main()