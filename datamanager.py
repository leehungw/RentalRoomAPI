import pandas as pd
import joblib
import tensorflow as tf
import numpy as np

class SingletonMeta(type):
    """
    This is a thread-safe implementation of Singleton.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class DataManager(metaclass=SingletonMeta):
    def __init__(self):
        # Load datasets
        self.rating_df = pd.read_csv('content/rating_randomized.csv')
        self.user_df = pd.read_csv('content/users.csv')
        self.room_df = pd.read_csv('content/rooms.csv')

        # Preprocess user_df
        self.user_df = self.user_df.drop(['email', 'birthDay', 'phone', 'name'], axis=1)
        self.user_df.rename(columns={'userID': 'userId'}, inplace=True)

        # Preprocess room_df
        self.room_df = self.room_df[['roomId', 'price/room', 'area', 'location', 'kind']]

        # Merge datasets
        self.df = self.rating_df.merge(self.user_df, on='userId').merge(self.room_df, on='roomId')

        # Load encoders
        self.user_encoder = joblib.load('content/user_encoder.pkl')
        self.room_encoder = joblib.load('content/room_encoder.pkl')
        self.location_encoder = joblib.load('content/location_encoder.pkl')
        self.gender_encoder = joblib.load('content/gender_encoder.pkl')
        self.kind_encoder = joblib.load('content/kind_encoder.pkl')
        self.desiredLocation_encoder = joblib.load('content/desiredLocation_encoder.pkl')

        # Load scalers
        self.roomPrice_scaler = joblib.load('content/roomPrice_scaler.pkl')
        self.area_scaler = joblib.load('content/area_scaler.pkl')
        self.desiredPrice_scaler = joblib.load('content/desiredPrice_scaler.pkl')
        self.distance_scaler = joblib.load('content/distance_scaler.pkl')
        self.priceDiff_scaler = joblib.load('content/priceDiff_scaler.pkl')

        # Load model
        # self.model = joblib.load('content/model1.joblib')

    def recommend_for_existing_user(self, user_id):
        user_index = self.user_encoder.transform([user_id])[0]
        user_data = self.user_df[self.user_df['userId'] == user_id]
        #userdata transform
        user_data['gender'] = self.gender_encoder.transform(user_data['gender'])
        user_data['desiredLocation'] = self.desiredLocation_encoder.transform(user_data['desiredLocation'])
        user_data['desiredPrice'] = self.desiredPrice_scaler.transform(user_data['desiredPrice'].values.reshape(-1, 1))
  
        user_features = user_data[['gender', 'desiredPrice', 'desiredLocation']].values
        # user_features = scaler.transform(user_features)
        all_room_ids = self.room_df['roomId'].unique()
        room_indices = self.room_encoder.transform(all_room_ids)
        room_features = self.room_df.copy()
        room_features['price/room'] = self.roomPrice_scaler.transform(room_features['price/room'].values.reshape(-1, 1))
        room_features['area'] = self.area_scaler.transform(room_features['area'].values.reshape(-1, 1))
        room_features['location'] = self.location_encoder.transform(room_features['location'])
        room_features['kind'] = self.kind_encoder.transform(room_features['kind'])
        room_features = room_features[['price/room', 'area', 'location', 'kind']].values
        # room_features = scaler.transform(room_features)
  
        predictions = self.model.predict({
            'user': tf.cast(np.asarray([user_index] * len(room_indices)), tf.float32),
            'room': tf.cast(room_indices, tf.float32),
            'user_features': tf.cast(np.repeat(user_features, len(room_indices), axis=0), tf.float32),
            'room_features': tf.cast(room_features, tf.float32)
        })
        top_indices = predictions.flatten().argsort()[-5:][::-1]
        top_room_ids = self.room_encoder.inverse_transform(room_indices[top_indices])
        return top_room_ids

    def recommend_for_new_user(self,user_input):
        ugender = self.gender_encoder.transform([user_input[0]])
        udesiredLocation = self.desiredLocation_encoder.transform([user_input[2]])
        a = pd.DataFrame({'dprice':user_input[1]}, index =[0])
        udesiredPrice = self.desiredPrice_scaler.transform(a['dprice'].values.reshape(-1, 1))
        user_features = pd.DataFrame({'gender':ugender, 'desiredPrice':udesiredPrice[0], 'desiredLocation':udesiredLocation})


        all_room_ids = self.room_df['roomId'].unique()
        room_indices = self.room_encoder.transform(all_room_ids)
        room_features = self.room_df.copy()
        room_features['price/room'] = self.roomPrice_scaler.transform(room_features['price/room'].values.reshape(-1, 1))
        room_features['area'] = self.area_scaler.transform(room_features['area'].values.reshape(-1, 1))
        room_features['location'] = self.location_encoder.transform(room_features['location'])
        room_features['kind'] = self.kind_encoder.transform(room_features['kind'])
        room_features = room_features[['price/room', 'area', 'location', 'kind']].values

        predictions = self.model.predict({
            'user': tf.cast(np.array([0] * len(room_indices)), tf.float32),  # Use a dummy user id
            'room': tf.cast(room_indices, tf.float32),
            'user_features': tf.cast(np.repeat(user_features, len(room_indices), axis=0), tf.float32),
            'room_features': tf.cast(room_features, tf.float32)
        })
        top_indices = predictions.flatten().argsort()[-5:][::-1]
        top_room_ids = self.room_encoder.inverse_transform(room_indices[top_indices])
        return top_room_ids