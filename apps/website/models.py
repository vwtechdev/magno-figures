from django.core.cache import cache
from django.core.validators import RegexValidator
from django.db import models

from core.models import BaseModel
from core.validators import validate_image_size

hex_color_validator = RegexValidator(
    regex=r"^#[0-9a-fA-F]{6}$",
    message="Use o formato hexadecimal, ex.: #EAC979.",
)


class BannerManager(models.Manager):
    def active(self):
        return self.get_queryset().filter(is_active=True)


class Banner(BaseModel):
    website = models.ForeignKey(
        "website.Website",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="banners",
        verbose_name="Website",
    )
    title = models.CharField(
        max_length=255, blank=True, verbose_name="Título"
    )
    subtitle = models.CharField(
        max_length=255, blank=True, verbose_name="Subtítulo"
    )
    image = models.ImageField(
        upload_to="website/banners/",
        validators=[validate_image_size],
        verbose_name="Imagem",
    )
    link = models.URLField(
        blank=True, verbose_name="Link"
    )
    order = models.PositiveSmallIntegerField(
        default=0, verbose_name="Ordem"
    )

    objects = BannerManager()

    class Meta:
        verbose_name = "Banner do Site"
        verbose_name_plural = "Banners do Site"
        ordering = ["order"]

    def __str__(self):
        return self.title or f"Banner {self.pk}"


class WebsiteManager(models.Manager):
    def get_config(self):
        cache_key = "website_config"
        config = cache.get(cache_key)
        if config is None:
            config, _ = self.get_queryset().get_or_create(
                pk=1,
                defaults={
                    "company_name": "Magno Figures",
                    "whatsapp": "",
                    "description": "",
                    "origin_zip_code": "",
                    "about": "",
                    "privacy_policy": "",
                },
            )
            cache.set(cache_key, config, timeout=3600)
        return config

    def clear_cache(self):
        cache.delete("website_config")


