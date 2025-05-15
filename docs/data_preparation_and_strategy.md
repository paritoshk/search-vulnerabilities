# Data Preparation and Query Strategy

This document outlines the strategy for preparing the CVE (Common Vulnerabilities and Exposures) data and the rationale behind creating a refined subset for the natural language search agent.

## 1. Initial Data Ingestion

- **Source:** NVD JSON feeds (specifically `nvdcve-1.1-2025.json` containing 12,040 CVEs).
- **Process:** A Python script (`supabase/connect_db.py`) was developed to:
    - Connect to the Supabase instance.
    - Define a schema and (initially) create a table named `cve_entries`.
    - Parse the JSON feed.
    - Upsert each CVE item into the `cve_entries` table.
- **Outcome:** 12,039 out of 12,040 CVEs were successfully ingested into the `cve_entries` table in Supabase.

## 2. Rationale for a Refined Data Subset

The full `cve_entries` dataset contains many entries that might be incomplete or lack detailed information in crucial fields like `problem_type_data`, `description_text`, `references_data`, or `impact_data`. 

For the natural language search agent to be effective and provide meaningful results, it's beneficial to have it operate on a dataset where entries are reasonably "rich" or "complete."

**Advantages of a refined subset:**

- **Improved Agent Performance:** Queries run faster on a smaller, more targeted dataset.
- **Simplified Agent Logic:** The agent doesn't need to bake in complex pre-filtering logic for data completeness into every query it generates.
- **More Relevant Results:** The likelihood of returning useful information from natural language queries increases when the underlying data is richer.
- **Focused Development:** Allows the agent development to focus on the core task of translating natural language to structured filters for the actual search intent, rather than data cleaning.

## 3. Defining "Rich" CVE Entries

A CVE entry is considered "rich" for the purpose of this project if it meets the following criteria:

1.  **Has detailed problem type information:** The `problem_type_data` field (a JSONB array) contains at least one entry, and that entry's `description` array is not empty.
2.  **Has an English description text:** The `description_text` field is not null and not an empty string.
3.  **Has reference data:** The `references_data` field (a JSONB array) is not null and not empty.
4.  **Has impact data:** The `impact_data` field (a JSONB object) is not null and not an empty JSON object (`{}`).

## 4. Creating the `rich_cve_entries` View

To implement this strategy, a SQL VIEW named `rich_cve_entries` was created in Supabase. A view is a virtual table based on the result-set of a stored query. It doesn't store data itself but executes the underlying query each time it's accessed, ensuring the data is always current relative to the base `cve_entries` table.

**SQL Query to Identify Rich Entries (and define the view):**

```sql
SELECT *
FROM cve_entries
WHERE
    -- Criteria 1: problem_type_data has meaningful content
    (problem_type_data IS NOT NULL AND problem_type_data -> 0 -> 'description' -> 0 IS NOT NULL)
    
    AND
    
    -- Criteria 2: description_text is present and not empty
    (description_text IS NOT NULL AND description_text != '')
    
    AND
    
    -- Criteria 3: references_data array is present and not empty
    (references_data IS NOT NULL AND references_data -> 0 IS NOT NULL)
    
    AND
    
    -- Criteria 4: impact_data object is present and not an empty object
    (impact_data IS NOT NULL AND impact_data::text != '{}');
```

**SQL Command to Create/Replace the View:**

```sql
CREATE OR REPLACE VIEW rich_cve_entries AS
SELECT 
    id,
    cve_id,
    assigner,
    problem_type_data,
    references_data,
    description_text,
    description_data_full,
    configurations_data,
    impact_data,
    published_date,
    last_modified_date,
    raw_cve_item,
    created_at,
    updated_at
FROM cve_entries
WHERE
    (problem_type_data IS NOT NULL AND problem_type_data -> 0 -> 'description' -> 0 IS NOT NULL)
    AND (description_text IS NOT NULL AND description_text != '')
    AND (references_data IS NOT NULL AND references_data -> 0 IS NOT NULL)
    AND (impact_data IS NOT NULL AND impact_data::text != '{}');
```

This view resulted in approximately 3,740 entries, providing a focused dataset for the search agent.

## 5. Next Steps for Agent Development

The natural language search agent will be developed to primarily query the `rich_cve_entries` view. This simplifies the agent's task to translating user intent (e.g., "recent critical vulnerabilities in Windows") into structured SQL WHERE clauses applicable to this pre-filtered, richer dataset. 



## Appendix: SQL Query to Create the `rich_cve_entries` View




We want to select all rows where:
1.  The `problem_type_data` JSONB object has meaningful content inside its `description` array (i.e., the inner `description` array is not empty).
2.  The entry also has `description_text` (not null or empty).
3.  The entry has `references_data` (the JSONB array is not null or empty).
4.  The entry has `impact_data` (the JSONB object is not null or empty).

Here's a SQL query we can use in the Supabase SQL editor to achieve this:

```sql
SELECT *
FROM cve_entries
WHERE
    -- 1. problem_type_data has actual descriptions
    --    Checks if the first element of problem_type_data array exists,
    --    and within that, the 'description' array also has at least one element.
    (problem_type_data IS NOT NULL AND problem_type_data -> 0 -> 'description' -> 0 IS NOT NULL)
    
    AND
    
    -- 2. description_text is present and not empty
    (description_text IS NOT NULL AND description_text != '')
    
    AND
    
    -- 3. references_data array is present and not empty
    --    Checks if the first element of references_data array exists.
    (references_data IS NOT NULL AND references_data -> 0 IS NOT NULL)
    
    AND
    
    -- 4. impact_data object is present and not an empty object
    --    Checks if impact_data is not NULL and is not just an empty JSON object '{}'.
    --    If 'baseMetricV3' is always present when impact_data is meaningful,
    --    you could also use: (impact_data ? 'baseMetricV3')
    (impact_data IS NOT NULL AND impact_data::text != '{}');

```

**Explanation of the `WHERE` clause conditions:**

*   `problem_type_data IS NOT NULL AND problem_type_data -> 0 -> 'description' -> 0 IS NOT NULL`:
    *   Ensures `problem_type_data` is not null.
    *   `-> 0` accesses the first element of the `problem_type_data` JSONB array.
    *   `-> 'description'` accesses the `description` key within that first element.
    *   `-> 0` then accesses the first element of the *inner* `description` array.
    *   `IS NOT NULL` effectively checks that this path is valid and the inner array is not empty.

*   `description_text IS NOT NULL AND description_text != ''`:
    *   Standard check for a non-null and non-empty text field.

*   `references_data IS NOT NULL AND references_data -> 0 IS NOT NULL`:
    *   Ensures `references_data` is not null.
    *   `-> 0` accesses the first element of the `references_data` array. If it exists, the array is not empty.

*   `impact_data IS NOT NULL AND impact_data::text != '{}'`:
    *   Ensures `impact_data` is not null.
    *   `impact_data::text != '{}'` converts the JSONB object to its text representation and checks if it's not an empty object (`{}`). This is a common way to check if a JSONB object has any key-value pairs. If you know a specific key (e.g., `baseMetricV3`) that always exists when `impact_data` is meaningful, using `(impact_data ? 'baseMetricV3')` would be more direct.

This query should give us a good subset of your CVE data that has richer information in these specific fields, which will be a solid foundation for testing and developing the natural language agent.

