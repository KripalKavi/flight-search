from abc import ABC, abstractmethod
from typing import Dict, List
from datetime import datetime
import logging

class BaseScraper(ABC):
    """Abstract base class for flight scrapers"""

    def __init__(self, config: dict):
        self.config = config
        self.source_name = "Unknown"
        self.logger = logging.getLogger('flight_search')

    @abstractmethod
    def search_flights(self, origin: str, destination: str,
                      depart_date: str, return_date: str,
                      adults: int, children: int) -> List[Dict]:
        """
        Search for flights and return results.

        Returns:
            List of dicts with structure:
            {
                'source': 'Kayak',
                'economy': {'price': 450, 'currency': 'USD', 'available': True},
                'premium_economy': {'price': 750, 'currency': 'USD', 'available': True},
                'business': {'price': 1200, 'currency': 'USD', 'available': False}
            }
        """
        pass

    def format_date(self, date_str: str) -> str:
        """Convert date from YYYY-MM-DD to MM/DD/YYYY format"""
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%m/%d/%Y")

    def log(self, message: str):
        self.logger.info(f"[{self.source_name}] {message}")
