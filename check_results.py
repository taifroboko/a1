#!/usr/bin/env python3
"""
Check Results Script - Verify A1 system database contents
"""

import sqlite3
import json
from pathlib import Path

def check_database():
    """Check the contents of the A1 results database."""
    db_path = Path("a1_results.db")
    
    if not db_path.exists():
        print("❌ Database file not found")
        return
    
    print("🔍 A1 Results Database Analysis")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM execution_results")
        total_results = cursor.fetchone()[0]
        print(f"📊 Total execution results: {total_results}")
        
        cursor.execute("""
            SELECT contract_address, success, exploits_found, iterations_used, 
                   total_profit_potential, created_at 
            FROM execution_results 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        results = cursor.fetchall()
        
        print(f"\n📋 Recent Results:")
        for i, (address, success, exploits, iterations, profit, created) in enumerate(results, 1):
            print(f"  {i}. Contract: {address[:10]}...")
            print(f"     Success: {'✅' if success else '❌'}")
            print(f"     Exploits Found: {exploits}")
            print(f"     Iterations Used: {iterations}")
            print(f"     Profit Potential: ${profit:,.2f}")
            print(f"     Created: {created}")
            print()
        
        cursor.execute("SELECT COUNT(*) FROM iteration_results")
        total_iterations = cursor.fetchone()[0]
        print(f"🔄 Total iteration records: {total_iterations}")
        
        cursor.execute("""
            SELECT session_id, iteration_number, phase, confidence_score, 
                   exploits_found, created_at
            FROM iteration_results 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        iterations = cursor.fetchall()
        
        print(f"\n🔄 Recent Iterations:")
        for session, iter_num, phase, confidence, exploits, created in iterations:
            print(f"  Session: {session[:15]}... | Iter: {iter_num} | Phase: {phase}")
            print(f"    Confidence: {confidence:.2f} | Exploits: {exploits} | Time: {created}")
        
        conn.close()
        
        successful_results = sum(1 for r in results if r[1])  # success column
        total_exploits = sum(r[2] for r in results)  # exploits_found column
        
        print(f"\n📈 Summary:")
        print(f"  Success Rate: {successful_results}/{len(results)} ({successful_results/len(results)*100:.1f}%)")
        print(f"  Total Exploits Found: {total_exploits}")
        print(f"  Database Status: ✅ Operational")
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == '__main__':
    check_database()
