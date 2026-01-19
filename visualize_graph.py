"""
Graph Visualization Tool
Generates an interactive HTML visualization of the Neo4j knowledge graph.
"""
import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def get_graph_data(project_id=None):
    """Fetch graph data from Neo4j"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    nodes = []
    edges = []
    
    with driver.session() as session:
        # Build query based on whether project_id is provided
        if project_id:
            node_query = """
                MATCH (n {project_id: $project_id})
                WHERE n:File OR n:Function OR n:Class OR n:Call
                RETURN elementId(n) as id, labels(n) as labels, n.name as name, 
                       n.filename as filename, n.line as line
            """
            edge_query = """
                MATCH (n {project_id: $project_id})-[r]->(m {project_id: $project_id})
                RETURN elementId(n) as source, elementId(m) as target, type(r) as type
            """
            params = {"project_id": project_id}
        else:
            node_query = """
                MATCH (n)
                WHERE n:File OR n:Function OR n:Class OR n:Call
                RETURN elementId(n) as id, labels(n) as labels, n.name as name,
                       n.filename as filename, n.line as line
                LIMIT 500
            """
            edge_query = """
                MATCH (n)-[r]->(m)
                WHERE (n:File OR n:Function OR n:Class OR n:Call) 
                  AND (m:File OR m:Function OR m:Class OR m:Call)
                RETURN elementId(n) as source, elementId(m) as target, type(r) as type
                LIMIT 1000
            """
            params = {}
        
        # Get nodes
        result = session.run(node_query, params)
        for record in result:
            label = record["labels"][0] if record["labels"] else "Unknown"
            name = record["name"] or "unnamed"
            line = record["line"]
            
            node_label = f"{label}: {name}"
            if line:
                node_label += f" (L{line})"
            
            nodes.append({
                "id": record["id"],
                "label": node_label,
                "group": label,
                "title": f"{label}: {name}\nFile: {record['filename'] or 'N/A'}\nLine: {line or 'N/A'}"
            })
        
        # Get edges
        result = session.run(edge_query, params)
        for record in result:
            edges.append({
                "from": record["source"],
                "to": record["target"],
                "label": record["type"],
                "arrows": "to"
            })
    
    driver.close()
    return {"nodes": nodes, "edges": edges}

def generate_html(graph_data, output_file="graph_visualization.html"):
    """Generate interactive HTML visualization"""
    
    html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Knowledge Graph Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        #controls {
            background: white;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        #mynetwork {
            width: 100%;
            height: 800px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .info {
            background: #e3f2fd;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 4px;
            border-left: 4px solid #2196f3;
        }
        button {
            background: #2196f3;
            color: white;
            border: none;
            padding: 8px 16px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background: #1976d2;
        }
        .legend {
            display: flex;
            gap: 20px;
            margin-top: 10px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 50%;
        }
    </style>
</head>
<body>
    <h1>🔍 Knowledge Graph Visualization</h1>
    
    <div id="controls">
        <div class="info">
            <strong>Nodes:</strong> {{node_count}} | <strong>Edges:</strong> {{edge_count}}
        </div>
        <button onclick="network.fit()">Fit to Screen</button>
        <button onclick="network.stabilize()">Stabilize</button>
        <button onclick="togglePhysics()">Toggle Physics</button>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background: #97c2fc;"></div>
                <span>File</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #fb7e81;"></div>
                <span>Function</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #7be141;"></div>
                <span>Class</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ffa807;"></div>
                <span>Call</span>
            </div>
        </div>
    </div>
    
    <div id="mynetwork"></div>

    <script type="text/javascript">
        // Graph data
        const nodes = new vis.DataSet({{nodes_json}});
        const edges = new vis.DataSet({{edges_json}});

        // Network configuration
        const container = document.getElementById('mynetwork');
        const data = { nodes: nodes, edges: edges };
        const options = {
            nodes: {
                shape: 'dot',
                size: 16,
                font: {
                    size: 14,
                    color: '#333'
                },
                borderWidth: 2,
                shadow: true
            },
            edges: {
                width: 2,
                shadow: true,
                smooth: {
                    type: 'continuous'
                },
                font: {
                    size: 12,
                    align: 'middle'
                }
            },
            groups: {
                File: {
                    color: { background: '#97c2fc', border: '#2b7ce9' }
                },
                Function: {
                    color: { background: '#fb7e81', border: '#c0392b' }
                },
                Class: {
                    color: { background: '#7be141', border: '#27ae60' }
                },
                Call: {
                    color: { background: '#ffa807', border: '#e67e22' }
                }
            },
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 95,
                    springConstant: 0.04
                },
                stabilization: {
                    iterations: 150
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200,
                navigationButtons: true,
                keyboard: true
            }
        };

        // Create network
        const network = new vis.Network(container, data, options);
        
        // Toggle physics
        let physicsEnabled = true;
        function togglePhysics() {
            physicsEnabled = !physicsEnabled;
            network.setOptions({ physics: { enabled: physicsEnabled } });
        }
        
        // Click event
        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                console.log("Clicked node:", node);
            }
        });
        
        // Stabilization progress
        network.on("stabilizationProgress", function(params) {
            const progress = Math.round((params.iterations / params.total) * 100);
            console.log("Stabilization progress:", progress + "%");
        });
        
        network.on("stabilizationIterationsDone", function() {
            console.log("Stabilization complete!");
        });
    </script>
</body>
</html>"""
    
    # Replace placeholders
    html = html_template.replace("{{node_count}}", str(len(graph_data["nodes"])))
    html = html.replace("{{edge_count}}", str(len(graph_data["edges"])))
    html = html.replace("{{nodes_json}}", json.dumps(graph_data["nodes"]))
    html = html.replace("{{edges_json}}", json.dumps(graph_data["edges"]))
    
    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ Visualization saved to: {output_file}")
    print(f"📊 Nodes: {len(graph_data['nodes'])}, Edges: {len(graph_data['edges'])}")

if __name__ == "__main__":
    print("=" * 60)
    print("Knowledge Graph Visualization Generator")
    print("=" * 60)
    
    # Ask for project_id
    project_id = input("\nEnter project_id (or press Enter for all projects): ").strip()
    
    if not project_id:
        project_id = None
        print("Fetching data for ALL projects...")
    else:
        print(f"Fetching data for project: {project_id}")
    
    # Get graph data
    print("\nQuerying Neo4j...")
    graph_data = get_graph_data(project_id)
    
    if not graph_data["nodes"]:
        print("❌ No data found in the graph!")
        print("Make sure you've initialized a project via /initialize or /add-repository")
    else:
        # Generate HTML
        generate_html(graph_data)
        print("\n🌐 Open 'graph_visualization.html' in your browser to view the graph!")
