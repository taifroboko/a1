"""
Result Storage - A1 Agentic System

Persistent storage system for execution results, analysis data, and system metrics.
Provides efficient storage, retrieval, and querying capabilities.

Based on the A1 research paper specifications.
"""

import asyncio
import json
import sqlite3
import aiosqlite
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from datetime import datetime, timedelta
import pickle
import gzip
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class StoredResult:
    """Stored execution result"""
    id: str
    contract_address: str
    network: str
    timestamp: float
    success: bool
    execution_time: float
    iterations_used: int
    strategies_generated: int
    exploits_found: int
    total_profit_potential: float
    confidence_score: float
    error_message: Optional[str]
    detailed_results: Optional[Dict[str, Any]]
    session_data: Optional[Dict[str, Any]]

class ResultStorage:
    """
    Advanced result storage system with SQLite backend.
    
    Provides persistent storage for execution results, analysis data,
    and comprehensive querying capabilities for historical analysis.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize result storage.
        
        Args:
            config: Configuration dictionary with storage settings
        """
        self.config = config
        
        self.db_path = Path(config.get('STORAGE_DB_PATH', 'a1_results.db'))
        self.data_dir = Path(config.get('STORAGE_DATA_DIR', 'data'))
        self.max_db_size = config.get('MAX_DB_SIZE_MB', 1000) * 1024 * 1024  # Convert to bytes
        self.compression_enabled = config.get('ENABLE_COMPRESSION', True)
        
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / 'sessions').mkdir(exist_ok=True)
        (self.data_dir / 'detailed_results').mkdir(exist_ok=True)
        
        self.db: Optional[aiosqlite.Connection] = None
        
        self.total_stored = 0
        self.total_retrieved = 0
        self.storage_errors = 0
    
    async def initialize(self):
        """Initialize the storage system."""
        try:
            self.db = await aiosqlite.connect(self.db_path)
            
            await self.db.execute("PRAGMA journal_mode=WAL")
            await self.db.execute("PRAGMA synchronous=NORMAL")
            await self.db.execute("PRAGMA cache_size=10000")
            
            await self._create_tables()
            
            await self._create_indexes()
            
            logger.info(f"Result storage initialized with database: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize result storage: {e}")
            raise
    
    async def _create_tables(self):
        """Create database tables."""
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS execution_results (
                id TEXT PRIMARY KEY,
                contract_address TEXT NOT NULL,
                network TEXT NOT NULL,
                timestamp REAL NOT NULL,
                success BOOLEAN NOT NULL,
                execution_time REAL NOT NULL,
                iterations_used INTEGER NOT NULL,
                strategies_generated INTEGER NOT NULL,
                exploits_found INTEGER NOT NULL,
                total_profit_potential REAL NOT NULL,
                confidence_score REAL NOT NULL,
                error_message TEXT,
                detailed_results_path TEXT,
                session_data_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS exploits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id TEXT NOT NULL,
                exploit_type TEXT NOT NULL,
                vulnerability_type TEXT NOT NULL,
                profit_potential REAL NOT NULL,
                confidence_score REAL NOT NULL,
                execution_steps TEXT,
                gas_estimate INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (result_id) REFERENCES execution_results (id)
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id TEXT NOT NULL,
                strategy_type TEXT NOT NULL,
                complexity_level TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                iteration INTEGER NOT NULL,
                execution_time REAL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (result_id) REFERENCES execution_results (id)
            )
        """)
        
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS iteration_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                iteration_number INTEGER NOT NULL,
                phase TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                exploits_found INTEGER NOT NULL,
                execution_time REAL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.db.commit()
    
    async def _create_indexes(self):
        """Create database indexes for performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_results_contract ON execution_results (contract_address)",
            "CREATE INDEX IF NOT EXISTS idx_results_network ON execution_results (network)",
            "CREATE INDEX IF NOT EXISTS idx_results_timestamp ON execution_results (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_results_success ON execution_results (success)",
            "CREATE INDEX IF NOT EXISTS idx_exploits_result ON exploits (result_id)",
            "CREATE INDEX IF NOT EXISTS idx_strategies_result ON strategies (result_id)"
        ]
        
        for index_sql in indexes:
            await self.db.execute(index_sql)
        
        await self.db.commit()
    
    async def store_result(self, session_id: str, result) -> str:
        """
        Store execution result.
        
        Args:
            session_id: Session identifier
            result: ExecutionResult object
            
        Returns:
            Stored result ID
        """
        try:
            result_id = self._generate_result_id(result.contract_address, time.time())
            
            detailed_results_path = None
            if result.detailed_results:
                detailed_results_path = await self._store_detailed_data(
                    result_id, "detailed_results", result.detailed_results
                )
            
            await self.db.execute("""
                INSERT INTO execution_results (
                    id, contract_address, network, timestamp, success,
                    execution_time, iterations_used, strategies_generated,
                    exploits_found, total_profit_potential, confidence_score,
                    error_message, detailed_results_path, session_data_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result_id, result.contract_address, result.network,
                time.time(), result.success, result.execution_time, 
                result.iterations_used, result.strategies_generated,
                result.exploits_found, result.total_profit_potential, 
                result.confidence_score, result.error_message, 
                detailed_results_path, None
            ))
            
            if result.detailed_results and 'best_exploits' in result.detailed_results:
                await self._store_exploits(result_id, result.detailed_results['best_exploits'])
            
            await self.db.commit()
            
            self.total_stored += 1
            logger.info(f"Stored result {result_id} for contract {result.contract_address}")
            
            return result_id
            
        except Exception as e:
            self.storage_errors += 1
            logger.error(f"Failed to store result for {result.contract_address}: {e}")
            raise
    
    def _generate_result_id(self, contract_address: str, timestamp: float) -> str:
        """Generate unique result ID."""
        data = f"{contract_address}_{timestamp}".encode()
        return hashlib.sha256(data).hexdigest()[:16]
    
    async def _store_detailed_data(self, result_id: str, data_type: str, data: Dict[str, Any]) -> str:
        """Store detailed data to file."""
        try:
            file_path = self.data_dir / data_type / f"{result_id}.json"
            
            if self.compression_enabled:
                file_path = file_path.with_suffix('.json.gz')
                with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)
            
            return str(file_path.relative_to(self.data_dir))
            
        except Exception as e:
            logger.error(f"Failed to store detailed data for {result_id}: {e}")
            return None
    
    async def _store_exploits(self, result_id: str, exploits: List[Dict[str, Any]]):
        """Store exploit details."""
        for exploit in exploits:
            strategy = exploit.get('strategy', {})
            execution_result = exploit.get('execution_result', {})
            
            await self.db.execute("""
                INSERT INTO exploits (
                    result_id, exploit_type, vulnerability_type,
                    profit_potential, confidence_score, execution_steps, gas_estimate
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result_id,
                strategy.get('execution_type', 'unknown'),
                strategy.get('vulnerability_type', 'unknown'),
                exploit.get('profit_potential', 0.0),
                exploit.get('confidence_score', 0.0),
                json.dumps(execution_result.get('execution_steps', [])),
                execution_result.get('gas_estimate', 0)
            ))
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            stats = {}
            
            cursor = await self.db.execute("SELECT COUNT(*) FROM execution_results")
            stats['total_results'] = (await cursor.fetchone())[0]
            
            cursor = await self.db.execute("SELECT COUNT(*) FROM execution_results WHERE success = 1")
            stats['successful_results'] = (await cursor.fetchone())[0]
            
            cursor = await self.db.execute("SELECT SUM(exploits_found) FROM execution_results")
            result = await cursor.fetchone()
            stats['total_exploits'] = result[0] if result[0] else 0
            
            cursor = await self.db.execute("SELECT SUM(total_profit_potential) FROM execution_results")
            result = await cursor.fetchone()
            stats['total_profit_potential'] = result[0] if result[0] else 0.0
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    async def close(self):
        """Close storage connections and cleanup."""
        try:
            if self.db:
                await self.db.close()
            
            logger.info("Result storage closed")
            
        except Exception as e:
            logger.error(f"Error closing result storage: {e}")
