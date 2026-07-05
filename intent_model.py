"""Level-2 intent classifier for the chat assistant.

Loads example phrases from intents.json and fits a TF-IDF vector space over
them. classify() returns the nearest intent by cosine similarity with a
confidence score, or (None, score) when the best match is below the
threshold. No trained model file is stored; vectors are built in memory at
import, so adding phrases to intents.json is enough to improve it.
"""
import os
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_DATA_PATH = os.path.join(os.path.dirname(__file__), "intents.json")
DEFAULT_THRESHOLD = 0.4

def _load(path=_DATA_PATH):
    """Build the TF-IDF matrix and parallel intent labels from the dataset."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    phrases = []
    labels = []
    for intent, examples in data.items():
        for example in examples:
            phrases.append(example)
            labels.append(intent)
    # Drop English stop words so filler ("tell me", "do we") doesn't pull
    # off-topic queries toward an intent; this sharpens precision.
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(phrases)
    return vectorizer, matrix, labels

_vectorizer, _matrix, _labels = _load()

def classify(message, threshold=DEFAULT_THRESHOLD):
    """Return (intent, score) for the closest example, or (None, score) below threshold."""
    if not message or not message.strip():
        return None, 0.0
    query = _vectorizer.transform([message])
    similarities = cosine_similarity(query, _matrix)[0]
    best = int(similarities.argmax())
    score = float(similarities[best])
    if score < threshold:
        return None, score
    return _labels[best], score
