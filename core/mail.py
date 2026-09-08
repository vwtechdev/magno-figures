import logging
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

from django.conf import settings
from django.core import mail as django_mail
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from django.core.validators import validate_email
from django.db import close_old_connections

logger = logging.getLogger(__name__)


_executor = None
_executor_pid = None
_executor_lock = threading.Lock()
_pending = set()
_pending_lock = threading.Lock()


def _int_setting(name, default):
    try:
        return max(1, int(os.getenv(name, getattr(settings, name, default))))
    except (TypeError, ValueError):
        return default


def _float_setting(name, default):
    try:
        return max(0.0, float(os.getenv(name, getattr(settings, name, default))))
    except (TypeError, ValueError):
        return default


def _get_executor():
    global _executor, _executor_pid
    pid = os.getpid()
    if _executor is None or _executor_pid != pid:
        with _executor_lock:
            if _executor is None or _executor_pid != pid:
                # Criado preguiçosamente por processo: o gunicorn usa
                # --preload, então um executor criado no import seria
                # herdado pelo fork em estado inválido.
                _executor = ThreadPoolExecutor(
                    max_workers=_int_setting("EMAIL_MAX_WORKERS", 2),
                    thread_name_prefix="email",
                )
                _executor_pid = pid
    return _executor


def _mask_email(value):
    try:
        local, _, domain = str(value).partition("@")
        if not domain:
            return "***"
        return f"{local[:1] or '*'}***@{domain}"
    except Exception:
        return "***"


def _clean_recipients(recipient_list):
    cleaned = []
    for recipient in recipient_list or []:
        address = str(recipient or "").strip()
        if not address:
            continue
        try:
            validate_email(address)
        except ValidationError:
            logger.warning(
                "E-mail ignorado por destinatário inválido: %s",
                _mask_email(address),
            )
            continue
        cleaned.append(address)
    return cleaned


def _completed_future(result):
    future = Future()
    future.set_result(result)
    return future


def _track(future):
    with _pending_lock:
        _pending.add(future)

    def _done(completed):
        with _pending_lock:
            _pending.discard(completed)

    future.add_done_callback(_done)
    return future


def _run_callback(callback, payload, what):
    try:
        callback(payload)
    except Exception:
        logger.exception("Falha no callback de e-mail (%s)", what)
    finally:
        close_old_connections()


def _send_single(subject, message, recipients, from_email, retries, retry_delay):
    for attempt in range(retries + 1):
        try:
            django_mail.send_mail(
                subject, message, from_email, recipients, fail_silently=False
            )
            return True
        except Exception as exc:
            if attempt < retries:
                logger.warning(
                    "Tentativa %s de envio de e-mail falhou para %s: %s",
                    attempt + 1,
                    ", ".join(_mask_email(r) for r in recipients),
                    exc,
                )
                if retry_delay > 0:
                    time.sleep(retry_delay * (attempt + 1))
            else:
                logger.error(
                    "Falha definitiva ao enviar e-mail para %s: %s",
                    ", ".join(_mask_email(r) for r in recipients),
                    exc,
                    exc_info=True,
                )
    return False


def _deliver_single(payload, on_success, on_error):
    try:
        ok = _send_single(
            payload["subject"],
            payload["message"],
            payload["recipients"],
            payload.get("from_email"),
            payload["retries"],
            payload["retry_delay"],
        )
    finally:
        close_old_connections()
    if ok:
        if on_success is not None:
            _run_callback(on_success, True, "single:success")
    elif on_error is not None:
        _run_callback(on_error, False, "single:error")
    return ok


def _deliver_batch(payloads, retries, retry_delay, on_success, on_error):
    results = []
    connection = None
    try:
        for payload in payloads:
            ok = False
            for attempt in range(retries + 1):
                try:
                    if connection is None:
                        connection = get_connection()
                    EmailMessage(
                        payload["subject"],
                        payload["message"],
                        payload.get("from_email"),
                        payload["recipients"],
                        connection=connection,
                    ).send(fail_silently=False)
                    ok = True
                    break
                except Exception as exc:
                    try:
                        if connection is not None:
                            connection.close()
                    except Exception:
                        pass
                    connection = None
                    if attempt < retries:
                        logger.warning(
                            "Tentativa %s de envio em lote falhou para %s: %s",
                            attempt + 1,
                            ", ".join(
                                _mask_email(r)
                                for r in payload["recipients"]
                            ),
                            exc,
                        )
                        if retry_delay > 0:
                            time.sleep(retry_delay * (attempt + 1))
                    else:
                        logger.error(
                            "Falha definitiva no lote para %s: %s",
                            ", ".join(
                                _mask_email(r)
                                for r in payload["recipients"]
                            ),
                            exc,
                            exc_info=True,
                        )
            results.append(ok)
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
        close_old_connections()
    if on_success is not None:
        _run_callback(on_success, results, "batch:success")
    if not all(results) and on_error is not None:
        _run_callback(on_error, results, "batch:error")
    return results


def send_mail_async(
    subject, message, recipient_list, from_email=None, on_success=None, on_error=None
):
    """Enfileira o envio em background sem bloquear a resposta HTTP."""
    recipients = _clean_recipients(recipient_list)
    if not recipients:
        logger.warning(
            "E-mail ignorado: nenhum destinatário válido (assunto: %s)",
            subject,
        )
        return _completed_future(False)
    payload = {
        "subject": subject,
        "message": message,
        "recipients": recipients,
        "from_email": from_email,
        "retries": _int_setting("EMAIL_MAX_RETRIES", 2),
        "retry_delay": _float_setting("EMAIL_RETRY_DELAY", 1.0),
    }
    try:
        return _track(
            _get_executor().submit(_deliver_single, payload, on_success, on_error)
        )
    except RuntimeError:
        logger.exception("Fila de e-mail indisponível; envio descartado")
        return _completed_future(False)


def dispatch_email_batch(payloads, on_success=None, on_error=None):
    """Enfileira um lote em uma única thread, reutilizando a conexão SMTP."""
    cleaned = []
    for payload in payloads or []:
        recipients = _clean_recipients(payload.get("recipients"))
        if not recipients:
            continue
        cleaned.append(
            {
                "subject": payload.get("subject", ""),
                "message": payload.get("message", ""),
                "recipients": recipients,
                "from_email": payload.get("from_email"),
            }
        )
    if not cleaned:
        logger.warning("Lote de e-mail ignorado: nenhum destinatário válido")
        return _completed_future([])
    try:
        return _track(
            _get_executor().submit(
                _deliver_batch,
                cleaned,
                _int_setting("EMAIL_MAX_RETRIES", 2),
                _float_setting("EMAIL_RETRY_DELAY", 1.0),
                on_success,
                on_error,
            )
        )
    except RuntimeError:
        logger.exception("Fila de e-mail indisponível; lote descartado")
        return _completed_future([False] * len(cleaned))


def flush_email_queue(timeout=10.0):
    """Aguarda o esvaziamento da fila. Uso exclusivo em testes."""
    deadline = time.time() + max(0.0, timeout)
    while True:
        with _pending_lock:
            futures = list(_pending)
        if not futures:
            return True
        for future in futures:
            remaining = deadline - time.time()
            if remaining <= 0:
                return False
            try:
                future.result(timeout=remaining)
            except Exception:
                logger.exception("Falha ao aguardar envio de e-mail em teste")


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
