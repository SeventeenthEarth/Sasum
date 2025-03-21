from django.contrib import admin
from .models import Announcement, AnnouncementNew

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('biz_pbanc_nm', 'is_interested', 'is_applied', 'created_at')
    list_filter = ('is_interested', 'is_applied')
    search_fields = ('biz_pbanc_nm', 'aply_trgt')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Announcement Information', {
            'fields': ('biz_pbanc_nm', 'detl_pg_url', 'aply_trgt', 'pbanc_rcpt_end_dt')
        }),
        ('User Status', {
            'fields': ('is_interested', 'is_applied', 'memo')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(AnnouncementNew)
class AnnouncementNewAdmin(admin.ModelAdmin):
    list_display = ('biz_pbanc_nm', 'pbanc_rcpt_bgng_dt', 'pbanc_rcpt_end_dt', 'is_interested', 'is_applied', 'created_at')
    list_filter = ('is_interested', 'is_applied', 'sprv_inst')
    search_fields = ('biz_pbanc_nm', 'aply_trgt', 'pbanc_ctnt')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('pbanc_sn', 'biz_pbanc_nm', 'detl_pg_url', 'intg_pbanc_biz_nm')
        }),
        ('Application Dates', {
            'fields': ('pbanc_rcpt_bgng_dt', 'pbanc_rcpt_end_dt')
        }),
        ('Supporting Organization', {
            'fields': ('pbanc_ntrp_nm', 'sprv_inst', 'supt_regin', 'supt_biz_clsfc')
        }),
        ('Target Information', {
            'fields': ('aply_trgt', 'aply_trgt_ctnt', 'aply_excl_trgt_ctnt', 'biz_enyy', 'biz_trgt_age')
        }),
        ('Content', {
            'fields': ('pbanc_ctnt',)
        }),
        ('User Status', {
            'fields': ('is_interested', 'is_applied', 'memo')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    ) 