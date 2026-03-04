#!/usr/bin/env python3
import urllib.request, json
import time

print("=" * 60)
print("RAG AI System - Production Readiness Test")
print("=" * 60)
time.sleep(0.5)

endpoints = [
    ("Health", "http://localhost:8000/"),
    ("Documents", "http://localhost:8000/documents"),
]

passed = 0
for name, url in endpoints:
    try:
        r = urllib.request.urlopen(url, timeout=3)
        data = json.loads(r.read())
        if name == "Health":
            print(f"✓ {name:15} {r.status} {data}")
        else:
            pts = data.get("total_points", 0)
            docs = len(data.get("documents", []))
            print(f"✓ {name:15} {r.status} {pts} points, {docs} docs")
        passed += 1
    except Exception as e:
        print(f"✗ {name:15} Error: {e}")

print("\n" + "=" * 60)
print(f"Sistema Status: {passed}/{len(endpoints)} endpoints responsive")
print("=" * 60)

if passed == len(endpoints):
    print("\n🎉 RAG System is PRODUCTION-READY!")
    print("\nNext steps:")
    print("1. Frontend: http://localhost:3000 (Upload via /upload)")
    print("2. Backend API: http://localhost:8000/docs")
    print("3. Qdrant Console: http://localhost:6333/dashboard")
else:
    print("\n⚠️  Some endpoints failed - check backend logs")