class Website(BaseModel):
    company_name = models.CharField(
        max_length=255, verbose_name="Título do Site"
    )
    logo = models.ImageField(
        upload_to="website/",
        blank=True,
        null=True,
        validators=[validate_image_size],
        verbose_name="Logo",
    )
    favicon = models.ImageField(
        upload_to="website/",
        blank=True,
        null=True,
        validators=[validate_image_size],
        verbose_name="Favicon",
    )
    whatsapp = models.CharField(
        max_length=20, verbose_name="WhatsApp"
    )
    description = models.CharField(
        max_length=160,
        blank=True,
        verbose_name="Descrição (SEO)",
        help_text="Texto curto usado no footer e como meta description nas buscas do Google (máx. 160 caracteres).",
    )
    origin_zip_code = models.CharField(
        max_length=9,
        blank=True,
        verbose_name="CEP de Origem",
        help_text="CEP de onde as encomendas são postadas (usado no cálculo de frete).",
    )
    instagram = models.URLField(
        blank=True, verbose_name="Instagram"
    )
    facebook = models.URLField(
        blank=True, verbose_name="Facebook"
    )
    twitter = models.URLField(
        blank=True, verbose_name="Twitter / X"
    )
    email = models.EmailField(
        blank=True, verbose_name="Email"
    )
    seo_keywords = models.TextField(
        blank=True,
        verbose_name="Palavras-chave (SEO)",
        help_text="Separadas por vírgula. Ex.: action figure, colecionáveis, bonecos importados.",
    )
    google_analytics = models.TextField(
        blank=True,
        verbose_name="Script Google Analytics",
        help_text="Cole o snippet completo fornecido pelo Google Analytics (tags <script>...</script>).",
    )
    about = models.TextField(
        verbose_name="Sobre"
    )
    privacy_policy = models.TextField(
        verbose_name="Política de Privacidade"
    )
    terms = models.TextField(
        blank=True, verbose_name="Termos de Uso"
    )
    theme_background = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Fundo",
        help_text="Em branco mantém o padrão (#0C0A09).",
    )
    theme_surface = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Superfícies (cards)",
        help_text="Em branco mantém o padrão (#1C1917).",
    )
    theme_text = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Texto",
        help_text="Em branco mantém o padrão (#F5F3F0).",
    )
    theme_muted = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Texto secundário",
        help_text="Em branco mantém o padrão (#A8A29E).",
    )
    theme_border = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Bordas",
        help_text="Em branco mantém o padrão (#44403C).",
    )
    theme_buttons = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Botões / dourado",
        help_text="Em branco mantém o dourado padrão.",
    )
    theme_hover = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Hover dos botões",
        help_text="Em branco mantém o padrão.",
    )
    theme_navbar = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Barra de navegação",
        help_text="Em branco mantém o padrão translúcido.",
    )
    theme_whatsapp = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Botão WhatsApp",
        help_text="Em branco mantém o verde padrão (#25D366).",
    )
    theme_success = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Sucesso (verde)",
        help_text="Em branco mantém o padrão (#34d399).",
    )
    theme_info = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Informação (azul)",
        help_text="Em branco mantém o padrão (#60a5fa).",
    )
    theme_warning = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Alerta (âmbar)",
        help_text="Em branco mantém o padrão (#fbbf24).",
    )
    theme_danger = models.CharField(
        max_length=7,
        blank=True,
        default="",
        validators=[hex_color_validator],
        verbose_name="Erro (vermelho)",
        help_text="Em branco mantém o padrão (#f87171).",
    )

    objects = WebsiteManager()

    class Meta:
        verbose_name = "Configuração do Site"
        verbose_name_plural = "Configurações do Site"

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        Website.objects.clear_cache()

    def _clean_whatsapp_number(self):
        number = "".join(filter(str.isdigit, self.whatsapp))
        if number and not number.startswith("55"):
            number = f"55{number}"
        return number

    @property
    def whatsapp_link(self):
        number = self._clean_whatsapp_number()
        return f"https://wa.me/{number}" if number else "#"

    @property
    def whatsapp_api_link(self):
        number = self._clean_whatsapp_number()
        return f"https://api.whatsapp.com/send?phone={number}" if number else "#"

    @staticmethod
    def _hex_to_rgb(value):
        value = value.lstrip("#")
        return (
            int(value[0:2], 16),
            int(value[2:4], 16),
            int(value[4:6], 16),
        )

    @staticmethod
    def _lighten(value, amount=0.55):
        red, green, blue = Website._hex_to_rgb(value)
        mixed = tuple(
            round(channel + (255 - channel) * amount)
            for channel in (red, green, blue)
        )
        return "#%02x%02x%02x" % mixed

    @property
    def theme_css_vars(self):
        """Mapeia os campos de tema para variáveis CSS. Vazio = padrão."""
        css_vars = {}
        if self.theme_background:
            css_vars["--bg"] = self.theme_background
        if self.theme_surface:
            css_vars["--bg-soft"] = self.theme_surface
            css_vars["--card"] = self.theme_surface
        if self.theme_text:
            css_vars["--text"] = self.theme_text
        if self.theme_muted:
            css_vars["--text-muted"] = self.theme_muted
        if self.theme_border:
            css_vars["--border"] = self.theme_border
        if self.theme_buttons:
            red, green, blue = self._hex_to_rgb(self.theme_buttons)
            css_vars["--gold-1"] = self.theme_buttons
            css_vars["--gold-2"] = self.theme_buttons
            css_vars["--gold-3"] = self.theme_buttons
            css_vars["--gold-gradient"] = self.theme_buttons
            css_vars["--gold-2-rgb"] = f"{red}, {green}, {blue}"
        if self.theme_hover:
            css_vars["--btn-hover"] = self.theme_hover
        if self.theme_navbar:
            css_vars["--navbar"] = self.theme_navbar
        if self.theme_whatsapp:
            red, green, blue = self._hex_to_rgb(self.theme_whatsapp)
            css_vars["--whatsapp"] = self.theme_whatsapp
            css_vars["--whatsapp-rgb"] = f"{red}, {green}, {blue}"
        for field_name, var_name in (
            ("theme_success", "--success"),
            ("theme_info", "--info"),
            ("theme_warning", "--warning"),
            ("theme_danger", "--danger"),
        ):
            value = getattr(self, field_name)
            if not value:
                continue
            red, green, blue = self._hex_to_rgb(value)
            css_vars[var_name] = value
            css_vars[f"{var_name}-rgb"] = f"{red}, {green}, {blue}"
        if self.theme_info:
            css_vars["--info-2"] = self.theme_info
            red, green, blue = self._hex_to_rgb(self.theme_info)
            css_vars["--info-2-rgb"] = f"{red}, {green}, {blue}"
        if self.theme_danger:
            soft = self._lighten(self.theme_danger)
            red, green, blue = self._hex_to_rgb(soft)
            css_vars["--danger-soft"] = soft
            css_vars["--danger-soft-rgb"] = f"{red}, {green}, {blue}"
        return css_vars
