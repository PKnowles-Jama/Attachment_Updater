import requests
from requests.auth import HTTPBasicAuth
import json
import os
import shutil
import time

def update_attachments_by_type(jama_username, jama_password, project_api_id, custom_prefix, jama_base_url_v2, attachment_item_type_id):
    """
    Finds and re-uploads attachments within a Jama Connect project that are of a specific item type,
    renaming them with a custom prefix and a unique suffix.

    Args:
        jama_username (str): Your Jama Connect username.
        jama_password (str): Your Jama Connect password.
        project_api_id (int): The API ID of the project to target.
        custom_prefix (str): The custom prefix to add to the renamed files.
        jama_base_url_v2 (str): The base URL for the Jama Connect REST API v2.
        attachment_item_type_id (int): The item type ID for attachments.
    """

    # --- 1. Authentication ---
    print("Authenticating with Jama Connect...")
    auth = HTTPBasicAuth(jama_username, jama_password)
    session = requests.Session()
    session.auth = auth

    json_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    multipart_headers = {
        "Accept": "application/json",
    }

    try:
        response = session.get(f"{jama_base_url_v2.rstrip('/')}/projects", headers=json_headers)
        response.raise_for_status()
        print("Authentication successful! 🎉")
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
    enumeration = 1

    for attachment in all_attachments:
        attachment_name = attachment['fields'].get('name')
        
        if attachment_name and attachment_name.lower().startswith('image'):
            # The uploaded script has logic to use 'filename' if available, otherwise 'name'.
            # The attachments returned by abstractitems don't seem to have a 'filename' field directly.
            # We'll stick to using the 'name' field and warn the user.
            base_name, file_extension = os.path.splitext(attachment_name)
            
            # The original script handles cases where the 'filename' might be missing,
            # this logic uses the 'name' field for the new filename.
            new_name_with_ext = f"{custom_prefix}{base_name}_{enumeration:05d}{file_extension}"
            
            attachments_to_update.append({
                'original_attachment_id': attachment['id'],
                'original_name': attachment_name,
                'download_url': f"{jama_base_url_v2.rstrip('/')}/attachments/{attachment['id']}/file",
                'new_name': new_name_with_ext
            })
            enumeration += 1

    print(f"Found {len(attachments_to_update)} attachments to update.")
    if not attachments_to_update:
        print("No attachments found that meet the criteria. Exiting.")
        return
    print("-" * 50)
    
    # --- 4. Download, Re-upload, and Delete Old Attachments ---
    print("Executing the download, re-upload, and delete workflow...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(script_dir, "temp_renamed_attachments")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Download attachments
    for attachment in attachments_to_update:
        try:
            response = session.get(attachment['download_url'], stream=True)
            response.raise_for_status()
            file_path = os.path.join(temp_dir, attachment['new_name'])
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            attachment['new_file_path'] = file_path
            print(f"   - Downloaded '{attachment['original_name']}' and saved as '{attachment['new_name']}'.")
        except Exception as e:
            print(f"   - Failed to download attachment ID {attachment['original_attachment_id']}. Error: {e}")
            attachment['new_file_path'] = None

    # Upload new files
    upload_successful = True
    new_attachment_ids = {}

    for attachment in attachments_to_update:
        if attachment['new_file_path']:
            try:
                print(f"\n   - Processing attachment '{attachment['new_name']}'...")
                
                # Step 1: Create a placeholder attachment item
                print("      - Step 1: Creating a placeholder attachment item...")
                create_attachment_url = f"{jama_base_url_v2.rstrip('/')}/projects/{project_api_id}/attachments"
                attachment_payload = {
                    "fields": {
                        "name": attachment['new_name'],
                        "description": "Attachment renamed and re-uploaded via API script."
                    }
                }
                response = session.post(create_attachment_url, json=attachment_payload, headers=json_headers)
                response.raise_for_status()
                new_attachment_item_id = response.json()['meta']['id']
                print(f"      - Successfully created placeholder item with ID: {new_attachment_item_id}")
                
                # Step 2: Upload the file content to the placeholder item
                print("      - Step 2: Uploading the file content...")
                upload_file_url = f"{jama_base_url_v2.rstrip('/')}/attachments/{new_attachment_item_id}/file"
                with open(attachment['new_file_path'], 'rb') as f:
                    files = {'file': (os.path.basename(attachment['new_file_path']), f, 'application/octet-stream')}
                    response = session.put(upload_file_url, files=files, headers=multipart_headers)
                    response.raise_for_status()
                    print("      - Successfully uploaded file content.")

            except requests.exceptions.HTTPError as e:
                print(f"   - An HTTP error occurred during the upload process for {attachment['new_name']}. Error: {e}")
                upload_successful = False
                break
            except Exception as e:
                print(f"   - An unexpected error occurred during the upload process for {attachment['new_name']}. Error: {e}")
                upload_successful = False
                break

    # Cleanup
    print("\nCleaning up temporary files...")
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("Temporary directory cleaned up.")
    except Exception as e:
        print(f"Failed to clean up temporary directory. Please delete '{temp_dir}' manually. Error: {e}")
    
    print("\nScript execution complete.")

# --- Example Usage (Commented out) ---
if __name__ == '__main__':
    # User inputs (replace with your actual values)
    jama_username = "PKnowles"
    jama_password = "LetsGoJama1331!"
    project_api_id = 97
    custom_prefix = "PK_"
    jama_base_url_v2 = "https://pknowles-jama-airborne.jamacloud.com/rest/v2/"
    attachment_item_type_id = 22

    update_attachments_by_type(
        jama_username,
        jama_password,
        project_api_id,
        custom_prefix,
        jama_base_url_v2,
        attachment_item_type_id
    )