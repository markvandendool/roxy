#!/usr/bin/env python3
"""
ROXY Business Automation MCP Server
Phase 7: Business Automation - Supabase CRM, Plane, Chatwoot
Uses Supabase (same as mindsong-juke-hub CRM)
"""
import asyncio
import json
import logging
import os
from typing import Optional, Dict, List
from datetime import datetime
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP('roxy-business')

# Configuration - Supabase (same as mindsong-juke-hub)
SUPABASE_URL = os.getenv('SUPABASE_URL', os.getenv('VITE_SUPABASE_URL', 'https://rlbltiuswhlzjvszhvsc.supabase.co'))
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY', os.getenv('VITE_SUPABASE_ANON_KEY', ''))
PLANE_API_URL = os.getenv('PLANE_API_URL', 'http://localhost:8000/api/v1')
CHATWOOT_API_URL = os.getenv('CHATWOOT_API_URL', 'http://localhost:3000/api/v1')
PLANE_API_KEY = os.getenv('PLANE_API_KEY', '')
CHATWOOT_ACCESS_TOKEN = os.getenv('CHATWOOT_ACCESS_TOKEN', '')


@mcp.tool()
async def crm_create_contact(
    first_name: str,
    last_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    stage: str = 'lead'
) -> str:
    """
    Create a contact in Supabase CRM (same as mindsong-juke-hub).
    
    Args:
        first_name: Contact first name
        last_name: Contact last name
        email: Contact email
        phone: Contact phone number
        company: Company name
        stage: Contact stage (subscriber, lead, marketing_qualified_lead, sales_qualified_lead, opportunity, customer)
    """
    try:
        from supabase import create_client, Client
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return json.dumps({'error': 'Supabase credentials not configured'})
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        response = supabase.table('crm_contacts').insert({
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'company': company,
            'stage': stage
        }).execute()
        
        if response.data:
            return json.dumps({'status': 'created', 'contact': response.data[0]})
        return json.dumps({'error': 'Failed to create contact'})
        
    except ImportError:
        # Fallback to REST API if supabase-py not installed
        try:
            import requests
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            response = requests.post(
                f'{SUPABASE_URL}/rest/v1/crm_contacts',
                json={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'company': company,
                    'stage': stage
                },
                headers=headers
            )
            if response.status_code in [200, 201]:
                return json.dumps({'status': 'created', 'contact': response.json()[0] if isinstance(response.json(), list) else response.json()})
            return json.dumps({'error': f'Supabase API error: {response.text}'})
        except Exception as e:
            return json.dumps({'error': f'Error creating contact: {e}'})
    except Exception as e:
        logger.error(f'Error creating contact: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def plane_create_issue(
    project_id: str,
    name: str,
    description: Optional[str] = None,
    priority: str = 'medium',
    assignee_id: Optional[str] = None
) -> str:
    """
    Create an issue in Plane project management.
    
    Args:
        project_id: Plane project ID
        name: Issue name/title
        description: Issue description
        priority: Priority level (low, medium, high, urgent)
        assignee_id: Optional assignee user ID
    """
    try:
        import requests
        
        headers = {'Authorization': f'Bearer {PLANE_API_KEY}'} if PLANE_API_KEY else {}
        response = requests.post(
            f'{PLANE_API_URL}/projects/{project_id}/issues',
            json={
                'name': name,
                'description': description,
                'priority': priority,
                'assignee_id': assignee_id
            },
            headers=headers
        )
        
        if response.status_code in [200, 201]:
            return json.dumps({'status': 'created', 'issue': response.json()})
        return json.dumps({'error': f'Plane API error: {response.text}'})
        
    except Exception as e:
        logger.error(f'Error creating Plane issue: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def chatwoot_send_message(
    account_id: str,
    conversation_id: str,
    message: str,
    message_type: str = 'outgoing'
) -> str:
    """
    Send a message via Chatwoot customer messaging.
    
    Args:
        account_id: Chatwoot account ID
        conversation_id: Conversation ID
        message: Message text
        message_type: Message type (incoming, outgoing)
    """
    try:
        import requests
        
        headers = {
            'api_access_token': CHATWOOT_ACCESS_TOKEN,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f'{CHATWOOT_API_URL}/accounts/{account_id}/conversations/{conversation_id}/messages',
            json={
                'content': message,
                'message_type': message_type
            },
            headers=headers
        )
        
        if response.status_code in [200, 201]:
            return json.dumps({'status': 'sent', 'message': response.json()})
        return json.dumps({'error': f'Chatwoot API error: {response.text}'})
        
    except Exception as e:
        logger.error(f'Error sending Chatwoot message: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def business_get_contacts(limit: int = 50, stage: Optional[str] = None) -> str:
    """
    Get contacts from Supabase CRM (same as mindsong-juke-hub).
    
    Args:
        limit: Maximum number of contacts to return
        stage: Optional filter by stage (subscriber, lead, marketing_qualified_lead, sales_qualified_lead, opportunity, customer)
    """
    try:
        from supabase import create_client, Client
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return json.dumps({'error': 'Supabase credentials not configured'})
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        query = supabase.table('crm_contacts').select('*')
        if stage:
            query = query.eq('stage', stage)
        query = query.order('created_at', desc=True).limit(limit)
        response = query.execute()
        
        if response.data:
            return json.dumps({'contacts': response.data, 'count': len(response.data)})
        return json.dumps({'error': 'Failed to fetch contacts'})
        
    except ImportError:
        # Fallback to REST API
        try:
            import requests
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}'
            }
            url = f'{SUPABASE_URL}/rest/v1/crm_contacts?limit={limit}&order=created_at.desc'
            if stage:
                url += f'&stage=eq.{stage}'
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return json.dumps({'contacts': response.json(), 'count': len(response.json())})
            return json.dumps({'error': f'Supabase API error: {response.text}'})
        except Exception as e:
            return json.dumps({'error': str(e)})
    except Exception as e:
        return json.dumps({'error': str(e)})


