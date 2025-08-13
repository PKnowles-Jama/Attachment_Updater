import requests
from requests.auth import HTTPBasicAuth
import json

# 1. Gather User Input
print("Please provide your Jama Connect API credentials and project details.")
print("------------------------------------------------------------------")
# jama_username = input("Enter your Jama Connect username: ")
# jama_password = input("Enter your Jama Connect password: ")
# project_api_id = input("Enter the Project API ID: ")
# custom_prefix = input("Enter the custom prefix for attachments (e.g., JSC_): ")
# jama_base_url = input("Enter your URL, i.e. https://<your_jama_instance_url>.com/rest/v1: ")

jama_username = "PKnowles"
jama_password = "LetsGoJama1331!"
project_api_id = 97
custom_prefix = "PK_"
jama_base_url = "https://pknowles-jama-airborne.jamacloud.com/rest/v1/"

# 2. Authenticate using a requests session
print("\nAttempting to authenticate with Jama Connect...")
session = requests.Session()
auth_object = HTTPBasicAuth(jama_username, jama_password)
test_url = f"{jama_base_url.rstrip('/')}/projects"

try:
    response = session.get(test_url, auth=auth_object)
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
# ------------------------------------------------------------------

# 3. Verify Project ID
print("Verifying Project ID...")
projects_url = f"{jama_base_url.rstrip('/')}/projects"
try:
    response = session.get(projects_url, auth=auth_object)
    response.raise_for_status()
    projects = response.json().get('data', [])

    project_ids = [p['id'] for p in projects]
    if int(project_api_id) not in project_ids:
        print(f"Error: Project ID {project_api_id} not found or you do not have permission to view it.")
        print(f"Available project IDs: {project_ids}")
        exit()

    print(f"Project ID {project_api_id} is valid.")

except requests.exceptions.HTTPError as e:
    print(f"Failed to fetch projects. Please check user permissions.")
    print(f"Error: {e}")
    exit()
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    exit()

# 4. Fetch all attachments (project-level and item-level)
print("Fetching attachments for the specified project...")
all_attachments = []

# Fetch project-level attachments
print("  - Fetching project-level attachments...")
attachments_url = f"{jama_base_url.rstrip('/')}/attachments?project={project_api_id}"
try:
    response = session.get(attachments_url, auth=auth_object)
    response.raise_for_status()
    project_attachments = response.json().get('data', [])
    all_attachments.extend(project_attachments)
    print(f"    - Found {len(project_attachments)} project-level attachments.")
except requests.exceptions.HTTPError as e:
    if e.response.status_code != 404:
        print(f"Failed to fetch project-level attachments for project ID {project_api_id}. Error: {e}")
except Exception as e:
    print(f"An unexpected error occurred while fetching project-level attachments: {e}")

# Fetch item-level attachments
print("  - Fetching item-level attachments...")
all_items = []
items_url = f"{jama_base_url.rstrip('/')}/items?project={project_api_id}"
page = 1
while items_url:
    params = {"startAt": (page - 1) * 20, "maxResults": 20}
    response = session.get(items_url, auth=auth_object, params=params)
    response.raise_for_status()

    data = response.json()
    all_items.extend(data['data'])

    if 'nextLink' in data['meta']:
        items_url = data['meta']['nextLink']
        page += 1
    else:
        items_url = None

print(f"  - Successfully fetched {len(all_items)} items from the project.")

for item in all_items:
    item_id = item['id']
    attachments_url = f"{jama_base_url.rstrip('/')}/items/{item_id}/attachments"
    
    try:
        # Fetch all attachments for the current item
        response = session.get(attachments_url, auth=auth_object)
        response.raise_for_status()
        item_attachments = response.json().get('data', [])
        all_attachments.extend(item_attachments)
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code != 404:
            print(f"Failed to fetch attachments for item ID {item_id}. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while fetching attachments for item ID {item_id}: {e}")

print(f"Successfully retrieved a total of {len(all_attachments)} attachments.")

# 5. Filter and Update Attachments
print("\nFiltering attachments that start with 'image' or 'Image'...")
attachments_to_update = []
for attachment in all_attachments:
    attachment_name = attachment['fields']['name']
    
    if attachment_name.lower().startswith('image'):
        attachments_to_update.append(attachment)

print(f"Found {len(attachments_to_update)} attachments to update.")

if attachments_to_update:
    enumeration = 1
    # Change the base URL to V2 for the update
    jama_base_url_v2 = jama_base_url.replace('/v1/', '/v2/')
    
    # We will need the CSRF token from the session cookies for V2 PATCH
    csrf_token = session.cookies.get('X-CSRF-TOKEN')
    headers = {
        "Content-Type": "application/json",
        "X-CSRF-TOKEN": csrf_token
    }

    for attachment in attachments_to_update:
        old_name_with_ext = attachment['fields']['name']
        filename_without_ext, file_extension = old_name_with_ext.rsplit('.', 1) if '.' in old_name_with_ext else (old_name_with_ext, '')
        
        # New name format: prefix_original_name_00001.extension
        new_name = f"{custom_prefix}{filename_without_ext}_{enumeration:05d}{'.' + file_extension if file_extension else ''}"
        
        # The payload for updating the attachment's name
        update_payload = {
            "name": new_name
        }
        
        # The correct V2 URL for updating an attachment
        update_url = f"{jama_base_url_v2.rstrip('/')}/attachments/{attachment['id']}"
        
        print(f"Updating attachment ID {attachment['id']}: '{old_name_with_ext}' -> '{new_name}'")
        
        try:
            # We use a PATCH request for partial updates in V2 with the CSRF token
            response = session.patch(update_url, auth=auth_object, json=update_payload, headers=headers)
            response.raise_for_status()
            
            print(f"  --> Update successful. Status code: {response.status_code}")
            enumeration += 1
            
        except requests.exceptions.HTTPError as e:
            print(f"  --> Failed to update attachment ID {attachment['id']}.")
            print(f"  --> Error: {e}")
        except Exception as e:
            print(f"  --> An unexpected error occurred: {e}")

    print("\nAttachment update process complete. Please check your Jama Connect project.")
else:
    print("No attachments found that meet the criteria. No updates were made.")