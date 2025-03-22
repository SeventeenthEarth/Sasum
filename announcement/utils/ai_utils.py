import os
import logging
from typing import List, Dict, Any, Optional
import json
import time

# AI model libraries
import openai
from anthropic import Anthropic
import google.generativeai as genai

# Models
from announcement.models import Announcement, AnnouncementNew

logger = logging.getLogger(__name__)

# Initialize AI clients
openai_client = None
gemini_client = None
openai_assistant_id = None

# Initialize OpenAI client if API key exists
if os.environ.get('OPENAI_API_KEY'):
    try:
        openai_client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        # Get assistant ID from environment variable
        openai_assistant_id = os.environ.get('OPENAI_ASSISTANT_ID')
        if not openai_assistant_id:
            logger.warning("OPENAI_ASSISTANT_ID not set in environment variables")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")

# Initialize Gemini client if API key exists
if os.environ.get('GEMINI_API_KEY'):
    try:
        genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
        gemini_client = genai
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {str(e)}")

def get_openai_filtered_indices(prompt: str, model_name: str = 'gpt-4o-mini') -> List[str]:
    """Use OpenAI to filter announcements and return matching serial numbers"""
    if not openai_client:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    
    if not openai_assistant_id:
        raise ValueError("OPENAI_ASSISTANT_ID가 설정되지 않았습니다.")
    
    try:
        # Create a thread
        thread = openai_client.beta.threads.create()
        
        # Add a message to the thread
        openai_client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )
        
        # Run the assistant on the thread
        run = openai_client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=openai_assistant_id
        )
        
        # Wait for the run to complete
        while run.status in ["queued", "in_progress"]:
            time.sleep(1)  # Wait for 1 second before checking again
            run = openai_client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        # Check if run completed successfully
        if run.status != "completed":
            logger.error(f"Assistant run failed with status: {run.status}")
            return []
        
        # Get the latest message from the assistant
        messages = openai_client.beta.threads.messages.list(
            thread_id=thread.id
        )
        
        # Get the content from the last assistant message
        content = None
        for message in messages.data:
            if message.role == "assistant":
                content = message.content[0].text.value
                break
        
        if not content:
            logger.error("No response from assistant")
            return []
        
        # Parse the JSON response
        try:
            # Extract JSON from the response if needed
            start_index = content.find('{')
            end_index = content.rfind('}') + 1
            
            if start_index != -1 and end_index != -1:
                json_content = content[start_index:end_index]
                result = json.loads(json_content)
            else:
                result = json.loads(content)
            
            if "serial_numbers" in result:
                return result["serial_numbers"]
            elif "indices" in result:  # Fallback for backward compatibility
                logger.warning("AI returned indices instead of serial numbers. Consider retraining.")
                return result["indices"]
            
            logger.error(f"Invalid response format from OpenAI Assistant: {content}")
            return []
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from OpenAI Assistant response: {content}")
            return []
    except Exception as e:
        logger.error(f"Error with OpenAI Assistant: {str(e)}")
        return []

def get_gemini_filtered_indices(prompt: str, model_name: str = 'gemini-1.5-flash-latest') -> List[str]:
    """Use Gemini to filter announcements and return matching serial numbers"""
    if not gemini_client:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
    
    try:
        model = gemini_client.GenerativeModel(model_name)
        response = model.generate_content(
            contents=[prompt],
            generation_config={
                "temperature": 0.2,
                "top_p": 0.8,
                "response_mime_type": "application/json",
            }
        )
        
        # Parse the response content
        content = response.text
        try:
            result = json.loads(content)
            
            if "serial_numbers" in result:
                return result["serial_numbers"]
            elif "indices" in result:  # Fallback for backward compatibility
                logger.warning("AI returned indices instead of serial numbers. Consider retraining.")
                return result["indices"]
            else:
                logger.error(f"Invalid response format from Gemini: {content}")
                return []
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from Gemini response: {content}")
            return []
    except Exception as e:
        logger.error(f"Error with Gemini: {str(e)}")
        return []

