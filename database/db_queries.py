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
    """Fetches a specified number of random anti-fan quotes from the Anti_Fan_Quotes collection."""
    if db is None:
        logging.warning("db_queries: Cannot fetch anti-fan quotes. DB object is None.")
        return []

    collection_name = db_config.ANTI_FAN_COLLECTION
    field_to_extract = "quote_text" # Field containing the quote

    try:
        collection = db[collection_name]
        
        # Use $sample for random fetching
        pipeline = [
            {"$sample": {"size": limit}},
            {"$project": {"_id": 0, field_to_extract: 1}}
        ]
        
        cursor = collection.aggregate(pipeline)
        docs = list(cursor)
        
        # Extract the text from the documents
        quotes = [
            doc.get(field_to_extract, "") for doc in docs 
            if doc and doc.get(field_to_extract) and isinstance(doc.get(field_to_extract), str)
        ]
        
        logging.debug(f"db_queries: Fetched {len(quotes)} random quotes from '{collection_name}'.")
        return quotes
        
    except OperationFailure as e:
        # Handle cases like empty collection or other DB operation errors
        if "empty K Slices" in str(e) or (hasattr(e, 'code') and e.code == 26): # Common error for $sample on empty/small collection
             logging.warning(f"db_queries: Collection '{collection_name}' might be empty or too small for $sample with limit {limit}. Error: {e}")
        else:
             logging.error(f"db_queries: OperationFailure fetching random quotes from '{collection_name}': {e}", exc_info=True)
        return [] # Return empty list on error
    except Exception as e:
        logging.error(f"db_queries: An unexpected error occurred fetching random quotes from '{collection_name}': {e}", exc_info=True)
        return []


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


