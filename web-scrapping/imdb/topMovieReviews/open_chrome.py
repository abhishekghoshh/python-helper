from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time 
import os,sys
import json

link="https://smallpdf.com/compress-pdf"
driver=webdriver.Chrome(os.path.join(os.getcwd(),"chromedriver.exe"))
driver.get(link)
