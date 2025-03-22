from django.urls import path
from . import views

app_name = 'announcement'

urlpatterns = [
    path('', views.StoredAnnouncementView.as_view(), name='index'),
    path('new-announcement/', views.NewAnnouncementView.as_view(), name='new-announcement'),
    path('stored-announcement/', views.StoredAnnouncementView.as_view(), name='stored-announcement'),
    path('update-announcement/', views.update_announcement, name='update-announcement'),
    path('delete-all-announcements/', views.delete_all_announcements, name='delete-all-announcements'),
    path('delete-selected-announcements/', views.delete_selected_announcements, name='delete-selected-announcements'),
] 