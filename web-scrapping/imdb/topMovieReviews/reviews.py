from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time 
import os,sys
import json,math

f=open("reviews.json","a+")
f.close()

f=open("noOfReviews.json","r")
x=""
for line in f:
	x=line
movies=json.loads(x)

chrome_options = Options()
chrome_options.add_argument("--incognito")
driver=webdriver.Chrome(os.path.join(os.getcwd(),"chromedriver.exe"),chrome_options=chrome_options)

reviews={}
movie_reviews=[]

def addReviews(driver,noOfReviews,id):
	loads=int(math.floor(noOfReviews/25))
	for _ in range(loads):
		try:
			WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.ipl-load-more__button'))).click()
		except Exception as e:
			pass
	divs=driver.find_elements_by_css_selector('div.imdb-user-review')
	for div in divs:
		try:
			rating=int(div.find_element_by_css_selector('span.rating-other-user-rating').find_element_by_tag_name('span').text)
		except Exception as e:
			rating=None
		title=div.find_element_by_css_selector('a.title').text.strip()
		review=div.find_element_by_css_selector('div.content').find_element_by_css_selector('div.text').text.strip()
		if review == None or review == "":
			div.find_element_by_css_selector("div.spoiler-warning__control").click()
			review=div.find_element_by_css_selector('div.content').find_element_by_css_selector('div.text').text.strip()
		review=review.replace("\n",". ").replace("\u0085","").replace("\u0096","").replace("\u00e9","").replace("\u00b7","").replace("\u00bd","").replace("\u00ef","")
		review=review.replace("...","").replace("..","").replace("\"","")
		movie_reviews.append({"rating":rating,"title":title,"review":review})
	reviews[str(id)]=movie_reviews


# link="https://www.imdb.com/title/tt0072890/reviews"
# noOfReviews=287
# id=link.split("/")[4]
# driver.get(link)
# addReviews(driver,noOfReviews,id)

starting_key=str(1)

for key in movies:
	if key == starting_key:
		link=movies[key]["imdb_link"]
		noOfReviews=int(movies[key]["noOfReviews"])
		id=link.split("/")[4]
		driver.get(link)
		addReviews(driver,noOfReviews,id)

		try:
			with open('reviews.json') as f:
				f.seek(0)
				first_char = f.read(1)
				if not first_char:
					with open('reviews.json', 'w') as f:
						json.dump(reviews, f)
				else:
					f.seek(0)
					with open('reviews.json') as f:
						data = json.load(f)
						data.update(reviews)
						with open('reviews.json', 'w') as f:
							json.dump(data, f)		                    
		except Exception as e:
			print(e)
		reviews={}
		movie_reviews=[]
		print(key,noOfReviews)
		starting_key=str(int(starting_key)+1)

driver.close()

