# database/db_queries.py
import logging
import random
import re
from pymongo.database import Database
from pymongo.errors import NetworkTimeout, OperationFailure

from . import db_config


def _fetch_documents_from_db(db: Database | None, collection_name: str, query, limit=0, projection=None):
    """Generic helper to fetch documents from a collection, given a db object."""
    if db is None: # <-- Modified
        logging.warning(f"db_queries: Cannot fetch from '{collection_name}'. DB object is None.")
        return []
    try:
        collection = db[collection_name]
        cursor = collection.find(query, projection)
        if limit > 0:
            cursor = cursor.limit(limit)
        documents = list(cursor)
        logging.debug(f"db_queries: Fetched {len(documents)} documents from '{collection_name}' with query {query} and projection {projection}.")
        return documents
    except NetworkTimeout as e:
        logging.error(f"db_queries: Network timeout fetching from '{collection_name}': {e}")
    except OperationFailure as e:
        logging.error(f"db_queries: Operation failed fetching from '{collection_name}': {e}")
    except Exception as e:
        logging.error(f"db_queries: An unexpected error occurred fetching from '{collection_name}': {e}", exc_info=True)
    return []


def search_streamer_names_in_db(db: Database | None, term: str, limit: int = 20):
    """Searches for streamer names in the Welcome collection using regex."""
    if db is None: return [] # <-- Modified
    try:
        collection = db[db_config.WELCOME_COLLECTION]
        regex_query = {"$regex": term, "$options": "i"} if term else {"$exists": True}
        names = collection.distinct("name", {"name": regex_query})

        if limit > 0 and len(names) > limit:
            return names[:limit]
        return names
    except Exception as e:
        logging.error(f"db_queries: Error searching streamer names for term '{term}': {e}", exc_info=True)
        return []


def fetch_danmaku_from_db(db: Database | None, streamer_name: str | None, danmaku_type: str, limit: int = 10):
    """
    Fetches danmaku of a specific type (e.g., 'welcome', 'roast').
    """
    if db is None: return [] # <-- Modified

    collection_map = {
        "welcome": db_config.WELCOME_COLLECTION,
        "roast": db_config.MOCK_COLLECTION,
    }

    if danmaku_type not in collection_map:
        logging.warning(f"db_queries: Unknown danmaku_type '{danmaku_type}' requested in fetch_danmaku_from_db.")
        return []

    collection_name = collection_map[danmaku_type]

    query = {}
    if streamer_name:
        query["name"] = {"$regex": f"^{re.escape(streamer_name)}$", "$options": "i"}

    projection = {"text": 1, "_id": 0}
    docs = _fetch_documents_from_db(db, collection_name, query, limit, projection)
    return [doc.get("text", "") for doc in docs if doc and doc.get("text") and isinstance(doc.get("text"), str)]


def fetch_anti_fan_quotes_from_db(db: Database | None, limit: int = 3):
    """Fetches anti-fan quotes."""
    if db is None: return []

    # 修改投影，使用正确的字段名 "quote_text"
    projection = {"quote_text": 1, "_id": 0}

    docs = _fetch_documents_from_db(db, db_config.ANTI_FAN_COLLECTION, {}, limit, projection)

    # 修改数据提取，使用正确的字段名 "quote_text"
    # Also ensure the extracted value is a non-empty string before including
    return [doc.get("quote_text", "") for doc in docs if doc and doc.get("quote_text") and isinstance(doc.get("quote_text"), str)]


def fetch_reversal_copy_data_from_db(db: Database | None, streamer_name: str, limit: int = 10):
    """Fetches Reversal_Copy data (danmaku_part, read_part) for a streamer."""
    if db is None: return [] # <-- Modified

    query = {"source_name": {"$regex": f"^{re.escape(streamer_name)}$", "$options": "i"}}
    projection = {"danmaku_part": 1, "read_part": 1, "_id": 0}

    all_documents = _fetch_documents_from_db(db, db_config.REVERSAL_COLLECTION, query, 0, projection)

    if all_documents:
        valid_entries = [
            # Bug 修复：添加空格
            entry for entry in all_documents
            if isinstance(entry.get('danmaku_part'), str) and entry.get('danmaku_part') is not None
            and isinstance(entry.get('read_part'), str) and entry.get('read_part') is not None
        ]
        if valid_entries:
            random.shuffle(valid_entries)
            logging.debug(f"db_queries: Found {len(valid_entries)} valid Reversal_Copy entries for '{streamer_name}'. Returning up to {limit}.")
            return valid_entries[:limit]
        else:
            logging.warning(f"db_queries: Documents found for '{streamer_name}' in {db_config.REVERSAL_COLLECTION}, but none have both 'danmaku_part'/'read_part' as valid strings.")
    else:
        logging.info(f"db_queries: No documents found for streamer '{streamer_name}' in {db_config.REVERSAL_COLLECTION}.")
    return []


