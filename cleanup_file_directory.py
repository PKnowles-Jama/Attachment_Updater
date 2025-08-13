import os
import shutil

def cleanup(delete_files_after_run, temp_dir):
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