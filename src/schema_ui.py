"""Schema editor UI for defining model input fields."""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from .registry import ModelRegistry
from .schema_manager import get_schema_manager

logger = logging.getLogger(__name__)


async def get_schema_editor_html(request: Request, registry: ModelRegistry) -> str:
    """Generate schema editor HTML page."""
    models = await registry.list_all_models()
    schema_mgr = get_schema_manager()
    
    # Get all schemas
    schemas = {s.model_id: s for s in schema_mgr.list_schemas()}
    
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Model Schema Editor - ML Registry</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            header {
                background: white;
                padding: 20px 30px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            h1 {
                color: #333;
                font-size: 24px;
                margin-bottom: 10px;
            }
            .nav-link {
                color: #1976d2;
                text-decoration: none;
                font-size: 14px;
            }
            .nav-link:hover {
                text-decoration: underline;
            }
            .models-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                gap: 20px;
            }
            .model-card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .model-header {
                display: flex;
                justify-content: space-between;
                align-items: start;
                margin-bottom: 15px;
            }
            .model-name {
                font-size: 16px;
                font-weight: 600;
                color: #333;
                margin-bottom: 5px;
            }
            .model-id {
                font-size: 12px;
                color: #666;
                font-family: monospace;
            }
            .schema-badge {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
            }
            .schema-badge.has-schema {
                background: #e8f5e9;
                color: #2e7d32;
            }
            .schema-badge.no-schema {
                background: #fff3e0;
                color: #e65100;
            }
            .field-list {
                margin: 15px 0;
                padding: 10px;
                background: #f9f9f9;
                border-radius: 5px;
                max-height: 150px;
                overflow-y: auto;
            }
            .field-item {
                padding: 5px 0;
                font-size: 13px;
                color: #555;
                display: flex;
                justify-content: space-between;
            }
            .field-name {
                font-weight: 500;
            }
            .field-type {
                color: #1976d2;
                font-size: 11px;
                text-transform: uppercase;
            }
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.2s;
            }
            .btn-primary {
                background: #1976d2;
                color: white;
            }
            .btn-primary:hover {
                background: #1565c0;
            }
            .btn-secondary {
                background: #f5f5f5;
                color: #333;
            }
            .btn-secondary:hover {
                background: #e0e0e0;
            }
            .btn-danger {
                background: #d32f2f;
                color: white;
            }
            .btn-danger:hover {
                background: #c62828;
            }
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 1000;
                align-items: center;
                justify-content: center;
            }
            .modal.active {
                display: flex;
            }
            .modal-content {
                background: white;
                border-radius: 10px;
                padding: 30px;
                max-width: 600px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
            }
            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            .modal-title {
                font-size: 20px;
                font-weight: 600;
                color: #333;
            }
            .close-btn {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #666;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-label {
                display: block;
                margin-bottom: 5px;
                font-weight: 500;
                color: #333;
                font-size: 14px;
            }
            .form-input, .form-select {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }
            .form-input:focus, .form-select:focus {
                outline: none;
                border-color: #1976d2;
            }
            .form-checkbox {
                margin-right: 8px;
            }
            .fields-editor {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
            }
            .field-editor-item {
                background: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            .field-editor-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .btn-small {
                padding: 4px 8px;
                font-size: 12px;
            }
            .btn-group {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            .empty-state {
                text-align: center;
                padding: 40px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🔧 Model Schema Editor</h1>
                <p style="color: #666; margin: 10px 0;">Define input fields and data types for your models</p>
                <a href="/" class="nav-link">← Back to Dashboard</a>
            </header>
            
            <div class="models-grid" id="modelsGrid">
                <!-- Models will be loaded here -->
            </div>
        </div>
        
        <!-- Schema Editor Modal -->
        <div class="modal" id="schemaModal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2 class="modal-title" id="modalTitle">Edit Schema</h2>
                    <button class="close-btn" onclick="closeModal()">&times;</button>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Model Name</label>
                    <input type="text" class="form-input" id="modelName" readonly>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Model ID</label>
                    <input type="text" class="form-input" id="modelId" readonly>
                </div>
                
                <div class="fields-editor">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <label class="form-label" style="margin: 0;">Input Fields</label>
                        <button class="btn btn-secondary btn-small" onclick="addField()">+ Add Field</button>
                    </div>
                    <div id="fieldsContainer">
                        <!-- Fields will be added here -->
                    </div>
                </div>
                
                <div class="btn-group">
                    <button class="btn btn-primary" onclick="saveSchema()">Save Schema</button>
                    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                    <button class="btn btn-danger" onclick="deleteSchema()" id="deleteBtn" style="margin-left: auto;">Delete Schema</button>
                </div>
            </div>
        </div>
        
        <script>
            let currentModelId = null;
            let fields = [];
            
            // Load models and schemas
            async function loadModels() {
                try {
                    const response = await fetch('/api/models');
                    const data = await response.json();
                    const schemasResponse = await fetch('/api/schemas');
                    const schemasData = await schemasResponse.json();
                    
                    const schemasMap = {};
                    schemasData.schemas.forEach(s => {
                        schemasMap[s.model_id] = s;
                    });
                    
                    const grid = document.getElementById('modelsGrid');
                    grid.innerHTML = '';
                    
                    if (data.models.length === 0) {
                        grid.innerHTML = '<div class="empty-state">No models found</div>';
                        return;
                    }
                    
                    data.models.forEach(model => {
                        const schema = schemasMap[model.id];
                        const hasSchema = !!schema;
                        const fieldCount = schema ? schema.fields.length : 0;
                        
                        const card = document.createElement('div');
                        card.className = 'model-card';
                        card.innerHTML = `
                            <div class="model-header">
                                <div>
                                    <div class="model-name">${model.name}</div>
                                    <div class="model-id">${model.id}</div>
                                </div>
                                <span class="schema-badge ${hasSchema ? 'has-schema' : 'no-schema'}">
                                    ${hasSchema ? fieldCount + ' fields' : 'No schema'}
                                </span>
                            </div>
                            ${hasSchema ? `
                                <div class="field-list">
                                    ${schema.fields.map(f => `
                                        <div class="field-item">
                                            <span class="field-name">${f.name}</span>
                                            <span class="field-type">${f.type}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : '<p style="color: #666; font-size: 13px; margin: 10px 0;">No input fields defined</p>'}
                            <button class="btn btn-primary" onclick="editSchema('${model.id}', '${model.name}')">
                                ${hasSchema ? 'Edit Schema' : 'Define Schema'}
                            </button>
                        `;
                        grid.appendChild(card);
                    });
                } catch (error) {
                    console.error('Error loading models:', error);
                    alert('Failed to load models');
                }
            }
            
            // Edit schema
            async function editSchema(modelId, modelName) {
                currentModelId = modelId;
                document.getElementById('modelName').value = modelName;
                document.getElementById('modelId').value = modelId;
                
                // Load existing schema
                try {
                    const response = await fetch(`/api/schemas/${modelId}`);
                    if (response.ok) {
                        const schema = await response.json();
                        fields = schema.fields || [];
                        document.getElementById('deleteBtn').style.display = 'block';
                    } else {
                        fields = [];
                        document.getElementById('deleteBtn').style.display = 'none';
                    }
                } catch (error) {
                    fields = [];
                    document.getElementById('deleteBtn').style.display = 'none';
                }
                
                renderFields();
                document.getElementById('schemaModal').classList.add('active');
            }
            
            // Add field
            function addField() {
                fields.push({
                    name: '',
                    type: 'string',
                    required: true,
                    description: ''
                });
                renderFields();
            }
            
            // Remove field
            function removeField(index) {
                fields.splice(index, 1);
                renderFields();
            }
            
            // Render fields
            function renderFields() {
                const container = document.getElementById('fieldsContainer');
                if (fields.length === 0) {
                    container.innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">No fields defined. Click "Add Field" to start.</p>';
                    return;
                }
                
                container.innerHTML = fields.map((field, index) => `
                    <div class="field-editor-item">
                        <div class="field-editor-header">
                            <strong>Field ${index + 1}</strong>
                            <button class="btn btn-danger btn-small" onclick="removeField(${index})">Remove</button>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Field Name</label>
                            <input type="text" class="form-input" value="${field.name}" 
                                   onchange="fields[${index}].name = this.value" placeholder="e.g., PART_NUM">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Data Type</label>
                            <select class="form-select" onchange="fields[${index}].type = this.value">
                                <option value="string" ${field.type === 'string' ? 'selected' : ''}>String</option>
                                <option value="integer" ${field.type === 'integer' ? 'selected' : ''}>Integer</option>
                                <option value="float" ${field.type === 'float' ? 'selected' : ''}>Float</option>
                                <option value="boolean" ${field.type === 'boolean' ? 'selected' : ''}>Boolean</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Description (optional)</label>
                            <input type="text" class="form-input" value="${field.description || ''}" 
                                   onchange="fields[${index}].description = this.value" placeholder="Field description">
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" class="form-checkbox" ${field.required ? 'checked' : ''} 
                                       onchange="fields[${index}].required = this.checked">
                                Required field
                            </label>
                        </div>
                    </div>
                `).join('');
            }
            
            // Save schema
            async function saveSchema() {
                if (!currentModelId) return;
                
                // Validate
                for (let i = 0; i < fields.length; i++) {
                    if (!fields[i].name.trim()) {
                        alert(`Field ${i + 1} must have a name`);
                        return;
                    }
                }
                
                const schema = {
                    model_id: currentModelId,
                    model_name: document.getElementById('modelName').value,
                    fields: fields
                };
                
                try {
                    const response = await fetch('/api/schemas', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(schema)
                    });
                    
                    if (response.ok) {
                        alert('Schema saved successfully!');
                        closeModal();
                        loadModels();
                    } else {
                        const error = await response.json();
                        alert('Failed to save schema: ' + (error.detail || 'Unknown error'));
                    }
                } catch (error) {
                    console.error('Error saving schema:', error);
                    alert('Failed to save schema');
                }
            }
            
            // Delete schema
            async function deleteSchema() {
                if (!currentModelId) return;
                if (!confirm('Are you sure you want to delete this schema?')) return;
                
                try {
                    const response = await fetch(`/api/schemas/${currentModelId}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        alert('Schema deleted successfully!');
                        closeModal();
                        loadModels();
                    } else {
                        alert('Failed to delete schema');
                    }
                } catch (error) {
                    console.error('Error deleting schema:', error);
                    alert('Failed to delete schema');
                }
            }
            
            // Close modal
            function closeModal() {
                document.getElementById('schemaModal').classList.remove('active');
                currentModelId = null;
                fields = [];
            }
            
            // Load on page load
            loadModels();
        </script>
    </body>
    </html>
    """
    
    return html

# Made with Bob