def call_ai_model_for_filtering(announcements: List[Any], user_condition: str, ai_choice: str = 'openai-gpt-4o-mini') -> tuple[List[Any], List[str]]:
    """
    Filter announcements using AI based on user conditions
    
    Args:
        announcements: List of Announcement objects or dictionaries to filter
        user_condition: User's filtering criteria in natural language
        ai_choice: The AI model to use ('openai-gpt-4o-mini' or 'gemini-1.5-flash')
        
    Returns:
        Tuple containing:
            - List of filtered announcements that match the user condition
            - List of serial numbers (pbanc_sn) of the matching announcements
    """
    if not announcements:
        logger.warning("No announcements provided to filter")
        return [], []
    
    # Parse AI platform and model from choice
    ai_parts = ai_choice.split('-', 1)
    ai_platform = ai_parts[0].lower()
    
    # Map AI choice to platform and model name
    ai_models = {
        'openai': {
            'default': 'gpt-4o-mini',
            'gpt-4o-mini': 'gpt-4o-mini'
        },
        'gemini': {
            'default': 'gemini-1.5-flash-lite',
            '2.0-flash-lite': 'gemini-2.0-flash-lite'
        }
    }
    
    # Get model name based on platform and model choice
    if ai_platform in ai_models:
        model_key = ai_parts[1] if len(ai_parts) > 1 else 'default'
        if model_key in ai_models[ai_platform]:
            model_name = ai_models[ai_platform][model_key]
        else:
            logger.warning(f"Unknown model '{model_key}' for platform '{ai_platform}'. Using default model.")
            model_name = ai_models[ai_platform]['default']
    else:
        supported_choices = ['openai-gpt-4o-mini', 'gemini-2.0-flash-lite']
        raise ValueError(f"지원되지 않는 AI 선택: {ai_choice}. 지원되는 옵션: {', '.join(supported_choices)}")
    
    # Check API key for selected platform
    if ai_platform == 'openai' and not openai_client:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    elif ai_platform == 'gemini' and not gemini_client:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
    
    # Set chunk size
    CHUNK_SIZE = 50
    
    # Split announcements into chunks of 50
    announcement_chunks = [announcements[i:i+CHUNK_SIZE] for i in range(0, len(announcements), CHUNK_SIZE)]
    logger.info(f"Split {len(announcements)} announcements into {len(announcement_chunks)} chunks of max {CHUNK_SIZE}")
    
    # Initialize combined results
    all_filtered_announcements = []
    all_filtered_serial_numbers = []
    
    # Process each chunk
    for chunk_idx, chunk in enumerate(announcement_chunks):
        logger.info(f"Processing chunk {chunk_idx+1}/{len(announcement_chunks)} with {len(chunk)} announcements")
        
        try:
            # Prepare the announcements data for the AI model
            simplified_announcements = []
            announcement_map = {}  # Map to store index -> announcement mapping
            
            for i, ann in enumerate(chunk):
                # Add the announcement information with serial number
                announcement_data = _create_announcement_text(ann)
                simplified_announcements.append(announcement_data)
                
                # Store the mapping of index to announcement
                announcement_map[i] = ann
            
            # Create prompt for the AI model
            prompt = f"""
            User Condition: {user_condition}
            
            Announcements:
            {json.dumps(simplified_announcements, ensure_ascii=False, indent=2)}
            """
            
            logger.info(f"Using AI: {ai_choice} (Platform: {ai_platform}, Model: {model_name})")
            
            # Call the appropriate platform-specific function
            if ai_platform == 'openai':
                indices = get_openai_filtered_indices(prompt, model_name)
            elif ai_platform == 'gemini':
                indices = get_gemini_filtered_indices(prompt, model_name)
            
            # Filter the announcements based on the serial numbers from AI
            chunk_filtered_announcements = []
            chunk_filtered_serial_numbers = []
            
            # Create a map of serial numbers to announcements for this chunk
            serial_to_announcement = {}
            for ann in chunk:
                if isinstance(ann, Announcement) or isinstance(ann, AnnouncementNew):
                    serial_number = getattr(ann, 'pbanc_sn', '')
                else:
                    serial_number = ann.get('pbanc_sn', '')
                    
                if serial_number:
                    serial_to_announcement[serial_number] = ann
            
            # Log available serial numbers for debugging
            logger.info(f"Available serial numbers in chunk {chunk_idx+1}: {list(serial_to_announcement.keys())[:5]}...")
            
            # Extract filtered announcements based on AI response
            for idx in indices:
                try:
                    # Now we're expecting the AI to return serial numbers directly
                    # If the response still has indices, convert to index-based access
                    if isinstance(idx, int) and 0 <= idx < len(chunk):
                        # Old format - AI still returning indices
                        ann = announcement_map[idx]
                        if isinstance(ann, Announcement) or isinstance(ann, AnnouncementNew):
                            serial_number = getattr(ann, 'pbanc_sn', '')
                        else:
                            serial_number = ann.get('pbanc_sn', '')
                        
                        if serial_number:
                            chunk_filtered_announcements.append(ann)
                            chunk_filtered_serial_numbers.append(serial_number)
                    else:
                        # New format - AI returning serial numbers directly
                        # Try different formats of the serial number
                        serial_number_str = str(idx)
                        if serial_number_str in serial_to_announcement:
                            chunk_filtered_announcements.append(serial_to_announcement[serial_number_str])
                            chunk_filtered_serial_numbers.append(serial_number_str)
                            continue
                        
                        # Try matching the integer value if serial numbers are stored as integers
                        if isinstance(idx, int):
                            # Check if any serial number converted to int matches
                            for serial_key in serial_to_announcement.keys():
                                try:
                                    if int(serial_key) == idx:
                                        chunk_filtered_announcements.append(serial_to_announcement[serial_key])
                                        chunk_filtered_serial_numbers.append(serial_key)
                                        logger.info(f"Matched integer serial number {idx} to string key {serial_key}")
                                        break
                                except (ValueError, TypeError):
                                    continue
                except (IndexError, TypeError, KeyError) as e:
                    logger.error(f"Error processing AI response item: {idx}, error: {str(e)}")
            
            # Log the filtered serial numbers for this chunk
            logger.info(f"Chunk {chunk_idx+1} filtered announcement serial numbers: {chunk_filtered_serial_numbers}")
            
            # Add chunk results to combined results
            all_filtered_announcements.extend(chunk_filtered_announcements)
            all_filtered_serial_numbers.extend(chunk_filtered_serial_numbers)
            
        except ValueError as e:
            # Handle API key errors
            logger.error(f"API key error in chunk {chunk_idx+1}: {str(e)}")
            raise  # Re-raise to handle at the caller level
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_idx+1}: {str(e)}")
            # Continue with other chunks in case of an error
    
    # Check if we have any results
    if not all_filtered_announcements and len(announcement_chunks) > 0:
        logger.warning("No announcements were filtered by AI across all chunks")
    
    # Log the final combined results
    logger.info(f"Total filtered announcements: {len(all_filtered_announcements)} out of {len(announcements)}")
    
    return all_filtered_announcements, all_filtered_serial_numbers

