import requests
from requests.auth import HTTPBasicAuth
import os
import shutil
from cleanup_file_directory import cleanup

def update_attachments_by_type(basic_oauth, jama_username, jama_password, project_api_id, custom_prefix, jama_base_url_v2, attachment_item_type_id, t_f, index):
    """
    Finds and re-uploads attachments within a Jama Connect project that are of a specific item type,
    renaming them with a custom prefix and a unique suffix, and replacing the original file.

    Args:
        basic_oauth (str): The authentication method ('basic' or 'oauth').
        jama_username (str): Your Jama Connect username or client ID.
        jama_password (str): Your Jama Connect password or client secret.
        project_api_id (int): The API ID of the project to target.
        custom_prefix (str): The custom prefix to add to the renamed files.
        jama_base_url_v2 (str): The base URL for the Jama Connect REST API v2.
        attachment_item_type_id (int): The item type ID for attachments.
        t_f (bool): Flag to determine if the temporary directory should be cleaned up.
        index (int): The starting index for the image renaming suffix.
    """

    # --- 1. Authentication ---
    print(f"Authenticating with Jama Connect using {basic_oauth.upper()}...")
    session = requests.Session()

    if basic_oauth == 'basic':
        auth = HTTPBasicAuth(jama_username, jama_password)
        session.auth = auth
    elif basic_oauth == 'oauth':
        # OAuth 2.0 Client Credentials Flow
        client_id = jama_username
        client_secret = jama_password
        token_url = f"{jama_base_url_v2.rstrip('/')}/rest/oauth/token"
        
        try:
            # Get the access token
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            token = response.json().get('access_token')
            
            # Use the token for subsequent requests
            session.headers.update({"Authorization": f"Bearer {token}"})
            print("OAuth 2.0 authentication successful! 🎉")
        except requests.exceptions.HTTPError as e:
            print(f"OAuth 2.0 authentication failed. Please check your client ID and secret.")
            print(f"Error: {e}")
            return
        except Exception as e:
            print(f"An unexpected error occurred during OAuth authentication: {e}")
            return
    else:
        print("Invalid 'basic_oauth' value. Please use 'basic' or 'oauth'.")
        return

    json_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    multipart_headers = {
        "Accept": "application/json",
    }
    
    # Test authentication with a simple API call
    try:
        response = session.get(f"{jama_base_url_v2.rstrip('/')}/projects", headers=json_headers)
        response.raise_for_status()
        print("Initial authentication check successful! 🎉")
    except requests.exceptions.HTTPError as e:
        print(f"Authentication failed. Please check your credentials. Error: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred during authentication: {e}")
        return
    print("-" * 50)

    # --- 2. Fetch Attachments of a Specific Type ---
    print(f"Fetching all attachments (Item Type ID: {attachment_item_type_id}) for the project...")
    all_attachments = []
    items_url = f"{jama_base_url_v2.rstrip('/')}/abstractitems"
    page = 1
    
    while items_url:
        params = {
            "project": project_api_id,
            "itemType": attachment_item_type_id,
            "startAt": (page - 1) * 20,
            "maxResults": 20
        }
        
        response = session.get(items_url, headers=json_headers, params=params)
        response.raise_for_status()
        data = response.json()
        all_attachments.extend(data['data'])
        
        if 'nextLink' in data['meta']:
            items_url = data['meta']['nextLink']
            page += 1
        else:
            items_url = None

    print(f"Successfully fetched {len(all_attachments)} attachments from the project.")
    print("-" * 50)
    
    # --- 3. Filter and Prepare Attachments for Update ---
    print("Filtering attachments that start with 'image' or 'Image'...")
    attachments_to_update = []
    
    # Use the 'index' argument to initialize the enumeration counter
    enumeration = index

    for attachment in all_attachments:
        attachment_name = attachment['fields'].get('name')
        
        if attachment_name and attachment_name.lower().startswith('image'):
            base_name, file_extension = os.path.splitext(attachment_name)
            
            # Format the suffix with leading zeros up to 5 digits
            new_name_with_ext = f"{custom_prefix}{base_name}_{enumeration:05d}{file_extension}"
            
            attachments_to_update.append({
                'original_attachment_id': attachment['id'],
                'original_name': attachment_name,
                'download_url': f"{jama_base_url_v2.rstrip('/')}/attachments/{attachment['id']}/file",
                'new_name': new_name_with_ext,
                'parent_item_id': attachment['fields'].get('parent'),
                'item_type_id': attachment['itemType']
            })
            enumeration += 1

    print(f"Found {len(attachments_to_update)} attachments to update.")
    if not attachments_to_update:
        print("No attachments found that meet the criteria. Exiting.")
        return
    print("-" * 50)
    
    # --- 4. Download and Update Attachments ---
    print("Executing the download and update workflow...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(script_dir, "temp_renamed_attachments")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    for attachment in attachments_to_update:
        print(f"\nProcessing attachment '{attachment['original_name']}'...")
        try:
            # Step A: Download the original attachment
            print("    - Step A: Downloading original attachment...")
            response = session.get(attachment['download_url'], stream=True)
            response.raise_for_status()
            
            # Save the file with the new name
            file_path = os.path.join(temp_dir, attachment['new_name'])
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            print(f"    - Saved '{attachment['original_name']}' as '{attachment['new_name']}'.")
            
            # Step C: Upload the new file content to the existing attachment
            print("    - Step C: Uploading the new file content...")
            upload_file_url = f"{jama_base_url_v2.rstrip('/')}/attachments/{attachment['original_attachment_id']}/file"
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                response = session.put(upload_file_url, files=files, headers=multipart_headers)
                response.raise_for_status()
                print("    - Successfully replaced the file content.")

        except requests.exceptions.HTTPError as e:
            print(f"    - An HTTP error occurred during the update process for {attachment['original_name']}. Error: {e}")
        except Exception as e:
            print(f"    - An unexpected error occurred during the update process for {attachment['original_name']}. Error: {e}")

    # --- 5. Asynchronous Name Update using PATCH ---
    print("\n--- 5. Finalizing Updates ---")
    if attachments_to_update:
        print("Submitting asynchronous PATCH request to update all attachment names...")
        
        # Correct endpoint for this operation is '/rest/v1/items'
        patch_items_url = f"{jama_base_url_v2.rstrip('/')}/../v1/items"
        
        # Build the payload according to the Swagger page format
        patch_payload = []
        for attachment in attachments_to_update:
            patch_payload.append({
                "items": [
                    attachment['original_attachment_id']
                ],
                "operations": [
                    {
                        "op": "replace",
                        "path": "/fields/name",
                        "value": attachment['new_name']
                    }
                ]
            })

        try:
            response = session.patch(patch_items_url, json=patch_payload, headers=json_headers)
            response.raise_for_status()
            response_data = response.json()
            work_identifier = response_data['data']['workKey']
            print(f"PATCH request successful! A work identifier has been provided for monitoring: {work_identifier} 🚀")
        except requests.exceptions.HTTPError as e:
            print(f"An HTTP error occurred during the asynchronous name update. Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during the asynchronous name update: {e}")
    else:
        print("No PATCH operations to submit.")

    #Cleanup
    cleanup(t_f, temp_dir)
    
    print("\n✅ Project Attachment Script execution complete. ✅")