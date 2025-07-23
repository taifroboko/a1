#!/usr/bin/env python3
"""
Simple Test Script - A1 Agentic System
Test the system with real contract data from targets.txt
"""

import asyncio
import sys
import os
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from main import ContractProcessor, ContractTarget
from config.configuration_manager import ConfigurationManager

async def test_system():
    """Test the A1 system with real contract data."""
    print("🔍 A1 Agentic System - Simple Test")
    print("=" * 50)
    
    print("🚀 Initializing system...")
    config_manager = ConfigurationManager()
    config = config_manager.get_config()
    
    processor = ContractProcessor(config)
    
    try:
        await processor.initialize()
        print("✅ System initialized successfully")
        
        targets_file = Path("~/attachments/e851e04a-6f7c-48cf-a499-9ad7ae71099c/targets.txt").expanduser()
        
        if not targets_file.exists():
            print("❌ Targets file not found")
            return False
        
        with open(targets_file, 'r') as f:
            all_targets = [line.strip() for line in f if line.strip()]
        
        print(f"📋 Found {len(all_targets)} target contracts")
        
        test_targets = all_targets[:3]
        print(f"🎯 Testing with {len(test_targets)} contracts")
        
        results = []
        
        for i, contract_address in enumerate(test_targets, 1):
            print(f"\n🔍 Processing Contract {i}/{len(test_targets)}: {contract_address}")
            
            try:
                start_time = time.time()
                
                contract_target = ContractTarget(
                    address=contract_address,
                    network='ethereum'
                )
                
                result = await processor.process_contract(contract_target)
                
                execution_time = time.time() - start_time
                
                if result.success:
                    print(f"✅ Contract {i}: SUCCESS")
                    print(f"   Exploits Found: {result.exploits_found}")
                    print(f"   Execution Time: {execution_time:.2f}s")
                    print(f"   Iterations Used: {result.iterations_used}")
                    if hasattr(result, 'total_profit_potential'):
                        print(f"   Profit Potential: ${result.total_profit_potential:,.2f}")
                else:
                    print(f"❌ Contract {i}: FAILED")
                    if hasattr(result, 'error_message'):
                        print(f"   Error: {result.error_message}")
                
                results.append({
                    'contract': contract_address,
                    'success': result.success,
                    'exploits': result.exploits_found if result.success else 0,
                    'time': execution_time
                })
                
            except Exception as e:
                print(f"❌ Contract {i}: ERROR - {e}")
                results.append({
                    'contract': contract_address,
                    'success': False,
                    'error': str(e),
                    'time': 0
                })
        
        successful = sum(1 for r in results if r['success'])
        total_exploits = sum(r.get('exploits', 0) for r in results)
        avg_time = sum(r['time'] for r in results) / len(results)
        
        print(f"\n📊 Test Summary:")
        print(f"   Contracts Processed: {len(results)}")
        print(f"   Successful: {successful}/{len(results)}")
        print(f"   Total Exploits Found: {total_exploits}")
        print(f"   Average Execution Time: {avg_time:.2f}s")
        
        print(f"\n🛠️ Tool Verification:")
        tools = processor.tools
        for tool_name in ['source_code_fetcher', 'constructor_parameter', 'state_reader', 
                         'code_sanitizer', 'concrete_execution', 'revenue_normalizer']:
            if tool_name in tools:
                print(f"   ✅ {tool_name}: Available")
            else:
                print(f"   ❌ {tool_name}: Missing")
        
        if hasattr(processor, 'agent') and processor.agent:
            print(f"   ✅ A1Agent: Available")
            if hasattr(processor.agent, 'grok_client'):
                print(f"   ✅ Grok Client: Available")
            else:
                print(f"   ❌ Grok Client: Missing")
        else:
            print(f"   ❌ A1Agent: Missing")
        
        return successful > 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        await processor.shutdown()

if __name__ == '__main__':
    success = asyncio.run(test_system())
    print(f"\n🎯 Test Result: {'PASS' if success else 'FAIL'}")
    sys.exit(0 if success else 1)
