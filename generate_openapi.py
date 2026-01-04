"""
API Documentation Generator
Generates OpenAPI 3.0 specification for ROXY HTTP IPC API
"""
import yaml
from pathlib import Path

ROXY_DIR = Path.home() / ".roxy"

openapi_spec = {
    "openapi": "3.0.0",
    "info": {
        "title": "ROXY Core API",
        "version": "1.0.0",
        "description": "AI Assistant HTTP IPC API - Voice-triggered operations with RAG",
        "contact": {
            "name": "ROXY Development",
            "url": "https://github.com/yourusername/roxy"
        }
    },
    "servers": [
        {
            "url": "http://127.0.0.1:8766/v1",
            "description": "Local IPC server (v1)"
        },
        {
            "url": "http://127.0.0.1:8766",
            "description": "Local IPC server (unversioned - deprecated)"
        }
    ],
    "security": [
        {"TokenAuth": []}
    ],
    "paths": {
        "/health": {
            "get": {
                "summary": "Health check",
                "description": "Check if ROXY core is running",
                "security": [],
                "responses": {
                    "200": {
                        "description": "Service healthy",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string", "example": "healthy"},
                                        "timestamp": {"type": "string", "format": "date-time"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/run": {
            "post": {
                "summary": "Execute command",
                "description": "Execute a natural language command",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["command"],
                                "properties": {
                                    "command": {
                                        "type": "string",
                                        "description": "Natural language command",
                                        "example": "what is the weather?"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Command executed successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string", "example": "success"},
                                        "command": {"type": "string"},
                                        "result": {"type": "string"},
                                        "response_time": {"type": "number", "format": "float"}
                                    }
                                }
                            }
                        }
                    },
                    "403": {"description": "Authentication failed"},
                    "429": {"description": "Rate limit exceeded"}
                }
            }
        },
        "/batch": {
            "post": {
                "summary": "Execute batch commands",
                "description": "Execute multiple commands in parallel",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["commands"],
                                "properties": {
                                    "commands": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "example": ["git status", "system health"]
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Batch executed",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "commands": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "command": {"type": "string"},
                                                    "status": {"type": "string"},
                                                    "result": {"type": "string"}
                                                }
                                            }
                                        },
                                        "total": {"type": "integer"},
                                        "response_time": {"type": "number"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/stream": {
            "get": {
                "summary": "Stream command response",
                "description": "Stream command response using Server-Sent Events",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Query string"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "SSE stream",
                        "content": {
                            "text/event-stream": {
                                "schema": {
                                    "type": "string",
                                    "description": "Server-Sent Events stream"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/metrics": {
            "get": {
                "summary": "Prometheus metrics",
                "description": "Get Prometheus metrics (if enabled)",
                "security": [],
                "responses": {
                    "200": {
                        "description": "Metrics in Prometheus format",
                        "content": {
                            "text/plain": {
                                "schema": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "securitySchemes": {
            "TokenAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-ROXY-Token",
                "description": "32-byte authentication token from ~/.roxy/secret.token"
            }
        }
    }
}


def generate_openapi_spec():
    """Generate and save OpenAPI spec"""
    docs_dir = ROXY_DIR / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    spec_file = docs_dir / "openapi.yaml"
    with open(spec_file, 'w') as f:
        yaml.dump(openapi_spec, f, sort_keys=False, default_flow_style=False)
    
    print(f"✅ OpenAPI spec generated: {spec_file}")
    print(f"   View with: https://editor.swagger.io/")
    return spec_file


if __name__ == "__main__":
    generate_openapi_spec()
