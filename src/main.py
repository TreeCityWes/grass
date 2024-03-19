from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, NoSuchDriverException
import time
import requests
import os
import re
import base64
from flask import Flask
import hashlib
import sys

extensionId = 'ilehaonighjijnmpnagapkhpcdbhclfg'
CRX_URL = "https://clients2.google.com/service/update2/crx?response=redirect&prodversion=98.0.4758.102&acceptformat=crx2,crx3&x=id%3D~~~~%26uc&nacl_arch=x86-64"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"

try:
    USER = os.environ['GRASS_USER']
    PASSW = os.environ['GRASS_PASS']
except KeyError:
    print('Environment variables for GRASS_USER and GRASS_PASS are not set.')
    sys.exit(1)

try:
    ALLOW_DEBUG = os.environ.get('ALLOW_DEBUG', 'False') == 'True'
except KeyError:
    ALLOW_DEBUG = False

if ALLOW_DEBUG:
    print('Debugging is enabled! This will generate a screenshot and console logs on error!')

def download_extension(extension_id):
    url = CRX_URL.replace("~~~~", extension_id)
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, stream=True, headers=headers)
    with open("grass.crx", "wb") as fd:
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)
    if ALLOW_DEBUG:
        md5 = hashlib.md5(open('grass.crx', 'rb').read()).hexdigest()
        print('Extension MD5: ' + md5)

def generate_error_report(driver):
    if not ALLOW_DEBUG:
        return
    driver.save_screenshot('error.png')
    logs = driver.get_log('browser')
    with open('error.log', 'w') as f:
        for log in logs:
            f.write(str(log) + '\n')
    url = 'https://imagebin.ca/upload.php'
    files = {'file': ('error.png', open('error.png', 'rb'), 'image/png')}
    response = requests.post(url, files=files)
    print(response.text)
    print('Error report generated! Provide the above information to the developer for debugging purposes.')

print('Downloading extension...')
download_extension(extensionId)
print('Downloaded! Installing extension and driver manager...')

options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--disable-dev-shm-usage")
options.add_argument('--no-sandbox')
options.add_extension('grass.crx')

print('Installed! Starting...')
try:
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    print('WebDriver started successfully.')
except Exception as e:
    print('Could not start WebDriver:', e)
    exit()

print('Started! Logging in...')
driver.get('https://app.getgrass.io/')

sleep = 0
while True:
    try:
        driver.find_element('xpath', '//*[@name="user"]')
        driver.find_element('xpath', '//*[@name="password"]')
        driver.find_element('xpath', '//*[@type="submit"]')
        break
    except:
        time.sleep(1)
        sleep += 1
        if sleep > 15:
            print('Could not load login form! Exiting...')
            generate_error_report(driver)
            driver.quit()
            sys.exit()

user = driver.find_element('xpath', '//*[@name="user"]')
passw = driver.find_element('xpath', '//*[@name="password"]')
submit = driver.find_element('xpath', '//*[@type="submit"]')

user.send_keys(USER)
passw.send_keys(PASSW)
submit.click()

sleep = 0
while True:
    try:
        driver.find_element('xpath', '//*[contains(text(), "Dashboard")]')
        break
    except:
        time.sleep(1)
        sleep += 1
        if sleep > 30:
            print('Could not login! Double Check your username and password! Exiting...')
            generate_error_report(driver)
            driver.quit()
            sys.exit()

print('Logged in! Waiting for connection...')
driver.get('chrome-extension://' + extensionId + '/index.html')

sleep = 0
while True:
    try:
        driver.find_element('xpath', '//*[contains(text(), "Open dashboard")]')
        break
    except:
        time.sleep(1)
        sleep += 1
        if sleep > 30:
            print('Could not load connection! Exiting...')
            generate_error_report(driver)
            driver.quit()
            sys.exit()

print('Connected! Starting API...')
app = Flask(__name__)

@app.route('/')
def get():
    try:
        network_quality = driver.find_element('xpath', '//*[contains(text(), "Network quality")]').text
        network_quality = re.findall(r'\d+', network_quality)[0]
    except:
        network_quality = 'Unknown'
        print('Could not get network quality!')
        generate_error_report(driver)

    try:
        token_element = driver.find_element('xpath', '//*[@alt="token"]/following-sibling::div')
        epoch_earnings = token_element.text
    except Exception as e:
        epoch_earnings = 'Unknown'
        print('Could not get earnings!')
        generate_error_report(driver)

    badges = driver.find_elements('xpath', '//*[@class="chakra-badge"]')
    connected = any('Connected' in badge.text for badge in badges)

    return {'connected': connected, 'network_quality': network_quality, 'epoch_earnings': epoch_earnings}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)





