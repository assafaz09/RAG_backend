#!/usr/bin/env python3
"""
סקריפט הפעלה ל-LangGraph Studio
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🚀 Starting LangGraph Studio...")
    print("=" * 50)
    
    # בדיקת גרף קיים
    graph_files = [
        "app/agents/graph.py",
        "hybrid_langgraph.py"
    ]
    
    graph_found = False
    for file in graph_files:
        if Path(file).exists():
            print(f"✅ Found graph file: {file}")
            graph_found = True
            break
    
    if not graph_found:
        print("❌ No graph file found!")
        print("📝 Please create a graph file first")
        return
    
    # הפעלת LangGraph Studio
    try:
        print("🔧 Starting LangGraph Studio...")
        print("📍 Open: http://localhost:8123")
        print("⏹️  Press Ctrl+C to stop")
        print("=" * 50)
        
        # הרצת langgraph studio עם python -m
        subprocess.run([
            sys.executable, "-m", "langgraph", "studio"
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting LangGraph Studio: {e}")
        print("🔧 Trying alternative method...")
        
        # נסה להפעיל ישירות מהגרף
        try:
            if Path("app/agents/graph.py").exists():
                print("🔧 Running graph directly...")
                os.environ["PYTHONPATH"] = "."
                subprocess.run([
                    sys.executable, "-c", 
                    """
import sys
sys.path.append('.')
from app.agents.graph import app
from langgraph studio import run_studio
run_studio(app)
"""
                ], check=True)
        except Exception as e2:
            print(f"❌ Alternative method failed: {e2}")
            print("🔧 Please install langgraph-cli and try manual setup")
            
    except KeyboardInterrupt:
        print("\n👋 LangGraph Studio stopped")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
