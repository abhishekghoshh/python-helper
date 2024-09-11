import os,json
import numpy as np
os.chdir(r"C:\Users\ASUS\Desktop\python\my_project\imdb project\top250MovieReviews")
f=open("reviews.json","r")
for line in f:
        line=json.loads(line)
keys=list(line.keys())
rated_reviews=[]
nonrated_reviews=[]
rated=[]
nonrated=[]
x=0
y=0
for key in line:
        reviews=line[key]
        for review in reviews:
                if(review['rating']!=None):
                        rated_reviews.append(np.array([review['review'],review['rating']],dtype=object))
                        x=x+1
                else:
                        nonrated_reviews.append(review['review'])
                        y=y+1
        rated.append(x)
        nonrated.append(y)
        x=0
        y=0
rated_reviews=np.array(rated_reviews,dtype=object)
nonrated_reviews=np.array(nonrated_reviews,dtype=object)
#rated=np.array(rated)
#nonrated=np.array(nonrated)
#total=rated+nonrated
#probablity=rated/total
print(len(line.keys()))
