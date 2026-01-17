# Frontend Integration Guide for /check-impact Endpoint

## API Endpoint

```
POST http://localhost:8000/check-impact
Content-Type: application/json
```

## Request Format

### Required Fields

```json
{
  "project_id": "string",
  "filename": "string",
  "changes": "string (optional)"
}
```

### Field Descriptions

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `project_id` | string | ✅ Yes | Unique identifier for the project (must match the ID used during `/initialize`) | `"my-app"` or `"sample2"` |
| `filename` | string | ✅ Yes | Path to the changed file (can be absolute or relative) | `"src/auth/login.py"` or `"D:\\project\\src\\auth\\login.py"` |
| `changes` | string | ❌ No | Description of what changed in the file | `"Modified authenticate_user function signature"` |

---

## Request Examples

### Example 1: Minimal Request (Relative Path)

```json
{
  "project_id": "sample2",
  "filename": "frontend_app/services/api_client.ts"
}
```

### Example 2: With Change Description

```json
{
  "project_id": "my-app",
  "filename": "src/auth/login.py",
  "changes": "Added new parameter 'session_id' to authenticate_user function"
}
```

### Example 3: Absolute Path (Windows)

```json
{
  "project_id": "sample2",
  "filename": "D:\\Arshid\\practice\\Nexus_ai_engine\\project_demo\\frontend_app\\services\\api_client.ts",
  "changes": "Modified createOrder function to include validation"
}
```

### Example 4: Absolute Path (Unix/Mac)

```json
{
  "project_id": "my-app",
  "filename": "/home/user/projects/my-app/src/models.py",
  "changes": "Changed User model schema"
}
```

---

## Response Format

### Success Response (200 OK)

```json
{
  "status": "success",
  "impact_level": "high|medium|low|none",
  "summary": "Brief description of impact",
  "changed_file": "normalized/path/to/file.py",
  "affected_items": [
    {
      "file": "path/to/affected/file.py",
      "symbol": "function_or_class_name",
      "symbol_type": "function|class",
      "line_number": 42,
      "depends_on": "changed_symbol",
      "impact_reason": "Why this is affected",
      "breaking": true
    }
  ],
  "recommendations": [
    "Action item 1",
    "Action item 2"
  ],
  "blast_zone_size": 3
}
```

### Error Responses

#### 404 - Project Not Found
```json
{
  "detail": "Project 'unknown-project' not found in registry"
}
```

#### 400 - Invalid File Path
```json
{
  "detail": "Invalid file path: Path 'invalid/path' is outside project root"
}
```

#### 422 - Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "filename"],
      "msg": "filename cannot be empty",
      "type": "value_error"
    }
  ]
}
```

---

## Frontend Implementation Examples

### JavaScript/TypeScript (Fetch API)

```typescript
async function checkImpact(projectId: string, filename: string, changes?: string) {
  const response = await fetch('http://localhost:8000/check-impact', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      project_id: projectId,
      filename: filename,
      changes: changes || ''
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return await response.json();
}

// Usage
try {
  const result = await checkImpact(
    'my-app',
    'src/auth/login.py',
    'Modified function signature'
  );
  
  console.log(`Impact Level: ${result.impact_level}`);
  console.log(`Affected Items: ${result.blast_zone_size}`);
  console.log(`Summary: ${result.summary}`);
  
  result.affected_items.forEach(item => {
    console.log(`- ${item.file}::${item.symbol} (${item.impact_reason})`);
  });
} catch (error) {
  console.error('Impact check failed:', error);
}
```

### React Hook Example

```typescript
import { useState } from 'react';

interface ImpactCheckRequest {
  project_id: string;
  filename: string;
  changes?: string;
}

interface ImpactCheckResponse {
  status: string;
  impact_level: 'high' | 'medium' | 'low' | 'none';
  summary: string;
  changed_file: string;
  affected_items: Array<{
    file: string;
    symbol: string;
    symbol_type: string;
    line_number: number;
    depends_on: string;
    impact_reason: string;
    breaking: boolean;
  }>;
  recommendations: string[];
  blast_zone_size: number;
}

function useImpactCheck() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImpactCheckResponse | null>(null);

  const checkImpact = async (request: ImpactCheckRequest) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/check-impact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail);
      }

      const data = await response.json();
      setResult(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { checkImpact, loading, error, result };
}

