import requests
import os
import json
import subprocess
from bs4 import BeautifulSoup
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from seleniumwire.utils import decode as sw_decode
import seleniumwire.undetected_chromedriver.v2 as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import sys
import re
import signal
import time
import tempfile
import pwinput

#Crash prevent attempt
def myexcepthook(type, value, tb):
    print(value)
    s_exit()

sys.excepthook = myexcepthook

def signal_handler(sig, frame):
    s_exit()

signal.signal(signal.SIGINT, signal_handler)

def s_exit():
    print('\nBye :)')
    global driver
    driver.quit()
    quit()

def suppress_exception_in_del(uc):
    old_del = uc.Chrome.__del__

    def new_del(self) -> None:
        try:
            old_del(self)
        except:
            pass
    
    setattr(uc.Chrome, '__del__', new_del)

suppress_exception_in_del(uc)

def selenium_init():
    print('Initializing selenium')

    options = uc.ChromeOptions()
    options.page_load_strategy = 'eager'
    
    options.add_argument('--user-data-dir=' + os.path.abspath(os.getcwd()) + '\\UserData')
    options.add_argument('--headless')
    options.add_argument('--disable-features=Translate')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--mute-audio")
    options.add_argument('--log-level=3')
    driver = uc.Chrome(options=options)
    
    return driver
    
def s_request(url, driver):
    driver.get(url)
    
    try:
        driver.wait_for_request('dash', timeout=60)
    except:
        print('Page load took too much time, please try again')
        s_exit()
    
    return driver
  
def choose_res(driver, choice=None):
    print('Setting resolution')
    
    actions = ActionChains(driver)
    
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "iqp-stream")))
    definition = driver.find_element(by=By.CLASS_NAME, value="iqp-btn-definition")
    
    actions.move_to_element(definition).perform()
    
    allres = definition.find_elements(by=By.CLASS_NAME, value="iqp-stream")
    
    if choice is None:
        i = 1
        for r in allres:
            print(str(i) + '. ' + r.text)
            i+=1
        
        choice = int(input('\nChoose resolution: '))
    
    r = allres[choice-1]
    
    parent = r.find_element(by=By.XPATH, value='..')
    p_class = parent.get_attribute("class")
    
    if 'selected' not in p_class:
        actions.move_to_element(definition).perform()
        actions.move_to_element(r).perform()
        
        del driver.requests
        r.click()
        
        try:
            driver.wait_for_request('dash', timeout=5)
        except:
            print('No dash request')
            
    return choice
  
def get_title(driver):
    title_class = BeautifulSoup(driver.page_source, 'html.parser').find("span", {"class": "intl-album-title-word-wrap"})
    return title_class.find("span").text
    
def get_episodes(driver):
    episode_class = BeautifulSoup(driver.page_source, 'html.parser').find("ul", {"class": "intl-episodes-list"})
    
    episodes = []
    
    children = episode_class.findChildren("li" , recursive=False)
    for c in children:
        a = c.findAll("a")[-1]
    
        e = {}
        e['title'] = a.text
        e['href'] = a['href'].replace('//', 'https://')
        
        episodes.append(e)
        
    return episodes

def extract_dash(driver):
    print('Extracting m3u8 from dash response')

    r = {}
    
    for request in driver.requests:
        if 'dash' in request.url:
            if len(request.response.body) != 0:
                body = sw_decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity')).decode()
    
    if body is None:
        print('Failed to extract dash response from url, please try again')
        return
    
    body = json.loads(body)
    program = body['data']['program']
    video = program['video']
    
    for v in video:
        if 'm3u8' in v:
            m3u8 = v['m3u8']
    
    
    with open('temp.m3u8', "w+") as file:
        file.write(m3u8)
        print('Saved temp m3u8 to file')
        
    print('Extracting subtitles from dash response')
    
    #Subtitles
    stl = program['stl']
    
    subtitles = []
    
    for s in stl:
        a = {}
        a['lang'] = s['_name']
        a['url'] = 'https://meta.video.iqiyi.com' + s['srt']
        subtitles.append(a)
        
    r['subtitles'] = subtitles
    
    return r
   
