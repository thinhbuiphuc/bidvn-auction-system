from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class User(AbstractUser):
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    role = models.CharField(max_length=20, default="Buyer")

    def __str__(self):
        return self.username

class Category(models.Model):
    name = models.CharField(max_length=64)

    class Meta:
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"

    def __str__(self):
        return self.name

class Auction(models.Model):
    DURATION_CHOICES = [
        (1, '1 Ngày'),
        (3, '3 Ngày'),
        (7, '7 Ngày'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Closed', 'Closed'),
        ('Completed', 'Completed'),
    ]
    title = models.CharField(max_length=200)
    desc = models.TextField()
    start_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    reserve_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    buy_now_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    listing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    duration = models.IntegerField(choices=DURATION_CHOICES, default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="listings", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)
    winner_user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="won_auctions")
    is_refused = models.BooleanField(default=False)
    refusal_reason = models.TextField(blank=True, null=True)
    contact_info = models.CharField(max_length=255, blank=False, default="Chưa cập nhật")

    class Meta:
        verbose_name = "Phiên đấu giá"
        verbose_name_plural = "Phiên đấu giá"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.pk:
            self.current_price = self.start_price
        super().save(*args, **kwargs)

    def calculate_fixed_costs(self):
        phi_danhmuc = 200
        phi_thoirian = 100

        if self.category:
            duration_val = int(self.duration or 1)
            
            active_rule = FeeRule.objects.filter(
                category=self.category,
                auction_duration=duration_val,
                is_active=True
            ).first()

            if active_rule:
                phi_danhmuc = float(active_rule.listing_fee)
                phi_thoirian = 0 

        phu_thu = 0
        if hasattr(self, 'reserve_price') and self.reserve_price and self.reserve_price > 0:
            phu_thu += 200
        if hasattr(self, 'buy_now_price') and self.buy_now_price and self.buy_now_price > 0:
            phu_thu += 200

        return phi_danhmuc + phi_thoirian + phu_thu

    def calculate_success_fee(self):
        phi_thanh_cong = 0
        if self.current_price:
            phi_thanh_cong = float(self.current_price) * 0.01
            if phi_thanh_cong < 100:
                phi_thanh_cong = 100
            elif phi_thanh_cong > 10000:
                phi_thanh_cong = 10000
        return int(phi_thanh_cong)

    def calculate_platform_fee(self):
        return int(self.calculate_fixed_costs() + self.calculate_success_fee())

    @property
    def highest_bid(self):
        return self.bids.order_by("-amount").first()

    @property
    def winner(self):
        highest = self.highest_bid
        if highest:
            return highest.bidder
        return None

class Bid(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bid_date = models.DateTimeField(auto_now_add=True)
    bidder = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bids")
    item = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="bids")

    class Meta:
        verbose_name = "Lượt đặt giá"
        verbose_name_plural = "Lượt đặt giá"

    def __str__(self):
        return f"{self.bidder.username} đặt {self.amount} cho {self.item.title}"

class Comment(models.Model):
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    listing = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="comments")

    class Meta:
        verbose_name = "Bình luận"
        verbose_name_plural = "Bình luận"

    def __str__(self):
        return f"Bình luận của {self.user.username} tại {self.listing.title}"

class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlist")
    item = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="watched_by")

    class Meta:
        verbose_name = "Mục theo dõi"
        verbose_name_plural = "Mục theo dõi"

    def __str__(self):
        return f"{self.user.username} quan tâm {self.item.title}"
    
class Review(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_made")
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_received")
    rating = models.IntegerField(choices=[(i, f"{i} Sao") for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Đánh giá"
        verbose_name_plural = "Đánh giá"

    def __str__(self):
        return f"{self.reviewer.username} đánh giá {self.reviewee.username}: {self.rating} Sao"
    
class FeeRule(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="fee_rules")
    auction_duration = models.IntegerField(default=1)
    listing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    success_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)  # 1%
    min_success_fee = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    max_success_fee = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)
    fee_rules_status = models.CharField(max_length=20, default="Active")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Luật phí"
        verbose_name_plural = "Luật phí"

    def __str__(self):
        return f"Luật phí cho {self.category.name} - {self.auction_duration} ngày"

class Order(models.Model):
    item_id = models.IntegerField(blank=True, null=True)
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="orders")
    order_date = models.DateTimeField(auto_now_add=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2)  # Giá chốt phiên cuối cùng
    shipping_address = models.TextField(default="Chưa cập nhật")
    order_status = models.CharField(max_length=50, default="Pending")

    fee_rule = models.ForeignKey(FeeRule, on_delete=models.SET_NULL, null=True, blank=True)
    total_platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Đơn hàng"
        verbose_name_plural = "Đơn hàng"

    def __str__(self):
        return f"Hóa đơn #{self.id} cho phiên {self.auction.title}"