import logging
import threading

from django.core.mail import send_mail
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend

logger = logging.getLogger(__name__)


def send_mail_async(subject, message, recipient_list, from_email=None):
    """Envia e-mail em uma thread daemon para não bloquear a resposta HTTP."""

    def _send():
        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=True)
        except Exception:
            logger.exception("Falha ao enviar e-mail em background")

    threading.Thread(target=_send, daemon=True).start()


class EmailBackend(ConsoleEmailBackend):
    """Console backend para dev que imprime o email de forma legível.

    O backend padrão imprime o MIME quoted-printable, que quebra URLs
    longas (ex.: link de reset de senha) aos 76 caracteres, impossibilitando
    copiar o link do console.
    """

    def write_message(self, message):
        lines = [
            "-" * 60,
            "Subject: %s" % (message.subject or ""),
            "To: %s" % ", ".join(message.to),
            "-" * 60,
            message.body or "",
            "-" * 60,
        ]
        self.stream.write("\n".join(lines) + "\n")
