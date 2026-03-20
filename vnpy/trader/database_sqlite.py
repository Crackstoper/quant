"""
SQLite database backend implementation.

Provides VeighNa framework data persistence using SQLite database.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, TickData
from vnpy.trader.database import BaseDatabase, BarOverview, TickOverview, convert_tz
from vnpy.trader.setting import SETTINGS


class SqliteDatabase(BaseDatabase):
    """
    SQLite database backend implementation.

    Uses SQLite database to store and retrieve trading data with efficient
    querying capabilities and ACID transactions.
    """

    def __init__(self) -> None:
        """Initialize database connection."""
        # Get database configuration from settings
        self.db_path: str = SETTINGS["database.database"]
        self.db_file = Path(self.db_path)

        # Create directory if it doesn't exist
        self.db_file.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self.connect()

        # Initialize tables
        self.init_tables()

    def connect(self) -> None:
        """Create database connection."""
        try:
            self.conn = sqlite3.connect(
                self.db_file,
                detect_types=sqlite3.PARSE_DECLTYPES,
                timeout=30.0
            )
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(f"连接数据库失败: {e}")
            raise

    def init_tables(self) -> None:
        """Initialize database tables."""
        try:
            # Create bar data table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS bar_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    datetime TIMESTAMP NOT NULL,
                    interval TEXT,
                    volume REAL NOT NULL DEFAULT 0,
                    turnover REAL NOT NULL DEFAULT 0,
                    open_interest REAL NOT NULL DEFAULT 0,
                    open_price REAL NOT NULL DEFAULT 0,
                    high_price REAL NOT NULL DEFAULT 0,
                    low_price REAL NOT NULL DEFAULT 0,
                    close_price REAL NOT NULL DEFAULT 0,
                    gateway_name TEXT NOT NULL,

                    UNIQUE(symbol, exchange, datetime, interval)
                )
            """)

            # Create index for faster queries
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bar_symbol_exchange_datetime
                ON bar_data (symbol, exchange, datetime)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bar_datetime
                ON bar_data (datetime)
            """)

            # Create tick data table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tick_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    datetime TIMESTAMP NOT NULL,
                    name TEXT,
                    volume REAL NOT NULL DEFAULT 0,
                    turnover REAL NOT NULL DEFAULT 0,
                    open_interest REAL NOT NULL DEFAULT 0,
                    last_price REAL NOT NULL DEFAULT 0,
                    last_volume REAL NOT NULL DEFAULT 0,
                    limit_up REAL NOT NULL DEFAULT 0,
                    limit_down REAL NOT NULL DEFAULT 0,
                    open_price REAL NOT NULL DEFAULT 0,
                    high_price REAL NOT NULL DEFAULT 0,
                    low_price REAL NOT NULL DEFAULT 0,
                    pre_close REAL NOT NULL DEFAULT 0,
                    bid_price_1 REAL NOT NULL DEFAULT 0,
                    bid_price_2 REAL NOT NULL DEFAULT 0,
                    bid_price_3 REAL NOT NULL DEFAULT 0,
                    bid_price_4 REAL NOT NULL DEFAULT 0,
                    bid_price_5 REAL NOT NULL DEFAULT 0,
                    ask_price_1 REAL NOT NULL DEFAULT 0,
                    ask_price_2 REAL NOT NULL DEFAULT 0,
                    ask_price_3 REAL NOT NULL DEFAULT 0,
                    ask_price_4 REAL NOT NULL DEFAULT 0,
                    ask_price_5 REAL NOT NULL DEFAULT 0,
                    bid_volume_1 REAL NOT NULL DEFAULT 0,
                    bid_volume_2 REAL NOT NULL DEFAULT 0,
                    bid_volume_3 REAL NOT NULL DEFAULT 0,
                    bid_volume_4 REAL NOT NULL DEFAULT 0,
                    bid_volume_5 REAL NOT NULL DEFAULT 0,
                    ask_volume_1 REAL NOT NULL DEFAULT 0,
                    ask_volume_2 REAL NOT NULL DEFAULT 0,
                    ask_volume_3 REAL NOT NULL DEFAULT 0,
                    ask_volume_4 REAL NOT NULL DEFAULT 0,
                    ask_volume_5 REAL NOT NULL DEFAULT 0,
                    localtime TIMESTAMP,
                    gateway_name TEXT NOT NULL,

                    UNIQUE(symbol, exchange, datetime)
                )
            """)

            # Create index for tick data
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tick_symbol_exchange_datetime
                ON tick_data (symbol, exchange, datetime)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tick_datetime
                ON tick_data (datetime)
            """)

            # Create overview tables
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS bar_overview (
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    start TIMESTAMP,
                    end TIMESTAMP,
                    PRIMARY KEY (symbol, exchange, interval)
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tick_overview (
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    start TIMESTAMP,
                    end TIMESTAMP,
                    PRIMARY KEY (symbol, exchange)
                )
            """)

            self.conn.commit()
            print(f"数据库表初始化完成: {self.db_file}")

        except Exception as e:
            print(f"初始化数据库表失败: {e}")
            raise

    def save_bar_data(self, bars: List[BarData], stream: bool = False) -> bool:
        """
        Save bar data into database.

        Args:
            bars: BarData objects list
            stream: Whether is streaming data (append mode)

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            if not bars:
                return True

            # Get symbol information
            symbol = bars[0].symbol
            exchange = bars[0].exchange.value
            interval = bars[0].interval.value if bars[0].interval else "unknown"

            # Convert timezone if needed
            converted_bars = []
            for bar in bars:
                if hasattr(bar.datetime, 'astimezone'):
                    converted_bar = BarData(**{
                        "symbol": bar.symbol,
                        "exchange": bar.exchange,
                        "datetime": convert_tz(bar.datetime),
                        "interval": bar.interval,
                        "volume": bar.volume,
                        "turnover": bar.turnover,
                        "open_interest": bar.open_interest,
                        "open_price": bar.open_price,
                        "high_price": bar.high_price,
                        "low_price": bar.low_price,
                        "close_price": bar.close_price,
                        "gateway_name": bar.gateway_name
                    })
                else:
                    converted_bar = bar
                converted_bars.append(converted_bar)

            # Remove duplicates based on symbol, exchange, datetime, interval
            unique_bars = self._remove_duplicates(converted_bars)

            # Sort by datetime
            unique_bars.sort(key=lambda x: x.datetime)

            # Prepare data for batch insert
            bar_data_list = []
            for bar in unique_bars:
                bar_data = (
                    bar.symbol,
                    bar.exchange.value,
                    bar.datetime,
                    bar.interval.value if bar.interval else None,
                    float(bar.volume),
                    float(bar.turnover),
                    float(bar.open_interest),
                    float(bar.open_price),
                    float(bar.high_price),
                    float(bar.low_price),
                    float(bar.close_price),
                    bar.gateway_name
                )
                bar_data_list.append(bar_data)

            # Use INSERT OR REPLACE to handle duplicates
            self.cursor.executemany("""
                INSERT OR REPLACE INTO bar_data
                (symbol, exchange, datetime, interval, volume, turnover, open_interest,
                 open_price, high_price, low_price, close_price, gateway_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, bar_data_list)

            # Update overview
            self._update_bar_overview(symbol, exchange, interval, unique_bars)

            self.conn.commit()
            print(f"保存{symbol}的K线数据成功: {len(unique_bars)}条记录")
            return True

        except Exception as e:
            print(f"保存{symbol}的K线数据失败: {e}")
            self.conn.rollback()
            return False

    def save_tick_data(self, ticks: List[TickData], stream: bool = False) -> bool:
        """
        Save tick data into database.

        Args:
            ticks: TickData objects list
            stream: Whether is streaming data (append mode)

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            if not ticks:
                return True

            # Get symbol information
            symbol = ticks[0].symbol
            exchange = ticks[0].exchange.value

            # Convert timezone if needed
            converted_ticks = []
            for tick in ticks:
                if hasattr(tick.datetime, 'astimezone'):
                    converted_tick = TickData(**{
                        "symbol": tick.symbol,
                        "exchange": tick.exchange,
                        "datetime": convert_tz(tick.datetime),
                        "name": tick.name,
                        "volume": tick.volume,
                        "turnover": tick.turnover,
                        "open_interest": tick.open_interest,
                        "last_price": tick.last_price,
                        "last_volume": tick.last_volume,
                        "limit_up": tick.limit_up,
                        "limit_down": tick.limit_down,
                        "open_price": tick.open_price,
                        "high_price": tick.high_price,
                        "low_price": tick.low_price,
                        "pre_close": tick.pre_close,
                        "bid_price_1": tick.bid_price_1,
                        "bid_price_2": tick.bid_price_2,
                        "bid_price_3": tick.bid_price_3,
                        "bid_price_4": tick.bid_price_4,
                        "bid_price_5": tick.bid_price_5,
                        "ask_price_1": tick.ask_price_1,
                        "ask_price_2": tick.ask_price_2,
                        "ask_price_3": tick.ask_price_3,
                        "ask_price_4": tick.ask_price_4,
                        "ask_price_5": tick.ask_price_5,
                        "bid_volume_1": tick.bid_volume_1,
                        "bid_volume_2": tick.bid_volume_2,
                        "bid_volume_3": tick.bid_volume_3,
                        "bid_volume_4": tick.bid_volume_4,
                        "bid_volume_5": tick.bid_volume_5,
                        "ask_volume_1": tick.ask_volume_1,
                        "ask_volume_2": tick.ask_volume_2,
                        "ask_volume_3": tick.ask_volume_3,
                        "ask_volume_4": tick.ask_volume_4,
                        "ask_volume_5": tick.ask_volume_5,
                        "localtime": tick.localtime,
                        "gateway_name": tick.gateway_name
                    })
                else:
                    converted_tick = tick
                converted_ticks.append(converted_tick)

            # Remove duplicates based on symbol, exchange, datetime
            unique_ticks = self._remove_ticks_duplicates(converted_ticks)

            # Sort by datetime
            unique_ticks.sort(key=lambda x: x.datetime or datetime.now())

            # Prepare data for batch insert
            tick_data_list = []
            for tick in unique_ticks:
                tick_data = (
                    tick.symbol,
                    tick.exchange.value,
                    tick.datetime,
                    tick.name,
                    float(tick.volume),
                    float(tick.turnover),
                    float(tick.open_interest),
                    float(tick.last_price),
                    float(tick.last_volume),
                    float(tick.limit_up),
                    float(tick.limit_down),
                    float(tick.open_price),
                    float(tick.high_price),
                    float(tick.low_price),
                    float(tick.pre_close),
                    float(tick.bid_price_1),
                    float(tick.bid_price_2),
                    float(tick.bid_price_3),
                    float(tick.bid_price_4),
                    float(tick.bid_price_5),
                    float(tick.ask_price_1),
                    float(tick.ask_price_2),
                    float(tick.ask_price_3),
                    float(tick.ask_price_4),
                    float(tick.ask_price_5),
                    float(tick.bid_volume_1),
                    float(tick.bid_volume_2),
                    float(tick.bid_volume_3),
                    float(tick.bid_volume_4),
                    float(tick.bid_volume_5),
                    float(tick.ask_volume_1),
                    float(tick.ask_volume_2),
                    float(tick.ask_volume_3),
                    float(tick.ask_volume_4),
                    float(tick.ask_volume_5),
                    tick.localtime,
                    tick.gateway_name
                )
                tick_data_list.append(tick_data)

            # Use INSERT OR REPLACE to handle duplicates
            self.cursor.executemany("""
                INSERT OR REPLACE INTO tick_data
                (symbol, exchange, datetime, name, volume, turnover, open_interest,
                 last_price, last_volume, limit_up, limit_down, open_price, high_price,
                 low_price, pre_close, bid_price_1, bid_price_2, bid_price_3, bid_price_4, bid_price_5,
                 ask_price_1, ask_price_2, ask_price_3, ask_price_4, ask_price_5,
                 bid_volume_1, bid_volume_2, bid_volume_3, bid_volume_4, bid_volume_5,
                 ask_volume_1, ask_volume_2, ask_volume_3, ask_volume_4, ask_volume_5,
                 localtime, gateway_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tick_data_list)

            # Update overview
            self._update_tick_overview(symbol, exchange, unique_ticks)

            self.conn.commit()
            print(f"保存{symbol}的Tick数据成功: {len(unique_ticks)}条记录")
            return True

        except Exception as e:
            print(f"保存{symbol}的Tick数据失败: {e}")
            self.conn.rollback()
            return False

    def load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """
        Load bar data from database.

        Args:
            symbol: Stock symbol
            exchange: Exchange
            interval: K-line period
            start: Start time
            end: End time

        Returns:
            List[BarData]: Bar data list
        """
        try:
            query = """
                SELECT * FROM bar_data
                WHERE symbol = ? AND exchange = ? AND datetime >= ? AND datetime <= ?
                ORDER BY datetime
            """

            params = [
                symbol,
                exchange.value,
                start,
                end
            ]

            # Add interval filter if specified
            if interval:
                query += " AND interval = ?"
                params.append(interval.value)

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            bars = []
            for row in rows:
                bar = BarData(
                    symbol=row["symbol"],
                    exchange=Exchange(row["exchange"]),
                    datetime=row["datetime"],
                    interval=Interval(row["interval"]) if row["interval"] else None,
                    volume=row["volume"],
                    turnover=row["turnover"],
                    open_interest=row["open_interest"],
                    open_price=row["open_price"],
                    high_price=row["high_price"],
                    low_price=row["low_price"],
                    close_price=row["close_price"],
                    gateway_name=row["gateway_name"]
                )
                bars.append(bar)

            print(f"加载{symbol}的K线数据成功: {len(bars)}条记录")
            return bars

        except Exception as e:
            print(f"加载{symbol}的K线数据失败: {e}")
            return []

    def load_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """
        Load tick data from database.

        Args:
            symbol: Stock symbol
            exchange: Exchange
            start: Start time
            end: End time

        Returns:
            List[TickData]: Tick data list
        """
        try:
            query = """
                SELECT * FROM tick_data
                WHERE symbol = ? AND exchange = ? AND datetime >= ? AND datetime <= ?
                ORDER BY datetime
            """

            params = [
                symbol,
                exchange.value,
                start,
                end
            ]

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            ticks = []
            for row in rows:
                tick = TickData(
                    symbol=row["symbol"],
                    exchange=Exchange(row["exchange"]),
                    datetime=row["datetime"],
                    name=row["name"],
                    volume=row["volume"],
                    turnover=row["turnover"],
                    open_interest=row["open_interest"],
                    last_price=row["last_price"],
                    last_volume=row["last_volume"],
                    limit_up=row["limit_up"],
                    limit_down=row["limit_down"],
                    open_price=row["open_price"],
                    high_price=row["high_price"],
                    low_price=row["low_price"],
                    pre_close=row["pre_close"],
                    bid_price_1=row["bid_price_1"],
                    bid_price_2=row["bid_price_2"],
                    bid_price_3=row["bid_price_3"],
                    bid_price_4=row["bid_price_4"],
                    bid_price_5=row["bid_price_5"],
                    ask_price_1=row["ask_price_1"],
                    ask_price_2=row["ask_price_2"],
                    ask_price_3=row["ask_price_3"],
                    ask_price_4=row["ask_price_4"],
                    ask_price_5=row["ask_price_5"],
                    bid_volume_1=row["bid_volume_1"],
                    bid_volume_2=row["bid_volume_2"],
                    bid_volume_3=row["bid_volume_3"],
                    bid_volume_4=row["bid_volume_4"],
                    bid_volume_5=row["bid_volume_5"],
                    ask_volume_1=row["ask_volume_1"],
                    ask_volume_2=row["ask_volume_2"],
                    ask_volume_3=row["ask_volume_3"],
                    ask_volume_4=row["ask_volume_4"],
                    ask_volume_5=row["ask_volume_5"],
                    localtime=row["localtime"],
                    gateway_name=row["gateway_name"]
                )
                ticks.append(tick)

            print(f"加载{symbol}的Tick数据成功: {len(ticks)}条记录")
            return ticks

        except Exception as e:
            print(f"加载{symbol}的Tick数据失败: {e}")
            return []

    def delete_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval
    ) -> int:
        """
        Delete all bar data with given symbol + exchange + interval.

        Args:
            symbol: Stock symbol
            exchange: Exchange
            interval: K-line period

        Returns:
            int: Number of deleted records
        """
        try:
            # Build query based on whether interval is specified
            if interval:
                query = """
                    DELETE FROM bar_data
                    WHERE symbol = ? AND exchange = ? AND interval = ?
                """
                params = [symbol, exchange.value, interval.value]
            else:
                query = """
                    DELETE FROM bar_data
                    WHERE symbol = ? AND exchange = ?
                """
                params = [symbol, exchange.value]

            self.cursor.execute(query, params)
            deleted_count = self.cursor.rowcount

            # Clear overview
            if interval:
                self.cursor.execute("""
                    DELETE FROM bar_overview
                    WHERE symbol = ? AND exchange = ? AND interval = ?
                """, [symbol, exchange.value, interval.value])
            else:
                self.cursor.execute("""
                    DELETE FROM bar_overview
                    WHERE symbol = ? AND exchange = ?
                """, [symbol, exchange.value])

            self.conn.commit()
            print(f"删除{symbol}的K线数据成功: {deleted_count}条记录")
            return deleted_count

        except Exception as e:
            print(f"删除{symbol}的K线数据失败: {e}")
            self.conn.rollback()
            return 0

    def delete_tick_data(
        self,
        symbol: str,
        exchange: Exchange
    ) -> int:
        """
        Delete all tick data with given symbol + exchange.

        Args:
            symbol: Stock symbol
            exchange: Exchange

        Returns:
            int: Number of deleted records
        """
        try:
            query = """
                DELETE FROM tick_data
                WHERE symbol = ? AND exchange = ?
            """
            params = [symbol, exchange.value]

            self.cursor.execute(query, params)
            deleted_count = self.cursor.rowcount

            # Clear overview
            self.cursor.execute("""
                DELETE FROM tick_overview
                WHERE symbol = ? AND exchange = ?
            """, [symbol, exchange.value])

            self.conn.commit()
            print(f"删除{symbol}的Tick数据成功: {deleted_count}条记录")
            return deleted_count

        except Exception as e:
            print(f"删除{symbol}的Tick数据失败: {e}")
            self.conn.rollback()
            return 0

    def get_bar_overview(self) -> List[BarOverview]:
        """
        Return bar data available in database.

        Returns:
            List[BarOverview]: Data overview list
        """
        try:
            query = """
                SELECT symbol, exchange, interval, COUNT(*) as count,
                       MIN(datetime) as start_time, MAX(datetime) as end_time
                FROM bar_data
                GROUP BY symbol, exchange, interval
                ORDER BY symbol, exchange, interval
            """

            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            overviews = []
            for row in rows:
                # Convert string back to proper types
                exchange_obj = Exchange(row["exchange"])
                interval_obj = Interval(row["interval"]) if row["interval"] else None

                overview = BarOverview(
                    symbol=row["symbol"],
                    exchange=exchange_obj,
                    interval=interval_obj,
                    count=row["count"],
                    start=row["start_time"],
                    end=row["end_time"]
                )
                overviews.append(overview)

            print(f"获取K线数据概览成功: {len(overviews)}个数据集")
            return overviews

        except Exception as e:
            print(f"获取K线数据概览失败: {e}")
            return []

    def get_tick_overview(self) -> List[TickOverview]:
        """
        Return tick data available in database.

        Returns:
            List[TickOverview]: Data overview list
        """
        try:
            query = """
                SELECT symbol, exchange, COUNT(*) as count,
                       MIN(datetime) as start_time, MAX(datetime) as end_time
                FROM tick_data
                GROUP BY symbol, exchange
                ORDER BY symbol, exchange
            """

            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            overviews = []
            for row in rows:
                # Convert string back to proper types
                exchange_obj = Exchange(row["exchange"])

                overview = TickOverview(
                    symbol=row["symbol"],
                    exchange=exchange_obj,
                    count=row["count"],
                    start=row["start_time"],
                    end=row["end_time"]
                )
                overviews.append(overview)

            print(f"获取Tick数据概览成功: {len(overviews)}个数据集")
            return overviews

        except Exception as e:
            print(f"获取Tick数据概览失败: {e}")
            return []

    def _remove_duplicates(self, bars: List[BarData]) -> List[BarData]:
        """Remove duplicate bar data."""
        seen = set()
        unique_bars = []

        for bar in bars:
            key = (bar.symbol, bar.exchange.value, bar.datetime)
            if key not in seen:
                seen.add(key)
                unique_bars.append(bar)

        return unique_bars

    def _remove_ticks_duplicates(self, ticks: List[TickData]) -> List[TickData]:
        """Remove duplicate tick data."""
        seen = set()
        unique_ticks = []

        for tick in ticks:
            key = (tick.symbol, tick.exchange.value, tick.datetime)
            if key not in seen:
                seen.add(key)
                unique_ticks.append(tick)

        return unique_ticks

    def _update_bar_overview(self, symbol: str, exchange: str, interval: str, bars: List[BarData]) -> None:
        """Update bar data overview."""
        try:
            if not bars:
                return

            start_dt = bars[0].datetime
            end_dt = bars[-1].datetime

            # Insert or replace overview
            self.cursor.execute("""
                INSERT OR REPLACE INTO bar_overview
                (symbol, exchange, interval, count, start, end)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [symbol, exchange, interval, len(bars), start_dt, end_dt])

        except Exception as e:
            print(f"更新K线数据概览失败: {e}")

    def _update_tick_overview(self, symbol: str, exchange: str, ticks: List[TickData]) -> None:
        """Update tick data overview."""
        try:
            if not ticks:
                return

            start_dt = ticks[0].datetime
            end_dt = ticks[-1].datetime

            # Insert or replace overview
            self.cursor.execute("""
                INSERT OR REPLACE INTO tick_overview
                (symbol, exchange, count, start, end)
                VALUES (?, ?, ?, ?, ?)
            """, [symbol, exchange, len(ticks), start_dt, end_dt])

        except Exception as e:
            print(f"更新Tick数据概览失败: {e}")

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()

    def __del__(self) -> None:
        """Destructor to ensure connection is closed."""
        self.close()


# Create database instance
database = None

def get_database() -> SqliteDatabase:
    """Get SQLite database instance."""
    global database
    if database is None:
        database = SqliteDatabase()
    return database

# Export for easy importing
Database = SqliteDatabase