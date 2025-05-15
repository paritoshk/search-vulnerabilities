import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    from supabase import create_client, Client
    from supabase.lib.client_options import ClientOptions
    from postgrest.exceptions import APIError
except ImportError:
    print("The 'supabase' library is not installed. Please install it with 'pip install supabase python-dotenv'")
    exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv() # Load environment variables from .env file if it exists
except ImportError:
    print("The 'python-dotenv' library is not installed. Not critical if env vars are set otherwise. To install: 'pip install python-dotenv'")


# --- Configuration ---
# Name of the table in Supabase
CVE_TABLE_NAME = "cve_entries"
# Path to the JSON data file relative to the project root
# Assuming this script is in a 'supabase' subdirectory and data is in 'data' at the root
# Adjust if your directory structure is different
PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_DATA_PATH = PROJECT_ROOT / "data" / "nvdcve-1.1-2025.json"

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_env_variable(var_name: str) -> Optional[str]:
    """
    Safely retrieves an environment variable.

    Args:
        var_name: The name of the environment variable.

    Returns:
        The value of the environment variable or None if not found.
    """
    value = os.getenv(var_name)
    if not value:
        # Changed to debug level as we will try multiple keys
        logger.debug(f"Environment variable {var_name} not found.")
    return value

def init_supabase_client() -> Optional[Client]:
    """
    Initializes and returns a Supabase client.

    Reads Supabase credentials from environment variables, trying common naming conventions.
    Prioritizes service role keys for necessary permissions.
    Exits if essential credentials are not found.

    Returns:
        A Supabase client instance or None if initialization fails.
    """
    supabase_url = get_env_variable("NEXT_PUBLIC_SUPABASE_URL")
    
    # Prioritize service role keys
    supabase_key = (
        get_env_variable("SUPABASE_KEY") or  # Common generic name, often service role
        get_env_variable("SUPABASE_SERVICE_ROLE_KEY") or # Explicit service role key
        get_env_variable("NEXT_PUBLIC_SUPABASE_SERIVCE_ROLE_KEY") # User provided service role key
    )

    if not supabase_key:
        logger.warning(
            "No explicit service role key (SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY, NEXT_PUBLIC_SUPABASE_SERIVCE_ROLE_KEY) found. "
            "Attempting to use anon key (NEXT_PUBLIC_SUPABASE_ANON_KEY). "
            "This may not have sufficient permissions for schema modifications."
        )
        supabase_key = get_env_variable("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error(
            "Supabase URL or Key is missing. Please set the appropriate environment variables. "
            "Checked: NEXT_PUBLIC_SUPABASE_URL for URL. "
            "Checked: SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY, NEXT_PUBLIC_SUPABASE_SERIVCE_ROLE_KEY, NEXT_PUBLIC_SUPABASE_ANON_KEY for Key."
        )
        return None

    # Add a check for the URL format
    if not (supabase_url.startswith("http://") or supabase_url.startswith("https://")):
        logger.error(
            f"Invalid Supabase URL format: {supabase_url}. "
            "It should start with 'http://' or 'https://' and be your project's API URL, "
            "not a PostgreSQL connection string."
        )
        return None

    logger.info(f"Using Supabase URL: {supabase_url[:30]}...") # Increased preview length slightly
    logger.info(f"Using Supabase Key: {'********' + supabase_key[-4:] if len(supabase_key) > 4 else 'Key too short to mask'}")
    if not (
        os.getenv("SUPABASE_KEY") or 
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or 
        os.getenv("NEXT_PUBLIC_SUPABASE_SERIVCE_ROLE_KEY")
    ) and os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY"):
        logger.warning("Proceeding with ANON key. Table creation and other administrative tasks may fail.")


    try:
        logger.info(f"Attempting to connect to Supabase at {supabase_url[:20]}...")
        # Explicitly set schema if needed, default is 'public'
        # options = ClientOptions(schema="public")
        # client: Client = create_client(supabase_url, supabase_key, options=options)
        client: Client = create_client(supabase_url, supabase_key)
        logger.info("Successfully initialized Supabase client.")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None

