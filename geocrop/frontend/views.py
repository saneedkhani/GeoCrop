from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from . import data

# Stub views - most will be filled in step by step.

def home_view(request):
    return render(request, "frontend/home.html")

def upload_view(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("satellite_image")
        if not uploaded_file:
            return render(request, "frontend/upload.html", {
                "error": "Please select a satellite image before analyzing."
            })
        # Prototype stage: no real model, just acknowledge the upload and
        # record it so it shows up as a real entry on the Profile page.
        record = {
            "filename": uploaded_file.name,
            "location": request.POST.get("location", ""),
            "capture_date": request.POST.get("capture_date", ""),
            "uploaded_at": timezone.now().strftime("%b %d, %Y %I:%M %p"),
        }
        uploads = request.session.get("uploads", [])
        uploads.append(record)
        request.session["uploads"] = uploads
        return redirect("frontend:processing")
    return render(request, "frontend/upload.html")

def processing_view(request):
    uploads = request.session.get("uploads", [])
    upload_filename = uploads[-1]["filename"] if uploads else None
    return render(request, "frontend/processing.html", {
        "upload_filename": upload_filename,
    })

def results_view(request):
    distinct = data.get_distinct_values()
    return render(request, "frontend/results.html", {
        "countries": distinct["countries"],
        "states": distinct["states"],
        "crop_types": distinct["crop_types"],
        "crop_colors": data.CROP_COLORS,
    })

def field_data_view(request):
    country = request.GET.get("country") or None
    state = request.GET.get("state") or None
    crop_type = request.GET.get("crop_type") or None

    fields = data.filter_fields(country=country, state=state, crop_type=crop_type)
    geojson = data.fields_to_geojson(fields)
    stats = data.aggregate_stats(fields)

    return JsonResponse({"geojson": geojson, "stats": stats})

def dashboard_view(request):
    distinct = data.get_distinct_values()
    return render(request, "frontend/dashboard.html", {
        "states": distinct["states"],
        "regions": distinct["regions"],
        "crop_types": distinct["crop_types"],
        "crop_colors": data.CROP_COLORS,
    })

def dashboard_stats_view(request):
    state = request.GET.get("state") or None
    region = request.GET.get("region") or None
    crop_type = request.GET.get("crop_type") or None

    fields = data.filter_fields(state=state, region=region, crop_type=crop_type)
    stats = data.aggregate_stats(fields)

    return JsonResponse(stats)

@login_required(login_url='frontend:login')
def profile_view(request):
    uploads = request.session.get("uploads", [])

    # Only real records: each entry is an actual satellite data upload the
    # user submitted this session. No dummy/placeholder activity is shown.
    records = [
        {
            "description": 'Uploaded satellite image "%s"' % u["filename"],
            "detail": (u.get("location") or "Location not specified")
                      + (" \u00b7 captured %s" % u["capture_date"] if u.get("capture_date") else "")
                      + " \u00b7 " + u["uploaded_at"],
        }
        for u in reversed(uploads)
    ]

    return render(request, "frontend/profile.html", {
        "activities": records,
    })

def login_view(request):
    next_url = request.POST.get("next") or request.GET.get("next") or ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url or "frontend:profile")
        return render(request, "frontend/login.html", {
            "error": "Invalid username or password.",
            "username": username,
            "next": next_url,
        })

    return render(request, "frontend/login.html", {"next": next_url})

def signup_view(request):
    next_url = request.POST.get("next") or request.GET.get("next") or ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        error = None
        if not username or not email or not password:
            error = "Please fill in all fields."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif User.objects.filter(username=username).exists():
            error = "That username is already taken."
        elif User.objects.filter(email=email).exists():
            error = "An account with that email already exists."

        if error:
            return render(request, "frontend/signup.html", {
                "error": error,
                "username": username,
                "email": email,
                "next": next_url,
            })

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect(next_url or "frontend:profile")

    return render(request, "frontend/signup.html", {"next": next_url})

def logout_view(request):
    logout(request)
    return redirect("frontend:home")