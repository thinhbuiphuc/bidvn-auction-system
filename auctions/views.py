from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from datetime import timedelta
from decimal import Decimal
from .models import User, Auction, Bid, Category, Comment, Watchlist, Review, Order, FeeRule
from .forms import NewCommentForm, NewListingForm, NewBidForm
from django.shortcuts import redirect
import datetime



def create_order_if_winner(auction, winner):
    if not winner:
        return
    fee_rule = None
    if auction.category:
        fee_rule = FeeRule.objects.filter(
            category=auction.category,
            auction_duration=auction.duration,
            is_active=True
        ).first()
    Order.objects.create(
        auction=auction,
        item_id=auction.id,
        final_price=auction.current_price,
        total_platform_fee=auction.listing_fee,
        fee_rule=fee_rule,
    )


def check_and_close_expired_auctions():
    now = timezone.now()
    expired_auctions = Auction.objects.filter(status='Active', end_time__lt=now)
    for auction in expired_auctions:
        auction.status = 'Closed'
        highest_bid = auction.bids.order_by("-amount").first()
        if highest_bid:
            auction.winner_user = highest_bid.bidder

        fee_thanh_toan = auction.calculate_platform_fee()
        auction.listing_fee = Decimal(fee_thanh_toan)

        seller = auction.seller
        seller.balance -= fee_thanh_toan
        seller.save()

        auction.save()
        create_order_if_winner(auction, auction.winner_user)


def index(request):
    check_and_close_expired_auctions()
    watching_ids = []
    if request.user.is_authenticated:
        watching_ids = Watchlist.objects.filter(user=request.user).values_list('item_id', flat=True)
    return render(request, "auctions/index.html", {
        "auctions": Auction.objects.filter(status='Active').order_by('-created_at'),
        "watching_ids": watching_ids
    })




def login_view(request):
    if request.method == "POST":


        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)


        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome, {username}. Đăng nhập thành công.')


            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")




def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))




def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Mật khẩu phải khớp."
            })


        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Tài Khoản đã tồn tại."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")




def categories(request):
    return render(request, "auctions/categories.html", {
        "categories": Category.objects.all()
    })




def category(request, category_id):
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return render(request, "auctions/error.html", {
            "code": 404,
            "message": "Danh mục không tồn tại."
        })


    auctions = Auction.objects.filter(category_id=category_id, status="Active").order_by('-created_at')

    watching_ids = []
    if request.user.is_authenticated:
        watching_ids = Watchlist.objects.filter(user=request.user).values_list('item_id', flat=True)

    return render(request, "auctions/category.html", {
        "auctions": auctions,
        "category": category,
        "watching_ids": watching_ids
    })




@login_required(login_url="login")
def watchlist(request):
    watchlist_items = Watchlist.objects.filter(user=request.user).order_by('-id')
    auctions = [wl.item for wl in watchlist_items]
    watchingNum = len(auctions)
   
    return render(request, "auctions/watchlist.html", {
        "watchlist": watchlist_items,
        "auctions": auctions,
        "watchingNum": watchingNum
    })


@login_required(login_url="login")
def create(request):
    if request.method == "POST":
        form = NewListingForm(request.POST, request.FILES)
        if form.is_valid():
            new_listing = form.save(commit=False)
            new_listing.seller = request.user
            new_listing.current_price = form.cleaned_data['start_price']
            new_listing.status = 'Active'
            
            reserve_price = request.POST.get("reserve_price") or "0"
            buy_now_price = request.POST.get("buy_now_price") or "0"
            new_listing.reserve_price = Decimal(reserve_price)
            new_listing.buy_now_price = Decimal(buy_now_price)
            
            category_id = request.POST.get("category")
            try:
                category_obj = Category.objects.get(pk=category_id)
                new_listing.category = category_obj
            except Category.DoesNotExist:
                new_listing.category = None
                
            duration = request.POST.get("duration")
            duration_days = 1
            if duration in ["3 Ngay", "3"]:
                duration_days = 3
            elif duration in ["7 Ngay", "7"]:
                duration_days = 7
            
            new_listing.duration = duration_days
            new_listing.end_time = timezone.now() + datetime.timedelta(days=duration_days)
            
            new_listing.listing_fee = Decimal(new_listing.calculate_fixed_costs())
            new_listing.save()
            
            messages.success(request, f"Tạo phiên đấu giá thành công! Tổng phí đăng tin cố định tạm tính: {int(new_listing.listing_fee):,} VNĐ.")
            return HttpResponseRedirect(reverse("index"))
        else:
            messages.error(request, 'Biểu mẫu nhập vào không hợp lệ. Vui lòng kiểm tra lại dữ liệu.')
            return render(request, "auctions/create.html", {"form": form})
    else:
        form = NewListingForm()
        return render(request, "auctions/create.html", {"form": form})



