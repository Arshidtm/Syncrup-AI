"""
Nexus AI Engine - Graph Visualization Generator

Fetches graph data from the API and generates an interactive HTML visualization.
"""

import requests
import json

# Configuration
API_URL = "http://localhost:8000"
PROJECT_ID = "default"  # Change this to visualize different projects

def generate_visualization(project_id: str, output_file: str = "graph_visualization.html"):
    """
    Fetches graph data from the API and generates an interactive visualization.
    """
    print(f"Fetching graph data for project: {project_id}")
    
    try:
        # Fetch graph data from API
        response = requests.get(f"{API_URL}/graph-data", params={"project_id": project_id})
        response.raise_for_status()
        data = response.json()
        
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        
        print(f"Found {len(nodes)} nodes and {len(edges)} edges")
        
        # Generate HTML with vis-network
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Nexus Knowledge Graph - {project_id}</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: #fff;
        }}
        #info {{
            margin-bottom: 20px;
            padding: 15px;
            background: #2a2a2a;
            border-radius: 8px;
        }}
        #mynetwork {{
            width: 100%;
            height: 800px;
            border: 1px solid #444;
            border-radius: 8px;
            background: #0a0a0a;
        }}
        .stat {{
            display: inline-block;
            margin-right: 30px;
            padding: 10px 15px;
            background: #333;
            border-radius: 5px;
        }}
        h1 {{
            margin: 0 0 10px 0;
            color: #4CAF50;
        }}
    </style>
</head>
<body>
    <div id="info">
        <h1>🧠 Nexus Knowledge Graph</h1>
        <div class="stat">📁 Project: <strong>{project_id}</strong></div>
        <div class="stat">🔵 Nodes: <strong>{len(nodes)}</strong></div>
        <div class="stat">🔗 Edges: <strong>{len(edges)}</strong></div>
    </div>
    <div id="mynetwork"></div>

    <script type="text/javascript">
        // Node data
        var nodes = new vis.DataSet({json.dumps(nodes)});
        
        // Edge data
        var edges = new vis.DataSet({json.dumps(edges)});

        // Create network
        var container = document.getElementById('mynetwork');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        
        var options = {{
            nodes: {{
                shape: 'dot',
                size: 16,
                font: {{
                    size: 14,
                    color: '#ffffff'
                }},
                borderWidth: 2,
                color: {{
                    border: '#4CAF50',
                    background: '#2196F3',
                    highlight: {{
                        border: '#FFC107',
                        background: '#FF9800'
                    }}
                }}
            }},
            edges: {{
                width: 2,
                color: {{
                    color: '#666',
                    highlight: '#FFC107'
                }},
                arrows: {{
                    to: {{
                        enabled: true,
                        scaleFactor: 0.5
                    }}
                }},
                smooth: {{
                    type: 'continuous'
                }}
            }},
            physics: {{
                stabilization: {{
                    iterations: 200
                }},
                barnesHut: {{
                    gravitationalConstant: -8000,
                    springConstant: 0.04,
                    springLength: 95
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 100,
                navigationButtons: true,
                keyboard: true
            }}
        }};
        
        var network = new vis.Network(container, data, options);
        
        // Add click event
        network.on("click", function (params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                console.log("Clicked node:", node);
            }}
        }});
        
        console.log("Graph loaded successfully!");
    </script>
</body>
</html>
"""
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Visualization generated: {output_file}")
        print(f"📂 Open this file in your browser to view the graph!")
        
        return output_file
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server")
        print("   Make sure the API server is running: python src/api_server.py")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    import sys
    
    # Allow project_id as command line argument
    project_id = sys.argv[1] if len(sys.argv) > 1 else PROJECT_ID
    
    print("="*60)
    print("Nexus AI Engine - Graph Visualization Generator")
    print("="*60)
    
    generate_visualization(project_id)
