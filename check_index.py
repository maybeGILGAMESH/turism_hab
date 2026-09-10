#!/usr/bin/env python3
"""
Script to check FAISS index structure and verify it matches image files
"""
import pickle
import os
from pathlib import Path

print("=== Checking FAISS Index Structure ===\n")

# Check index.pkl
print("1. Reading index.pkl...")
try:
    with open('artifacts/db/index.pkl', 'rb') as f:
        index_data = pickle.load(f)
    print(f"   Type: {type(index_data)}")
    
    if isinstance(index_data, tuple):
        print(f"   Tuple length: {len(index_data)}")
        for i, item in enumerate(index_data):
            print(f"   Item {i}: {type(item)} - {str(item)[:100] if not isinstance(item, (dict, list)) else f'{len(item)} items'}")
            if isinstance(item, dict):
                print(f"      Keys: {list(item.keys())[:10]}")
                # Check if it's docstore
                if 'docstore' in str(type(item)) or hasattr(item, 'get'):
                    sample_keys = list(item.keys())[:5]
                    print(f"      Sample keys: {sample_keys}")
    
    # Try to load FAISS vectorstore properly
    print("\n   Trying to load FAISS vectorstore...")
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_core.embeddings import Embeddings
        import clip
        from PIL import Image
        import torch
        import numpy as np
        
        class DummyEmbeddings(Embeddings):
            def __init__(self):
                self.device = "cpu"
                self.model, self.preprocess = clip.load("ViT-B/16", device=self.device)
            
            def embed_query(self, image_path):
                img = self.preprocess(Image.open(image_path)).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    embedding = self.model.encode_image(img)
                embedding /= np.linalg.norm(embedding)
                return embedding.cpu().numpy()
            
            def embed_documents(self, texts):
                raise NotImplementedError
        
        embedder = DummyEmbeddings()
        vectorstore = FAISS.load_local('artifacts/db', embedder, allow_dangerous_deserialization=True)
        
        # Check docstore
        if hasattr(vectorstore, 'docstore'):
            print(f"   ✅ Vectorstore loaded successfully")
            print(f"   Has docstore: True")
            
            # Try to get documents
            if hasattr(vectorstore.docstore, '_dict'):
                docs = list(vectorstore.docstore._dict.values())
                print(f"   Number of documents: {len(docs)}")
                
                # Show sample documents
                print("\n   Sample document names (first 10):")
                for i, doc in enumerate(docs[:10]):
                    content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                    print(f"   {i+1}. '{content}'")
                
                # Check format
                print("\n   Checking filename format...")
                formats = {}
                for doc in docs:
                    content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                    if '/' in content:
                        formats['full_path'] = formats.get('full_path', 0) + 1
                    elif content.startswith('O') and '_' in content:
                        formats['OXXXX_YYYYYY'] = formats.get('OXXXX_YYYYYY', 0) + 1
                    else:
                        formats['other'] = formats.get('other', 0) + 1
                        if len(formats.get('other_samples', [])) < 5:
                            formats.setdefault('other_samples', []).append(content)
                
                print(f"   Format distribution: {formats}")
                
            elif hasattr(vectorstore.docstore, 'search'):
                print("   Docstore has search method")
                print(f"   Docstore type: {type(vectorstore.docstore)}")
        else:
            print("   No docstore in loaded vectorstore")
            print(f"   Vectorstore type: {type(vectorstore)}")
            print(f"   Attributes: {[a for a in dir(vectorstore) if not a.startswith('_')][:15]}")
            
    except Exception as e:
        print(f"   Error loading FAISS: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Checking Image Files ===\n")

# Check actual image files
print("2. Checking image files in data/images/...")
image_files = []
for folder in sorted(os.listdir('data/images')):
    if folder.startswith('O'):
        folder_path = Path('data/images') / folder
        if folder_path.is_dir():
            files = list(folder_path.glob('*.jpg'))
            if files:
                image_files.append((folder, len(files)))

print(f"   Found {len(image_files)} object folders")
for folder, count in image_files[:10]:
    print(f"   {folder}: {count} images")

print("\n=== Checking metro_objects.json ===\n")

# Check metadata
import json
with open('artifacts/metro_objects.json', 'r', encoding='utf-8') as f:
    metadata = json.load(f)
    
print(f"3. Metadata objects: {len(metadata)}")
print(f"   Object IDs in metadata: {sorted([int(k) for k in metadata.keys() if k.isdigit()])[:10]}...")

print("\n=== Expected vs Actual ===\n")
print("4. Expected format in code:")
print("   - Filename format: 'OXXXX_YYYYYY.jpg' (from _find_best_class_id)")
print("   - Code extracts: filename.split('_')[0][1:] to get class ID")
print("   - Example: 'O0001_000001.jpg' -> '0001' -> 1")

