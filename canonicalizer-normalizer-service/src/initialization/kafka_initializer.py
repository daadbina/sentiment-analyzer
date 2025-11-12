"""Kafka topic initializer."""
import logging
from typing import List, Dict
from confluent_kafka.admin import AdminClient, NewTopic, KafkaException

logger = logging.getLogger(__name__)


class KafkaInitializer:
    """Initialize Kafka topics if they don't exist."""
    
    def __init__(self, bootstrap_servers: str):
        """Initialize Kafka initializer.

        Args:
            bootstrap_servers: Kafka bootstrap servers
        """
        logger.info(f"KafkaInitializer: Creating AdminClient with bootstrap.servers={bootstrap_servers}")
        config = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'canonicalizer-admin-client',
            'debug': 'broker,admin'
        }
        logger.info(f"AdminClient config: {config}")
        self.admin_client = AdminClient(config)
    
    def ensure_topics_exist(self, topics: List[Dict[str, any]]) -> None:
        """Ensure all required topics exist, create if missing.
        
        Args:
            topics: List of topic configurations with keys: name, num_partitions, replication_factor
        """
        try:
            # Get existing topics
            metadata = self.admin_client.list_topics(timeout=10)
            existing_topics = set(metadata.topics.keys())
            
            # Determine which topics need to be created
            topics_to_create = []
            for topic_config in topics:
                topic_name = topic_config['name']
                if topic_name not in existing_topics:
                    logger.info(f"Topic '{topic_name}' does not exist, will create it")
                    topics_to_create.append(
                        NewTopic(
                            topic=topic_name,
                            num_partitions=topic_config.get('num_partitions', 3),
                            replication_factor=topic_config.get('replication_factor', 1)
                        )
                    )
                else:
                    logger.info(f"Topic '{topic_name}' already exists")
            
            # Create missing topics
            if topics_to_create:
                logger.info(f"Creating {len(topics_to_create)} missing topics...")
                fs = self.admin_client.create_topics(topics_to_create)
                
                # Wait for each operation to finish
                for topic, f in fs.items():
                    try:
                        f.result()  # The result itself is None
                        logger.info(f"Topic '{topic}' created successfully")
                    except KafkaException as e:
                        if 'TOPIC_ALREADY_EXISTS' in str(e):
                            logger.info(f"Topic '{topic}' already exists (race condition)")
                        else:
                            logger.error(f"Failed to create topic '{topic}': {e}")
                            raise
            else:
                logger.info("All required topics already exist")
                
        except Exception as e:
            logger.error(f"Error ensuring topics exist: {e}")
            raise

