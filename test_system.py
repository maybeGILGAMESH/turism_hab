#!/usr/bin/env python3
"""
Test script for Moscow Metro Cultural Heritage Recognition System
Verifies all components are working correctly
"""

import requests
import time
import sys
import os
from pathlib import Path

def test_backend_health():
    """Test if the backend API is responding"""
    print("🏥 Testing backend health...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend is healthy")
            print(f"   Status: {data['status']}")
            print(f"   RAG Searcher: {data['rag_searcher']}")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Is it running on localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ Backend health check error: {e}")
        return False

def test_api_endpoints():
    """Test all API endpoints"""
    print("\n🔗 Testing API endpoints...")
    
    base_url = "http://localhost:8000"
    
    # Test root endpoint
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("✅ Root endpoint working")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False
    
    # Test objects endpoint
    try:
        response = requests.get(f"{base_url}/api/objects", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                print(f"✅ Objects endpoint working - {data['total_count']} objects found")
            else:
                print("❌ Objects endpoint returned error")
                return False
        else:
            print(f"❌ Objects endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Objects endpoint error: {e}")
        return False
    
    # Test stats endpoint
    try:
        response = requests.get(f"{base_url}/api/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                stats = data["stats"]
                print(f"✅ Stats endpoint working")
                print(f"   Total objects: {stats['total_objects']}")
                print(f"   Total images: {stats['total_images']}")
                print(f"   System status: {stats['system_status']}")
            else:
                print("❌ Stats endpoint returned error")
                return False
        else:
            print(f"❌ Stats endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Stats endpoint error: {e}")
        return False
    
    return True

def test_recognition():
    """Test the recognition endpoint with a sample image"""
    print("\n🔍 Testing recognition endpoint...")
    
    # Look for a test image
    test_images = [
        "data/test_img.jpg",
        "data/test_img_1.jpg"
    ]
    
    test_image = None
    for img_path in test_images:
        if Path(img_path).exists():
            test_image = img_path
            break
    
    if not test_image:
        print("⚠️ No test image found. Skipping recognition test.")
        return True
    
    print(f"📸 Using test image: {test_image}")
    
    try:
        with open(test_image, 'rb') as f:
            # Properly format the file upload with content type
            files = {'file': ('test_image.jpg', f, 'image/jpeg')}
            response = requests.post(
                "http://localhost:8000/api/recognize",
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                print(f"✅ Recognition successful!")
                print(f"   Object ID: {data['object_id']}")
                print(f"   Confidence: {data['confidence']:.2%}")
                print(f"   Description: {data['description'][:100]}...")
            else:
                print(f"⚠️ Recognition completed but object not found")
                print(f"   Message: {data['message']}")
        else:
            print(f"❌ Recognition failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Recognition test error: {e}")
        return False
    
    return True

def test_file_structure():
    """Test if all required files and directories exist"""
    print("\n📁 Testing file structure...")
    
    required_paths = [
        "artifacts/db/index.faiss",
        "artifacts/db/index.pkl", 
        "artifacts/metro_objects.json",
        "rag_searcher.py",
        "app.py",
        "frontend.py",
        "static/index.html"
    ]
    
    all_exist = True
    for path in required_paths:
        if Path(path).exists():
            print(f"✅ {path}")
        else:
            print(f"❌ {path} - MISSING")
            all_exist = False
    
    return all_exist

def test_rag_searcher():
    """Test if the RAG searcher can be imported and initialized"""
    print("\n🧠 Testing RAG searcher...")
    
    try:
        from rag_searcher import RAGSearcher
        
        # Try to initialize
        ragger = RAGSearcher(
            device="cpu",
            vectorstore_path="artifacts/db",
            object_descr_path="artifacts/metro_objects.json"
        )
        
        print("✅ RAG searcher imported and initialized successfully")
        return True
        
    except ImportError as e:
        print(f"⚠️ Cannot import RAG searcher directly: {e}")
        print("   This is expected if running in a different environment than the backend")
        print("   The backend test will verify RAG functionality")
        return True  # Don't fail the test for this
    except Exception as e:
        print(f"❌ RAG searcher initialization failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚇 Система распознавания культурного наследия Московского метро")
    print("🧪 Набор тестов системы")
    print("=" * 50)
    
    tests = [
        ("Структура файлов", test_file_structure),
        ("RAG поисковик", test_rag_searcher),
        ("Состояние Backend", test_backend_health),
        ("API endpoints", test_api_endpoints),
        ("Распознавание", test_recognition)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТОВ")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ ПРОЙДЕНО" if success else "❌ ПРОВАЛЕНО"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nИтого: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены! Система готова к использованию.")
        print("\n🚀 Для запуска системы выполните:")
        print("   python run_system.py")
    else:
        print("⚠️ Некоторые тесты провалены. Проверьте проблемы выше.")
        print("\n💡 Общие решения:")
        print("   - Установите зависимости: pip install -r requirements.txt")
        print("   - Запустите backend: python app.py")
        print("   - Проверьте права доступа и пути")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