@mcp.tool()
async def crm_get_deals(limit: int = 50, stage: Optional[str] = None) -> str:
    """
    Get deals from Supabase CRM.
    
    Args:
        limit: Maximum number of deals to return
        stage: Optional filter by deal stage
    """
    try:
        from supabase import create_client, Client
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return json.dumps({'error': 'Supabase credentials not configured'})
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        query = supabase.table('crm_deals').select('*')
        if stage:
            query = query.eq('stage', stage)
        query = query.order('created_at', desc=True).limit(limit)
        response = query.execute()
        
        if response.data:
            total_value = sum(deal.get('value', 0) or 0 for deal in response.data)
            return json.dumps({
                'deals': response.data,
                'count': len(response.data),
                'total_value': total_value
            })
        return json.dumps({'error': 'Failed to fetch deals'})
        
    except ImportError:
        try:
            import requests
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}'
            }
            url = f'{SUPABASE_URL}/rest/v1/crm_deals?limit={limit}&order=created_at.desc'
            if stage:
                url += f'&stage=eq.{stage}'
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                deals = response.json()
                total_value = sum(deal.get('value', 0) or 0 for deal in deals)
                return json.dumps({'deals': deals, 'count': len(deals), 'total_value': total_value})
            return json.dumps({'error': f'Supabase API error: {response.text}'})
        except Exception as e:
            return json.dumps({'error': str(e)})
    except Exception as e:
        return json.dumps({'error': str(e)})


@mcp.tool()
async def crm_create_deal(
    name: str,
    value: float,
    contact_id: Optional[str] = None,
    stage: str = 'prospecting',
    expected_close_date: Optional[str] = None
) -> str:
    """
    Create a deal in Supabase CRM.
    
    Args:
        name: Deal name
        value: Deal value
        contact_id: Optional associated contact ID
        stage: Deal stage (prospecting, qualification, proposal, negotiation, closed_won, closed_lost)
        expected_close_date: Optional expected close date (ISO format)
    """
    try:
        from supabase import create_client, Client
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return json.dumps({'error': 'Supabase credentials not configured'})
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        deal_data = {
            'name': name,
            'value': value,
            'stage': stage
        }
        if contact_id:
            deal_data['contact_id'] = contact_id
        if expected_close_date:
            deal_data['expected_close_date'] = expected_close_date
        
        response = supabase.table('crm_deals').insert(deal_data).execute()
        
        if response.data:
            return json.dumps({'status': 'created', 'deal': response.data[0]})
        return json.dumps({'error': 'Failed to create deal'})
        
    except ImportError:
        try:
            import requests
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            deal_data = {
                'name': name,
                'value': value,
                'stage': stage
            }
            if contact_id:
                deal_data['contact_id'] = contact_id
            if expected_close_date:
                deal_data['expected_close_date'] = expected_close_date
            
            response = requests.post(
                f'{SUPABASE_URL}/rest/v1/crm_deals',
                json=deal_data,
                headers=headers
            )
            if response.status_code in [200, 201]:
                return json.dumps({'status': 'created', 'deal': response.json()[0] if isinstance(response.json(), list) else response.json()})
            return json.dumps({'error': f'Supabase API error: {response.text}'})
        except Exception as e:
            return json.dumps({'error': str(e)})
    except Exception as e:
        logger.error(f'Error creating deal: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def crm_get_workflows(limit: int = 50, status: Optional[str] = None) -> str:
    """
    Get CRM automation workflows from Supabase.
    
    Args:
        limit: Maximum number of workflows to return
        status: Optional filter by status (active, inactive, paused)
    """
    try:
        from supabase import create_client, Client
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return json.dumps({'error': 'Supabase credentials not configured'})
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        query = supabase.table('automation_workflows_crm').select('*')
        if status:
            query = query.eq('status', status)
        query = query.order('created_at', desc=True).limit(limit)
        response = query.execute()
        
        if response.data:
            return json.dumps({
                'workflows': response.data,
                'count': len(response.data)
            })
        return json.dumps({'error': 'Failed to fetch workflows'})
        
    except ImportError:
        try:
            import requests
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}'
            }
            url = f'{SUPABASE_URL}/rest/v1/automation_workflows_crm?limit={limit}&order=created_at.desc'
            if status:
                url += f'&status=eq.{status}'
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return json.dumps({'workflows': response.json(), 'count': len(response.json())})
            return json.dumps({'error': f'Supabase API error: {response.text}'})
        except Exception as e:
            return json.dumps({'error': str(e)})
    except Exception as e:
        return json.dumps({'error': str(e)})


