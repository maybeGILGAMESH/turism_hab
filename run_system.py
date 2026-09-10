#!/usr/bin/env python3
"""
Startup script for Moscow Metro Cultural Heritage Recognition System
Launches both backend API and frontend interfaces
"""

import subprocess
import time
import sys
import os
import signal
import threading
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ['fastapi', 'streamlit', 'uvicorn']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Please install them with: pip install -r requirements.txt")
        return False
    
    return True

def check_files():
    """Check if required files exist"""
    required_files = [
        'artifacts/db/index.faiss',
        'artifacts/db/index.pkl',
        'artifacts/metro_objects.json',
        'rag_searcher.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        print("Please ensure all artifacts are present in the project directory")
        return False
    
    return True

def start_backend():
    """Start the FastAPI backend server"""
    print("🚀 Starting FastAPI backend server...")
    try:
        # Start backend in a subprocess
        backend_process = subprocess.Popen(
            [sys.executable, "app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        time.sleep(3)
        
        # Check if backend is running
        if backend_process.poll() is None:
            print("✅ Backend server started successfully on http://localhost:8000")
            return backend_process
        else:
            stdout, stderr = backend_process.communicate()
            print(f"❌ Backend failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        return None

def start_streamlit():
    """Start the Streamlit frontend"""
    print("🎨 Starting Streamlit frontend...")
    try:
        # Start Streamlit in a subprocess
        frontend_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "frontend.py", "--server.port", "8501"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        time.sleep(5)
        
        # Check if frontend is running
        if frontend_process.poll() is None:
            print("✅ Streamlit frontend started successfully on http://localhost:8501")
            return frontend_process
        else:
            stdout, stderr = frontend_process.communicate()
            print(f"❌ Frontend failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        return None

def start_html_server():
    """Start a simple HTTP server for the HTML frontend"""
    print("🌐 Starting HTML frontend server...")
    try:
        # Start HTTP server in a subprocess
        html_process = subprocess.Popen(
            [sys.executable, "-m", "http.server", "8080"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        time.sleep(2)
        
        # Check if server is running
        if html_process.poll() is None:
            print("✅ HTML frontend server started successfully on http://localhost:8080")
            print("   Visit: http://localhost:8080/static/index.html")
            return html_process
        else:
            stdout, stderr = html_process.communicate()
            print(f"❌ HTML server failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting HTML server: {e}")
        return None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print("\n🛑 Shutting down system...")
    sys.exit(0)

def main():
    """Main startup function"""
    print("🚇 Moscow Metro Cultural Heritage Recognition System")
    print("=" * 60)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check dependencies and files
    if not check_dependencies():
        sys.exit(1)
    
    if not check_files():
        sys.exit(1)
    
    print("✅ All dependencies and files verified")
    print()
    
    # Ask user which frontend to use
    print("Choose your frontend interface:")
    print("1. Streamlit (Recommended - Full admin features)")
    print("2. HTML (Simple visitor interface)")
    print("3. Both")
    
    while True:
        choice = input("Enter your choice (1-3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Please enter 1, 2, or 3")
    
    print()
    
    # Start backend first
    backend_process = start_backend()
    if not backend_process:
        print("❌ Cannot start frontend without backend. Exiting.")
        sys.exit(1)
    
    # Start frontend based on user choice
    frontend_process = None
    html_process = None
    
    try:
        if choice in ['1', '3']:
            frontend_process = start_streamlit()
        
        if choice in ['2', '3']:
            html_process = start_html_server()
        
        print()
        print("🎉 System startup complete!")
        print()
        print("📱 Access your system:")
        print(f"   Backend API: http://localhost:8000")
        if frontend_process:
            print(f"   Streamlit UI: http://localhost:8501")
        if html_process:
            print(f"   HTML UI: http://localhost:8080/static/index.html")
        print()
        print("📚 API Documentation: http://localhost:8000/docs")
        print("🏥 Health Check: http://localhost:8000/health")
        print()
        print("💡 Press Ctrl+C to stop all services")
        print()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
            # Check if any process has died
            if backend_process.poll() is not None:
                print("❌ Backend process has stopped unexpectedly")
                break
            
            if frontend_process and frontend_process.poll() is not None:
                print("❌ Frontend process has stopped unexpectedly")
                break
            
            if html_process and html_process.poll() is not None:
                print("❌ HTML server process has stopped unexpectedly")
                break
    
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    
    finally:
        # Clean up processes
        print("🧹 Cleaning up processes...")
        
        if backend_process:
            backend_process.terminate()
            backend_process.wait()
            print("✅ Backend stopped")
        
        if frontend_process:
            frontend_process.terminate()
            frontend_process.wait()
            print("✅ Frontend stopped")
        
        if html_process:
            html_process.terminate()
            html_process.wait()
            print("✅ HTML server stopped")
        
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()
