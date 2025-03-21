from django.db import models

class Announcement(models.Model):
    """
    Model to store announcement data from the public data portal API
    """
    # Using the announcement name as the primary key
    biz_pbanc_nm = models.CharField(max_length=255, primary_key=True)
    detl_pg_url = models.URLField(max_length=512, blank=True)
    rcrt_prgs_yn = models.CharField(max_length=50, blank=True)
    aply_trgt = models.TextField(blank=True)
    pbanc_rcpt_end_dt = models.CharField(max_length=100, blank=True)
    
    # Additional fields for user interaction
    is_interested = models.BooleanField(default=False)
    is_applied = models.BooleanField(default=False)
    memo = models.TextField(blank=True)
    
    # Automatically track when the record was created and updated
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.biz_pbanc_nm


class AnnouncementNew(models.Model):
    """
    Updated model with announcement serial number as primary key
    and additional fields from the API
    """
    # Using the announcement serial number as the primary key
    pbanc_sn = models.CharField(max_length=100, primary_key=True)  # 공고일련번호
    
    # API data fields
    biz_pbanc_nm = models.CharField(max_length=255)  # 사업공고명
    pbanc_ctnt = models.TextField(blank=True)  # 공고내용
    supt_biz_clsfc = models.CharField(max_length=255, blank=True)  # 지원사업분류
    pbanc_rcpt_bgng_dt = models.DateField(null=True, blank=True)  # 공고접수시작일시
    pbanc_rcpt_end_dt = models.DateField(null=True, blank=True)  # 공고접수종료일시
    aply_trgt_ctnt = models.TextField(blank=True)  # 신청대상내용
    aply_excl_trgt_ctnt = models.TextField(blank=True)  # 신청제외대상내용
    supt_regin = models.CharField(max_length=255, blank=True)  # 지원지역
    pbanc_ntrp_nm = models.CharField(max_length=255, blank=True)  # 공고기업명
    sprv_inst = models.CharField(max_length=255, blank=True)  # 주관기관
    detl_pg_url = models.URLField(max_length=512, blank=True)  # 상세페이지 URL
    aply_trgt = models.TextField(blank=True)  # 신청대상
    biz_enyy = models.CharField(max_length=100, blank=True)  # 사업업력
    biz_trgt_age = models.CharField(max_length=100, blank=True)  # 사업대상연령
    rcrt_prgs_yn = models.CharField(max_length=50, blank=True)  # 모집진행여부
    intg_pbanc_biz_nm = models.CharField(max_length=255, blank=True)  # 통합공고사업명
    
    # Additional fields for user interaction
    is_interested = models.BooleanField(default=False)  # 관심 여부
    is_applied = models.BooleanField(default=False)  # 지원 여부
    memo = models.TextField(blank=True)  # 메모
    
    # Automatically track when the record was created and updated
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.biz_pbanc_nm 