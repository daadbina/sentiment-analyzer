"""Database initializer."""
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Initialize database schema and seed data."""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """Initialize database initializer.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            user: PostgreSQL user
            password: PostgreSQL password
            database: PostgreSQL database name
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
    
    def ensure_schema_exists(self) -> None:
        """Ensure all required tables exist, create if missing."""
        try:
            # Connect to database
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            
            # Create publishers table
            logger.info("Checking if publishers table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS publishers (
                    publisher_id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    domain VARCHAR(255) UNIQUE NOT NULL,
                    credibility_score FLOAT NOT NULL CHECK (credibility_score >= 0.0 AND credibility_score <= 1.0),
                    country VARCHAR(10),
                    ownership_type VARCHAR(50),
                    verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Publishers table ready")
            
            # Create index on domain
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_publishers_domain ON publishers(domain)
            """)
            
            # Create canonicalization_audit_log table
            logger.info("Checking if canonicalization_audit_log table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS canonicalization_audit_log (
                    log_id SERIAL PRIMARY KEY,
                    article_id VARCHAR(255) NOT NULL,
                    original_url TEXT NOT NULL,
                    canonical_url TEXT,
                    publisher_id VARCHAR(255),
                    normalization_score FLOAT,
                    transformations JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Canonicalization audit log table ready")
            
            # Create index on article_id
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_log_article_id ON canonicalization_audit_log(article_id)
            """)
            
            # Create index on created_at
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON canonicalization_audit_log(created_at)
            """)
            
            # Create normalization_summary table
            logger.info("Checking if normalization_summary table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS normalization_summary (
                    summary_id SERIAL PRIMARY KEY,
                    batch_id VARCHAR(255) UNIQUE NOT NULL,
                    total_articles INTEGER NOT NULL,
                    successful_normalizations INTEGER NOT NULL,
                    failed_normalizations INTEGER NOT NULL,
                    average_score FLOAT,
                    processing_time_seconds FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Normalization summary table ready")
            
            # Create index on batch_id
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_summary_batch_id ON normalization_summary(batch_id)
            """)
            
            cur.close()
            conn.close()
            
            logger.info("Database schema initialization complete")
            
        except Exception as e:
            logger.error(f"Error ensuring database schema exists: {e}")
            raise
    
    def seed_publishers(self) -> None:
        """Seed initial publisher data if table is empty."""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            
            # Check if publishers table is empty
            cur.execute("SELECT COUNT(*) FROM publishers")
            count = cur.fetchone()[0]
            
            if count > 0:
                logger.info(f"Publishers table already has {count} entries, skipping seed")
                cur.close()
                conn.close()
                return
            
            logger.info("Seeding initial publisher data...")
            
            # Initial publisher data
            publishers = [
                ('bbc', 'BBC', 'bbc.com', 0.95, 'GB', 'public', True),
                ('bbc-uk', 'BBC', 'bbc.co.uk', 0.95, 'GB', 'public', True),
                ('cnn', 'CNN', 'cnn.com', 0.85, 'US', 'private', True),
                ('reuters', 'Reuters', 'reuters.com', 0.95, 'GB', 'private', True),
                ('ap', 'Associated Press', 'apnews.com', 0.95, 'US', 'private', True),
                ('aljazeera', 'Al Jazeera', 'aljazeera.com', 0.90, 'QA', 'state', True),
                ('rt', 'RT', 'rt.com', 0.70, 'RU', 'state', True),
                ('dw', 'Deutsche Welle', 'dw.com', 0.90, 'DE', 'public', True),
                ('voa', 'Voice of America', 'voanews.com', 0.85, 'US', 'public', True),
                ('xinhua', 'Xinhua', 'xinhuanet.com', 0.75, 'CN', 'state', True),
                ('tasnim', 'Tasnim', 'tasnimnews.com', 0.75, 'IR', 'private', True),
                ('isna', 'ISNA', 'isna.ir', 0.80, 'IR', 'private', True),
                ('irna', 'IRNA', 'irna.ir', 0.75, 'IR', 'state', True),
                ('ft', 'Financial Tribune', 'financialtribune.com', 0.80, 'IR', 'private', True),
                ('coindesk', 'CoinDesk', 'coindesk.com', 0.85, 'US', 'private', True),
                ('cointelegraph', 'Cointelegraph', 'cointelegraph.com', 0.80, 'US', 'private', True),
                ('nytimes', 'The New York Times', 'nytimes.com', 0.95, 'US', 'private', True),
                ('washingtonpost', 'The Washington Post', 'washingtonpost.com', 0.90, 'US', 'private', True),
                ('wsj', 'The Wall Street Journal', 'wsj.com', 0.90, 'US', 'private', True),
                ('theguardian', 'The Guardian', 'theguardian.com', 0.90, 'GB', 'private', True),
                ('bloomberg', 'Bloomberg', 'bloomberg.com', 0.90, 'US', 'private', True),
                ('forbes', 'Forbes', 'forbes.com', 0.85, 'US', 'private', True),
                ('economist', 'The Economist', 'economist.com', 0.90, 'GB', 'private', True),
                ('ft-com', 'Financial Times', 'ft.com', 0.90, 'GB', 'private', True),
                ('independent', 'The Independent', 'independent.co.uk', 0.85, 'GB', 'private', True),
                ('telegraph', 'The Telegraph', 'telegraph.co.uk', 0.85, 'GB', 'private', True),
                ('france24', 'France 24', 'france24.com', 0.85, 'FR', 'public', True),
                ('spiegel', 'Der Spiegel', 'spiegel.de', 0.85, 'DE', 'private', True),
                ('lemonde', 'Le Monde', 'lemonde.fr', 0.85, 'FR', 'private', True),
                ('elpais', 'El País', 'elpais.com', 0.85, 'ES', 'private', True),
                ('corriere', 'Corriere della Sera', 'corriere.it', 0.85, 'IT', 'private', True),
                ('asahi', 'Asahi Shimbun', 'asahi.com', 0.85, 'JP', 'private', True),
                ('nhk', 'NHK', 'nhk.or.jp', 0.90, 'JP', 'public', True),
                ('scmp', 'South China Morning Post', 'scmp.com', 0.80, 'HK', 'private', True),
                ('straitstimes', 'The Straits Times', 'straitstimes.com', 0.85, 'SG', 'private', True),
                ('abc-au', 'ABC News (Australia)', 'abc.net.au', 0.90, 'AU', 'public', True),
                ('cbc', 'CBC News', 'cbc.ca', 0.90, 'CA', 'public', True),
                ('globeandmail', 'The Globe and Mail', 'theglobeandmail.com', 0.85, 'CA', 'private', True),
                ('thetimes', 'The Times', 'thetimes.co.uk', 0.85, 'GB', 'private', True),
                ('usatoday', 'USA Today', 'usatoday.com', 0.80, 'US', 'private', True),
                ('latimes', 'Los Angeles Times', 'latimes.com', 0.85, 'US', 'private', True),
                ('chicagotribune', 'Chicago Tribune', 'chicagotribune.com', 0.80, 'US', 'private', True),
                ('bostonglobe', 'The Boston Globe', 'bostonglobe.com', 0.85, 'US', 'private', True),
            ]
            
            for pub in publishers:
                try:
                    cur.execute("""
                        INSERT INTO publishers (publisher_id, name, domain, credibility_score, country, ownership_type, verified)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (domain) DO NOTHING
                    """, pub)
                    logger.info(f"  Seeded publisher: {pub[1]} ({pub[2]})")
                except Exception as e:
                    logger.warning(f"  Failed to seed publisher {pub[1]}: {e}")
            
            cur.close()
            conn.close()
            
            logger.info(f"Seeded {len(publishers)} publishers")
            
        except Exception as e:
            logger.error(f"Error seeding publishers: {e}")
            raise

