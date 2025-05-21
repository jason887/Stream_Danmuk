# database/db_connection_manager.py
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ConfigurationError
# Assuming db_config.py is in the same directory or package
from .db_config import MONGO_URI, DB_NAME # Use relative import if in a package


_db_manager_instance = None

class DatabaseConnectionManager:
    """Manages the MongoDB connection."""

    def __init__(self):
        logging.info("DatabaseConnectionManager: Instance created.")
        self.client = None
        self.db = None
        self._is_connected = False

    def connect_db(self):
        """Attempts to connect to the MongoDB database."""
        if self._is_connected and self.client is not None:
            logging.info("DatabaseConnectionManager: Already connected to MongoDB.")
            return True

        uri_to_log = MONGO_URI
        if "@" in uri_to_log: # Avoid logging credentials
            uri_to_log = "mongodb://" + uri_to_log.split('@')[-1]
        logging.info(f"DatabaseConnectionManager: Attempting connection to MongoDB: {uri_to_log}")

        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) # 5 second timeout
            self.client.admin.command('ismaster') # Verify connection
            self.db = self.client[DB_NAME]
            self._is_connected = True
            logging.info(f"DatabaseConnectionManager: Successfully connected to MongoDB database: '{self.db.name}'")
            return True
        except ConnectionFailure as e:
            logging.error(f"DatabaseConnectionManager: MongoDB connection failed: {e}")
        except OperationFailure as e: # Catches issues like auth failure after connection
            logging.error(f"DatabaseConnectionManager: MongoDB operation failed during connection: {e}")
        except ConfigurationError as e:
            logging.error(f"DatabaseConnectionManager: MongoDB configuration error: {e}")
        except Exception as e: # Catch any other unexpected errors
            logging.error(f"DatabaseConnectionManager: An unexpected error occurred during MongoDB connection: {e}", exc_info=True)

        # If any exception occurred, ensure cleanup
        self._is_connected = False
        if self.client:
            try:
                self.client.close()
            except Exception as close_e:
                logging.error(f"DatabaseConnectionManager: Error closing client after connection failure: {close_e}")
        self.client = None
        self.db = None
        return False

    def disconnect_db(self):
        """Disconnects from the MongoDB database."""
        if self.client:
            logging.info("DatabaseConnectionManager: Closing MongoDB connection.")
            try:
                self.client.close()
                logging.info("DatabaseConnectionManager: MongoDB connection closed.")
            except Exception as e:
                logging.error(f"DatabaseConnectionManager: Error closing MongoDB connection: {e}")
            finally:
                self.client = None
                self.db = None
                self._is_connected = False
        else:
            logging.info("DatabaseConnectionManager: MongoDB client was not connected or already closed.")
            self._is_connected = False # Ensure flag is correct

    def is_connected(self):
        """Checks if the database connection is currently active."""
        return self._is_connected

    def get_db(self):
        """Returns the database object if connected, otherwise None."""
        # Fix: Check self.db explicitly against None
        if self.is_connected() and self.db is not None: # <-- Modified this line
            return self.db
        # logging.warning("DatabaseConnectionManager: Requested DB object, but not connected or DB object is None.")
        return None

# --- Singleton Management ---
def init_db_manager() -> DatabaseConnectionManager:
    """Initializes and returns the singleton DatabaseConnectionManager instance."""
    global _db_manager_instance
    if _db_manager_instance is None:
        logging.info("DatabaseConnectionManager: Initializing new manager instance.")
        _db_manager_instance = DatabaseConnectionManager()
    # else:
    #     logging.info("DatabaseConnectionManager: Returning existing manager instance.")
    return _db_manager_instance

def get_db_manager() -> DatabaseConnectionManager | None:
    """Returns the module-level global instance of DatabaseConnectionManager."""
    if _db_manager_instance is None:
        logging.error("DatabaseConnectionManager: get_db_manager() called before init_db_manager(). CRITICAL: Initialize first.")
    return _db_manager_instance
