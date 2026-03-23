"""
VeighNa Trader module.

This module provides the core trading functionality including:
- Event-driven architecture
- Trading engine
- Gateway system for connecting to exchanges
- Database abstraction layer
"""

# Import key modules to make them available at package level
from .database import get_database
from .engine import MainEngine
from .event import *
from .object import *
from .setting import SETTINGS

# Version info
__version__ = "4.0.0"

# Export database classes
from .database import BaseDatabase, BarOverview, TickOverview, convert_tz

# Export data objects
from .object import (
    BarData, TickData, OrderData, TradeData, PositionData,
    AccountData, ContractData, LogData
)

# Export constants
from .constant import *

# Export utility functions
from .utility import *