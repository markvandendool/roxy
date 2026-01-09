#!/usr/bin/env python3
"""
ROXY AI Orchestrator MCP Server
Phase 8: AI Excellence - LangGraph, Mem0, Unified Gateway, Human-in-the-Loop
"""
import asyncio
import json
import logging
import os
from typing import Optional, Dict, List, Any
from datetime import datetime
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP('roxy-ai-orchestrator')

# Configuration
MEM0_API_URL = os.getenv('MEM0_API_URL', 'http://localhost:8000')
LANGGRAPH_API_URL = os.getenv('LANGGRAPH_API_URL', 'http://localhost:8123')
# Supabase for persistent memory storage (same as mindsong-juke-hub)
SUPABASE_URL = os.getenv('SUPABASE_URL', os.getenv('VITE_SUPABASE_URL', 'https://rlbltiuswhlzjvszhvsc.supabase.co'))
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY', os.getenv('VITE_SUPABASE_ANON_KEY', ''))


@mcp.tool()
async def ai_create_memory(
    user_id: str,
    memory_text: str,
    metadata: Optional[Dict] = None
) -> str:
    """
    Create a persistent memory using Supabase (fallback to Mem0 if available).
    
    Args:
        user_id: User identifier
        memory_text: Memory content
        metadata: Optional metadata
    """
    try:
        # Try Supabase first (same as mindsong-juke-hub pattern)
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                from supabase import create_client, Client
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                
                memory_data = {
                    'user_id': user_id,
                    'memory_text': memory_text,
                    'metadata': json.dumps(metadata) if metadata else None,
                    'created_at': datetime.now().isoformat()
                }
                
                # Try to insert into ai_memories table (may need to be created)
                try:
                    response = supabase.table('ai_memories').insert(memory_data).execute()
                    if response.data:
                        return json.dumps({'status': 'created', 'memory': response.data[0], 'storage': 'supabase'})
                except:
                    # Fallback to Mem0 if Supabase table doesn't exist
                    pass
            except ImportError:
                # Fallback to REST API
                try:
                    import requests
                    headers = {
                        'apikey': SUPABASE_KEY,
                        'Authorization': f'Bearer {SUPABASE_KEY}',
                        'Content-Type': 'application/json',
                        'Prefer': 'return=representation'
                    }
                    memory_data = {
                        'user_id': user_id,
                        'memory_text': memory_text,
                        'metadata': metadata,
                        'created_at': datetime.now().isoformat()
                    }
                    response = requests.post(
                        f'{SUPABASE_URL}/rest/v1/ai_memories',
                        json=memory_data,
                        headers=headers
                    )
                    if response.status_code in [200, 201]:
                        return json.dumps({'status': 'created', 'memory': response.json()[0] if isinstance(response.json(), list) else response.json(), 'storage': 'supabase'})
                except:
                    pass
        
        # Fallback to Mem0 API
        try:
            import requests
            response = requests.post(
                f'{MEM0_API_URL}/memories',
                json={
                    'user_id': user_id,
                    'memory': memory_text,
                    'metadata': metadata or {}
                }
            )
            
            if response.status_code in [200, 201]:
                return json.dumps({'status': 'created', 'memory': response.json(), 'storage': 'mem0'})
        except:
            pass
        
        return json.dumps({'error': 'Memory storage not available (Supabase ai_memories table or Mem0 API)'})
        
    except Exception as e:
        logger.error(f'Error creating memory: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def ai_get_memories(
    user_id: str,
    limit: int = 10
) -> str:
    """
    Retrieve memories for a user from Supabase (fallback to Mem0).
    
    Args:
        user_id: User identifier
        limit: Maximum number of memories to retrieve
    """
    try:
        # Try Supabase first
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                from supabase import create_client, Client
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                
                try:
                    response = supabase.table('ai_memories').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
                    if response.data:
                        return json.dumps({'memories': response.data, 'count': len(response.data), 'storage': 'supabase'})
                except:
                    pass
            except ImportError:
                # Fallback to REST API
                try:
                    import requests
                    headers = {
                        'apikey': SUPABASE_KEY,
                        'Authorization': f'Bearer {SUPABASE_KEY}'
                    }
                    response = requests.get(
                        f'{SUPABASE_URL}/rest/v1/ai_memories?user_id=eq.{user_id}&order=created_at.desc&limit={limit}',
                        headers=headers
                    )
                    if response.status_code == 200:
                        memories = response.json()
                        return json.dumps({'memories': memories, 'count': len(memories), 'storage': 'supabase'})
                except:
                    pass
        
        # Fallback to Mem0 API
        try:
            import requests
            response = requests.get(
                f'{MEM0_API_URL}/memories',
                params={'user_id': user_id, 'limit': limit}
            )
            
            if response.status_code == 200:
                return json.dumps({'memories': response.json(), 'storage': 'mem0'})
        except:
            pass
        
        return json.dumps({'error': 'Memory storage not available'})
        
    except Exception as e:
        logger.error(f'Error getting memories: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def ai_run_workflow(
    workflow_name: str,
    input_data: Dict,
    config: Optional[Dict] = None
) -> str:
    """
    Run a LangGraph workflow.
    
    Args:
        workflow_name: Name of the workflow to run
        input_data: Input data for the workflow
        config: Optional workflow configuration
    """
    try:
        import requests
        
        response = requests.post(
            f'{LANGGRAPH_API_URL}/workflows/{workflow_name}/run',
            json={
                'input': input_data,
                'config': config or {}
            }
        )
        
        if response.status_code == 200:
            return json.dumps({'status': 'completed', 'result': response.json()})
        return json.dumps({'error': f'LangGraph API error: {response.text}'})
        
    except Exception as e:
        logger.error(f'Error running workflow: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def ai_request_approval(
    action: str,
    description: str,
    context: Optional[Dict] = None
) -> str:
    """
    Request human approval for an action (Human-in-the-Loop).
    Stores approval request in Supabase if available.
    
    Args:
        action: Action to be approved
        description: Description of the action
        context: Additional context
    """
    try:
        import uuid
        approval_id = str(uuid.uuid4())
        approval_data = {
            'id': approval_id,
            'action': action,
            'description': description,
            'context': json.dumps(context) if context else None,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        # Try to store in Supabase
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                from supabase import create_client, Client
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                
                try:
                    # Try to insert into approval_requests table
                    response = supabase.table('approval_requests').insert({
                        'id': approval_id,
                        'action': action,
                        'description': description,
                        'context': context,
                        'status': 'pending'
                    }).execute()
                    if response.data:
                        return json.dumps({
                            'status': 'pending_approval',
                            'approval_id': approval_id,
                            'approval': response.data[0],
                            'message': 'Human approval required. Check approval queue in Supabase.'
                        })
                except:
                    pass
            except ImportError:
                # Fallback to REST API
                try:
                    import requests
                    headers = {
                        'apikey': SUPABASE_KEY,
                        'Authorization': f'Bearer {SUPABASE_KEY}',
                        'Content-Type': 'application/json',
                        'Prefer': 'return=representation'
                    }
                    response = requests.post(
                        f'{SUPABASE_URL}/rest/v1/approval_requests',
                        json={
                            'id': approval_id,
                            'action': action,
                            'description': description,
                            'context': context,
                            'status': 'pending'
                        },
                        headers=headers
                    )
                    if response.status_code in [200, 201]:
                        return json.dumps({
                            'status': 'pending_approval',
                            'approval_id': approval_id,
                            'approval': response.json()[0] if isinstance(response.json(), list) else response.json(),
                            'message': 'Human approval required. Check approval queue in Supabase.'
                        })
                except:
                    pass
        
        # Fallback if Supabase not available
        return json.dumps({
            'status': 'pending_approval',
            'approval_id': approval_id,
            'approval': approval_data,
            'message': 'Human approval required. Check approval queue. (Supabase storage not available)'
        })
        
    except Exception as e:
        logger.error(f'Error requesting approval: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def ai_get_approval_status(approval_id: str) -> str:
    """
    Get status of an approval request from Supabase.
    
    Args:
        approval_id: Approval request ID
    """
    try:
        # Try Supabase first
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                from supabase import create_client, Client
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                
                try:
                    response = supabase.table('approval_requests').select('*').eq('id', approval_id).single().execute()
                    if response.data:
                        return json.dumps({
                            'approval_id': approval_id,
                            'status': response.data.get('status', 'pending'),
                            'approval': response.data
                        })
                except:
                    pass
            except ImportError:
                # Fallback to REST API
                try:
                    import requests
                    headers = {
                        'apikey': SUPABASE_KEY,
                        'Authorization': f'Bearer {SUPABASE_KEY}'
                    }
                    response = requests.get(
                        f'{SUPABASE_URL}/rest/v1/approval_requests?id=eq.{approval_id}',
                        headers=headers
                    )
                    if response.status_code == 200:
                        approvals = response.json()
                        if approvals:
                            return json.dumps({
                                'approval_id': approval_id,
                                'status': approvals[0].get('status', 'pending'),
                                'approval': approvals[0]
                            })
                except:
                    pass
        
        # Fallback
        return json.dumps({
            'approval_id': approval_id,
            'status': 'unknown',
            'message': 'Approval status not found (Supabase table may not exist)'
        })
    except Exception as e:
        return json.dumps({'error': str(e)})


@mcp.tool()
async def ai_unified_gateway_call(
    service: str,
    action: str,
    parameters: Dict
) -> str:
    """
    Unified MCP Gateway - Route calls to any MCP server.
    
    Args:
        service: Service name (voice, content, social, business, etc.)
        action: Action to perform
        parameters: Action parameters
    """
    try:
        # This would route to the appropriate MCP server
        # For now, return a placeholder
        return json.dumps({
            'service': service,
            'action': action,
            'parameters': parameters,
            'status': 'routed',
            'message': 'Unified gateway routing pending full implementation'
        })
        
    except Exception as e:
        logger.error(f'Error in unified gateway: {e}')
        return json.dumps({'error': str(e)})


if __name__ == '__main__':
    mcp.run()