def fetch_social_topics_data_from_db(db: Database | None, topic_name: str, limit: int = 10):
    """Fetches items from the 'generated_danmaku' array for a specific topic."""
    if db is None: return [] # <-- Modified

    query = {"topic_name": {"$regex": f"^{re.escape(topic_name)}$", "$options": "i"}}
    projection = {"generated_danmaku": 1, "_id": 0}

    documents = _fetch_documents_from_db(db, db_config.CAPTIONS_COLLECTION, query, 1, projection)
    document = documents[0] if documents else None

    if document and 'generated_danmaku' in document and isinstance(document['generated_danmaku'], list):
        topic_items = [
            item for item in document['generated_danmaku']
            if item and isinstance(item, str) and item.strip()
        ]
        if topic_items:
            random.shuffle(topic_items)
            logging.debug(f"db_queries: Extracted {len(topic_items)} items for topic '{topic_name}'. Returning up to {limit}.")
            return topic_items[:limit]
        else:
            logging.warning(f"db_queries: Topic '{topic_name}' found in {db_config.CAPTIONS_COLLECTION}, but 'generated_danmaku' list is empty or has no valid strings.")
    else:
        logging.info(f"db_queries: No document found for topic '{topic_name}' in {db_config.CAPTIONS_COLLECTION}, or 'generated_danmaku' field is missing/invalid.")
    return []


# Assuming this is a synchronous function using PyMongo
def get_random_danmaku_from_db(db: Database | None, collection_name: str, count: int):
    """Fetches a specified number of random danmaku strings from a collection using $sample."""
    if db is None:
        logging.error("db_queries: DB object is None for get_random_danmaku.")
        return []

    if not collection_name:
        logging.error("db_queries: collection_name cannot be empty for get_random_danmaku.")
        return []

    try:
        collection = db[collection_name]

        # 修改 field_name 的判断逻辑
        field_name = 'text'  # Default field
        if collection_name == db_config.ANTI_FAN_COLLECTION:
            field_name = 'quote_text'
        elif collection_name in [db_config.BIG_BROTHERS_COLLECTION, db_config.GIFT_THANKS_COLLECTION]:
            field_name = 'template'

        pipeline = [{"$sample": {"size": count}}]

        if collection_name in [
            db_config.WELCOME_COLLECTION, db_config.MOCK_COLLECTION, db_config.ANTI_FAN_COLLECTION,
            db_config.BIG_BROTHERS_COLLECTION, db_config.GIFT_THANKS_COLLECTION
        ]:
            pipeline.append({"$project": {"_id": 0, field_name: 1}})
        else:
            logging.debug(f"db_queries: Fetching random documents from '{collection_name}' without specific field projection (may return full docs).")

        cursor = collection.aggregate(pipeline)
        results = list(cursor) # Synchronous call

        if collection_name in [
            db_config.WELCOME_COLLECTION, db_config.MOCK_COLLECTION, db_config.ANTI_FAN_COLLECTION,
            db_config.BIG_BROTHERS_COLLECTION, db_config.GIFT_THANKS_COLLECTION
        ]:
            extracted_list = [doc.get(field_name) for doc in results if doc and isinstance(doc.get(field_name), str) and doc.get(field_name) is not None]
            return extracted_list
        else:
            logging.debug(f"db_queries: Returning {len(results)} raw/full documents for '{collection_name}' from $sample.")
            return results

    except OperationFailure as e:
        if "empty K Slices" in str(e) or (hasattr(e, 'code') and e.code == 26):
             logging.warning(f"db_queries: Collection '{collection_name}' might be empty or not found for $sample. Error: {e}")
        else:
             logging.error(f"db_queries: OperationFailure fetching random danmaku from '{collection_name}': {e}", exc_info=True)
        return []
    except Exception as e:
        logging.error(f"db_queries: Unexpected error fetching random danmaku from '{collection_name}': {e}", exc_info=True)
        return []
