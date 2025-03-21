import os
import requests
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class PublicDataAPIClient:
    """
    Client for the Korean public data portal API for startup announcements
    """
    
    def __init__(self):
        self.api_key = os.environ.get('PUBLIC_DATA_API_KEY')
        self.base_url = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
        
        # Check if we're in debug mode
        self.debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
        
        # Get per_page from environment or use default of 30
        # In debug mode, force per_page to 1
        if self.debug_mode:
            logger.warning("Running in DEBUG mode: per_page set to 1, max 5 announcements")
            self.per_page = 1
            self.max_items = 5
        else:
            try:
                self.per_page = int(os.environ.get('PER_PAGE_FOR_API', 30))
                self.max_items = None  # No limit in normal mode
            except (ValueError, TypeError):
                logger.warning("Invalid PER_PAGE_FOR_API value, using default of 30")
                self.per_page = 30
                self.max_items = None
        
        if not self.api_key:
            logger.warning("PUBLIC_DATA_KEY not found in environment variables")
    
    def _build_params(self, page: int, per_page: int, region: str = None, 
                     startup_period: str = None, target_age: str = None) -> Dict[str, Any]:
        """
        Build request parameters for the API
        
        Args:
            page (int): Page number 
            per_page (int): Number of items per page
            region (str, optional): Region filter
            startup_period (str, optional): Startup period filter
            target_age (str, optional): Target age filter
            
        Returns:
            Dict[str, Any]: Request parameters
        """
        params = {
            "serviceKey": self.api_key,
            "page": page,
            "perPage": per_page,
            "returnType": "json"
        }
        
        # Add conditional parameter for active recruitments
        params["cond[rcrt_prgs_yn::EQ]"] = "Y"
        
        # Add filter parameters if provided
        if region:
            params["cond[supt_regin::LIKE]"] = region
        
        if startup_period:
            params["cond[biz_enyy::LIKE]"] = startup_period
        
        if target_age:
            params["cond[biz_trgt_age::LIKE]"] = target_age
            
        return params
    
    def _make_api_request(self, params: Dict[str, Any], page_num: int) -> Optional[requests.Response]:
        """
        Make API request with given parameters
        
        Args:
            params (Dict[str, Any]): Request parameters
            page_num (int): Page number for logging
            
        Returns:
            Optional[requests.Response]: Response object or None if request failed
        """
        try:
            # Log API call details
            logger.info(f"API 호출 URL: {self.base_url}")
            logger.info(f"API 호출 페이지: {page_num}")
            logger.info(f"API 호출 파라미터: {params}")
            
            # Make API request
            response = requests.get(self.base_url, params=params)
            logger.info(f"API 응답 상태 코드: {response.status_code}")
            
            # Check response status code
            if response.status_code != 200:
                logger.error(f"API 오류 응답: {response.status_code}")
                if response.status_code == 401:
                    logger.error("인증 오류: API 키를 확인하세요")
                elif response.status_code == 500:
                    logger.error("서버 오류: 잠시 후 다시 시도하세요")
                return None
            
            # Log raw response content
            raw_response = response.text
            logger.info(f"API 응답 내용 (일부): {raw_response[:500]}...")
            
            # Check if response is empty
            if not raw_response.strip():
                logger.error("API returned empty response")
                return None
                
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 오류: {str(e)}")
            return None
    
    def _parse_response_data(self, response: requests.Response, per_page: int) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Parse API response and extract items and pagination info
        
        Args:
            response (requests.Response): API response
            per_page (int): Number of items per page for pagination calculation
            
        Returns:
            Tuple[List[Dict[str, Any]], int, int]: (items, match_count, total_pages)
            Returns empty list and 0, 0 if parsing failed
        """
        try:
            # Parse JSON response
            data = response.json()
            logger.error(f"데이터 타입: {type(data)}")
            
            # Check for error in response
            if isinstance(data, dict) and 'error' in data:
                logger.error(f"API error: {data['error']}")
                return [], 0, 0
            
            # Extract items from response
            items = []
            
            if isinstance(data, list):
                # API directly returned a list of items
                logger.error("API가 리스트 형식으로 응답을 반환했습니다")
                items = data
                match_count = len(items)
                total_pages = 1  # Assume single page if direct list
                
            elif isinstance(data, dict):
                # Normal nested structure
                if "data" in data and isinstance(data["data"], dict) and "data" in data["data"]:
                    items = data["data"]["data"]
                elif "data" in data and isinstance(data["data"], list):
                    items = data["data"]
                
                # Get match count from the response if available
                match_count = int(data.get("matchCount", len(items)))
                logger.info(f"총 매칭 항목 수: {match_count}")
                
                if match_count == 0:
                    logger.error("일치하는 항목이 없습니다")
                    return [], 0, 0
                
                # If in debug mode, limit the match count and calculate fewer pages
                if self.debug_mode and self.max_items and match_count > self.max_items:
                    logger.info(f"DEBUG 모드: 전체 {match_count}개 중 최대 {self.max_items}개만 가져옵니다")
                    match_count = self.max_items
                
                total_pages = (match_count + per_page - 1) // per_page
                logger.info(f"총 페이지 수: {total_pages}")
            else:
                logger.error(f"예상치 못한 응답 형식: {type(data)}")
                return [], 0, 0
            
            logger.info(f"현재 페이지 아이템 수: {len(items)}")
            return items, match_count, total_pages
            
        except ValueError as e:
            logger.error(f"JSON 파싱 오류: {str(e)}")
            return [], 0, 0
    
    def _fetch_additional_pages(self, params: Dict[str, Any], start_page: int, 
                               total_pages: int, current_item_count: int) -> List[Dict[str, Any]]:
        """
        Fetch additional pages beyond the first one
        
        Args:
            params (Dict[str, Any]): Base request parameters
            start_page (int): Page to start from (usually initial_page + 1)
            total_pages (int): Total number of pages to fetch
            current_item_count (int): Number of items already fetched
            
        Returns:
            List[Dict[str, Any]]: Items from additional pages
        """
        additional_items = []
        
        for page_num in range(start_page, total_pages + 1):
            # In debug mode, check if we've reached the maximum items
            if self.debug_mode and self.max_items and current_item_count + len(additional_items) >= self.max_items:
                logger.warning(f"DEBUG 모드: 최대 항목 수 {self.max_items}에 도달했습니다. 추가 페이지를 가져오지 않습니다.")
                break
                
            # Update page parameter
            params["page"] = page_num
            
            # Log API call details
            logger.error(f"추가 API 호출 페이지: {page_num}")
            
            # Make API request
            response = self._make_api_request(params, page_num)
            
            if not response:
                break
            
            try:
                page_data = response.json()
                
                # Extract items from this page
                page_items = []
                if isinstance(page_data, list):
                    page_items = page_data
                elif isinstance(page_data, dict):
                    if "data" in page_data and isinstance(page_data["data"], dict) and "data" in page_data["data"]:
                        page_items = page_data["data"]["data"]
                    elif "data" in page_data and isinstance(page_data["data"], list):
                        page_items = page_data["data"]
                
                logger.error(f"페이지 {page_num} 아이템 수: {len(page_items)}")
                
                # In debug mode, add items until we reach the maximum
                if self.debug_mode and self.max_items:
                    remaining_slots = self.max_items - (current_item_count + len(additional_items))
                    if remaining_slots <= 0:
                        # Already have enough items
                        break
                    elif len(page_items) > remaining_slots:
                        # Need to truncate the items to fit the max
                        additional_items.extend(page_items[:remaining_slots])
                        break
                    else:
                        # Can add all items
                        additional_items.extend(page_items)
                else:
                    # Normal mode, add all items
                    additional_items.extend(page_items)
                
            except ValueError as e:
                logger.error(f"추가 페이지 JSON 파싱 오류: {str(e)}")
                break
                
        return additional_items
    
    def get_announcements(self, page: int = 1, per_page: int = None, region: str = None, 
                          startup_period: str = None, target_age: str = None) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch announcements from the public data portal API
        
        Args:
            page (int): Page number for pagination (0-based)
            per_page (int, optional): Number of items per page, defaults to value from env
            region (str, optional): Region filter
            startup_period (str, optional): Startup period filter (e.g., "7년미만", "예비창업자")
            target_age (str, optional): Target age filter (e.g., "만 20세 미만")
            
        Returns:
            List[Dict[str, Any]] or None: List of announcement data as dictionaries, or None if request failed
        """
        if not self.api_key:
            logger.error("No supplier key available for public data portal")
            return None
        
        # Use provided per_page or default from environment
        per_page = per_page or self.per_page
        
        # Build request parameters
        params = self._build_params(page, per_page, region, startup_period, target_age)
        
        # Make the initial API request 
        response = self._make_api_request(params, page)
        if not response:
            return None
        
        # Parse the response and get initial items
        items, match_count, total_pages = self._parse_response_data(response, per_page)
        if not items:
            return []
        
        # In debug mode, truncate first page items if needed
        if self.debug_mode and self.max_items and len(items) > self.max_items:
            all_items = items[:self.max_items]
            logger.warning(f"DEBUG 모드: 첫 페이지에서 {self.max_items}개 항목으로 제한했습니다")
        else:
            all_items = items.copy()
        
        # Always fetch all pages if there are more than one (respecting max_items in debug mode)
        if total_pages > 1 and (not self.debug_mode or len(all_items) < self.max_items):
            additional_items = self._fetch_additional_pages(params, page + 1, total_pages, len(all_items))
            all_items.extend(additional_items)
        
        logger.error(f"총 {len(all_items)}개의 항목을 가져왔습니다")
        return all_items 