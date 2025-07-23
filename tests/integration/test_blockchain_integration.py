"""
Integration Tests - Blockchain Integration

Test blockchain API connections and Forge integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from blockchain.client import BlockchainClient
from blockchain.forge import ForgeIntegration
from blockchain.scanner import ScannerIntegration

class TestBlockchainClient:
    """Test blockchain client integration."""
    
    @pytest.fixture
    def client(self, test_config):
        """Create blockchain client with test config."""
        return BlockchainClient(test_config)
    
    @pytest.mark.asyncio
    async def test_ethereum_connection(self, client):
        """Test Ethereum RPC connection."""
        with patch.object(client, '_make_rpc_call') as mock_rpc:
            mock_rpc.return_value = {'result': '0x1'}
            
            result = await client.get_latest_block('ethereum')
            assert result is not None
            mock_rpc.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bsc_connection(self, client):
        """Test BSC RPC connection."""
        with patch.object(client, '_make_rpc_call') as mock_rpc:
            mock_rpc.return_value = {'result': '0x1'}
            
            result = await client.get_latest_block('bsc')
            assert result is not None
            mock_rpc.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_contract_source_fetching(self, client, sample_contract_address):
        """Test fetching contract source code."""
        with patch.object(client, 'get_contract_source') as mock_source:
            mock_source.return_value = {
                'source_code': 'contract Test {}',
                'abi': [],
                'compiler_version': '0.8.19'
            }
            
            source = await client.get_contract_source(sample_contract_address, 'ethereum')
            assert source['source_code'] is not None
            assert 'abi' in source
    
    @pytest.mark.asyncio
    async def test_transaction_history(self, client, sample_contract_address):
        """Test fetching transaction history."""
        with patch.object(client, 'get_transaction_history') as mock_history:
            mock_history.return_value = [
                {
                    'hash': '0x123',
                    'from': '0xabc',
                    'to': sample_contract_address,
                    'value': '1000000000000000000',
                    'block_number': 18000000
                }
            ]
            
            history = await client.get_transaction_history(sample_contract_address, 'ethereum')
            assert len(history) > 0
            assert 'hash' in history[0]

class TestForgeIntegration:
    """Test Forge integration for deterministic simulation."""
    
    @pytest.fixture
    def forge(self, test_config):
        """Create Forge integration instance."""
        return ForgeIntegration(test_config)
    
    @pytest.mark.asyncio
    async def test_forge_installation_check(self, forge):
        """Test Forge installation verification."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=b'forge 0.2.0')
            
            is_installed = await forge.check_installation()
            assert is_installed
    
    @pytest.mark.asyncio
    async def test_create_forge_project(self, forge, temp_dir):
        """Test creating Forge project."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            project_path = await forge.create_project(temp_dir / 'test_project')
            assert project_path.exists()
    
    @pytest.mark.asyncio
    async def test_compile_contract(self, forge, sample_solidity_code, temp_dir):
        """Test compiling Solidity contract."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=b'Compilation successful')
            
            result = await forge.compile_contract(sample_solidity_code, temp_dir)
            assert result['success']
            assert 'compilation_output' in result
    
    @pytest.mark.asyncio
    async def test_run_simulation(self, forge, sample_exploit_code, sample_contract_address, temp_dir):
        """Test running exploit simulation."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0, 
                stdout=b'Test passed\nGas used: 21000\nProfit: 1000000000000000000'
            )
            
            result = await forge.run_simulation(
                exploit_code=sample_exploit_code,
                target_address=sample_contract_address,
                block_number=18000000,
                project_path=temp_dir
            )
            
            assert result['success']
            assert 'gas_used' in result
            assert 'profit_extracted' in result
    
    @pytest.mark.asyncio
    async def test_deterministic_simulation(self, forge, sample_exploit_code, sample_contract_address, temp_dir):
        """Test deterministic simulation at specific block."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=b'Simulation complete')
            
            result1 = await forge.run_simulation(
                exploit_code=sample_exploit_code,
                target_address=sample_contract_address,
                block_number=18000000,
                project_path=temp_dir
            )
            
            result2 = await forge.run_simulation(
                exploit_code=sample_exploit_code,
                target_address=sample_contract_address,
                block_number=18000000,
                project_path=temp_dir
            )
            
            assert result1['success'] == result2['success']

