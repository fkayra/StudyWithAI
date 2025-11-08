#!/usr/bin/env python3
"""
Test script to diagnose login issues
"""
import requests
import sys

API_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

# Test credentials
email = "nurican@gmail.com"
password = input("Enter password for nurican@gmail.com: ")

print(f"Testing login at {API_URL}/auth/login")
print(f"Email: {email}")

try:
    response = requests.post(
        f"{API_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=10
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("✓ Login successful!")
        data = response.json()
        print(f"  User: {data.get('user', {}).get('email')}")
        print(f"  Has access_token: {bool(data.get('access_token'))}")
    else:
        print(f"✗ Login failed!")
        print(f"  Response: {response.text}")
        try:
            error_data = response.json()
            print(f"  Error detail: {error_data.get('detail', 'Unknown error')}")
        except:
            print(f"  Raw response: {response.text[:500]}")
            
except requests.exceptions.ConnectionError:
    print(f"✗ Could not connect to {API_URL}")
    print("  Make sure the backend server is running")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

