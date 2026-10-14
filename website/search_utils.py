from sentence_transformers import SentenceTransformer
import numpy as np


model = None


def _load_model():
    global model

    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")

    return model


def semantic_search(query, events):
    """
    Find the single event that is most semantically similar
    to the user's natural-language search.
    """

    if not events or not query.strip():
        return []

    model = _load_model()

    event_texts = []

    for event in events:
        category_name = (
            event.category.categoryName
            if event.category
            else ""
        )

        venue_name = (
            event.venue.venueName
            if event.venue
            else ""
        )

        venue_suburb = (
            event.venue.suburb
            if event.venue
            else ""
        )

        event_text = " ".join([
            event.title or "",
            event.description or "",
            category_name,
            event.skillLevel or "",
            event.surfaceType or "",
            venue_name,
            venue_suburb,
        ])

        event_texts.append(event_text)

    # Encode the user search and all events
    embeddings = model.encode(
        [query] + event_texts,
        normalize_embeddings=True
    )

    query_embedding = embeddings[0]
    event_embeddings = embeddings[1:]

    # Cosine similarity because embeddings are normalized
    scores = event_embeddings @ query_embedding

    best_index = int(np.argmax(scores))
    best_score = float(scores[best_index])

    return [(events[best_index], best_score)]