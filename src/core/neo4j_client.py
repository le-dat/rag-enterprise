from neo4j import GraphDatabase
from src.core.config import settings

class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI, 
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def query(self, cypher_query, parameters=None):
        """Hàm helper chạy truy vấn Cypher và trả về kết quả"""
        with self.driver.session() as session:
            result = session.run(cypher_query, parameters)
            return [record.data() for record in result]
