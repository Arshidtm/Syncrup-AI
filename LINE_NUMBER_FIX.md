# Line Number & Metadata Storage - Fixed!

## The Problem

Your impact report showed `"line_number": null` for all affected items because the graph manager wasn't storing line numbers.

## What Was Wrong

**In `src/graph/manager.py` line 38-43:**

```python
# BEFORE (line numbers NOT stored)
MERGE (d:{label} {name: $name, filename: $filename, project_id: $project_id})
WITH d
MATCH (f:File {name: $filename, project_id: $project_id})
MERGE (f)-[:CONTAINS]->(d)
```

The parsers were sending line numbers in the `definitions` array:
```python
{
  "definitions": [
    {"type": "function", "name": "create_diary_entry", "line": 15}  # ← Line number sent!
  ]
}
```

But the graph manager **ignored** the `line` property!

## The Fix

**Updated `src/graph/manager.py`:**

```python
# AFTER (line numbers ARE stored)
line = definition.get("line")  # Extract line number

MERGE (d:{label} {name: $name, filename: $filename, project_id: $project_id})
SET d.line = $line  # ← NOW STORING LINE NUMBER!
WITH d
MATCH (f:File {name: $filename, project_id: $project_id})
MERGE (f)-[:CONTAINS]->(d)
```

## What This Means

Now when you create the graph, **line numbers will be stored** for:
- ✅ Functions
- ✅ Classes
- ✅ Calls (already working)

## How to Test

1. **Clear the database:**
   ```bash
   python clear_database.py
   ```

2. **Re-index your project:**
   ```bash
   POST /add-repository
   {
     "project_id": "your-project-id",
     "repo_url": "https://github.com/your/repo.git"
   }
   ```

3. **Check impact again:**
   ```bash
   POST /check-impact
   {
     "project_id": "your-project-id",
     "filename": "backend/app/services/diary_service.py"
   }
   ```

4. **Now you should see:**
   ```json
   {
     "affected_items": [
       {
         "file": "frontend/src/api/diaryApiClient.ts",
         "symbol": "apiFetch",
         "line_number": 42,  // ← NO LONGER NULL!
         "depends_on": "create_diary_entry"
       }
     ]
   }
   ```

## Additional Metadata Support

The fix also supports storing **any additional metadata** from parsers:

```python
# Parsers can send:
{
  "definitions": [
    {
      "type": "function",
      "name": "foo",
      "line": 10,
      "params": ["x", "y"],      # ← Can be stored
      "return_type": "int",       # ← Can be stored
      "docstring": "Does stuff"   # ← Can be stored
    }
  ]
}
```

To store additional metadata, just add more `SET` statements:

```python
SET d.line = $line,
    d.params = $params,
    d.return_type = $return_type,
    d.docstring = $docstring
```

## Summary

✅ **Fixed**: Line numbers now stored in Neo4j  
✅ **Impact reports**: Will show actual line numbers  
✅ **Extensible**: Can add more metadata easily  
⚠️ **Action required**: Re-index your projects to populate line numbers