def listing(request, auction_id):  
    try:
        auction = Auction.objects.get(pk=auction_id)
    except Auction.DoesNotExist:
        return render(request, "auctions/error.html", {
            "code": 404,
            "message": "Phiên đấu giá không tồn tại."
        })

    watching = False
    highest_bidder = None
    if request.user.is_authenticated and Watchlist.objects.filter(user=request.user, item=auction):
        watching = True
        
    user = request.user
    bid_Num = Bid.objects.filter(item=auction_id).count()
   
    comments = Comment.objects.filter(listing=auction_id).order_by("-timestamp")
    reviews = auction.reviews.all().order_by("-created_at")
    highest_bid = Bid.objects.filter(item_id=auction_id).order_by("-amount").first()
   
    if request.method == "GET":
        form = NewBidForm()
        commentForm = NewCommentForm()

        if auction.status == 'Active':
            return render(request, "auctions/listing.html", {
                "auction": auction,
                "form": form,
                "user": user,
                "bid_Num": bid_Num,
                "commentForm": commentForm,
                "comments": comments,
                "reviews": reviews,
                "watching": watching
            })
        else:
            if highest_bid is None:
                messages.info(request, 'Phiên đấu giá đã kết thúc và không có người tham gia đặt giá.')
                return render(request, "auctions/listing.html", {
                    "auction": auction,
                    "form": form,
                    "user": user,
                    "bid_Num": bid_Num,
                    "highest_bidder": highest_bidder,
                    "commentForm": commentForm,
                    "comments": comments,
                    "reviews": reviews,
                    "watching": watching
                })
            else:
                highest_bidder = highest_bid.bidder
                auction.winner_user = highest_bidder

                if user == highest_bidder:
                    messages.info(request, 'Chúc mừng! Bạn đã thắng phiên đấu giá này.')
                else:
                    messages.info(request, f'Phiên đấu giá đã kết thúc. Người thắng cuộc là {highest_bidder.username}.')
                
                return render(request, "auctions/listing.html", {
                    "auction": auction,
                    "form": form,
                    "user": user,
                    "highest_bidder": highest_bidder,
                    "bid_Num": bid_Num,
                    "commentForm": commentForm,
                    "comments": comments,
                    "reviews": reviews,
                    "watching": watching
                })

    else:
        return render(request, "auctions/error.html", {
            "code": 405,
            "message": "Không cho phép sử dụng phương thức POST."
        })
       
       
@login_required
def close(request, auction_id):
    if request.method == "POST":
        auction = get_object_or_404(Auction, pk=auction_id)
       
        if auction.status == 'Active' and request.user == auction.seller:
            auction.status = 'Closed'
           
            highest_bid = auction.highest_bid
            if highest_bid:
                auction.winner_user = highest_bid.bidder
           
            sf = auction.calculate_success_fee()
            auction.listing_fee = Decimal(auction.calculate_fixed_costs()) + Decimal(sf)
           
            seller = auction.seller
            seller.balance -= auction.listing_fee
            seller.save()

            auction.save()
            create_order_if_winner(auction, auction.winner_user)

            messages.success(request, f"Phiên đấu giá đã được đóng thành công. Phí dịch vụ khấu trừ: {sf:,} VNĐ.")
        else:
            messages.error(request, "Bạn không có quyền đóng phiên đấu giá này.")
           
        return redirect('listing', auction_id=auction.id)
       


