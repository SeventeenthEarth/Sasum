import os
import logging
from typing import List, Dict, Any, Optional
import json

# AI model libraries
import openai
from anthropic import Anthropic
import google.generativeai as genai

# Models
from announcement.models import Announcement, AnnouncementNew

logger = logging.getLogger(__name__)

# Initialize AI clients
openai_client = None
claude_client = None
gemini_client = None

# Initialize OpenAI client if API key exists
if os.environ.get('OPENAI_API_KEY'):
    try:
        openai_client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")

# Initialize Claude client if API key exists
if os.environ.get('CLAUDE_API_KEY'):
    try:
        claude_client = Anthropic(api_key=os.environ.get('CLAUDE_API_KEY'))
    except Exception as e:
        logger.error(f"Failed to initialize Claude client: {str(e)}")

# Initialize Gemini client if API key exists
if os.environ.get('GEMINI_API_KEY'):
    try:
        genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
        gemini_client = genai
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {str(e)}")

def get_openai_filtered_indices(prompt: str, model_name: str = 'gpt-4o-mini') -> List[int]:
    """Use OpenAI to filter announcements and return matching indices"""
    # For API testing, just log and return all indices (this will be determined in call_ai_model_for_filtering)
    logger.info("OpenAI filtering bypassed for API testing")
    return []  # Return empty list to be handled in call_ai_model_for_filtering

def get_claude_filtered_indices(prompt: str, model_name: str = 'claude-3-haiku-20240307') -> List[int]:
    """Use Claude to filter announcements and return matching indices"""
    # For API testing, just log and return all indices (this will be determined in call_ai_model_for_filtering)
    logger.info("Claude filtering bypassed for API testing")
    return []  # Return empty list to be handled in call_ai_model_for_filtering

def get_gemini_filtered_indices(prompt: str, model_name: str = 'gemini-1.0-pro') -> List[int]:
    """Use Gemini to filter announcements and return matching indices"""
    # For API testing, just log and return all indices (this will be determined in call_ai_model_for_filtering)
    logger.info("Gemini filtering bypassed for API testing")
    return []  # Return empty list to be handled in call_ai_model_for_filtering

def call_ai_model_for_filtering(announcements: List[Any], user_condition: str, ai_platform: str = 'openai', model_name: str = None) -> List[Any]:
    """
    Filter announcements using AI based on user conditions
    
    Args:
        announcements: List of Announcement objects or dictionaries to filter
        user_condition: User's filtering criteria in natural language
        ai_platform: The AI platform to use ('openai', 'claude', or 'gemini')
        model_name: The specific model to use (if None, a default will be used)
        
    Returns:
        List of filtered announcements that match the user condition
    """
    if not announcements:
        logger.warning("No announcements provided to filter")
        return []
    
    logger.info(f"API 테스트 모드: {len(announcements)}개의 모든 공지사항을 필터링 없이 반환합니다")
    
    # For API testing, populate indices with all announcement indices
    all_indices = list(range(len(announcements)))
    logger.info(f"All indices: {all_indices}")
    
    # Return all announcements without actual AI filtering
    return announcements
    
    '''
    # The code below is kept but not executed for future reference
    
    # Prepare the announcements data for the AI model
    simplified_announcements = []
    for ann in announcements:
        # Handle both model instances and dictionaries
        if hasattr(ann, '__dict__'):
            # It's a model instance
            simplified = {
                'name': getattr(ann, 'biz_pbanc_nm', ''),
                'target': getattr(ann, 'aply_trgt', ''),
                'status': getattr(ann, 'rcrt_prgs_yn', ''),
                'end_date': getattr(ann, 'pbanc_rcpt_end_dt', ''),
                'url': getattr(ann, 'detl_pg_url', '')
            }
        else:
            # It's a dictionary
            simplified = {
                'name': ann.get('biz_pbanc_nm', ''),
                'target': ann.get('aply_trgt', ''),
                'status': ann.get('rcrt_prgs_yn', ''),
                'end_date': ann.get('pbanc_rcpt_end_dt', ''),
                'url': ann.get('detl_pg_url', '')
            }
        simplified_announcements.append(simplified)
    
    # Create prompt for the AI model
    prompt = f"""
    You are an expert grant advisor helping filter startup grant announcements.
    Below are startup grant announcements, and a user's condition for what they're looking for.
    
    User Condition: {user_condition}
    
    Announcements:
    {json.dumps(simplified_announcements, ensure_ascii=False, indent=2)}
    
    Please analyze each announcement and return ONLY the indices (starting from 0) of announcements that match the user's condition. 
    Return your response as a JSON array of integers, and nothing else.
    
    Your output should be valid JSON in the following format:
    {{"indices": [0, 2, 5]}}
    """

    try:
        # Set default models if none provided
        if ai_platform == 'openai':
            if not model_name:
                model_name = 'gpt-4o-mini'
            indices = get_openai_filtered_indices(prompt, model_name)
        elif ai_platform == 'claude':
            if not model_name:
                model_name = 'claude-3-haiku-20240307'
            indices = get_claude_filtered_indices(prompt, model_name)
        elif ai_platform == 'gemini':
            if not model_name:
                model_name = 'gemini-1.0-pro'
            indices = get_gemini_filtered_indices(prompt, model_name)
        else:
            raise ValueError(f"Unsupported AI platform: {ai_platform}")
            
        # Filter the announcements based on the indices
        filtered_announcements = []
        for idx in indices:
            if 0 <= idx < len(announcements):
                filtered_announcements.append(announcements[idx])
        
        return filtered_announcements
        
    except ValueError as e:
        # This will catch API key configuration errors
        logger.error(str(e))
        raise
    except Exception as e:
        logger.error(f"Error calling AI model: {str(e)}")
        # Return all announcements if AI filtering fails during general error
        return announcements 
    ''' 

def _create_announcement_text(ann):
    """
    Create a text representation of an announcement for AI processing
    """
    if isinstance(ann, Announcement) or isinstance(ann, AnnouncementNew):
        # It's a model instance
        return {
            'title': getattr(ann, 'biz_pbanc_nm', ''),
            'content': getattr(ann, 'pbanc_ctnt', '') or getattr(ann, 'aply_trgt', ''),
            'url': getattr(ann, 'detl_pg_url', ''),
            'target': getattr(ann, 'aply_trgt', ''),
            'start_date': getattr(ann, 'pbanc_rcpt_bgng_dt', ''),
            'end_date': getattr(ann, 'pbanc_rcpt_end_dt', ''),
            'region': getattr(ann, 'supt_regin', ''),
            'organization': getattr(ann, 'pbanc_ntrp_nm', ''),
        }
    else:
        # It's a dictionary
        return {
            'title': ann.get('biz_pbanc_nm', ''),
            'content': ann.get('pbanc_ctnt', '') or ann.get('aply_trgt', ''),
            'url': ann.get('detl_pg_url', ''),
            'target': ann.get('aply_trgt', ''),
            'start_date': ann.get('pbanc_rcpt_bgng_dt', ''),
            'end_date': ann.get('pbanc_rcpt_end_dt', ''),
            'region': ann.get('supt_regin', ''),
            'organization': ann.get('pbanc_ntrp_nm', ''),
        } 