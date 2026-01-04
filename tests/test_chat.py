import requests
import json
import sys

# Configuration
email = "dinhdat201fb@gmail.com"
password = "123456"
API_URL = "http://localhost:8000/api/"

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
        if 'response' in locals():
            print(response.text)
        sys.exit(1)

    # 2. Get Notebooks
    print_step("2. Get Notebooks")
    get_notebook_url = API_URL + "notebook"
    try:
        response = requests.get(get_notebook_url, headers=headers)
        response.raise_for_status()
        notebooks = response.json()
        print(f"Found {len(notebooks)} notebooks")
        
        if not notebooks:
            print("No notebooks found. Please create one first.")
            sys.exit(1)
            
        first_notebook = notebooks[0]
        notebook_id = first_notebook.get("id")
        print(f"Selected notebook: {first_notebook.get('name')} (ID: {notebook_id})")
    except Exception as e:
        print(f"Get notebooks failed: {e}")
        sys.exit(1)

    # 3. Get Sources (Prerequisite for Retrieve)
    print_step("3. Get Sources")
    get_sources_url = API_URL + f"notebook/{notebook_id}/sources"
    source_ids = []
    try:
        response = requests.get(get_sources_url, headers=headers)
        response.raise_for_status()
        sources = response.json()
        print(f"Found {len(sources)} sources")
        source_ids = [s.get("id") for s in sources]
    except Exception as e:
        print(f"Get sources failed: {e}")
        sys.exit(1)

    # 4. Get History & Retrieve Documents (Concurrent)
    print_step("4. Get History & Retrieve Documents (Concurrent)")
    get_history_url = API_URL + f"notebook/{notebook_id}/history"
    retrieve_url = API_URL + "retrieve"
    user_query = input() 
    
    retrieve_body = {
        "user_query": user_query,
        "docs_ids": source_ids
    }

    import concurrent.futures

    def fetch_history():
        print("Fetching history...")
        resp = requests.get(get_history_url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def fetch_retrieval():
        if not source_ids:
            return []
        print("Retrieving documents...")
        resp = requests.post(retrieve_url, json=retrieve_body, headers=headers)
        resp.raise_for_status()
        print(f"Retrieved {len(resp.json())} relevant context chunks")
        print(f"{resp.json()[0]["text"]}")
        return resp.json()

    chat_history = {}
    retrieved_docs = []

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_history = executor.submit(fetch_history)
            future_retrieval = executor.submit(fetch_retrieval)
            
            chat_history = future_history.result()
            retrieved_docs = future_retrieval.result()
            
        print(f"Found {len(chat_history) if isinstance(chat_history, list) else 1} history item(s)")
        print(f"Retrieved {len(retrieved_docs)} relevant context chunks")

    except Exception as e:
        print(f"Concurrent fetch failed: {e}")
        sys.exit(1)

    # 5. Chat
    print_step("5. Chat")
    chat_url = API_URL + f"notebook/{notebook_id}/message"
    
    chat_body = {
        "query": user_query,
        "history": chat_history.get("summary", "") if isinstance(chat_history, dict) else "",
        "documents": retrieved_docs
    }
    
    try:
        print(f"Sending query: '{user_query}'")
        response = requests.post(chat_url, json=chat_body, headers=headers)
        response.raise_for_status()
        
        # Check content type to handle streaming or json
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
             answer = response.json()
             print("\nResponse:")
             print(json.dumps(answer, indent=2, ensure_ascii=False))
        else:
             print("\nResponse (Text):")
             print(response.text)
             
    except Exception as e:
        print(f"Chat failed: {e}")
        if 'response' in locals():
            print(response.text)
        sys.exit(1)

if __name__ == "__main__":
    run_test()