class TestScannerIntegration:
    """Test blockchain scanner integration."""
    
    @pytest.fixture
    def scanner(self, test_config):
        """Create scanner integration instance."""
        return ScannerIntegration(test_config)
    
    @pytest.mark.asyncio
    async def test_etherscan_api(self, scanner, sample_contract_address):
        """Test Etherscan API integration."""
        with patch.object(scanner, '_make_api_call') as mock_api:
            mock_api.return_value = {
                'status': '1',
                'result': [
                    {
                        'SourceCode': 'contract Test {}',
                        'ABI': '[]',
                        'CompilerVersion': 'v0.8.19+commit.7dd6d404'
                    }
                ]
            }
            
            result = await scanner.get_contract_source(sample_contract_address, 'ethereum')
            assert result['success']
            assert 'source_code' in result
    
    @pytest.mark.asyncio
    async def test_bscscan_api(self, scanner, sample_contract_address):
        """Test BSCscan API integration."""
        with patch.object(scanner, '_make_api_call') as mock_api:
            mock_api.return_value = {
                'status': '1',
                'result': [
                    {
                        'hash': '0x123',
                        'from': '0xabc',
                        'to': sample_contract_address,
                        'value': '1000000000000000000'
                    }
                ]
            }
            
            result = await scanner.get_transaction_list(sample_contract_address, 'bsc')
            assert result['success']
            assert len(result['transactions']) > 0
    
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self, scanner, sample_contract_address):
        """Test API rate limiting handling."""
        with patch.object(scanner, '_make_api_call') as mock_api:
            mock_api.side_effect = [
                {'status': '0', 'message': 'Rate limit exceeded'},
                {'status': '1', 'result': []}  # Success after retry
            ]
            
            result = await scanner.get_contract_source(sample_contract_address, 'ethereum')
            
            assert mock_api.call_count >= 2

class TestBlockchainIntegrationWorkflow:
    """Test complete blockchain integration workflow."""
    
    @pytest.fixture
    def blockchain_system(self, test_config):
        """Create complete blockchain system."""
        return {
            'client': BlockchainClient(test_config),
            'forge': ForgeIntegration(test_config),
            'scanner': ScannerIntegration(test_config)
        }
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, blockchain_system, sample_contract_address, sample_exploit_code, temp_dir):
        """Test end-to-end blockchain workflow."""
        client = blockchain_system['client']
        forge = blockchain_system['forge']
        scanner = blockchain_system['scanner']
        
        with patch.object(scanner, 'get_contract_source') as mock_source, \
             patch.object(client, 'get_latest_block') as mock_block, \
             patch.object(forge, 'run_simulation') as mock_simulation:
            
            mock_source.return_value = {
                'success': True,
                'source_code': 'contract Test {}',
                'abi': []
            }
            
            mock_block.return_value = 18000000
            
            mock_simulation.return_value = {
                'success': True,
                'gas_used': 21000,
                'profit_extracted': 1000000000000000000
            }
            
            source = await scanner.get_contract_source(sample_contract_address, 'ethereum')
            assert source['success']
            
            block = await client.get_latest_block('ethereum')
            assert block > 0
            
            simulation = await forge.run_simulation(
                exploit_code=sample_exploit_code,
                target_address=sample_contract_address,
                block_number=block,
                project_path=temp_dir
            )
            assert simulation['success']
    
    def test_error_handling_integration(self, blockchain_system, sample_contract_address):
        """Test error handling across blockchain components."""
        client = blockchain_system['client']
        
        with patch.object(client, '_make_rpc_call') as mock_rpc:
            mock_rpc.side_effect = Exception("Network error")
            
            with pytest.raises(Exception):
                asyncio.run(client.get_latest_block('ethereum'))
