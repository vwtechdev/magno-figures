from decimal import Decimal
from io import BytesIO
import time

from PIL import Image
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.figures.models import Figure
from apps.newsletters.models import (
    NewsletterCampaign,
    NewsletterSubscriber,
    StockAlert,
)
from apps.newsletters.notifications import send_campaign, stock_alert_token
from apps.website.models import Website


def make_image(name="figure.png"):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_website():
    return Website.objects.create(
        company_name="Magno Figures",
        logo=make_image("logo.png"),
        favicon=make_image("favicon.png"),
        whatsapp="5511999999999",
        email="",
        about="Sobre a loja.",
        privacy_policy="Política de privacidade.",
    )


class StockAlertTest(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        make_website()
        self.figure = Figure.objects.create(
            name="Iron Man",
            slug="iron-man",
            description="Action figure do Homem de Ferro.",
            price=Decimal("199.90"),
            stock=0,
            sold_out=True,
            image=make_image("iron.png"),
        )

    def _wait_for_email(self, timeout=2.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if mail.outbox:
                return True
            time.sleep(0.01)
        return False

    def test_sold_out_page_shows_notify_form(self):
        response = self.client.get(
            reverse("figures:detail", args=[self.figure.slug])
        )
        self.assertContains(response, "Me avise quando disponível")
        self.assertContains(
            response, reverse("figures:notify", args=[self.figure.slug])
        )

    def test_available_page_has_no_notify_form(self):
        self.figure.sold_out = False
        self.figure.save()
        response = self.client.get(
            reverse("figures:detail", args=[self.figure.slug])
        )
        self.assertNotContains(response, "Me avise quando disponível")

    def test_subscribe_creates_alert(self):
        response = self.client.post(
            reverse("figures:notify", args=[self.figure.slug]),
            {"email": "cliente@example.com"},
            follow=True,
        )
        self.assertTrue(
            StockAlert.objects.filter(
                figure=self.figure, email="cliente@example.com"
            ).exists()
        )
        self.assertContains(response, "Avisaremos quando estiver disponível.")

    def test_subscribe_duplicate_keeps_single_alert(self):
        url = reverse("figures:notify", args=[self.figure.slug])
        self.client.post(url, {"email": "cliente@example.com"})
        response = self.client.post(
            url, {"email": "cliente@example.com"}, follow=True
        )
        self.assertEqual(
            StockAlert.objects.filter(figure=self.figure).count(), 1
        )
        self.assertContains(response, "já está na lista de avisos.")

    def test_subscribe_invalid_email_rejected(self):
        response = self.client.post(
            reverse("figures:notify", args=[self.figure.slug]),
            {"email": "nao-email"},
            follow=True,
        )
        self.assertEqual(
            StockAlert.objects.filter(figure=self.figure).count(), 0
        )
        self.assertContains(response, "Informe um email válido.")

    def test_subscribe_available_figure_rejected(self):
        self.figure.sold_out = False
        self.figure.save()
        response = self.client.post(
            reverse("figures:notify", args=[self.figure.slug]),
            {"email": "cliente@example.com"},
            follow=True,
        )
        self.assertEqual(
            StockAlert.objects.filter(figure=self.figure).count(), 0
        )
        self.assertContains(response, "já está disponível.")

    def test_restock_sends_email_and_marks_notified(self):
        alert = StockAlert.objects.create(
            figure=self.figure, email="cliente@example.com"
        )
        self.figure.sold_out = False
        self.figure.save()
        self.assertTrue(self._wait_for_email(), "e-mail não foi enviado a tempo")
        message = mail.outbox[0]
        self.assertEqual(message.to, ["cliente@example.com"])
        self.assertIn("Iron Man", message.subject)
        self.assertIn("/figures/iron-man/", message.body)
        self.assertIn("/newsletter/stock-alerts/unsubscribe/", message.body)
        alert.refresh_from_db()
        self.assertTrue(alert.is_notified)

    def test_other_edits_do_not_send(self):
        StockAlert.objects.create(
            figure=self.figure, email="cliente@example.com"
        )
        self.figure.price = Decimal("179.90")
        self.figure.save()
        time.sleep(0.3)
        self.assertEqual(len(mail.outbox), 0)

    def test_unsubscribe_valid_token(self):
        alert = StockAlert.objects.create(
            figure=self.figure, email="cliente@example.com"
        )
        token = stock_alert_token(alert)
        response = self.client.get(
            reverse("newsletters:stock_alert_unsubscribe", args=[token])
        )
        self.assertContains(response, "Aviso cancelado")
        self.assertFalse(
            StockAlert.objects.filter(pk=alert.pk).exists()
        )

    def test_unsubscribe_invalid_token(self):
        response = self.client.get(
            reverse("newsletters:stock_alert_unsubscribe", args=["invalido"])
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Link inválido", status_code=400
        )

    def test_legacy_unsubscribe_url_redirects(self):
        alert = StockAlert.objects.create(
            figure=self.figure, email="cliente@example.com"
        )
        token = stock_alert_token(alert)
        response = self.client.get(
            reverse("figures:unsubscribe", args=[token])
        )
        self.assertRedirects(
            response,
            reverse("newsletters:stock_alert_unsubscribe", args=[token]),
        )


class NewsletterSubscribeTest(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        make_website()

    def test_footer_contains_newsletter_form(self):
        response = self.client.get(reverse("website:home"))
        self.assertContains(response, 'id="newsletterForm"')
        self.assertContains(response, reverse("newsletters:subscribe"))

    def test_subscribe_ajax_creates_subscriber(self):
        response = self.client.post(
            reverse("newsletters:subscribe"),
            {"email": "leitor@example.com"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(
            NewsletterSubscriber.objects.filter(
                email="leitor@example.com", is_active=True
            ).exists()
        )

    def test_subscribe_duplicate_keeps_single(self):
        url = reverse("newsletters:subscribe")
        self.client.post(
            url,
            {"email": "leitor@example.com"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        response = self.client.post(
            url,
            {"email": "leitor@example.com"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)
        self.assertIn("já está inscrito", response.json()["message"])

    def test_subscribe_invalid_email_rejected(self):
        response = self.client.post(
            reverse("newsletters:subscribe"),
            {"email": "nao-email"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(NewsletterSubscriber.objects.count(), 0)

    def test_resubscribe_reactivates(self):
        NewsletterSubscriber.objects.create(
            email="leitor@example.com", is_active=False
        )
        response = self.client.post(
            reverse("newsletters:subscribe"),
            {"email": "leitor@example.com"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertTrue(response.json()["ok"])
        subscriber = NewsletterSubscriber.objects.get(
            email="leitor@example.com"
        )
        self.assertTrue(subscriber.is_active)

    def test_subscribe_fallback_redirects_back(self):
        response = self.client.post(
            reverse("newsletters:subscribe"),
            {"email": "leitor@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            NewsletterSubscriber.objects.filter(
                email="leitor@example.com"
            ).exists()
        )

    def test_unsubscribe_deactivates(self):
        from apps.newsletters.notifications import newsletter_token

        subscriber = NewsletterSubscriber.objects.create(
            email="leitor@example.com"
        )
        token = newsletter_token(subscriber)
        response = self.client.get(
            reverse("newsletters:unsubscribe", args=[token])
        )
        self.assertContains(response, "Aviso cancelado")
        subscriber.refresh_from_db()
        self.assertFalse(subscriber.is_active)

    def test_unsubscribe_invalid_token(self):
        response = self.client.get(
            reverse("newsletters:unsubscribe", args=["invalido"])
        )
        self.assertEqual(response.status_code, 400)


class NewsletterCampaignTest(TestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        make_website()
        NewsletterSubscriber.objects.create(email="a@example.com")
        NewsletterSubscriber.objects.create(email="b@example.com")
        NewsletterSubscriber.objects.create(
            email="off@example.com", is_active=False
        )
        self.campaign = NewsletterCampaign.objects.create(
            subject="Novidades da semana",
            message="Chegaram figures novas!",
        )

    def _wait_for_email(self, count, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if len(mail.outbox) >= count:
                return True
            time.sleep(0.01)
        return False

    def test_send_campaign_notifies_actives_only(self):
        total = send_campaign(self.campaign)
        self.assertEqual(total, 2)
        self.assertTrue(self._wait_for_email(2), "e-mails não enviados a tempo")
        recipients = sorted(message.to[0] for message in mail.outbox)
        self.assertEqual(recipients, ["a@example.com", "b@example.com"])
        for message in mail.outbox:
            self.assertEqual(message.subject, "Novidades da semana")
            self.assertIn("Chegaram figures novas!", message.body)
            self.assertIn("/newsletter/unsubscribe/", message.body)
        self.campaign.refresh_from_db()
        self.assertTrue(self.campaign.is_sent)

    def test_send_campaign_skips_already_sent(self):
        send_campaign(self.campaign)
        self.assertTrue(self._wait_for_email(2))
        sent = len(mail.outbox)
        total = send_campaign(self.campaign)
        self.assertEqual(total, 0)
        time.sleep(0.2)
        self.assertEqual(len(mail.outbox), sent)
