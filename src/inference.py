import re
import pickle
import joblib
import numpy as np
import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk import pos_tag
from nltk.corpus import stopwords as sw
from src.schemas import PropertyInput  # Ensure relative import if running via 'cd .. && uvicorn src.app:app'

# Ensure all required NLTK data is downloaded (including the newer punkt_tab)
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)
nltk.download('stopwords', quiet=True)

REPLACE_BY_SPACE = re.compile(r"[/(){}\[\]\|@,;!]")
BAD_SYMBOLS = re.compile(r"[^0-9a-z #+_]")
STOPWORDS = set(sw.words('english'))

# Load all 6 artifacts globally
try:
    model = joblib.load('model/property_price_prediction_voting.sav')
    vectorizer = pickle.load(open('model/count_vectorizer.pkl', 'rb'))
    sub_area_map = pickle.load(open('model/sub_area_price_map.pkl', 'rb'))
    amenities_map = pickle.load(open('model/amenities_score_price_map.pkl', 'rb'))
    interval_est = pickle.load(open('model/interval_est.pkl', 'rb'))
    feature_names = pickle.load(open('model/all_feature_names.pkl', 'rb'))
except Exception as e:
    print(f"Failed to load model artifacts. Ensure the 'model/' directory exists and contains all files. Error: {e}")
    raise

def get_prediction_interval(prediction, interval_est):
    """Apply interval estimate to a single prediction. Returns (lower, upper)."""
    margin = interval_est['z_score'] * interval_est['residual_std']
    return prediction - margin, prediction + margin

def predict_price(data: PropertyInput) -> dict:
    """
    Complete inference pipeline: raw input → prediction + confidence interval.
    """
    # Step 1: Text preprocessing
    text = str(data.description).lower() if data.description else ""
    text = REPLACE_BY_SPACE.sub(' ', text)
    text = BAD_SYMBOLS.sub('', text)
    text = ' '.join(w for w in text.split() if w not in STOPWORDS and len(w) > 2)

    # Step 2: POS counts
    tokens = word_tokenize(text) if text else []
    tagged = pos_tag(tokens) if tokens else []
    noun_count = sum(1 for _, t in tagged if t[1] in ('NN', 'NNS', 'NNP'))
    verb_count = sum(1 for _, t in tagged if t[1].startswith('VB'))
    adj_count = sum(1 for _, t in tagged if t[1] in ('JJ', 'JJR', 'JJS'))

    # Step 3: Target encoding lookups
    sub_area_clean = str(data.sub_area).lower().strip()
    price_by_subarea = sub_area_map.get(sub_area_clean, np.mean(list(sub_area_map.values())))

    amenity_list = [data.clubhouse, data.school, data.hospital, data.mall, data.park, data.pool, data.gym]
    amenity_score = sum(amenity_list)
    price_by_amenities = amenities_map.get(amenity_score, np.mean(list(amenities_map.values())))

    # Step 4: Vectorize description
    text_features = vectorizer.transform([text]).toarray()[0]

    # Step 5: Assemble feature vector (maintain exact training order)
    structural = [
        data.property_type, data.area,
        data.clubhouse, data.school, data.hospital, data.mall, data.park, data.pool, data.gym,
        price_by_subarea, amenity_score, price_by_amenities,
        noun_count, verb_count, adj_count
    ]
    feature_vector = np.array(structural + text_features.tolist()).reshape(1, -1)

    # Step 6: Predict (using DataFrame to satisfy Scikit-Learn feature names warning)
    feature_df = pd.DataFrame(feature_vector, columns=feature_names)
    prediction = model.predict(feature_df)[0]

    # Step 7: Confidence interval
    lower, upper = get_prediction_interval(prediction, interval_est)

    return {
        'predicted_price': round(prediction, 2),
        'lower_bound': round(max(0, lower), 2),  # Ensure lower bound doesn't go below 0
        'upper_bound': round(upper, 2),
        'features_used': feature_vector.shape[1],
    }

def get_model_info() -> dict:
    """Helper function to fetch loaded model properties for the /model/info endpoint."""
    return {
        "model_type": type(model).__name__,
        "vectorizer_vocab_size": len(vectorizer.vocabulary_),
        "interval_margin": round(interval_est['z_score'] * interval_est['residual_std'], 2)
    }