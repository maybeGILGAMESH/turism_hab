#!/usr/bin/env python3
"""
Test RAG searcher to see what filenames it returns
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_searcher import RAGSearcher
from pathlib import Path

print("=== Testing RAG Searcher ===\n")

# Initialize searcher
print("1. Initializing RAG searcher...")
try:
    ragger = RAGSearcher(
        device="cpu",
        vectorstore_path="artifacts/db",
        object_descr_path="artifacts/metro_objects.json"
    )
    print("   ✅ RAG searcher initialized\n")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Check vectorstore docstore
print("2. Checking vectorstore docstore...")
if hasattr(ragger.vectorstore, 'docstore'):
    print(f"   ✅ Has docstore: {type(ragger.vectorstore.docstore)}")
    
    # Try different ways to access documents
    if hasattr(ragger.vectorstore.docstore, '_dict'):
        docs = list(ragger.vectorstore.docstore._dict.values())
        print(f"   📄 Number of documents: {len(docs)}")
        
        print("\n   Sample document names (first 15):")
        for i, doc in enumerate(docs[:15]):
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            print(f"   {i+1:2d}. '{content}'")
        
        # Check format
        print("\n   Format analysis:")
        full_path_count = 0
        filename_only_count = 0
        other_count = 0
        
        for doc in docs:
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            if '/' in content:
                full_path_count += 1
            elif content.startswith('O') and '_' in content:
                filename_only_count += 1
            else:
                other_count += 1
                if other_count <= 5:
                    print(f"      Other format: '{content}'")
        
        print(f"   Full paths: {full_path_count}")
        print(f"   Filenames only (OXXXX_YYYYYY): {filename_only_count}")
        print(f"   Other: {other_count}")
        
    else:
        print("   ⚠️ docstore._dict not found")
        print(f"   Docstore attributes: {[a for a in dir(ragger.vectorstore.docstore) if not a.startswith('_')][:10]}")
else:
    print("   ⚠️ No docstore found")

# Test search with multiple images
print("\n3. Testing search with multiple images...")
import json

# Load metadata
with open('artifacts/metro_objects.json', 'r', encoding='utf-8') as f:
    metadata = json.load(f)

test_images = [
    "data/images/O0001/O0001_000001.jpg",
    "data/images/O0002/O0002_000001.jpg",
    "data/images/O0005/O0005_000001.jpg",
    "data/images/O0010/O0010_000001.jpg",
    "data/images/O0020/O0020_000001.jpg",
    "data/images/O0027/O0027_000001.jpg",
]

print(f"\n   Testing {len(test_images)} images...")
correct = 0
total = 0

for test_img in test_images:
    if os.path.exists(test_img):
        expected_id = int(Path(test_img).parent.name[1:])
        print(f"\n   📸 Testing: {test_img}")
        print(f"      Expected ID: {expected_id}")
        
        try:
            # Use search method directly
            result_id = ragger.search(test_img)
            
            print(f"      Result ID: {result_id}")
            
            if result_id == expected_id:
                print(f"      ✅ CORRECT")
                correct += 1
            else:
                print(f"      ❌ WRONG! Expected {expected_id}, got {result_id}")
                
                # Check if result exists in metadata
                if str(result_id) in metadata:
                    print(f"      ⚠️  Result ID {result_id} exists in metadata")
                else:
                    print(f"      ⚠️  Result ID {result_id} NOT in metadata!")
                
                # Check if expected exists in metadata
                if str(expected_id) in metadata:
                    print(f"      ℹ️  Expected ID {expected_id} exists in metadata")
                else:
                    print(f"      ⚠️  Expected ID {expected_id} NOT in metadata!")
            
            total += 1
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"   ⚠️  Image not found: {test_img}")

print(f"\n   📊 Results: {correct}/{total} correct ({correct/total*100:.1f}%)")

# Check metadata vs index
print("\n4. Checking metadata vs index coverage...")
index_ids = set()
for doc in list(ragger.vectorstore.docstore._dict.values()):
    content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
    if content.startswith('O') and '_' in content:
        obj_id = int(content.split('_')[0][1:])
        index_ids.add(obj_id)

metadata_ids = set([int(k) for k in metadata.keys() if k.isdigit()])

print(f"   Objects in index: {sorted(index_ids)}")
print(f"   Objects in metadata: {sorted(metadata_ids)}")
print(f"   Missing in metadata: {sorted(index_ids - metadata_ids)}")
print(f"   Missing in index: {sorted(metadata_ids - index_ids)}")

print("\n=== Test Complete ===")

