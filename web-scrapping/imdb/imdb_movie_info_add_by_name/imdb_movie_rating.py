import requests
from bs4 import BeautifulSoup
import webbrowser as wb
import json

movies={}
#"http://www.imdb.com/find?ref_=nv_sr_fn&q=the+matrix&s=all"
first_part="http://www.imdb.com/find?ref_=nv_sr_fn&q="
end_part="&s=all"
movie_name= str(input("Name of the movie is : "))
movie_name=movie_name.replace("  "," ")
movie_name=movie_name.replace(" ","+")
movie_query=first_part+movie_name+end_part

page=requests.get(movie_query)
soup=BeautifulSoup(page.text,"html.parser")
table=soup.find("table","findList")
all_links=table.find_all("a")
movie_link = all_links[0].get("href") 
movie_link="http://www.imdb.com"+movie_link
movie_link=(movie_link.split("?"))[0]

movie_list=soup.find_all("td","result_text")
movie_name=movie_list[0].find("a").string

page=requests.get(movie_link)
#wb.open_new_tab(movie_link)
movie_id=(movie_link.split("/"))[-2]
soup=BeautifulSoup(page.text,"html.parser")


title_block=soup.find("div","title_block")

ratingValue=title_block.find("div","ratingValue")
rating_bar=float((ratingValue.find_all('span'))[0].string)
no_of_user_rated=((title_block.find("div","imdbRating")).find("a")).find("span").string
no_of_user_rated=int(no_of_user_rated.strip().replace(",",""))
year=((title_block.find("div","title_wrapper")).find("h1")).find("a").string
year=int(year.strip())
subtext=title_block.find("div","subtext")
all_a=subtext.find_all("a")
i=0
genres=[]
while i<len(all_a)-1:
    genres.append(all_a[i].string)
    i=i+1
    
cast_link=movie_link+"fullcredits"
user_rating_link=movie_link+"ratings"
review_link=movie_link+"reviews"

page=requests.get(review_link)
soup=BeautifulSoup(page.text,"html.parser")
review=soup.find_all("div","imdb-user-review")
i=0
reviews=[]
while i<len(review):
    title=(review[i].find("a","title").string).replace("\n","")
    #content=review[i].find("div","text").string
    reviews.append(title)
    i=i+1

movies[movie_id]={
    "imdb_id":movie_id,
    "movie_name":movie_name,
    "imdb_link":movie_link,
    "genres":genres,
    "rating_bar":rating_bar,
    "no_of_user_rated":no_of_user_rated,
    "reviews":reviews
}


with open('movies.json') as f:
        f.seek(0)
        first_char = f.read(1)
        if not first_char:
            with open('movies.json', 'w') as f:
                json.dump(movies, f)
        else:
            f.seek(0)
            with open('movies.json') as f:
                data = json.load(f)
                data.update(movies)
                with open('movies.json', 'w') as f:
                    json.dump(data, f)
                
print("Written")
f.close()






