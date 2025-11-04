"""Entity linking module."""
from src.linking.dbpedia_client import DBpediaSpotlightClient
from src.linking.opensanctions_client import OpenSanctionsClient

__all__ = [
    "DBpediaSpotlightClient",
    "OpenSanctionsClient",
]