def create_cve_table_if_not_exists(client: Client) -> bool:
    """
    Creates the CVE table in Supabase if it doesn't already exist.

    The table schema includes columns for CVE ID, assigner, various data fields as JSONB,
    timestamps, and the raw CVE item. It also creates indexes for common query fields.

    Args:
        client: The initialized Supabase client.

    Returns:
        True if table creation was successful or table already exists, False otherwise.
    """
    # User has indicated they will create the table and triggers manually.
    # This function will now just confirm that and allow the script to proceed.
    logger.info(f"Skipping automatic creation of table '{CVE_TABLE_NAME}' and triggers as per user instruction.")
    logger.info("Please ensure the table exists and has the correct schema before data loading.")
    return True

    # try:
    #     logger.info(f"Attempting to create table '{CVE_TABLE_NAME}' and associated triggers if they don't exist...")
        
    #     # Use rpc with 'exec_sql' as client.sql() method is not found
    #     # The client.sql() method itself uses this RPC call internally.
    #     # Parameter for the SQL query is expected to be 'sql'.
        
    #     logger.info("Executing table creation SQL...")
    #     # client.rpc("exec_sql", {"sql": table_creation_sql}).execute() # User removed table_creation_sql
    #     logger.info(f"Table '{CVE_TABLE_NAME}' schema ensured.")
        
    #     logger.info("Executing trigger function creation SQL...")
    #     # client.rpc("exec_sql", {"sql": trigger_function_sql}).execute() # User removed trigger_function_sql
    #     logger.info("Trigger function 'trigger_set_timestamp' ensured.")
        
    #     logger.info("Executing trigger creation SQL...")
    #     # client.rpc("exec_sql", {"sql": trigger_creation_sql}).execute() # User removed trigger_creation_sql
    #     logger.info(f"Update trigger for '{CVE_TABLE_NAME}' ensured.")

    #     logger.info(f"Successfully ensured table '{CVE_TABLE_NAME}' and triggers exist.")
    #     return True
    # except APIError as e:
    #     logger.error(f"Supabase APIError during table creation: {e.message}")
    #     if hasattr(e, 'details'): logger.error(f"Details: {e.details}")
    #     if hasattr(e, 'hint'): logger.error(f"Hint: {e.hint}")
    #     return False
    # except Exception as e:
    #     logger.error(f"An unexpected error occurred during table creation: {e}")
    #     return False

