from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend


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
