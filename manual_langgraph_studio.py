#!/usr/bin/env python3
"""
LangGraph Studio ידני - פשוט ועובד
"""

import asyncio
import sys
import os
from pathlib import Path

# הוספת התיקייה הנוכחית ל-path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.agents.graph import app
    print("✅ Loaded graph from app/agents/graph.py")
except ImportError as e:
    print(f"❌ Failed to load graph: {e}")
    print("🔧 Trying alternative...")
    
    try:
        from hybrid_langgraph import app
        print("✅ Loaded graph from hybrid_langgraph.py")
    except ImportError as e2:
        print(f"❌ Failed to load alternative graph: {e2}")
        print("📝 Please create a graph file first")
        sys.exit(1)

async def run_manual_studio():
    """הרצת Studio ידני"""
    print("🚀 Manual LangGraph Studio")
    print("=" * 50)
    print("📍 This is a manual Studio interface")
    print("🔍 You can test the graph interactively")
    print("⏹️  Type 'exit' to quit")
    print("=" * 50)
    
    while True:
        try:
            # קלט מהמשתמש
            user_input = input("\n📝 Enter your query (or 'exit'): ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            print(f"\n🔍 Processing: {user_input}")
            print("-" * 30)
            
            # הפעלת הגרף
            initial_state = {
                "messages": [{"role": "user", "content": user_input}],
                "mcp_config": {},
                "mcp_tools": {
                    "echo_tool": {
                        "description": "Echo tool",
                        "schema": {},
                        "server_config": {"command": "echo"}
                    }
                }
            }
            
            # הרצת הגרף
            result = await app.ainvoke(initial_state)
            
            # הצגת תוצאות
            print("\n📋 Results:")
            for i, msg in enumerate(result["messages"], 1):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                msg_type = msg.get("type", "unknown")
                
                print(f"\n{i}. [{msg_type}] {role.upper()}:")
                print(f"   {content[:200]}{'...' if len(content) > 200 else ''}")
            
            print("\n" + "=" * 50)
            
        except KeyboardInterrupt:
            print("\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("🔧 Please try again")

if __name__ == "__main__":
    print("🎯 Manual LangGraph Studio")
    print("=" * 50)
    print("This is a manual testing interface for your LangGraph")
    print("For full Studio UI, please check LangGraph documentation")
    print("=" * 50)
    
    # הרצת ה-Studio הידני
    asyncio.run(run_manual_studio())
