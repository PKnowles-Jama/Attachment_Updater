import requests
from requests.auth import HTTPBasicAuth
import json
import os
import shutil
import base64

# --- 1. Request user inputs ---
print("Please provide your Jama Connect API credentials and project details.")
print("------------------------------------------------------------------")
jama_username = "PKnowles"
jama_password = "LetsGoJama1331!"
project_api_id = 97
custom_prefix = "PK_"
jama_base_url_v2 = "https://pknowles-jama-airborne.jamacloud.com/rest/v2/"

# --- Ask the user whether to delete the local files ---
while True:
    delete_files_input = input("Do you want to delete the local files after the script runs? (True/False): ").strip().lower()
    if delete_files_input in ['true', 'false']:
        delete_files_after_run = delete_files_input == 'true'
        break
    else:
        print("Invalid input. Please enter 'True' or 'False'.")

# --- 2. Authenticate using HTTPBasicAuth (cleaner approach) ---
print("\nAttempting to authenticate with Jama Connect using Basic Auth...")
auth = HTTPBasicAuth(jama_username, jama_password)

# Create session with consistent auth
session = requests.Session()
session.auth = auth

json_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

multipart_headers = {
    "Accept": "application/json",
}

test_url = f"{jama_base_url_v2.rstrip('/')}/projects"
try:
    response = session.get(test_url, headers=json_headers)
    response.raise_for_status()
    print("Authentication successful! 🎉")
except requests.exceptions.HTTPError as e:
    print(f"Authentication failed. Please check your username and password.")
    print(f"Error: {e}")
    exit()
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    exit()

print("\nAuthentication complete. Ready to fetch attachments.")

# -------------------------------------------------------------------------------------------
## 3. Find all items with attachments and prepare the list
print("Fetching all items for the specified project...")
all_attachments = []
all_items = []
items_url = f"{jama_base_url_v2.rstrip('/')}/items?project={project_api_id}"
page = 1

while items_url:
    params = {"startAt": (page - 1) * 20, "maxResults": 20}
    response = session.get(items_url, headers=json_headers, params=params)
    response.raise_for_status()
    data = response.json()
    all_items.extend(data['data'])
    if 'nextLink' in data['meta']:
        items_url = data['meta']['nextLink']
        page += 1
    else:
        items_url = None

print(f"Successfully fetched {len(all_items)} items from the project.")

for item in all_items:
    item_id = item['id']
    attachments_url = f"{jama_base_url_v2.rstrip('/')}/items/{item_id}/attachments"
    try:
        response = session.get(attachments_url, headers=json_headers)
        response.raise_for_status()
        item_attachments = response.json().get('data', [])
        for att in item_attachments:
            att['parent_item_id'] = item_id
        all_attachments.extend(item_attachments)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code != 404:
            print(f"Failed to fetch attachments for item ID {item_id}. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while fetching attachments for item ID {item_id}: {e}")

print(f"Successfully retrieved a total of {len(all_attachments)} attachments.")

# -------------------------------------------------------------------------------------------
## 4. Filter and Update Attachments
print("\nFiltering attachments that start with 'image' or 'Image'...")
attachments_to_update = []
enumeration = 1

for attachment in all_attachments:
    attachment_name = attachment['fields'].get('name')
    if attachment_name and attachment_name.lower().startswith('image'):
        file_name = attachment['fields'].get('filename')
        
        if file_name:
            base_name, file_extension = os.path.splitext(file_name)
            new_name_with_ext = f"{custom_prefix}{base_name}_{enumeration:05d}{file_extension}"
        else:
            base_name, file_extension = os.path.splitext(attachment_name)
            new_name_with_ext = f"{custom_prefix}{base_name}_{enumeration:05d}{file_extension}"
            print(f"Warning: Attachment ID {attachment['id']} has no filename. Using attachment name for new file name.")
        
        attachments_to_update.append({
            'item_id': attachment['parent_item_id'],
            'original_attachment_id': attachment['id'],
            'original_name': attachment_name,
            'original_file_name': file_name,
            'download_url': f"{jama_base_url_v2.rstrip('/')}/attachments/{attachment['id']}/file",
            'new_name': new_name_with_ext
        })
        enumeration += 1

print(f"Found {len(attachments_to_update)} attachments to update.")
if not attachments_to_update:
    print("No attachments found that meet the criteria. Exiting.")
    exit()

