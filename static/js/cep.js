const CEP = (() => {
    const API_BASE = "https://viacep.com.br/ws";

    function onlyDigits(value) {
        return (value || "").replace(/\D/g, "");
    }

    function format(value) {
        const digits = onlyDigits(value).slice(0, 8);
        if (digits.length <= 5) {
            return digits;
        }
        return `${digits.slice(0, 5)}-${digits.slice(5)}`;
    }

    function fillFields(data) {
        const mapping = {
            state: data.uf,
            city: data.localidade,
            neighborhood: data.bairro,
            street: data.logradouro,
            complement: data.complemento,
        };
        Object.entries(mapping).forEach(([name, value]) => {
            const element = document.getElementById(`id_${name}`);
            if (element) {
                element.value = value || "";
            }
        });
    }

    function clearFields() {
        ["state", "city", "neighborhood", "street"].forEach((name) => {
            const element = document.getElementById(`id_${name}`);
            if (element) {
                element.value = "";
            }
        });
    }

    async function lookup(cep, { status, onEmpty } = {}) {
        const digitCep = onlyDigits(cep);
        if (digitCep.length !== 8) return;

        setStatus(status, "Consultando CEP...", "loading");
        try {
            const response = await fetch(`${API_BASE}/${digitCep}/json/`);
            const data = await response.json();
            if (data.erro) {
                setStatus(status, "CEP não encontrado.", "error");
                clearFields();
                if (onEmpty) onEmpty();
                return;
            }
            fillFields(data);
            setStatus(status, "");
        } catch {
            setStatus(status, "Erro ao consultar o CEP. Tente novamente.", "error");
        }
    }

    function setStatus(el, message, kind) {
        if (!el) return;
        el.textContent = message;
        el.classList.toggle("is-loading", kind === "loading");
        el.classList.toggle("is-error", kind === "error");
    }

    function init({ input, status, onEmpty } = {}) {
        const cepInput = input || document.getElementById("id_zip_code");
        if (!cepInput) return;

        cepInput.addEventListener("input", () => {
            cepInput.value = format(cepInput.value);
            setStatus(status, "");
        });

        cepInput.addEventListener("blur", () => {
            lookup(cepInput.value, { status, onEmpty });
        });

        cepInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                cepInput.blur();
            }
        });
    }

    return {
        init,
        lookup,
        format,
        onlyDigits,
    };
})();