def _create_announcement_text(ann):
    """
    Create a text representation of an announcement for AI processing
    """
    # Helper function to convert date objects to strings
    def format_date(date_obj):
        if date_obj is None:
            return ""
        if hasattr(date_obj, 'strftime'):
            return date_obj.strftime('%Y-%m-%d')
        return str(date_obj) if date_obj else ""
    
    if isinstance(ann, Announcement) or isinstance(ann, AnnouncementNew):
        # It's a model instance
        return {
            'pbanc_sn': getattr(ann, 'pbanc_sn', ''),
            'title': getattr(ann, 'biz_pbanc_nm', ''),
            'content': getattr(ann, 'pbanc_ctnt', '') or getattr(ann, 'aply_trgt', ''),
            'target': getattr(ann, 'aply_trgt', ''),
            'start_date': format_date(getattr(ann, 'pbanc_rcpt_bgng_dt', '')),
            'end_date': format_date(getattr(ann, 'pbanc_rcpt_end_dt', '')),
            'region': getattr(ann, 'supt_regin', ''),
            'organization': getattr(ann, 'pbanc_ntrp_nm', ''),
        }
    else:
        # It's a dictionary
        return {
            'pbanc_sn': ann.get('pbanc_sn', ''),
            'title': ann.get('biz_pbanc_nm', ''),
            'content': ann.get('pbanc_ctnt', '') or ann.get('aply_trgt', ''),
            'target': ann.get('aply_trgt', ''),
            'start_date': format_date(ann.get('pbanc_rcpt_bgng_dt', '')),
            'end_date': format_date(ann.get('pbanc_rcpt_end_dt', '')),
            'region': ann.get('supt_regin', ''),
            'organization': ann.get('pbanc_ntrp_nm', ''),
        } 