@login_required(login_url="login")
def bid(request, auction_id):    
    if request.method == "POST":
        try:
            auction = Auction.objects.get(pk=auction_id)      
        except Auction.DoesNotExist:
            return render(request, "auctions/error.html", {
                "code": 404,
                "message": "The auction does not exist."
            })


        if auction.status != 'Active':
            messages.error(request, "Phiên đấu giá này đã kết thúc, không thể đặt giá.")
            return redirect("listing", auction_id=auction_id)

        if auction.seller == request.user:
            messages.error(request, "Bạn không thể tự đấu giá sản phẩm của chính mình!")
            return redirect("listing", auction_id=auction_id)

        form = NewBidForm(request.POST, request.FILES)

        if form.is_valid():
            bidded_price = form.cleaned_data["amount"]
            highest_bid = Bid.objects.filter(item=auction_id).order_by("-amount").first()
            highest_bid_price = highest_bid.amount if highest_bid else auction.current_price

            if bidded_price <= highest_bid_price:
                messages.error(request, "Mức giá đặt phải lớn hơn giá hiện tại!")
                return redirect("listing", auction_id=auction_id)

            new_bid = Bid(bidder=request.user, item=auction, amount=bidded_price)
            new_bid.save()

            auction.current_price = bidded_price
            auction.save()

            return redirect("listing", auction_id=auction_id)

        else:
            messages.error(request, "Vui lòng nhập số tiền hợp lệ!")
            return redirect("listing", auction_id=auction_id)


@login_required(login_url="login")
def comment(request, auction_id):
    if request.method == "POST":


        try:
            auction = Auction.objects.get(pk=auction_id)    
           
        except Auction.DoesNotExist:
            return render(request, "auctions/error.html", {
                "code": 404,
                "message": "The auction does not exist."
            })
           
        form = NewCommentForm(request.POST, request.FILES)


        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.user = request.user
           
            new_comment.listing = auction
           
            new_comment.save()


            messages.success(request, 'Bình luận của bạn đã được nhận thành công.')


            return HttpResponseRedirect(reverse("listing", args=(auction.id,)))
       
        else:
            messages.error(request, 'Vui lòng gửi một bình luận hợp lệ.')
            return HttpResponseRedirect(reverse("listing", args=(auction_id,)))
     
    else:
        return render(request, "auctions/error.html", {
            "code": 405,
            "message": "Phương thức GET không được phép."
        })




@login_required(login_url="login")
def addWatchlist(request, auction_id):
    if request.method == "POST":
        try:
            auction = Auction.objects.get(pk=auction_id)
        except Auction.DoesNotExist:
            return render(request, "auctions/error.html", {
                "code": 404,
                "message": "Phiên đấu giá không tồn tại."
            })

        redirect_to = request.META.get('HTTP_REFERER') or reverse("listing", args=(auction.id,))

        if Watchlist.objects.filter(user=request.user, item=auction).exists():
            messages.error(request, 'Tin này đã có trong danh sách theo dõi của bạn.')
            return HttpResponseRedirect(redirect_to)

        Watchlist.objects.create(user=request.user, item=auction)
        messages.success(request, 'Đã thêm vào danh sách theo dõi.')
        return HttpResponseRedirect(redirect_to)

    else:
        return render(request, "auctions/error.html", {
            "code": 405,
            "message": "Phương thức GET không được phép."
        })




