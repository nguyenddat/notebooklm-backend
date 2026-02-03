import requests
import json
import sys

# Configuration
email = "dinhdat201fb@gmail.com"
password = "123456"
API_URL = "http://localhost:4000/api/"

def print_step(step_name):
    print(f"\n{'='*20} {step_name} {'='*20}")

def run_test():
    # 1. Login
    print_step("1. Login")
    login_url = API_URL + "user/login"
    login_data = {
        "username": email,
        "password": password
    }
    
    try:
        response = requests.post(login_url, data=login_data)
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            print("Error: No access_token found in login response")
            sys.exit(1)
        print("Login successful!")
        headers = {"Authorization": f"Bearer {access_token}"}
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit(1)

    # 2. Get Notebooks
    print_step("2. Get Notebooks")
    get_notebook_url = API_URL + "notebook"
    try:
        response = requests.get(get_notebook_url, headers=headers)
        response.raise_for_status()
        notebooks = response.json()
        
        if not notebooks:
            print("No notebooks found. Please create one first.")
            sys.exit(1)
            
    # Select notebook with highest ID (latest)
        latest_notebook = max(notebooks, key=lambda x: x.get("id"))
        notebook_id = latest_notebook.get("id")
        print(f"Selected notebook: {latest_notebook.get('title')} (ID: {notebook_id})")
    except Exception as e:
        print(f"Get notebooks failed: {e}")
        sys.exit(1)

    # 3. Chat (Auto-Retrieve)
    print_step("3. Chat with Auto-Retrieve")
    chat_url = API_URL + f"notebook/{notebook_id}/message"
    
    # Simulate user sending empty documents
    user_query = "SV_STARTUP"
    chat_body = {
        "query": user_query,
        "history": "",
        "documents": {
            "texts": [],
            "images": []
        }
    }
    
    try:
        print(f"Sending query: '{user_query}' with EMPTY documents...")
        response = requests.post(chat_url, json=chat_body, headers=headers)
        response.raise_for_status()
        
        answer = response.json()
        print("\nResponse:")
        print(json.dumps(answer, indent=2, ensure_ascii=False))
        
        # Validation
        if answer.get("citations"):
            print("\n[PASS] Citations found, retrieval worked!")
        else:
            print("\n[WARN] No citations found. Check if documents actually contain relevant info.")

    except Exception as e:
        print(f"Chat failed: {e}")
        if 'response' in locals():
            print(response.text)
        sys.exit(1)

if __name__ == "__main__":
    run_test()
