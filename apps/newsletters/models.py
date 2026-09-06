from django.db import models

from core.models import BaseModel


class NewsletterSubscriber(BaseModel):
    email = models.EmailField(
        unique=True, db_index=True, verbose_name="Email"
    )

    class Meta:
        verbose_name = "Assinante"
        verbose_name_plural = "Assinantes"
        ordering = ["email"]

    def __str__(self):
        return self.email


class NewsletterCampaign(BaseModel):
    subject = models.CharField(
        max_length=255, verbose_name="Assunto"
    )
    message = models.TextField(
        verbose_name="Mensagem"
    )
    sent_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Enviado em"
    )

    class Meta:
        verbose_name = "Campanha"
        verbose_name_plural = "Campanhas"
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject

    @property
    def is_sent(self):
        return self.sent_at is not None


class StockAlert(BaseModel):
    figure = models.ForeignKey(
        "figures.Figure",
        on_delete=models.CASCADE,
        related_name="stock_alerts",
        verbose_name="Action Figure",
    )
    email = models.EmailField(
        db_index=True, verbose_name="Email"
    )
    is_notified = models.BooleanField(
        default=False, db_index=True, verbose_name="Avisado"
    )

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["figure", "email"],
                name="unique_stock_alert_per_figure_email",
            )
        ]

    def __str__(self):
        return f"{self.email} - {self.figure.name}"
