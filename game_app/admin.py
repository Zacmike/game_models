from django.contrib import admin
from .models import (
    Player, BoostType, Boost, PlayerBoostHistory,
    PlayerTask2, Level, Award, PlayerLevel, LevelAward, PlayerAward
)


#Админ для первого задания

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'login_count', 'total_points', 'first_login', 'last_login']
    list_filter = ['created_at', 'first_login']
    search_fields = ['username', 'email']
    readonly_fields = ['created_at', 'first_login', 'last_login']


@admin.register(BoostType)
class BoostTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'duration_minutes', 'multiplier']
    list_filter = ['name']


@admin.register(Boost)
class BoostAdmin(admin.ModelAdmin):
    list_display = ['player', 'boost_type', 'quantity', 'source', 'level_earned', 'is_active', 'created_at']
    list_filter = ['boost_type', 'source', 'is_active', 'created_at']
    search_fields = ['player__username']
    readonly_fields = ['created_at', 'used_at', 'expires_at']


@admin.register(PlayerBoostHistory)
class PlayerBoostHistoryAdmin(admin.ModelAdmin):
    list_display = ['player', 'boost_type', 'activated_at', 'expired_at', 'level_used']
    list_filter = ['boost_type', 'activated_at']
    search_fields = ['player__username']


#Админ для воторого задания

@admin.register(PlayerTask2)
class PlayerTask2Admin(admin.ModelAdmin):
    list_display = ['player_id']
    search_fields = ['player_id']


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['title', 'order']
    list_filter = ['order']
    ordering = ['order']


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = ['title']
    search_fields = ['title']


@admin.register(PlayerLevel)
class PlayerLevelAdmin(admin.ModelAdmin):
    list_display = ['player', 'level', 'is_completed', 'completed', 'score']
    list_filter = ['is_completed', 'completed', 'level']
    search_fields = ['player__player_id', 'level__title']


@admin.register(LevelAward)
class LevelAwardAdmin(admin.ModelAdmin):
    list_display = ['level', 'award']
    list_filter = ['level', 'award']


@admin.register(PlayerAward)
class PlayerAwardAdmin(admin.ModelAdmin):
    list_display = ['player', 'award', 'level', 'received']
    list_filter = ['award', 'level', 'received']
    search_fields = ['player__player_id', 'award__title', 'level__title']
    readonly_fields = ['received']