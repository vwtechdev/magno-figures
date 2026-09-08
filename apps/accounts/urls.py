from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("verify-email/sent/", views.verification_sent_view, name="verification_sent"),
    path("verify-email/resend/", views.resend_verification_view, name="resend_verification"),
    path("verify-email/<uidb64>/<token>/", views.verify_email_view, name="verify_email"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/dados/", views.profile_data_view, name="profile_data"),
    path("password-reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
