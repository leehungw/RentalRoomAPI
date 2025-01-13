# import datamanager
from fastapi import FastAPI
import uvicorn
import nest_asyncio
from pyngrok import ngrok
import userinput
from geopy.distance import great_circle 
import schedule
import powercut
import time
from google.cloud import firestore
import random
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from firebase_admin import credentials, firestore
import firebase_admin

# dm = datamanager.DataManager()

app = FastAPI()
token = '2hmXBdAHRPJEqCV38bc3S1l7eQ9_6RSpPDYEgRDfnWx8BEoct'

# Initialize Firestore


@app.get('/')
def read_root():
    return {'message': 'recommend model api'}

@app.post('/recommend/')
def recommend(user_input: userinput.UserInput):
    db = firestore.client()
    # Fetch rooms from Firebase
    rooms_ref = db.collection('Rooms')
    docs = rooms_ref.stream()
    rooms = [doc.to_dict() for doc in docs]

    # Create DataFrame
    df = pd.DataFrame(rooms)

    # Preprocess features
    def preprocess_features(row):
        return " ".join(row["tags"]) + " " + " ".join(row["amenities"]) + " " + row["room_type"]

    df["features"] = df.apply(preprocess_features, axis=1)

    # TF-IDF Vectorization
    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(df["features"])

    # User preferences
    user_features = " ".join(user_input.tags) + " " + " ".join(user_input.amenities) + " " + user_input.room_type
    user_tfidf = tfidf.transform([user_features])

    # Calculate similarity scores
    similarity_scores = cosine_similarity(user_tfidf, tfidf_matrix)
    df["similarity_score"] = similarity_scores[0]

    # Filter by budget
    filtered_df = df[df["price"].apply(lambda x: x["room"] <= user_input.desiredPrice)]

    # Sort and get top 5 recommendations
    recommended_rooms = filtered_df.sort_values("similarity_score", ascending=False).head(5)

    # Return top 5 room IDs
    response = userinput.Response(recommend=recommended_rooms["roomId"].tolist())
    return response

ngrok.set_auth_token(token = token)
ngrok_tunnel = ngrok.connect("3000")
print('Public URL:', ngrok_tunnel.public_url)
nest_asyncio.apply()
# uvicorn.run(app, port=3000)

pc = powercut.PowerCutDataScrap()

def reloadPowerCut():
  pc.resetPowerCutCollection(col_name="PowerCut", batch_size=3)
  pc.scrapData()
  pc.uploadDataToFirebase()

reloadPowerCut()
schedule.every().day.at("06:00").do(reloadPowerCut)

while True:
  schedule.run_pending()
  time.sleep(60)