// Usage in component
function ImpactAnalyzer() {
  const { checkImpact, loading, error, result } = useImpactCheck();

  const handleCheck = async () => {
    await checkImpact({
      project_id: 'my-app',
      filename: 'src/auth/login.py',
      changes: 'Modified function signature'
    });
  };

  return (
    <div>
      <button onClick={handleCheck} disabled={loading}>
        Check Impact
      </button>
      {loading && <p>Analyzing...</p>}
      {error && <p>Error: {error}</p>}
      {result && (
        <div>
          <h3>Impact: {result.impact_level}</h3>
          <p>{result.summary}</p>
          <p>Affected items: {result.blast_zone_size}</p>
        </div>
      )}
    </div>
  );
}
```

### Python (requests library)

```python
import requests

def check_impact(project_id: str, filename: str, changes: str = ""):
    url = "http://localhost:8000/check-impact"
    payload = {
        "project_id": project_id,
        "filename": filename,
        "changes": changes
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()  # Raise exception for 4xx/5xx
    
    return response.json()

# Usage
try:
    result = check_impact(
        project_id="my-app",
        filename="src/auth/login.py",
        changes="Modified function signature"
    )
    
    print(f"Impact Level: {result['impact_level']}")
    print(f"Summary: {result['summary']}")
    print(f"Affected Items: {result['blast_zone_size']}")
    
    for item in result['affected_items']:
        print(f"- {item['file']}::{item['symbol']} ({item['impact_reason']})")
        
except requests.exceptions.HTTPError as e:
    print(f"Error: {e.response.json()['detail']}")
```

---

## Important Notes

### 1. Project Must Be Initialized First

Before calling `/check-impact`, you must initialize the project:

```json
POST /initialize
{
  "project_id": "my-app",
  "project_path": "path/to/project"
}
```

### 2. Path Handling

The backend automatically handles:
- ✅ Absolute paths (Windows: `D:\...`, Unix: `/home/...`)
- ✅ Relative paths (`src/main.py`)
- ✅ Paths with `../` patterns
- ✅ Forward slashes `/` or backslashes `\`

**Recommendation**: Send the **absolute path** from your IDE/editor for accuracy.

### 3. File Doesn't Need to Exist Locally

If the file was indexed from a repository but doesn't exist locally, the analysis will still work using graph data only.

### 4. Changes Field is Optional

If you don't provide `changes`, the LLM will perform generic impact analysis based on the dependency graph.

---

## VS Code Extension Example

```typescript
import * as vscode from 'vscode';

async function analyzeImpact(document: vscode.TextDocument) {
  const projectId = vscode.workspace.name || 'default';
  const filename = document.fileName; // Absolute path
  
  // Get unsaved changes
  const changes = document.isDirty 
    ? 'File has unsaved changes' 
    : 'Saved changes';

  try {
    const response = await fetch('http://localhost:8000/check-impact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        filename: filename,
        changes: changes
      })
    });

    const result = await response.json();
    
    // Show notification
    if (result.impact_level === 'high') {
      vscode.window.showWarningMessage(
        `High Impact: ${result.summary} (${result.blast_zone_size} files affected)`
      );
    } else if (result.impact_level === 'none') {
      vscode.window.showInformationMessage('No impact detected');
    }
    
    return result;
  } catch (error) {
    vscode.window.showErrorMessage(`Impact analysis failed: ${error}`);
  }
}

// Trigger on file save
vscode.workspace.onDidSaveTextDocument(async (document) => {
  await analyzeImpact(document);
});
```

---

## Testing with cURL

```bash
# Basic request
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "sample2",
    "filename": "frontend_app/services/api_client.ts",
    "changes": "Modified createOrder function"
  }'

# With absolute path
curl -X POST http://localhost:8000/check-impact \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "sample2",
    "filename": "D:\\Arshid\\practice\\Nexus_ai_engine\\project_demo\\frontend_app\\services\\api_client.ts"
  }'
```

---

## Summary

**Minimum Required Data from Frontend:**
1. `project_id` - Which project to analyze
2. `filename` - Which file changed (absolute or relative path)

**Optional but Recommended:**
3. `changes` - Description of what changed (helps LLM provide better analysis)

The backend handles all path normalization automatically!
