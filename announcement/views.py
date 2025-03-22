from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
import logging
from django.utils import timezone
from datetime import datetime
from django.db.models import Q

from .models import Announcement, AnnouncementNew
from .utils.api_client import PublicDataAPIClient
from .utils.ai_utils import call_ai_model_for_filtering

logger = logging.getLogger(__name__)

class NewAnnouncementView(View):
    """View for fetching and filtering new announcements"""
    template_name = 'announcement/new_announcement.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        """Display the form for fetching new announcements"""
        # Available AI integrated models for dropdown (limited to 3 specific models)
        ai_models = [
            ('openai-gpt-4o-mini', 'OpenAI - GPT-4o Mini'),
            ('gemini-2.0-flash-lite', 'Gemini - 2.0 Flash-Lite'),
        ]
        
        # Check for 'refresh' parameter (indicates browser refresh)
        is_refresh = request.GET.get('refresh', '') == 'true'
        
        # Always present a clean form on GET request
        context = {
            'ai_models': ai_models,
            'user_condition': '',
            'selected_ai_model': 'openai-gpt-4o-mini',
            'region': '',
            'startup_period': '',
            'target_age': '',
        }
        
        # Explicitly clear session data and results on refresh to prevent form resubmission
        if is_refresh:
            if 'form_submitted' in request.session:
                del request.session['form_submitted']
            if 'query_results' in request.session:
                del request.session['query_results']
                
            # Clear any carried-over context variables that might be persisted
            context['total_count'] = None
            context['new_count'] = None
            context['filtered_count'] = None
            context['filtered_announcements'] = None
            
            # Set a flag to ensure results are not displayed
            context['hide_results'] = True
        
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Process the form submission, fetch new announcements and apply AI filtering"""
        user_condition = request.POST.get('user_condition', '')
        selected_ai_model = request.POST.get('selected_ai_model', 'openai-gpt-4o-mini')
        
        # Get additional filter parameters
        region = request.POST.get('region', '')
        startup_period = request.POST.get('startup_period', '')
        target_age = request.POST.get('target_age', '')
        
        # Available AI integrated models for dropdown (limited to 3 specific models)
        ai_models = [
            ('openai-gpt-4o-mini', 'OpenAI - GPT-4o Mini'),
            ('gemini-2.0-flash-lite', 'Gemini - 2.0 Flash-Lite'),
        ]
        
        # Set is_processing flag to true initially
        context = {
            'ai_models': ai_models,
            'user_condition': user_condition,
            'selected_ai_model': selected_ai_model,
            'region': region,
            'startup_period': startup_period,
            'target_age': target_age,
            'is_processing': True,  # Flag to indicate processing is happening
        }
        
        try:
            # 1. Call the public data portal API
            api_client = PublicDataAPIClient()
            new_items = api_client.get_announcements(
                page=1, 
                per_page=50,
                region=region,
                startup_period=startup_period,
                target_age=target_age
            )
            
            if new_items is None:
                messages.error(request, "API에서 데이터를 가져오지 못했습니다. 나중에 다시 시도해 주세요.")
                return render(request, self.template_name, context)
            
            if not new_items:
                messages.info(request, "API에서 새 공고를 찾을 수 없습니다.")
                return render(request, self.template_name, context)
            
            # Count of total announcements from API
            total_count = len(new_items)
            
            # 2. Apply AI filtering on the API results before saving
            filtered_items = []
            filtered_serial_numbers = []
            
            if user_condition:
                try:
                    # Convert API items to a format suitable for AI filtering
                    api_items_for_ai = []
                    for item in new_items:
                        serial_number = item.get("pbanc_sn", "")
                        if serial_number and not AnnouncementNew.objects.filter(pk=serial_number).exists():
                            api_items_for_ai.append(item)
                    
                    # Apply AI filtering with the integrated model format
                    filtered_items, filtered_serial_numbers = call_ai_model_for_filtering(
                        api_items_for_ai, 
                        user_condition,
                        selected_ai_model
                    )
                except ValueError as e:
                    # This is caught when API key is missing
                    ai_platform = selected_ai_model.split('-')[0].upper()
                    api_key_error_msg = f"{ai_platform}_API_KEY가 설정되지 않았습니다. .env 파일에 API 키를 추가해 주세요."
                    messages.error(request, api_key_error_msg)
                    # No filtering if AI API key is missing
                    filtered_items = [item for item in new_items if item.get("pbanc_sn", "") and not AnnouncementNew.objects.filter(pk=item.get("pbanc_sn", "")).exists()]
                    filtered_serial_numbers = [item.get("pbanc_sn", "") for item in filtered_items]
            else:
                # If no filtering condition, use all new announcements that don't exist in DB
                filtered_items = [item for item in new_items if item.get("pbanc_sn", "") and not AnnouncementNew.objects.filter(pk=item.get("pbanc_sn", "")).exists()]
                filtered_serial_numbers = [item.get("pbanc_sn", "") for item in filtered_items]
            
            # 3. Save only the filtered announcements to DB
            saved_new_announcements = []
            with transaction.atomic():
                for item in filtered_items:
                    serial_number = item.get("pbanc_sn", "")
                    if not serial_number:
                        continue
                    
                    # Convert date strings to date objects
                    start_date = None
                    end_date = None
                    
                    start_date_str = item.get("pbanc_rcpt_bgng_dt", "") or ""
                    end_date_str = item.get("pbanc_rcpt_end_dt", "") or ""
                    
                    if start_date_str:
                        try:
                            # Check if the date is in YYYYMMDD format
                            if len(start_date_str) == 8 and start_date_str.isdigit():
                                # Convert YYYYMMDD to YYYY-MM-DD
                                start_date_str = f"{start_date_str[:4]}-{start_date_str[4:6]}-{start_date_str[6:8]}"
                            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            # If date conversion fails, leave as None
                            pass
                    
                    if end_date_str:
                        try:
                            # Check if the date is in YYYYMMDD format
                            if len(end_date_str) == 8 and end_date_str.isdigit():
                                # Convert YYYYMMDD to YYYY-MM-DD
                                end_date_str = f"{end_date_str[:4]}-{end_date_str[4:6]}-{end_date_str[6:8]}"
                            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            # If date conversion fails, leave as None
                            pass
                            
                    ann = AnnouncementNew(
                        pbanc_sn=serial_number,
                        biz_pbanc_nm=item.get("biz_pbanc_nm", "") or "",
                        pbanc_ctnt=item.get("pbanc_ctnt", "") or "",
                        supt_biz_clsfc=item.get("supt_biz_clsfc", "") or "",
                        pbanc_rcpt_bgng_dt=start_date,
                        pbanc_rcpt_end_dt=end_date,
                        aply_trgt_ctnt=item.get("aply_trgt_ctnt", "") or "",
                        aply_excl_trgt_ctnt=item.get("aply_excl_trgt_ctnt", "") or "",
                        supt_regin=item.get("supt_regin", "") or "",
                        pbanc_ntrp_nm=item.get("pbanc_ntrp_nm", "") or "",
                        sprv_inst=item.get("sprv_inst", "") or "",
                        detl_pg_url=item.get("detl_pg_url", "") or "",
                        aply_trgt=item.get("aply_trgt", "") or "",
                        biz_enyy=item.get("biz_enyy", "") or "",
                        biz_trgt_age=item.get("biz_trgt_age", "") or "",
                        intg_pbanc_biz_nm=item.get("intg_pbanc_biz_nm", "") or ""
                    )
                    ann.save()
                    saved_new_announcements.append(ann)
            
            # Count of new saved announcements
            new_count = len(saved_new_announcements)
            
            # Set non-resubmission flag in session
            request.session['form_submitted'] = True
            request.session['query_results'] = {
                'filtered_serial_numbers': filtered_serial_numbers,
                'total_count': total_count,
                'new_count': new_count,
                'filtered_count': len(saved_new_announcements),
            }
            
            # Update context with results
            context.update({
                'filtered_announcements': saved_new_announcements,
                'filtered_serial_numbers': filtered_serial_numbers,
                'total_count': total_count,
                'new_count': new_count,
                'filtered_count': len(saved_new_announcements),
                'is_processing': False,  # Processing is now complete
            })
            
            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.exception("Error in NewAnnouncementView: %s", str(e))
            messages.error(request, f"오류가 발생했습니다: {str(e)}")
            return render(request, self.template_name, context)


class StoredAnnouncementView(View):
    """View for displaying and filtering stored announcements"""
    template_name = 'announcement/stored_announcement.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        """Display stored announcements with filtering options"""
        # Query both old and new models
        old_queryset = Announcement.objects.all()
        new_queryset = AnnouncementNew.objects.all()
        
        # Filter by keyword
        keyword = request.GET.get('keyword', '')
        if keyword:
            old_queryset = old_queryset.filter(
                Q(biz_pbanc_nm__icontains=keyword) | 
                Q(aply_trgt__icontains=keyword)
            )
            new_queryset = new_queryset.filter(
                Q(biz_pbanc_nm__icontains=keyword) | 
                Q(pbanc_ctnt__icontains=keyword) |
                Q(aply_trgt__icontains=keyword) |
                Q(aply_trgt_ctnt__icontains=keyword) |
                Q(aply_excl_trgt_ctnt__icontains=keyword) |
                Q(supt_regin__icontains=keyword) |
                Q(intg_pbanc_biz_nm__icontains=keyword)
            )
        
        # Get both querysets first
        old_results = []
        for ann in old_queryset:
            # For old model, attempt to parse the date fields
            end_date = None
            if ann.pbanc_rcpt_end_dt:
                try:
                    # Check if the date is in YYYYMMDD format
                    end_date_str = ann.pbanc_rcpt_end_dt
                    if len(end_date_str) == 8 and end_date_str.isdigit():
                        # Convert YYYYMMDD to YYYY-MM-DD
                        end_date_str = f"{end_date_str[:4]}-{end_date_str[4:6]}-{end_date_str[6:8]}"
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    # If date conversion fails, leave as None
                    pass
            
            # Calculate days remaining
            days_remaining = "-"
            today = timezone.now().date()
            if end_date:
                if today == end_date:
                    days_remaining = "D-day"
                elif today < end_date:
                    days_remaining = f"D-{(end_date - today).days}"
                    
            old_results.append({
                'model_type': 'old',
                'pbanc_sn': "",  # Old model doesn't have this field
                'biz_pbanc_nm': ann.biz_pbanc_nm,
                'pbanc_ctnt': "",
                'supt_biz_clsfc': "",
                'pbanc_rcpt_bgng_dt': None,  # Old model doesn't have start date
                'pbanc_rcpt_end_dt': end_date,
                'days_remaining': days_remaining,
                'aply_trgt_ctnt': "",
                'aply_excl_trgt_ctnt': "",
                'supt_regin': "",
                'pbanc_ntrp_nm': "",
                'sprv_inst': "",
                'detl_pg_url': ann.detl_pg_url,
                'aply_trgt': ann.aply_trgt,
                'biz_enyy': "",
                'biz_trgt_age': "",
                'rcrt_prgs_yn': ann.rcrt_prgs_yn,
                'intg_pbanc_biz_nm': "",
                'is_interested': ann.is_interested,
                'is_applied': ann.is_applied,
                'memo': ann.memo,
                'created_at': ann.created_at,
                'updated_at': ann.updated_at,
                'pk': ann.pk,  # Store primary key for form submission
            })
        
        # Get the new model results
        new_results = []
        for ann in new_queryset:
            # Calculate days remaining
            days_remaining = "-"
            today = timezone.now().date()
            if ann.pbanc_rcpt_end_dt:
                if today == ann.pbanc_rcpt_end_dt:
                    days_remaining = "D-day"
                elif today < ann.pbanc_rcpt_end_dt:
                    days_remaining = f"D-{(ann.pbanc_rcpt_end_dt - today).days}"
                    
            new_results.append({
                'model_type': 'new',
                'pbanc_sn': ann.pbanc_sn,
                'biz_pbanc_nm': ann.biz_pbanc_nm,
                'pbanc_ctnt': ann.pbanc_ctnt,
                'supt_biz_clsfc': ann.supt_biz_clsfc,
                'pbanc_rcpt_bgng_dt': ann.pbanc_rcpt_bgng_dt,
                'pbanc_rcpt_end_dt': ann.pbanc_rcpt_end_dt,
                'days_remaining': days_remaining,
                'aply_trgt_ctnt': ann.aply_trgt_ctnt,
                'aply_excl_trgt_ctnt': ann.aply_excl_trgt_ctnt,
                'supt_regin': ann.supt_regin,
                'pbanc_ntrp_nm': ann.pbanc_ntrp_nm,
                'sprv_inst': ann.sprv_inst,
                'detl_pg_url': ann.detl_pg_url,
                'aply_trgt': ann.aply_trgt,
                'biz_enyy': ann.biz_enyy,
                'biz_trgt_age': ann.biz_trgt_age,
                'rcrt_prgs_yn': ann.rcrt_prgs_yn,
                'intg_pbanc_biz_nm': ann.intg_pbanc_biz_nm,
                'is_interested': ann.is_interested,
                'is_applied': ann.is_applied,
                'memo': ann.memo,
                'created_at': ann.created_at,
                'updated_at': ann.updated_at,
                'pk': ann.pk,  # Store primary key for form submission
            })
        
        # Combine results from both models
        all_results = old_results + new_results
        
        # Apply status filter
        status_filters = request.GET.getlist('status_filter')
        # If status_filters is not empty, apply filtering
        # If no filters are selected, all announcements will be shown
        if status_filters:
            filtered_results = []
            for ann in all_results:
                start_date = ann.get('pbanc_rcpt_bgng_dt', None)
                end_date = ann.get('pbanc_rcpt_end_dt', None)
                today = timezone.now().date()
                
                # Check if any of the selected filters match
                if ('before' in status_filters and start_date and today < start_date) or \
                   ('ongoing' in status_filters and start_date and end_date and start_date <= today and today <= end_date) or \
                   ('closed' in status_filters and end_date and today > end_date) or \
                   ('interested' in status_filters and ann['is_interested']) or \
                   ('applied' in status_filters and ann['is_applied']):
                    filtered_results.append(ann)
            
            all_results = filtered_results
        # When no status filters are selected, all_results remains unchanged
        # and all announcements will be displayed
        
        # Sort by order_by parameter
        order_by = request.GET.get('order_by', 'name_asc')
        if order_by == 'name_asc':
            all_results.sort(key=lambda x: x['biz_pbanc_nm'])
        elif order_by == 'name_desc':
            all_results.sort(key=lambda x: x['biz_pbanc_nm'], reverse=True)
        elif order_by == 'end_date_asc':
            # Sort by reception end date, handling None values (they go to the end)
            all_results.sort(key=lambda x: (x['pbanc_rcpt_end_dt'] is None, x['pbanc_rcpt_end_dt'] or timezone.now().date()))
        elif order_by == 'end_date_desc':
            # Sort by reception end date in reverse order, handling None values (they go to the end)
            all_results.sort(key=lambda x: (x['pbanc_rcpt_end_dt'] is None, x['pbanc_rcpt_end_dt'] or timezone.now().date()), reverse=True)
        elif order_by == 'start_date_asc':
            # Sort by reception start date, handling None values (they go to the end)
            all_results.sort(key=lambda x: (x['pbanc_rcpt_bgng_dt'] is None, x['pbanc_rcpt_bgng_dt'] or timezone.now().date()))
        elif order_by == 'start_date_desc':
            # Sort by reception start date in reverse order, handling None values (they go to the end)
            all_results.sort(key=lambda x: (x['pbanc_rcpt_bgng_dt'] is None, x['pbanc_rcpt_bgng_dt'] or timezone.now().date()), reverse=True)
        elif order_by == 'reg_date_asc':
            all_results.sort(key=lambda x: x['created_at'])
        elif order_by == 'reg_date_desc':
            all_results.sort(key=lambda x: x['created_at'], reverse=True)
        
        context = {
            'announcements': all_results,
            'keyword': keyword,
            'status_filter': status_filters,
            'order_by': order_by,
            'count': len(all_results)
        }
        
        return render(request, self.template_name, context)


def update_announcement(request: HttpRequest) -> HttpResponse:
    """Update the status of an announcement"""
    if request.method == 'POST':
        model_type = request.POST.get('model_type', '')
        serial_number = request.POST.get('pbanc_sn', '')
        name = request.POST.get('biz_pbanc_nm', '')
        is_interested = 'is_interested' in request.POST
        is_applied = 'is_applied' in request.POST
        memo = request.POST.get('memo', '')
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            with transaction.atomic():
                if model_type == 'old' and name:
                    # Update old model using biz_pbanc_nm as primary key
                    ann = Announcement.objects.get(pk=name)
                    ann.is_interested = is_interested
                    ann.is_applied = is_applied
                    ann.memo = memo
                    ann.save()
                    message = f"'{name}' 공고의 상태가 업데이트되었습니다"
                elif model_type == 'new' and serial_number:
                    # Update new model using pbanc_sn as primary key
                    ann = AnnouncementNew.objects.get(pk=serial_number)
                    ann.is_interested = is_interested
                    ann.is_applied = is_applied
                    ann.memo = memo
                    ann.save()
                    message = f"'{ann.biz_pbanc_nm}' 공고의 상태가 업데이트되었습니다"
                else:
                    message = "공고 정보가 올바르지 않습니다"
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': message})
                    messages.error(request, message)
                    return redirect(request.META.get('HTTP_REFERER', '/stored-announcement/'))
                
                if is_ajax:
                    return JsonResponse({'success': True, 'message': message})
                messages.success(request, message)
        except (Announcement.DoesNotExist, AnnouncementNew.DoesNotExist):
            message = f"해당 공고를 찾을 수 없습니다"
            if is_ajax:
                return JsonResponse({'success': False, 'message': message})
            messages.error(request, message)
        except Exception as e:
            logger.exception("Error updating announcement: %s", str(e))
            message = f"공고 업데이트 중 오류 발생: {str(e)}"
            if is_ajax:
                return JsonResponse({'success': False, 'message': message})
            messages.error(request, message)
        
    return redirect(request.META.get('HTTP_REFERER', '/stored-announcement/'))


def delete_all_announcements(request: HttpRequest) -> HttpResponse:
    """Delete all announcements from the database"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Count both models
                old_count = Announcement.objects.all().count()
                new_count = AnnouncementNew.objects.all().count()
                total_count = old_count + new_count
                
                # Delete both models
                Announcement.objects.all().delete()
                AnnouncementNew.objects.all().delete()
                
                messages.success(request, f"{total_count}개의 모든 공고가 삭제되었습니다")
        except Exception as e:
            logger.exception("Error deleting all announcements: %s", str(e))
            messages.error(request, f"공고 삭제 중 오류 발생: {str(e)}")
    
    return redirect('announcement:stored-announcement')