def fetch_complaints_data(db: Database | None, reversed_anchor_name: str | None, theme_event_name: str | None, total_limit: int = 10):
    """
    Fetches data for "Welcome Complaints" feature from multiple collections.
    Aims for a combined total of `total_limit` items.
    """
    if db is None:
        logging.warning("db_queries: Cannot fetch complaints data. DB object is None.")
        return []

    results = []
    # Approx limit per collection, can be adjusted
    # Ensure at least 1 if total_limit is small, e.g. total_limit=1, num_collections=4 -> limit_per_collection = 0. So, max(1, total_limit // num_collections)
    num_collections = 4
    limit_per_collection = max(1, total_limit // num_collections)
    remaining_limit = total_limit

    # Helper to build regex query
    def build_regex_query(term: str | None):
        return {"$regex": re.escape(term), "$options": "i"} if term and term.strip() else None

    # 1. Welcome_Danmaku
    if remaining_limit > 0:
        query_welcome = {}
        welcome_filters = []
        regex_anchor = build_regex_query(reversed_anchor_name)
        regex_theme = build_regex_query(theme_event_name)

        if regex_anchor:
            welcome_filters.append({"text": regex_anchor}) # Search anchor name in text content
        if regex_theme:
            welcome_filters.append({"text": regex_theme})  # Search theme name in text content
        
        if welcome_filters:
            query_welcome["$or"] = welcome_filters # If either term matches in the text
        
        # If no search terms, query_welcome remains {} (fetch any) - this might be too broad.
        # Let's only fetch if there's at least one term for Welcome/Mock, or make it configurable.
        # For now, if filters exist, apply them. Otherwise, it fetches any.
        
        docs = _fetch_documents_from_db(db, db_config.WELCOME_COLLECTION, query_welcome, min(limit_per_collection, remaining_limit), {"text": 1, "_id": 0})
        for doc in docs:
            if doc and isinstance(doc.get("text"), str) and doc["text"].strip():
                results.append(f"[欢迎] {doc['text']}")
        remaining_limit = total_limit - len(results)

    # 2. Mock_Danmaku
    if remaining_limit > 0:
        query_mock = {}
        mock_filters = []
        # Regex terms already built above
        if regex_anchor:
            mock_filters.append({"text": regex_anchor})
        if regex_theme:
            mock_filters.append({"text": regex_theme})

        if mock_filters:
            query_mock["$or"] = mock_filters
            
        docs = _fetch_documents_from_db(db, db_config.MOCK_COLLECTION, query_mock, min(limit_per_collection, remaining_limit), {"text": 1, "_id": 0})
        for doc in docs:
            if doc and isinstance(doc.get("text"), str) and doc["text"].strip():
                results.append(f"[吐槽] {doc['text']}")
        remaining_limit = total_limit - len(results)

    # 3. Reversal_Copy
    if remaining_limit > 0:
        query_reversal = {}
        reversal_filters = []
        if regex_anchor:
            reversal_filters.append({"source_name": regex_anchor})
        if regex_theme:
            reversal_filters.append({"danmaku_part": regex_theme}) # Search theme in danmaku_part
        
        if reversal_filters: # Only query if there's something to filter by for relevant fields
            query_reversal["$and"] = reversal_filters # Must match both if both provided for their respective fields
        
        # If no relevant filters for this collection, query_reversal remains {} (fetch any)
        # This might be too broad. Let's only fetch if there's at least one relevant term.
        if query_reversal: # only fetch if query is not empty
            docs = _fetch_documents_from_db(db, db_config.REVERSAL_COLLECTION, query_reversal, min(limit_per_collection, remaining_limit), {"danmaku_part": 1, "read_part": 1, "source_name":1, "_id": 0})
            for doc in docs:
                dp = doc.get("danmaku_part")
                rp = doc.get("read_part")
                sn = doc.get("source_name")
                if dp and isinstance(dp, str) and dp.strip():
                    results.append(f"[反转@{sn}] {dp} (提示: {rp or '无'})")
            remaining_limit = total_limit - len(results)

    # 4. Social_Topics (Generated_Captions)
    if remaining_limit > 0:
        query_captions = {}
        captions_filters = []
        if regex_theme: # Theme name for topic_name
            captions_filters.append({"topic_name": regex_theme})
        
        # How to apply reversed_anchor_name to generated_danmaku array?
        # This requires a more complex query, e.g., $elemMatch on generated_danmaku if regex_anchor is present.
        # For simplicity now, only topic_name is the primary filter.
        # If reversed_anchor_name is provided, we could filter the returned list of strings in Python.
        
        if captions_filters: # Only query if there's a theme to filter by
            query_captions["$and"] = captions_filters
        
        if query_captions: # only fetch if query is not empty
            # Fetching the whole document and then its list
            docs = _fetch_documents_from_db(db, db_config.CAPTIONS_COLLECTION, query_captions, 1, {"generated_danmaku": 1, "topic_name": 1, "_id": 0})
            if docs and isinstance(docs[0].get("generated_danmaku"), list):
                topic_name = docs[0].get("topic_name", "未知主题")
                danmakus = docs[0]["generated_danmaku"]
                
                # If reversed_anchor_name was provided, filter danmakus list here
                filtered_danmakus = []
                if regex_anchor:
                    for d in danmakus:
                        if isinstance(d, str) and re.search(regex_anchor["$regex"], d, re.IGNORECASE):
                            filtered_danmakus.append(d)
                else: # No anchor name filter, take all
                    filtered_danmakus = [d for d in danmakus if isinstance(d, str) and d.strip()]

                random.shuffle(filtered_danmakus)
                count = 0
                for item_text in filtered_danmakus:
                    if len(results) < total_limit:
                        results.append(f"[主题@{topic_name}] {item_text}")
                        count += 1
                        if count >= min(limit_per_collection, remaining_limit):
                            break
                    else:
                        break
            remaining_limit = total_limit - len(results)
            
    random.shuffle(results) # Shuffle combined results
    return results[:total_limit]


def fetch_big_brother_templates(db: Database | None, limit: int = 30):
    """Fetches a specified number of random templates from the Big_Brothers collection."""
    if db is None:
        logging.warning("db_queries: Cannot fetch Big Brother templates. DB object is None.")
        return []

    collection_name = db_config.BIG_BROTHERS_COLLECTION
    field_to_extract = "template"  # Field containing the template text

    try:
        collection = db[collection_name]
        
        # Use $sample for random fetching
        pipeline = [
            {"$sample": {"size": limit}},
            {"$project": {"_id": 0, field_to_extract: 1}}
        ]
        
        cursor = collection.aggregate(pipeline)
        docs = list(cursor)
        
        templates = [
            doc.get(field_to_extract, "") for doc in docs 
            if doc and doc.get(field_to_extract) and isinstance(doc.get(field_to_extract), str)
        ]
        
        logging.debug(f"db_queries: Fetched {len(templates)} random templates from '{collection_name}'.")
        return templates
        
    except OperationFailure as e:
        if "empty K Slices" in str(e) or (hasattr(e, 'code') and e.code == 26):
             logging.warning(f"db_queries: Collection '{collection_name}' might be empty or too small for $sample with limit {limit}. Error: {e}")
        else:
             logging.error(f"db_queries: OperationFailure fetching random templates from '{collection_name}': {e}", exc_info=True)
        return []
    except Exception as e:
        logging.error(f"db_queries: An unexpected error occurred fetching random templates from '{collection_name}': {e}", exc_info=True)
        return []


def fetch_reversal_scripts(db: Database | None, limit: int = 10):
    """Fetches a specified number of random reversal scripts (danmaku_part) from the Reversal_Copy collection."""
    if db is None:
        logging.warning("db_queries: Cannot fetch reversal scripts. DB object is None.")
        return []

    collection_name = db_config.REVERSAL_COLLECTION
    field_to_extract = "danmaku_part" 

    try:
        collection = db[collection_name]
        
        pipeline = [
            {"$sample": {"size": limit}},
            {"$project": {"_id": 0, field_to_extract: 1}}
        ]
        
        cursor = collection.aggregate(pipeline)
        docs = list(cursor)
        
        scripts = [
            doc.get(field_to_extract, "") for doc in docs 
            if doc and doc.get(field_to_extract) and isinstance(doc.get(field_to_extract), str)
        ]
        
        logging.debug(f"db_queries: Fetched {len(scripts)} random reversal scripts from '{collection_name}'.")
        return scripts
        
    except OperationFailure as e:
        if "empty K Slices" in str(e) or (hasattr(e, 'code') and e.code == 26):
             logging.warning(f"db_queries: Collection '{collection_name}' might be empty or too small for $sample with limit {limit}. Error: {e}")
        else:
             logging.error(f"db_queries: OperationFailure fetching random reversal scripts from '{collection_name}': {e}", exc_info=True)
        return []
    except Exception as e:
        logging.error(f"db_queries: An unexpected error occurred fetching random reversal scripts from '{collection_name}': {e}", exc_info=True)
        return []


def fetch_gift_thanks_templates(db: Database | None, limit: int = 30):
    """Fetches a specified number of random templates from the Gift_Thanks_Danmaku collection."""
    if db is None:
        logging.warning("db_queries: Cannot fetch Gift Thanks templates. DB object is None.")
        return []

    collection_name = db_config.GIFT_THANKS_COLLECTION
    field_to_extract = "template"  # Field containing the template text

    try:
        collection = db[collection_name]
        
        # Use $sample for random fetching
        pipeline = [
            {"$sample": {"size": limit}},
            {"$project": {"_id": 0, field_to_extract: 1}}
        ]
        
        cursor = collection.aggregate(pipeline)
        docs = list(cursor)
        
        templates = [
            doc.get(field_to_extract, "") for doc in docs 
            if doc and doc.get(field_to_extract) and isinstance(doc.get(field_to_extract), str)
        ]
        
        logging.debug(f"db_queries: Fetched {len(templates)} random templates from '{collection_name}'.")
        return templates
        
    except OperationFailure as e:
        if "empty K Slices" in str(e) or (hasattr(e, 'code') and e.code == 26):
             logging.warning(f"db_queries: Collection '{collection_name}' might be empty or too small for $sample with limit {limit}. Error: {e}")
        else:
             logging.error(f"db_queries: OperationFailure fetching random templates from '{collection_name}': {e}", exc_info=True)
        return []
    except Exception as e:
        logging.error(f"db_queries: An unexpected error occurred fetching random templates from '{collection_name}': {e}", exc_info=True)
        return []