@mcp.tool()
async def crm_get_analytics() -> str:
    """Get CRM analytics (contacts count, deals value, active workflows)."""
    try:
        from supabase import create_client, Client
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return json.dumps({'error': 'Supabase credentials not configured'})
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Get contacts count
        contacts_res = supabase.table('crm_contacts').select('id', count='exact', head=True).execute()
        contacts_count = contacts_res.count if hasattr(contacts_res, 'count') else 0
        
        # Get deals with value
        deals_res = supabase.table('crm_deals').select('value, stage').execute()
        deals = deals_res.data if deals_res.data else []
        total_deal_value = sum(deal.get('value', 0) or 0 for deal in deals)
        
        # Get active workflows count
        workflows_res = supabase.table('automation_workflows_crm').select('id', count='exact', head=True).eq('status', 'active').execute()
        active_workflows = workflows_res.count if hasattr(workflows_res, 'count') else 0
        
        return json.dumps({
            'contacts_count': contacts_count,
            'deals_count': len(deals),
            'total_deal_value': total_deal_value,
            'active_workflows': active_workflows
        })
        
    except ImportError:
        try:
            import requests
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}'
            }
            
            # Get contacts count
            contacts_res = requests.get(
                f'{SUPABASE_URL}/rest/v1/crm_contacts?select=id&limit=1',
                headers={**headers, 'Prefer': 'count=exact'}
            )
            contacts_count = int(contacts_res.headers.get('content-range', '0').split('/')[-1]) if contacts_res.status_code == 200 else 0
            
            # Get deals
            deals_res = requests.get(
                f'{SUPABASE_URL}/rest/v1/crm_deals?select=value,stage',
                headers=headers
            )
            deals = deals_res.json() if deals_res.status_code == 200 else []
            total_deal_value = sum(deal.get('value', 0) or 0 for deal in deals)
            
            # Get active workflows
            workflows_res = requests.get(
                f'{SUPABASE_URL}/rest/v1/automation_workflows_crm?select=id&status=eq.active&limit=1',
                headers={**headers, 'Prefer': 'count=exact'}
            )
            active_workflows = int(workflows_res.headers.get('content-range', '0').split('/')[-1]) if workflows_res.status_code == 200 else 0
            
            return json.dumps({
                'contacts_count': contacts_count,
                'deals_count': len(deals),
                'total_deal_value': total_deal_value,
                'active_workflows': active_workflows
            })
        except Exception as e:
            return json.dumps({'error': str(e)})
    except Exception as e:
        return json.dumps({'error': str(e)})


@mcp.tool()
async def business_get_issues(project_id: str, limit: int = 50) -> str:
    """Get issues from Plane project."""
    try:
        import requests
        headers = {'Authorization': f'Bearer {PLANE_API_KEY}'} if PLANE_API_KEY else {}
        response = requests.get(f'{PLANE_API_URL}/projects/{project_id}/issues?limit={limit}', headers=headers)
        if response.status_code == 200:
            return json.dumps({'issues': response.json()})
        return json.dumps({'error': f'Plane API error: {response.text}'})
    except Exception as e:
        return json.dumps({'error': str(e)})


if __name__ == '__main__':
    mcp.run()


