from django.forms import ModelForm
from django import forms
from .models import Auction, Bid, Comment 

class NewListingForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["contact_info"].initial = ""

    class Meta:
        model = Auction
        fields = ["title", "desc", "start_price", "reserve_price", "buy_now_price", "category", "image_url", "duration", "contact_info"]
        labels = {
            "title": "Tiêu đề",
            "desc": "Mô tả",
            "start_price": "Giá khởi điểm",
            "reserve_price": "Giá tối thiểu (Tùy chọn có phụ thu)",
            "buy_now_price": "Giá bán đứt (Tùy chọn có phụ thu)",
            "category": "Danh mục",
            "image_url": "Đường dẫn ảnh",
            "duration": "Thời gian đấu giá",
            "contact_info": "Thông tin liên hệ (SĐT/Zalo...)",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Nhập tiêu đề danh sách đấu giá của bạn",
                    "class": "form-control"
                }
            ),
            "desc": forms.Textarea(
                attrs={
                    "placeholder": "Nhập mô tả sản phẩm...",
                    "class": "form-control",
                    "rows": 5
                }
            ),
            "start_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nhập giá khởi điểm"
                }
            ),
            "reserve_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nhập giá tối thiểu bảo vệ sản phẩm (bỏ trống nếu không dùng)"
                }
            ),
            "buy_now_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nhập giá khách có thể mua đứt luôn (bỏ trống nếu không dùng)"
                }
            ),
            "image_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nhập đường dẫn hình ảnh",
                }
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "duration": forms.Select(attrs={"class": "form-control"}),
            "contact_info": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Số điện thoại/Zalo để người thắng liên hệ nhận hàng",
                }
            ),
        }

class NewBidForm(ModelForm):
    class Meta:
        model = Bid
        fields = ["amount"]
        labels = {
            "amount": "Số tiền đặt giá",
        }
        widgets = {
            "amount": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nhập số tiền bạn muốn đặt giá",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                    "oninput": "this.value = this.value.replace(/\\D/g, '').replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.')",
                }
            )
        }

class NewCommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        labels = {
            "content": "Bình luận",
        }
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "placeholder": "Nhập bình luận của bạn...",
                    "class": "form-control",
                    "rows": 4
                }
            )
        }