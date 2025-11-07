"""Initialize semantic groups at clustering service startup."""

import asyncio
import asyncpg
import json
from uuid import uuid4
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


# GDELT event types
GDELT_EVENT_TYPES = {
    "PROTEST": "Protests and Demonstrations",
    "RIOT": "Riots and Civil Unrest",
    "VIOLENCE_AGAINST_CIVILIANS": "Violence Against Civilians",
    "MASS_VIOLENCE": "Mass Violence Events",
    "ARMED_CONFLICT": "Armed Conflict",
    "MILITARY_ACTION": "Military Actions",
}

# Key countries for semantic groups (country code -> country name)
# Expanded to 50+ countries for better coverage
KEY_COUNTRIES = {
    # Americas
    "US": "United States",
    "CA": "Canada",
    "MX": "Mexico",
    "BR": "Brazil",
    "AR": "Argentina",
    "CL": "Chile",
    "CO": "Colombia",
    "PE": "Peru",
    "VE": "Venezuela",

    # Europe
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "IT": "Italy",
    "ES": "Spain",
    "PL": "Poland",
    "UA": "Ukraine",
    "RU": "Russia",
    "TR": "Turkey",
    "GR": "Greece",
    "SE": "Sweden",
    "NO": "Norway",
    "NL": "Netherlands",
    "BE": "Belgium",
    "CH": "Switzerland",
    "AT": "Austria",
    "CZ": "Czech Republic",
    "HU": "Hungary",
    "RO": "Romania",
    "BG": "Bulgaria",

    # Middle East & North Africa
    "SA": "Saudi Arabia",
    "AE": "United Arab Emirates",
    "IR": "Iran",
    "IQ": "Iraq",
    "SY": "Syria",
    "IL": "Israel",
    "PS": "Palestine",
    "JO": "Jordan",
    "LB": "Lebanon",
    "EG": "Egypt",
    "LY": "Libya",
    "TN": "Tunisia",
    "MA": "Morocco",
    "YE": "Yemen",
    "OM": "Oman",
    "KW": "Kuwait",
    "QA": "Qatar",
    "BH": "Bahrain",

    # Asia
    "CN": "China",
    "IN": "India",
    "JP": "Japan",
    "KR": "South Korea",
    "KP": "North Korea",
    "TH": "Thailand",
    "VN": "Vietnam",
    "PH": "Philippines",
    "ID": "Indonesia",
    "MY": "Malaysia",
    "SG": "Singapore",
    "PK": "Pakistan",
    "BD": "Bangladesh",
    "AF": "Afghanistan",
    "MM": "Myanmar",
    "LA": "Laos",
    "KH": "Cambodia",
    "TW": "Taiwan",
    "HK": "Hong Kong",

    # Africa
    "NG": "Nigeria",
    "ZA": "South Africa",
    "KE": "Kenya",
    "ET": "Ethiopia",
    "GH": "Ghana",
    "UG": "Uganda",
    "TZ": "Tanzania",
    "DZ": "Algeria",
    "SD": "Sudan",
    "SS": "South Sudan",
    "SO": "Somalia",
    "ZM": "Zambia",
    "ZW": "Zimbabwe",
    "MW": "Malawi",
    "RW": "Rwanda",
    "BW": "Botswana",
    "NA": "Namibia",
    "AO": "Angola",
    "MZ": "Mozambique",
    "CI": "Ivory Coast",

    # Oceania
    "AU": "Australia",
    "NZ": "New Zealand",
    "FJ": "Fiji",
    "PG": "Papua New Guinea",
}


async def initialize_semantic_groups(db_host: str, db_port: int, db_user: str, db_password: str, db_name: str):
    """Initialize semantic groups at startup if they don't exist.
    
    Creates country+event combinations so both news articles and GDELT events can contribute.
    """
    try:
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )
        
        # Check if semantic groups already exist
        count = await conn.fetchval('SELECT COUNT(*) FROM semantic_groups;')
        
        if count > 0:
            logger.info(f"Semantic groups already initialized ({count} groups exist)")
            await conn.close()
            return
        
        logger.info("Initializing semantic groups at startup...")
        
        # Create semantic groups for country+event combinations
        semantic_groups = []

        for event_type, event_label in GDELT_EVENT_TYPES.items():
            for country_code, country_name in KEY_COUNTRIES.items():
                group_id = str(uuid4())
                topic_label = f"{event_label} in {country_name}"

                # Create metadata as JSON string
                metadata = {
                    "event_type": event_type,
                    "country": country_code,
                    "country_name": country_name,
                    "event_label": event_label,
                    "initialized": True,
                    "article_ids": [],
                }

                semantic_groups.append({
                    "group_id": group_id,
                    "article_count": 0,
                    "similarity_avg": 0.0,
                    "topic_label": topic_label,
                    "centroid_vector": "[" + ",".join(["0.0"] * 384) + "]",  # JSON string vector
                    "cluster_metadata": json.dumps(metadata),  # Convert dict to JSON string
                    "created_at": datetime.utcnow(),  # Offset-naive datetime for PostgreSQL
                    "updated_at": datetime.utcnow()   # Offset-naive datetime for PostgreSQL
                })
        
        # Insert semantic groups in batches
        batch_size = 50
        for i in range(0, len(semantic_groups), batch_size):
            batch = semantic_groups[i:i+batch_size]
            
            for group in batch:
                await conn.execute("""
                    INSERT INTO semantic_groups 
                    (group_id, article_count, similarity_avg, topic_label, centroid_vector, cluster_metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                group["group_id"],
                group["article_count"],
                group["similarity_avg"],
                group["topic_label"],
                group["centroid_vector"],
                group["cluster_metadata"],
                group["created_at"],
                group["updated_at"]
                )
        
        # Verify
        final_count = await conn.fetchval('SELECT COUNT(*) FROM semantic_groups;')
        await conn.close()
        
        logger.info(f"✓ Initialized {final_count} semantic groups (country+event combinations)")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error initializing semantic groups: {str(e)}", exc_info=True)
        return False