def slugify(value, allow_unicode=False):
    value = str(value)
    value = re.sub(r'[^\w\s-]', '', value)
    return re.sub(r'[-\s]+', '.', value).strip('-_')
            
def dl_media(foldername, filename):
    dash_response = extract_dash(driver)

    foldername = slugify(foldername)
    filename = slugify(filename)

    proc_list = ['N_m3u8DL-RE.exe', '--save-dir', 'Downloads/' + foldername, '--tmp-dir', 'Temp/', '--save-name', filename, './temp.m3u8', '-M', 'mp4']
    print('Downloading')
    subprocess.run(proc_list)
    
    os.remove('./temp.m3u8')
    
    print('Downloading subtitles')
    subtitles = dash_response['subtitles']
    for s in subtitles:
        lang = s['lang']
        sub_url = s['url']
        
        subpath = '.\\Downloads\\' + foldername + '\\' + filename + ' ' + lang + '.srt'
        
        f = open(subpath, "w", encoding="utf-8")
        f.write(requests.get(sub_url).text)
        f.close()
          
    print('Done')

def do_login(driver):
    print('Checking user account')
    driver.get('https://www.iq.com/')
    
    #Double load to get rid of usless ad
    driver.get('https://www.iq.com/')

    actions = ActionChains(driver)

    logged_in = False

    for cookie in driver.get_cookies():
        if cookie['name'] == 'I00002':
            logged_in = True

    if logged_in:
        print('Already logged in')
    else:
        print('Please log in')
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.userImg-wrap > div")))
        actions.move_to_element(driver.find_element(by=By.CSS_SELECTOR, value='div.userImg-wrap > div')).perform()
        driver.find_element(by=By.CSS_SELECTOR, value='div.no-login-list > div > span').click()
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.passport-entry-wrapper > div:nth-child(2)")))
        driver.find_element(by=By.CSS_SELECTOR, value='div.passport-entry-wrapper > div:nth-child(2)').click()
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.passport-input > div:nth-child(1) > div > label > input")))
        username = input('Enter email/username: ')
        u_input = driver.find_element(by=By.CSS_SELECTOR, value='div.passport-input > div:nth-child(1) > div > label > input')
        driver.execute_script("arguments[0].value = '" + username + "';", u_input)
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.passport-input > div:nth-child(2) > div > div > label > input")))
        password = pwinput.pwinput('Enter password: ')
        p_input = driver.find_element(by=By.CSS_SELECTOR, value='div.passport-input > div:nth-child(2) > div > div > label > input')
        driver.execute_script("arguments[0].value = '" + password + "';", p_input)
        p_input.click()
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.passport-btn.passport-btn-primary.hover30")))
        login_button = driver.find_element(by=By.CSS_SELECTOR, value='div.passport-btn.passport-btn-primary.hover30')
        login_button.click()
        
        try:
            driver.wait_for_request('loginMode', timeout=5)
        except:
            print('Login failed')
            s_exit()
            
        last_check = False

        for cookie in driver.get_cookies():
            if cookie['name'] == 'I00002':
                last_check = True
                
        if last_check:
            print('Login successful')
        else:
            print('Login failed')
            s_exit()
            
    driver.add_cookie({"name":"intl_playbackRate","domain":".iq.com","value":"1"})

try:
    os.rmdir('Temp')
except:
    pass

driver = selenium_init()
do_login(driver)

url = input('Enter iq.com url: ').replace('album', 'play')
print('Opening provided url')
s_request(url, driver)

main_title = get_title(driver)
print('Found title: ' + main_title)
res = choose_res(driver)

episodes = get_episodes(driver)

if len(episodes) > 1:
    print('Detected series')
    
    c = input('Do you want to download the entire series? (y/n): ')
    
    if c.lower() != 'y':
        print('Single episode download selected')
        dl_media(main_title, main_title)
        s_exit()
        
    for e in episodes:
        print(e['title'])
        s_request(e['href'], driver)
        choose_res(driver, res)
        dl_media(main_title, e['title'])
        
    s_exit()
    
else:
    print('Detected single')
    
dl_media(main_title, main_title)
s_exit()