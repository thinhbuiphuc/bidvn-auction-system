from django.contrib import admin
from django.contrib.admin.exceptions import NotRegistered
from django.contrib.auth.models import Group
from .models import User, Auction, Bid, Comment, Category, FeeRule, Order

try:
    admin.site.unregister(Group)
except NotRegistered:
    pass

admin.site.site_header = "BidVN — Quản Trị"
admin.site.site_title = "BidVN Admin"
admin.site.index_title = "Bảng điều khiển"

@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'current_price', 'status', 'contact_info', 'created_at')
    list_editable = ('contact_info',)
    actions = ['delete_selected']

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'balance', 'is_staff')
    actions = ['delete_selected']

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('bidder', 'item', 'amount', 'bid_date')
    actions = ['delete_selected']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'listing', 'content', 'timestamp')
    actions = ['delete_selected']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    actions = ['delete_selected']

@admin.register(FeeRule)
class FeeRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'auction_duration', 'listing_fee', 'success_fee_percent', 'is_active')
    list_filter = ('is_active', 'category')
    actions = ['delete_selected']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'auction', 'final_price', 'fee_rule', 'total_platform_fee', 'order_status', 'order_date')
    list_filter = ('order_status', 'order_date')
    actions = ['delete_selected']