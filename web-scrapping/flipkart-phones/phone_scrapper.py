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
import mysql.connector

chrome_options = Options()
chrome_options.add_argument("--incognito")
os.chdir("../")
driver=webdriver.Chrome(os.path.join(os.getcwd(),"chromedriver.exe"),chrome_options=chrome_options)
os.chdir(os.path.join(os.getcwd(),"phone"))

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  passwd="",
  database="clg_project"
)

mycursor = mydb.cursor()
try:
	mycursor.execute("create table phone (id int(10) NOT NULL AUTO_INCREMENT,brand varchar(20) Not NULL,price int(10) Not NULL,quantity int(10) DEFAULT 10,img varchar(255) Not NULL,comming int(1) NOT NULL,description text NOT NULL,rating varchar(5) NOT NULL,camera varchar(5) NOT NULL,display varchar(5) NOT NULL,battery varchar(5) NOT NULL,category_id int(5) NOT NULL,PRIMARY KEY(id),FOREIGN KEY(category_id) REFERENCES category(category_id))")
except Exception as e:
	print(e)
f=open("phone_.sql","a+")

def getLinks(url):
	links=[]
	for i in range(1,40):
		driver.get(url+str(i))
		soup=BeautifulSoup(driver.page_source, 'lxml')
		try:
			images=soup.find_all("a", class_="_31qSD5")
			for item in images:
				links.append(item['href'])
		except Exception as e:
			pass
	return links

def getContents(link):
	driver.get("https://www.flipkart.com"+link)
	try:
		WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.uSQV49'))).click()
		comming=0
	except Exception as e:
		WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button._17GYlK'))).click()
		WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.uSQV49'))).click()
		comming=1
	try:
		soup=BeautifulSoup(driver.page_source, 'lxml')
		brand=soup.find_all('a',class_="_1KHd47")
		brand=((brand[3].string).split(" "))[0]
		price=soup.find('div',class_="_3qQ9m1").string
		price=int("".join(price.split(","))[1:])
		key_list=soup.find_all('td',class_="_3-wDH3")
		value_list=soup.find_all('li',class_="_3YhLQA")
		description=""
		for i in range(len(key_list)):
			description=description+key_list[i].string+"@"+value_list[i].string+"@"
		img_div=soup.find('div',class_="_3iN4zu")
		img=img_div.find('img',class_="Yun65Y")['src']
		print(img)
		rating=soup.find('div',class_='_1i0wk8').string
		rate=soup.find_all("text",class_="PRNS4f")
		camera=rate[0].string
		battery=rate[1].string
		display=rate[2].string
		f.write("Insert into phone (price,brand,img,comming,description,rating,camera,display,battery,category_id) values({},'{}','{}',{},'{}','{}','{}','{}','{}',{});\n".format(price,brand,img,comming,description,rating,camera,display,battery,1))
	except Exception as e:
		print(e)
		pass


url="https://www.flipkart.com/search?sid=tyy%2C4io&otracker=CLP_Filters&p%5B%5D=facets.brand%255B%255D%3DMi&p%5B%5D=facets.brand%255B%255D%3DSamsung&p%5B%5D=facets.brand%255B%255D%3DOPPO&p%5B%5D=facets.brand%255B%255D%3DApple&p%5B%5D=facets.brand%255B%255D%3DHonor&p%5B%5D=facets.brand%255B%255D%3DAsus&p%5B%5D=facets.brand%255B%255D%3DGoogle&p%5B%5D=facets.brand%255B%255D%3DHTC&p%5B%5D=facets.brand%255B%255D%3DLenovo&p%5B%5D=facets.brand%255B%255D%3DMicrosoft&p%5B%5D=facets.brand%255B%255D%3DMotorola&p%5B%5D=facets.brand%255B%255D%3DMuphone&p%5B%5D=facets.brand%255B%255D%3DOnePlus&p%5B%5D=facets.brand%255B%255D%3DPOCO&p%5B%5D=facets.brand%255B%255D%3DRedmi&p%5B%5D=facets.brand%255B%255D%3DVivo&page="
mobile_links=getLinks(url=url)
for link in mobile_links:
	getContents(link)

driver.close()
f.close()


# for i in range(int(len(description)/2)):
# 	print(description[2*i-2]+" : "+description[2*i-1])


	#id,,brand,price,quantity,img,comming,description,rate,camera,display,battery,value_for_money,category_id
	# try:
	# 	mycursor.execute("Insert into phone (price,img,comming,description,rating,camera,display,battery,value_for_money,category_id) values(%d,%s,%d,%s,%s,%s,%s,%s,%s,%d)",(price,img,comming,description,rating,camera,display,battery,value_for_money,1))
	# 	mydb.commit()
	# except Exception as e:
	# 	print(e)