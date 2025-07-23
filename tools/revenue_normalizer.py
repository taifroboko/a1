"""
Revenue Normalizer Tool - A1 Agentic System

This tool implements token balance reconciliation and economic validation,
ensuring the agent can accurately assess exploit profitability across
different tokens and blockchain networks with real-time price data.

Based on the A1 research paper specifications.
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from decimal import Decimal, getcontext
from web3 import Web3
from eth_utils import to_checksum_address
import logging
import time

logger = logging.getLogger(__name__)

getcontext().prec = 28

@dataclass
class TokenInfo:
    """Container for token information"""
    address: str
    symbol: str
    name: str
    decimals: int
    chain_id: int
    price_usd: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    volume_24h: Optional[Decimal] = None

@dataclass
class BalanceSnapshot:
    """Container for balance snapshot"""
    address: str
    token_address: str
    balance_raw: int
    balance_normalized: Decimal
    balance_usd: Optional[Decimal]
    block_number: int
    timestamp: int

@dataclass
class ProfitabilityAnalysis:
    """Container for profitability analysis results"""
    total_profit_usd: Decimal
    profit_by_token: Dict[str, Decimal]
    gas_cost_usd: Decimal
    net_profit_usd: Decimal
    roi_percentage: Decimal
    execution_cost_breakdown: Dict[str, Decimal]
    risk_metrics: Dict[str, Any]

class RevenueNormalizer:
    """
    Implements token balance reconciliation and economic validation.
    
    Provides accurate profitability assessment across different tokens
    and blockchain networks with real-time price data integration.
    """
    
    def __init__(self, web3_clients: Dict[str, Web3], price_apis: Optional[List[str]] = None):
        """
        Initialize the revenue normalizer.
        
        Args:
            web3_clients: Dictionary mapping chain names to Web3 instances
            price_apis: List of price API endpoints (defaults to common ones)
        """
        self.web3_clients = web3_clients
        self.price_apis = price_apis or [
            "https://api.coingecko.com/api/v3",
            "https://api.coinmarketcap.com/v1",
            "https://api.1inch.io/v5.0"
        ]
        
        self.token_cache: Dict[str, TokenInfo] = {}
        self.price_cache: Dict[str, Tuple[Decimal, int]] = {}  # (price, timestamp)
        self.cache_ttl = 300  # 5 minutes
        
        self.COMMON_TOKENS = {
            1: {  # Ethereum
                'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                'USDC': '0xA0b86a33E6441b8C4505E2c8C5b8b8b8b8b8b8b8',
                'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
                'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'
            },
            56: {  # BSC
                'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
                'BUSD': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
                'USDT': '0x55d398326f99059fF775485246999027B3197955',
                'CAKE': '0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82'
            }
        }
        
        self.gas_prices: Dict[int, Decimal] = {}
    
    async def get_token_info(self, token_address: str, chain_id: int) -> TokenInfo:
        """
        Get comprehensive token information.
        
        Args:
            token_address: Token contract address
            chain_id: Blockchain chain ID
            
        Returns:
            TokenInfo object with token details
        """
        cache_key = f"{chain_id}:{token_address.lower()}"
        
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        token_address = to_checksum_address(token_address)
        
        web3_client = self._get_web3_client(chain_id)
        
        erc20_abi = [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
        ]
        
        try:
            contract = web3_client.eth.contract(address=token_address, abi=erc20_abi)
            
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            
            price_usd = await self._get_token_price(symbol, chain_id)
            
            token_info = TokenInfo(
                address=token_address,
                symbol=symbol,
                name=name,
                decimals=decimals,
                chain_id=chain_id,
                price_usd=price_usd
            )
            
            self.token_cache[cache_key] = token_info
            return token_info
            
        except Exception as e:
            logger.error(f"Failed to get token info for {token_address}: {e}")
            
            return TokenInfo(
                address=token_address,
                symbol="UNKNOWN",
                name="Unknown Token",
                decimals=18,
                chain_id=chain_id
            )
    
    def _get_web3_client(self, chain_id: int) -> Web3:
        """Get Web3 client for specified chain."""
        for chain_name, client in self.web3_clients.items():
            if client.eth.chain_id == chain_id:
                return client
        
        raise ValueError(f"No Web3 client available for chain ID {chain_id}")
    
    async def _get_token_price(self, symbol: str, chain_id: int) -> Optional[Decimal]:
        """Get token price in USD from multiple sources."""
        cache_key = f"{symbol}:{chain_id}"
        
        if cache_key in self.price_cache:
            price, timestamp = self.price_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return price
        
        price = await self._fetch_price_coingecko(symbol)
        
        if price is None:
            price = await self._fetch_price_1inch(symbol, chain_id)
        
        if price is not None:
            self.price_cache[cache_key] = (price, int(time.time()))
        
        return price
    
    async def _fetch_price_coingecko(self, symbol: str) -> Optional[Decimal]:
        """Fetch price from CoinGecko API."""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if symbol.lower() in data and 'usd' in data[symbol.lower()]:
                            return Decimal(str(data[symbol.lower()]['usd']))
        
        except Exception as e:
            logger.warning(f"CoinGecko price fetch failed for {symbol}: {e}")
        
        return None
    
    async def _fetch_price_1inch(self, symbol: str, chain_id: int) -> Optional[Decimal]:
        """Fetch price from 1inch API."""
        try:
            network_map = {1: "1", 56: "56", 137: "137"}
            
            if chain_id not in network_map:
                return None
            
            network = network_map[chain_id]
            url = f"https://api.1inch.io/v5.0/{network}/quote"
            
            usdc_address = self.COMMON_TOKENS.get(chain_id, {}).get('USDC')
            if not usdc_address:
                return None
            
            params = {
                'fromTokenAddress': usdc_address,
                'toTokenAddress': self._get_token_address_by_symbol(symbol, chain_id),
                'amount': '1000000'  # 1 USDC (6 decimals)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'toTokenAmount' in data:
                            to_amount = Decimal(data['toTokenAmount'])
                            return Decimal('1') / to_amount if to_amount > 0 else None
        
        except Exception as e:
            logger.warning(f"1inch price fetch failed for {symbol}: {e}")
        
        return None
    
    def _get_token_address_by_symbol(self, symbol: str, chain_id: int) -> Optional[str]:
        """Get token address by symbol for a specific chain."""
        chain_tokens = self.COMMON_TOKENS.get(chain_id, {})
        return chain_tokens.get(symbol.upper())
    
    async def capture_balance_snapshot(self, address: str, token_addresses: List[str], chain_id: int, block_number: Optional[int] = None) -> List[BalanceSnapshot]:
        """
        Capture balance snapshot for multiple tokens.
        
        Args:
            address: Address to check balances for
            token_addresses: List of token contract addresses
            chain_id: Blockchain chain ID
            block_number: Block number for historical snapshot
            
        Returns:
            List of balance snapshots
        """
        web3_client = self._get_web3_client(chain_id)
        block_identifier = block_number or 'latest'
        
        if block_number:
            block_info = web3_client.eth.get_block(block_number)
            timestamp = block_info.timestamp
            actual_block = block_number
        else:
            block_info = web3_client.eth.get_block('latest')
            timestamp = block_info.timestamp
            actual_block = block_info.number
        
        snapshots = []
        
        native_balance = web3_client.eth.get_balance(address, block_identifier)
        native_symbol = 'ETH' if chain_id == 1 else 'BNB' if chain_id == 56 else 'NATIVE'
        native_price = await self._get_token_price(native_symbol, chain_id)
        
        native_balance_normalized = Decimal(native_balance) / Decimal(10 ** 18)
        native_balance_usd = native_balance_normalized * native_price if native_price else None
        
        snapshots.append(BalanceSnapshot(
            address=address,
            token_address='0x0000000000000000000000000000000000000000',  # Native token
            balance_raw=native_balance,
            balance_normalized=native_balance_normalized,
            balance_usd=native_balance_usd,
            block_number=actual_block,
            timestamp=timestamp
        ))
        
        erc20_abi = [
            {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}
        ]
        
        for token_address in token_addresses:
            try:
                token_info = await self.get_token_info(token_address, chain_id)
                contract = web3_client.eth.contract(address=token_address, abi=erc20_abi)
                
                balance_raw = contract.functions.balanceOf(address).call(block_identifier=block_identifier)
                balance_normalized = Decimal(balance_raw) / Decimal(10 ** token_info.decimals)
                balance_usd = balance_normalized * token_info.price_usd if token_info.price_usd else None
                
                snapshots.append(BalanceSnapshot(
                    address=address,
                    token_address=token_address,
                    balance_raw=balance_raw,
                    balance_normalized=balance_normalized,
                    balance_usd=balance_usd,
                    block_number=actual_block,
                    timestamp=timestamp
                ))
                
            except Exception as e:
                logger.error(f"Failed to get balance for token {token_address}: {e}")
        
        return snapshots
    
    async def calculate_profit_loss(self, before_snapshots: List[BalanceSnapshot], after_snapshots: List[BalanceSnapshot]) -> Dict[str, Any]:
        """
        Calculate profit/loss between two balance snapshots.
        
        Args:
            before_snapshots: Balance snapshots before operation
            after_snapshots: Balance snapshots after operation
            
        Returns:
            Detailed profit/loss analysis
        """
        before_balances = {snap.token_address: snap for snap in before_snapshots}
        after_balances = {snap.token_address: snap for snap in after_snapshots}
        
        all_tokens = set(before_balances.keys()) | set(after_balances.keys())
        
        profit_loss = {
            'total_profit_usd': Decimal('0'),
            'total_loss_usd': Decimal('0'),
            'net_profit_usd': Decimal('0'),
            'token_changes': {},
            'percentage_changes': {},
            'significant_changes': []
        }
        
        for token_address in all_tokens:
            before_snap = before_balances.get(token_address)
            after_snap = after_balances.get(token_address)
            
            before_balance = before_snap.balance_normalized if before_snap else Decimal('0')
            after_balance = after_snap.balance_normalized if after_snap else Decimal('0')
            balance_change = after_balance - before_balance
            
            before_usd = before_snap.balance_usd if before_snap and before_snap.balance_usd else Decimal('0')
            after_usd = after_snap.balance_usd if after_snap and after_snap.balance_usd else Decimal('0')
            usd_change = after_usd - before_usd
            
            if balance_change != 0 or usd_change != 0:
                token_info = await self.get_token_info(token_address, before_snap.chain_id if before_snap else after_snap.chain_id)
                
                profit_loss['token_changes'][token_address] = {
                    'symbol': token_info.symbol,
                    'balance_change': balance_change,
                    'usd_change': usd_change,
                    'before_balance': before_balance,
                    'after_balance': after_balance,
                    'before_usd': before_usd,
                    'after_usd': after_usd
                }
                
                if before_balance > 0:
                    percentage_change = (balance_change / before_balance) * 100
                    profit_loss['percentage_changes'][token_address] = percentage_change
                
                if abs(usd_change) > 100 or (before_usd > 0 and abs(usd_change / before_usd) > 0.01):
                    profit_loss['significant_changes'].append({
                        'token': token_info.symbol,
                        'address': token_address,
                        'usd_change': usd_change,
                        'percentage_change': profit_loss['percentage_changes'].get(token_address, 0)
                    })
                
                if usd_change > 0:
                    profit_loss['total_profit_usd'] += usd_change
                else:
                    profit_loss['total_loss_usd'] += abs(usd_change)
        
        profit_loss['net_profit_usd'] = profit_loss['total_profit_usd'] - profit_loss['total_loss_usd']
        
        return profit_loss
    
    async def analyze_exploit_profitability(self, exploit_results: Dict[str, Any], gas_costs: List[Dict[str, Any]]) -> ProfitabilityAnalysis:
        """
        Comprehensive profitability analysis for exploit strategies.
        
        Args:
            exploit_results: Results from exploit execution including balance changes
            gas_costs: List of gas cost information for each transaction
            
        Returns:
            ProfitabilityAnalysis with detailed economic assessment
        """
        total_gas_cost_usd = Decimal('0')
        gas_breakdown = {}
        
        for gas_info in gas_costs:
            chain_id = gas_info.get('chain_id', 1)
            gas_used = gas_info.get('gas_used', 0)
            gas_price = gas_info.get('gas_price', 0)
            
            if gas_price == 0:
                gas_price = await self._get_current_gas_price(chain_id)
            
            gas_cost_native = Decimal(gas_used * gas_price) / Decimal(10 ** 18)
            
            native_symbol = 'ETH' if chain_id == 1 else 'BNB' if chain_id == 56 else 'NATIVE'
            native_price = await self._get_token_price(native_symbol, chain_id)
            
            gas_cost_usd = gas_cost_native * native_price if native_price else Decimal('0')
            total_gas_cost_usd += gas_cost_usd
            
            gas_breakdown[f"tx_{len(gas_breakdown)}"] = {
                'chain_id': chain_id,
                'gas_used': gas_used,
                'gas_price': gas_price,
                'cost_native': gas_cost_native,
                'cost_usd': gas_cost_usd
            }
        
        profit_by_token = exploit_results.get('token_changes', {})
        total_profit_usd = sum(
            change.get('usd_change', Decimal('0')) 
            for change in profit_by_token.values() 
            if change.get('usd_change', Decimal('0')) > 0
        )
        
        net_profit_usd = total_profit_usd - total_gas_cost_usd
        
        initial_investment = total_gas_cost_usd  # Minimum investment is gas costs
        roi_percentage = (net_profit_usd / max(initial_investment, Decimal('0.01'))) * 100
        
        risk_metrics = await self._assess_exploit_risks(exploit_results, gas_costs)
        
        return ProfitabilityAnalysis(
            total_profit_usd=total_profit_usd,
            profit_by_token={addr: change.get('usd_change', Decimal('0')) for addr, change in profit_by_token.items()},
            gas_cost_usd=total_gas_cost_usd,
            net_profit_usd=net_profit_usd,
            roi_percentage=roi_percentage,
            execution_cost_breakdown=gas_breakdown,
            risk_metrics=risk_metrics
        )
    
    async def _get_current_gas_price(self, chain_id: int) -> int:
        """Get current gas price for a chain."""
        if chain_id in self.gas_prices:
            return self.gas_prices[chain_id]
        
        try:
            web3_client = self._get_web3_client(chain_id)
            gas_price = web3_client.eth.gas_price
            self.gas_prices[chain_id] = gas_price
            return gas_price
        except Exception as e:
            logger.warning(f"Failed to get gas price for chain {chain_id}: {e}")
            return 20_000_000_000 if chain_id == 1 else 5_000_000_000  # 20 gwei for ETH, 5 gwei for BSC
    
    async def _assess_exploit_risks(self, exploit_results: Dict[str, Any], gas_costs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess risks associated with exploit execution."""
        risks = {
            'liquidity_risk': 'low',
            'slippage_risk': 'low',
            'mev_risk': 'medium',
            'detection_risk': 'medium',
            'revert_probability': 0.1,
            'max_extractable_value': Decimal('0'),
            'time_sensitivity': 'low'
        }
        
        tx_count = len(gas_costs)
        if tx_count > 5:
            risks['detection_risk'] = 'high'
            risks['revert_probability'] = 0.3
        elif tx_count > 2:
            risks['detection_risk'] = 'medium'
            risks['revert_probability'] = 0.2
        
        total_profit = exploit_results.get('net_profit_usd', Decimal('0'))
        if total_profit > 10000:  # $10k+
            risks['mev_risk'] = 'high'
            risks['time_sensitivity'] = 'high'
        elif total_profit > 1000:  # $1k+
            risks['mev_risk'] = 'medium'
            risks['time_sensitivity'] = 'medium'
        
        risks['max_extractable_value'] = total_profit * Decimal('0.9')  # Assume 10% slippage
        
        return risks
    
    async def normalize_cross_chain_balances(self, balances: Dict[int, List[BalanceSnapshot]]) -> Dict[str, Any]:
        """
        Normalize balances across multiple chains for comparison.
        
        Args:
            balances: Dictionary mapping chain IDs to balance snapshots
            
        Returns:
            Normalized cross-chain balance analysis
        """
        normalized = {
            'total_value_usd': Decimal('0'),
            'value_by_chain': {},
            'value_by_token': {},
            'largest_holdings': [],
            'chain_distribution': {}
        }
        
        all_snapshots = []
        for chain_id, snapshots in balances.items():
            all_snapshots.extend(snapshots)
        
        token_totals = {}
        
        for snapshot in all_snapshots:
            if snapshot.balance_usd:
                normalized['total_value_usd'] += snapshot.balance_usd
                
                chain_name = self._get_chain_name(snapshot.token_address, snapshot.block_number)
                if chain_name not in normalized['value_by_chain']:
                    normalized['value_by_chain'][chain_name] = Decimal('0')
                normalized['value_by_chain'][chain_name] += snapshot.balance_usd
                
                token_info = await self.get_token_info(snapshot.token_address, getattr(snapshot, 'chain_id', 1))
                symbol = token_info.symbol
                
                if symbol not in token_totals:
                    token_totals[symbol] = {
                        'total_usd': Decimal('0'),
                        'total_balance': Decimal('0'),
                        'chains': set()
                    }
                
                token_totals[symbol]['total_usd'] += snapshot.balance_usd
                token_totals[symbol]['total_balance'] += snapshot.balance_normalized
                token_totals[symbol]['chains'].add(chain_name)
        
        normalized['value_by_token'] = {
            symbol: {
                'total_usd': data['total_usd'],
                'total_balance': data['total_balance'],
                'chains': list(data['chains'])
            }
            for symbol, data in sorted(token_totals.items(), key=lambda x: x[1]['total_usd'], reverse=True)
        }
        
        if normalized['total_value_usd'] > 0:
            for chain, value in normalized['value_by_chain'].items():
                percentage = (value / normalized['total_value_usd']) * 100
                normalized['chain_distribution'][chain] = {
                    'value_usd': value,
                    'percentage': percentage
                }
        
        for snapshot in sorted(all_snapshots, key=lambda x: x.balance_usd or Decimal('0'), reverse=True)[:10]:
            if snapshot.balance_usd and snapshot.balance_usd > 0:
                token_info = await self.get_token_info(snapshot.token_address, getattr(snapshot, 'chain_id', 1))
                normalized['largest_holdings'].append({
                    'symbol': token_info.symbol,
                    'address': snapshot.address,
                    'token_address': snapshot.token_address,
                    'balance': snapshot.balance_normalized,
                    'value_usd': snapshot.balance_usd,
                    'chain': self._get_chain_name(snapshot.token_address, snapshot.block_number)
                })
        
        return normalized
    
    def _get_chain_name(self, token_address: str, block_number: int) -> str:
        """Get human-readable chain name."""
        if token_address == '0x0000000000000000000000000000000000000000':
            return 'ethereum'  # Native token assumption
        return 'ethereum'  # Default assumption
    
    async def calculate_arbitrage_opportunities(self, token_prices: Dict[str, Dict[int, Decimal]]) -> List[Dict[str, Any]]:
        """
        Calculate arbitrage opportunities across chains.
        
        Args:
            token_prices: Dictionary mapping token symbols to chain_id -> price mappings
            
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        
        for symbol, chain_prices in token_prices.items():
            if len(chain_prices) < 2:
                continue
            
            min_price = min(chain_prices.values())
            max_price = max(chain_prices.values())
            
            min_chain = next(chain for chain, price in chain_prices.items() if price == min_price)
            max_chain = next(chain for chain, price in chain_prices.items() if price == max_price)
            
            if min_price > 0:
                profit_percentage = ((max_price - min_price) / min_price) * 100
                
                if profit_percentage > 0.5:
                    opportunities.append({
                        'token': symbol,
                        'buy_chain': min_chain,
                        'sell_chain': max_chain,
                        'buy_price': min_price,
                        'sell_price': max_price,
                        'profit_percentage': profit_percentage,
                        'estimated_profit_per_unit': max_price - min_price
                    })
        
        return sorted(opportunities, key=lambda x: x['profit_percentage'], reverse=True)
    
    async def validate_economic_assumptions(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate economic assumptions in an exploit strategy.
        
        Args:
            strategy: Exploit strategy with economic parameters
            
        Returns:
            Validation results with recommendations
        """
        validation = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': [],
            'risk_score': 0.0
        }
        
        expected_profit = strategy.get('expected_profit_usd', Decimal('0'))
        if expected_profit < 100:  # $100 minimum
            validation['warnings'].append("Expected profit below $100 minimum threshold")
            validation['risk_score'] += 0.2
        
        gas_costs = strategy.get('estimated_gas_cost_usd', Decimal('0'))
        if gas_costs > 0 and expected_profit > 0:
            gas_ratio = gas_costs / expected_profit
            if gas_ratio > 0.5:  # Gas costs >50% of profit
                validation['warnings'].append(f"High gas cost ratio: {gas_ratio:.2%}")
                validation['risk_score'] += 0.3
        
        required_liquidity = strategy.get('required_liquidity_usd', Decimal('0'))
        if required_liquidity > 1000000:  # $1M+
            validation['warnings'].append("High liquidity requirement may cause slippage")
            validation['risk_score'] += 0.2
        
        time_window = strategy.get('execution_time_window_seconds', 0)
        if time_window > 0 and time_window < 60:  # Less than 1 minute
            validation['errors'].append("Execution window too narrow for reliable execution")
            validation['valid'] = False
            validation['risk_score'] += 0.5
        
        if validation['risk_score'] > 0.7:
            validation['recommendations'].append("Consider alternative strategies with lower risk")
        
        if gas_ratio > 0.3:
            validation['recommendations'].append("Optimize transaction batching to reduce gas costs")
        
        if required_liquidity > 100000:
            validation['recommendations'].append("Split execution across multiple transactions to reduce slippage")
        
        return validation
    
    async def generate_profitability_report(self, analysis: ProfitabilityAnalysis) -> str:
        """
        Generate a comprehensive profitability report.
        
        Args:
            analysis: Profitability analysis results
            
        Returns:
            Formatted report string
        """
        report_lines = [
            "=== EXPLOIT PROFITABILITY ANALYSIS ===",
            "",
            f"Total Profit (USD): ${analysis.total_profit_usd:,.2f}",
            f"Gas Costs (USD): ${analysis.gas_cost_usd:,.2f}",
            f"Net Profit (USD): ${analysis.net_profit_usd:,.2f}",
            f"ROI: {analysis.roi_percentage:.2f}%",
            "",
            "=== PROFIT BY TOKEN ===",
        ]
        
        for token_addr, profit in analysis.profit_by_token.items():
            if profit != 0:
                report_lines.append(f"{token_addr}: ${profit:,.2f}")
        
        report_lines.extend([
            "",
            "=== EXECUTION COST BREAKDOWN ===",
        ])
        
        for tx_id, cost_info in analysis.execution_cost_breakdown.items():
            report_lines.append(
                f"{tx_id}: {cost_info['gas_used']:,} gas @ {cost_info['gas_price']} wei = ${cost_info['cost_usd']:,.2f}"
            )
        
        report_lines.extend([
            "",
            "=== RISK ASSESSMENT ===",
            f"Liquidity Risk: {analysis.risk_metrics.get('liquidity_risk', 'unknown')}",
            f"MEV Risk: {analysis.risk_metrics.get('mev_risk', 'unknown')}",
            f"Detection Risk: {analysis.risk_metrics.get('detection_risk', 'unknown')}",
            f"Revert Probability: {analysis.risk_metrics.get('revert_probability', 0):.1%}",
            f"Time Sensitivity: {analysis.risk_metrics.get('time_sensitivity', 'unknown')}",
            "",
            f"Recommendation: {'PROCEED' if analysis.net_profit_usd > 0 and analysis.roi_percentage > 10 else 'RECONSIDER'}",
        ])
        
        return "\n".join(report_lines)
    
    async def batch_normalize_revenues(self, exploit_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch normalize revenues from multiple exploit attempts.
        
        Args:
            exploit_results: List of exploit result dictionaries
            
        Returns:
            Aggregated and normalized revenue analysis
        """
        batch_analysis = {
            'total_attempts': len(exploit_results),
            'successful_attempts': 0,
            'total_profit_usd': Decimal('0'),
            'total_gas_cost_usd': Decimal('0'),
            'average_profit_per_attempt': Decimal('0'),
            'success_rate': Decimal('0'),
            'best_performing_strategy': None,
            'worst_performing_strategy': None,
            'profit_distribution': [],
            'risk_adjusted_returns': {}
        }
        
        profitable_attempts = []
        
        for i, result in enumerate(exploit_results):
            profit = result.get('net_profit_usd', Decimal('0'))
            gas_cost = result.get('gas_cost_usd', Decimal('0'))
            
            batch_analysis['total_profit_usd'] += profit
            batch_analysis['total_gas_cost_usd'] += gas_cost
            
            if profit > 0:
                batch_analysis['successful_attempts'] += 1
                profitable_attempts.append((i, profit))
            
            batch_analysis['profit_distribution'].append({
                'attempt': i,
                'profit_usd': profit,
                'gas_cost_usd': gas_cost,
                'roi_percentage': result.get('roi_percentage', Decimal('0'))
            })
        
        if batch_analysis['total_attempts'] > 0:
            batch_analysis['average_profit_per_attempt'] = batch_analysis['total_profit_usd'] / batch_analysis['total_attempts']
            batch_analysis['success_rate'] = Decimal(batch_analysis['successful_attempts']) / batch_analysis['total_attempts']
        
        if profitable_attempts:
            best_idx, best_profit = max(profitable_attempts, key=lambda x: x[1])
            batch_analysis['best_performing_strategy'] = {
                'attempt_index': best_idx,
                'profit_usd': best_profit,
                'strategy': exploit_results[best_idx]
            }
        
        if batch_analysis['profit_distribution']:
            worst_result = min(batch_analysis['profit_distribution'], key=lambda x: x['profit_usd'])
            batch_analysis['worst_performing_strategy'] = worst_result
        
        return batch_analysis
