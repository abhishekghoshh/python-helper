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



items={}

f=open("top250movies.json","a+")
f.close()

def add_item(driver):
	soup=BeautifulSoup(driver.page_source, 'lxml')
	lister_item=soup.find_all("div", class_="lister-item")
	for item in lister_item:
		try:
			header=item.find("h3",class_="lister-item-header")

			index=int((header.find("span",class_="lister-item-index").string)[:-1])
			name=header.find("a").string
			imdb_id=header.find("a").get("href").split("/")[2]
			year=header.find("span","lister-item-year").string.strip()
			year =int(year[-5:-1])

			text_muted=item.find_all("p",class_="text-muted")

			if text_muted[0].find("span",class_="certificate"):
				certificate=text_muted[0].find("span",class_="certificate").string
			else:
				certificate=None
			runtime=text_muted[0].find("span",class_="runtime").string
			runtime=int(runtime[:-4])
			genre=text_muted[0].find("span",class_="genre").string.strip()

			ratings_bar=item.find("div",class_="ratings-bar")
			ratings=float(ratings_bar.find("strong").string)
			if ratings_bar.find("span",class_="metascore"):
				metascore =int(ratings_bar.find("span",class_="metascore").string.strip())
			else:
				metascore=None

			vote_gross=item.find("p",class_="sort-num_votes-visible").find_all("span",attrs={"name": "nv"})
			vote=vote_gross[0].string.split(",")
			vote=int("".join(vote))
			if(len(vote_gross))==2:
				gross=(str(vote_gross[1]).split("\""))[1]
				gross=int("".join(gross.split(",")))
			else:
				gross=None

			lister_item_content=item.find("div",class_="lister-item-content")
			p=(lister_item_content.find_all("p"))[-2]
			director=p.find_all("a")[0].string.strip()


			items[index]={
			"name":name,
			"id":imdb_id,
			"year":year,
			"certificate":certificate,
			"runtime":runtime,
			"genre":genre,
			"ratings":ratings,
			"metascore":metascore,
			"director":director,
			"vote":vote,
			"gross":gross}

		except Exception as e:
			print(e)
			driver.close()
			sys.exit()


chrome_options = Options()
chrome_options.add_argument("--incognito")

link="https://www.imdb.com/search/title?groups=top_250&sort=user_rating"
driver=webdriver.Chrome(os.path.join(os.getcwd(),"chromedriver.exe"),chrome_options=chrome_options)
driver.get(link)

add_item(driver)
for i in range(4):
	element = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.lister-page-next'))).click()
	add_item(driver)
driver.close()

try:
	with open('top250movies.json') as f:
	        f.seek(0)
	        first_char = f.read(1)
	        if not first_char:
	            with open('top250movies.json', 'w') as f:
	                json.dump(items, f)
	        else:
	            f.seek(0)
	            with open('top250movies.json') as f:
	                data = json.load(f)
	                data.update(items)
	                with open('top250movies.json', 'w') as f:
	                    json.dump(data, f)
except Exception as e:
	print(e)


