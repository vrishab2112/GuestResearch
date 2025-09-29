import os, requests
key ="AIzaSyB9Idtjje00e0C7t3jmtYzhOxFs9X2hdFY"
video = "dQw4w9WgXcQ"
r = requests.get("https://www.googleapis.com/youtube/v3/commentThreads", params={"part":"snippet","maxResults":1,"videoId":video,"key":key}, timeout=30)
print(r.status_code, r.json())