@login_required(login_url="login")
def removeWatchlist(request, auction_id):
    if request.method == "POST":
        try:
            auction = Auction.objects.get(pk=auction_id)
        except Auction.DoesNotExist:
            return render(request, "auctions/error.html", {
                "code": 404,
                "message": "Phiên đấu giá không tồn tại."
            })

        redirect_to = request.META.get('HTTP_REFERER') or reverse("listing", args=(auction.id,))
        deleted_count, _ = Watchlist.objects.filter(user=request.user, item=auction).delete()

        if deleted_count:
            messages.success(request, 'Đã xóa khỏi danh sách theo dõi.')
        else:
            messages.error(request, 'Tin này không có trong danh sách theo dõi của bạn.')
        return HttpResponseRedirect(redirect_to)
    else:
        return render(request, "auctions/error.html", {
            "code": 405,
            "message": "Phương thức GET không được phép."
        })


@login_required
def won_listings(request):
    listings = Auction.objects.filter(
        winner_user=request.user,
        status__in=["Closed", "Completed"]
    ).order_by('-created_at')
   
    return render(request, "auctions/won_listings.html", {
        "listings": listings
    })


@login_required
def refuse_auction(request, auction_id):
    auction = get_object_or_404(Auction, pk=auction_id, winner_user=request.user)
   
    if request.method == "POST":
        auction.is_refused = True
        auction.refusal_reason = request.POST.get("reason", "Không có lý do cụ thể")
        auction.save()
        messages.success(request, f"Bạn đã từ chối nhận sản phẩm: {auction.title}")
       
    return redirect('won_listings')


@login_required
def my_listings(request):
    user_listings = Auction.objects.filter(seller=request.user).order_by('-created_at')
   
    active_listings = user_listings.filter(status='Active', is_refused=False)
    closed_listings = user_listings.filter(status__in=['Closed', 'Completed', 'Success'], is_refused=False, winner_user__isnull=False)
    refused_listings = user_listings.filter(is_refused=True)
   
    return render(request, "auctions/my_listings.html", {
        "active_listings": active_listings,
        "closed_listings": closed_listings,
        "refused_listings": refused_listings,
    })


@login_required
def receive_auction(request, auction_id):
    if request.method == "POST":
        auction = get_object_or_404(Auction, pk=auction_id)
       
        if auction.winner_user == request.user:
            auction.status = 'Completed'
            auction.is_refused = False
            auction.save()
            messages.success(request, f"🎉 Bạn đã xác nhận nhận hàng thành công sản phẩm: {auction.title}!")
        else:
            messages.error(request, "Bạn không có quyền thực hiện hành động này.")
           
    return redirect('won_listings')


@login_required
def buy_now(request, auction_id):
    if request.method == "POST":
        auction = get_object_or_404(Auction, pk=auction_id)
        buyer = request.user
       
        if auction.status == 'Active' and auction.buy_now_price > 0 and buyer != auction.seller:
            new_bid = Bid()
            new_bid.item = auction
            new_bid.bidder = buyer
            new_bid.amount = auction.buy_now_price
            new_bid.save()
           
            auction.status = 'Closed'
            auction.winner_user = buyer
            auction.current_price = auction.buy_now_price
           
            sf = auction.calculate_success_fee()
            auction.listing_fee = Decimal(auction.calculate_fixed_costs()) + Decimal(sf)
           
            seller = auction.seller
            seller.balance -= auction.listing_fee
            seller.save()

            auction.save()
            create_order_if_winner(auction, auction.winner_user)

            if auction.seller == request.user:
                messages.success(request, f"Phiên đấu giá đã được đóng thành công. Phí dịch vụ khấu trừ: {sf:,} VNĐ.")
            else:
                messages.success(request, "Chúc mừng! Bạn đã mua ngay sản phẩm này thành công.")

        return redirect('listing', auction_id=auction.id)

@login_required
def leave_review(request, auction_id):
    if request.method == "POST":
        auction = get_object_or_404(Auction, pk=auction_id)
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")
        
        if auction.status in ['Closed', 'Completed']:
            if request.user == auction.seller:
                reviewee = auction.winner_user
            else:
                reviewee = auction.seller
                
            Review.objects.create(
                auction=auction,
                reviewer=request.user,
                reviewee=reviewee,
                rating=int(rating),
                comment=comment
            )
            messages.success(request, "Gửi đánh giá thành công!")
    return redirect('listing', auction_id=auction_id)