# -------------------------------------------------------------------------------------------
## 5. Download, Upload, and Delete
print("\nExecuting the download, upload, and delete workflow...")
script_dir = os.path.dirname(os.path.abspath(__file__))
temp_dir = os.path.join(script_dir, "temp_renamed_attachments")
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

# Download and rename attachments
for attachment in attachments_to_update:
    try:
        response = session.get(attachment['download_url'], stream=True)
        response.raise_for_status()
        file_path = os.path.join(temp_dir, attachment['new_name'])
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        attachment['new_file_path'] = file_path
        print(f"   - Downloaded '{attachment['original_name']}' and saved as '{attachment['new_name']}'.")
    except Exception as e:
        print(f"   - Failed to download attachment ID {attachment['original_attachment_id']}. Error: {e}")
        attachment['new_file_path'] = None

# --- NEW UPLOAD LOGIC: Using the correct three-step Jama API workflow ---
print("\nExecuting the three-step attachment upload process...")
upload_successful = True
new_attachment_ids = {}

for attachment in attachments_to_update:
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
        
        try:
            response_data = response.json()
            print("      - Raw JSON response:", json.dumps(response_data, indent=2))
            new_attachment_item_id = response_data['meta']['id']
            print(f"      - Successfully created placeholder item with ID: {new_attachment_item_id}")
        except KeyError:
            raise Exception(f"Could not find attachment ID in the server response. Please inspect the raw JSON output above.")
        
        # Step 2: Upload the file content to the placeholder item
        print("      - Step 2: Uploading the file content...")
        upload_file_url = f"{jama_base_url_v2.rstrip('/')}/attachments/{new_attachment_item_id}/file"
        
        with open(attachment['new_file_path'], 'rb') as f:
            files = {'file': (os.path.basename(attachment['new_file_path']), f, 'application/octet-stream')}
            response = session.put(upload_file_url, files=files, headers=multipart_headers)
            response.raise_for_status()
            print("      - Successfully uploaded file content.")
        
        # Step 3: Link the new attachment to the original item
        print("      - Step 3: Linking the new attachment to the original item...")
        link_attachment_url = f"{jama_base_url_v2.rstrip('/')}/items/{attachment['item_id']}/attachments"
        link_payload = {
            "attachment": new_attachment_item_id
        }
        
        response = session.post(link_attachment_url, json=link_payload, headers=json_headers)
        response.raise_for_status()
        print(f"      - Successfully linked new attachment to item {attachment['item_id']}.")

        new_attachment_ids[attachment['original_attachment_id']] = new_attachment_item_id

    except requests.exceptions.HTTPError as e:
        print(f"   - An HTTP error occurred during the upload process for {attachment['new_name']}.")
        print(f"     Status Code: {e.response.status_code}")
        print(f"     Response: {e.response.text}")
        upload_successful = False
        break
    except Exception as e:
        print(f"   - An unexpected error occurred during the upload process for {attachment['new_name']}. Error: {e}")
        upload_successful = False
        break

# Conditionally delete the original attachments
if upload_successful and len(new_attachment_ids) == len(attachments_to_update):
    print("\nAll files successfully uploaded and linked. Deleting original attachments...")
    for attachment in attachments_to_update:
        try:
            # --- FIX: Use the correct endpoint for deletion, including both IDs ---
            delete_url = f"{jama_base_url_v2.rstrip('/')}/items/{attachment['item_id']}/attachments/{attachment['original_attachment_id']}"
            delete_response = session.delete(delete_url, headers=json_headers)
            delete_response.raise_for_status()
            print(f"   - Deleted original attachment ID {attachment['original_attachment_id']} from item {attachment['item_id']}.")
        except Exception as e:
            print(f"   - Failed to delete original attachment ID {attachment['original_attachment_id']}. Error: {e}")
            print("   - Original attachments may remain. Please check manually.")
else:
    print("\n⚠️ An error occurred during the upload/link process. Deletion of original attachments has been skipped.")

# Cleanup
print("\nCleaning up temporary files...")
if delete_files_after_run:
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("Temporary directory cleaned up.")
    except Exception as e:
        print(f"Failed to clean up temporary directory. Please delete '{temp_dir}' manually. Error: {e}")
else:
    print("User chose not to delete temporary files. The 'temp_renamed_attachments' folder remains.")

print("\nScript execution complete.")