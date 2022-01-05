import dependency_injector.providers as providers
from data.mongo_context import MongoDBContext


class DBContext:
    """DI class for future development"""

    mongo_db_context = providers.Singleton(MongoDBContext)