def extract_and_transform_cve_data(cve_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extracts relevant data from a single CVE item and transforms it for database insertion.

    Args:
        cve_item: A dictionary representing a single CVE item from the NVD JSON feed.

    Returns:
        A dictionary containing the structured data for the database, or None if essential
        data (like CVE ID) is missing.
    """
    cve_data = cve_item.get("cve", {})
    if not cve_data:
        logger.warning("CVE item missing 'cve' block. Skipping.")
        return None

    cve_meta = cve_data.get("CVE_data_meta", {})
    cve_id = cve_meta.get("ID")
    if not cve_id:
        logger.warning(f"CVE item missing 'ID' in CVE_data_meta. Raw item: {str(cve_item)[:200]}")
        return None

    assigner = cve_meta.get("ASSIGNER")

    problem_type_data = cve_data.get("problemtype", {}).get("problemtype_data")
    references_data = cve_data.get("references", {}).get("reference_data")
    description_data_full = cve_data.get("description", {}).get("description_data")

    description_text = None
    if description_data_full and isinstance(description_data_full, list):
        for desc_entry in description_data_full:
            if isinstance(desc_entry, dict) and desc_entry.get("lang") == "en":
                description_text = desc_entry.get("value")
                break
    
    # Ensure problem_type_data, references_data, description_data_full are stored as valid JSON
    # by converting them to JSON strings if they are Python dicts/lists,
    # though Supabase client often handles this. Explicit is safer for JSONB.
    # However, Supabase client usually handles Python dicts/lists directly for JSONB.

    return {
        "cve_id": cve_id,
        "assigner": assigner,
        "problem_type_data": problem_type_data, # Directly pass the Python object
        "references_data": references_data,     # Directly pass the Python object
        "description_text": description_text,
        "description_data_full": description_data_full, # Directly pass the Python object
        "configurations_data": cve_item.get("configurations"), # Directly pass the Python object
        "impact_data": cve_item.get("impact"),               # Directly pass the Python object
        "published_date": cve_item.get("publishedDate"),
        "last_modified_date": cve_item.get("lastModifiedDate"),
        "raw_cve_item": cve_item # Store the whole original item as JSONB
    }

def load_and_process_cve_data(client: Client, json_file_path: Path) -> None:
    """
    Loads CVE data from the specified JSON file, processes each item,
    and upserts it into the Supabase table.

    Args:
        client: The initialized Supabase client.
        json_file_path: Path object for the JSON data file.
    """
    if not json_file_path.exists():
        logger.error(f"JSON data file not found at: {json_file_path}")
        return

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {json_file_path}: {e}")
        return
    except Exception as e:
        logger.error(f"Error reading file {json_file_path}: {e}")
        return

    cve_items: List[Dict[str, Any]] = data.get("CVE_Items", [])
    if not cve_items:
        logger.warning("No 'CVE_Items' found in the JSON data.")
        return

    total_items = len(cve_items)
    logger.info(f"Found {total_items} CVE items to process.")

    processed_count = 0
    upserted_count = 0
    failed_count = 0
    
    # Batching for upsert might be more performant for very large datasets
    # For now, upserting one by one for simplicity.
    # batch_size = 100 
    # current_batch = []

    for i, item in enumerate(cve_items):
        transformed_data = extract_and_transform_cve_data(item)
        if transformed_data:
            try:
                # Upsert logic: Inserts if cve_id doesn't exist, updates if it does.
                response = client.table(CVE_TABLE_NAME).upsert(
                    transformed_data, 
                    on_conflict="cve_id" # Specify the column for conflict resolution
                ).execute()
                
                # Supabase upsert response usually contains data if successful.
                # Check for errors in response if APIError is not raised.
                if hasattr(response, 'error') and response.error:
                    logger.error(f"Failed to upsert CVE ID {transformed_data['cve_id']}. Error: {response.error}")
                    failed_count +=1
                else:
                    upserted_count += 1
                
                if (i + 1) % 100 == 0 or (i + 1) == total_items: # Log progress every 100 items
                    logger.info(f"Processed {i+1}/{total_items} items. Upserted: {upserted_count}, Failed: {failed_count}")

            except APIError as e:
                logger.error(f"Supabase APIError during upsert for CVE ID {transformed_data.get('cve_id', 'N/A')}: {e.message}")
                if hasattr(e, 'details'): logger.error(f"Details: {e.details}")
                failed_count +=1
            except Exception as e:
                logger.error(f"Unexpected error during upsert for CVE ID {transformed_data.get('cve_id', 'N/A')}: {e}")
                failed_count +=1
        else:
            failed_count +=1 # Failed to transform
        processed_count +=1
            
    logger.info(f"--- Processing Complete ---")
    logger.info(f"Total items read: {processed_count}")
    logger.info(f"Successfully upserted: {upserted_count}")
    logger.info(f"Failed/Skipped: {failed_count}")


def main():
    """
    Main function to orchestrate the CVE data processing.
    Initializes Supabase client, creates table, and processes data.
    """
    logger.info("Starting CVE data import process...")
    
    supabase_client = init_supabase_client()
    if not supabase_client:
        logger.error("Exiting due to Supabase client initialization failure.")
        return

    if not create_cve_table_if_not_exists(supabase_client):
        logger.error("Exiting due to table creation failure.")
        return

    load_and_process_cve_data(supabase_client, JSON_DATA_PATH)
    
    logger.info("CVE data import process finished.")

if __name__ == "__main__":
    main()
