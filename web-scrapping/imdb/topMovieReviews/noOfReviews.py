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

start="https://www.imdb.com/title"
end="reviews"

f=open("noOfReviews.json","a+")
f.close()

f=open("top250Movies.json","r")
x=""
for line in f:
	x=line
movies= json.loads(x)

reviews={}

chrome_options = Options()
chrome_options.add_argument("--incognito")
driver=webdriver.Chrome(os.path.join(os.getcwd(),"chromedriver.exe"),chrome_options=chrome_options)

for key in movies:
	id=(movies[key])["id"]
	link=start+"/"+id+"/"+end
	driver.get(link)
	soup=BeautifulSoup(driver.page_source, 'lxml')
	no=soup.find("div",class_="header").find("span").string
	no=(no[:-8]).split(",")
	no= int("".join(no))
	reviews[key]={
	"imdb_link":link,
	"noOfReviews":no
	}


driver.close()

try:
	with open('noOfReviews.json') as f:
	        f.seek(0)
	        first_char = f.read(1)
	        if not first_char:
	            with open('noOfReviews.json', 'w') as f:
	                json.dump(reviews, f)
	        else:
	            f.seek(0)
	            with open('noOfReviews.json') as f:
	                data = json.load(f)
	                data.update(reviews)
	                with open('noOfReviews.json', 'w') as f:
	                    json.dump(data, f)
except Exception as e:
	print(e)