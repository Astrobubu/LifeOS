"""
Verification Script
Checks if MasterAgent and sub-agents load correctly
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    print("🔄 Importing MasterAgent...")
    from agent.master_agent import MasterAgent
    from agent.planning import AgentType
    
    print("🤖 Instantiating MasterAgent...")
    master = MasterAgent()
    
    print("✅ MasterAgent initialized.")
    print(f"📋 Sub-agents loaded: {len(master.sub_agents)}")
    
    for agent_type, agent in master.sub_agents.items():
        print(f"  - {agent_type}: {agent.__class__.__name__}")
        tools = agent.get_tools()
        print(f"    Tools available: {len(tools)}")
        print(f"    Tool mapping: {agent.get_tool_mapping().keys()}")
        
    print("\n🎉 Verification Successful!")
    
except Exception as e:
    print(f"\n❌ Verification Failed: {e}")
    import traceback
    traceback.print_exc()
