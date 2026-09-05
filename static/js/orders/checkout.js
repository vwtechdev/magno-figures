document.addEventListener("DOMContentLoaded", () => {
    CEP.init({
        input: document.getElementById("id_zip_code"),
        status: document.getElementById("cepStatus"),
        onEmpty: () => {
            document.getElementById("id_complement").value = "";
        },
    });

    const form = document.querySelector(".checkout__form");
    const hasCpf = form && form.dataset.hasCpf === "1";
    const subtotal = parseFloat((form && form.dataset.subtotal) || "0") || 0;

    const useNew = document.getElementById("id_use_new");
    const newBox = document.getElementById("newAddressBox");
    const newCepInput = document.getElementById("id_zip_code");
    const radios = Array.from(
        document.querySelectorAll('input[name="address_id"]')
    );

    const steps = {
        address: document.querySelector('[data-step="address"]'),
        shipping: document.querySelector('[data-step="shipping"]'),
        cpf: document.querySelector('[data-step="cpf"]'),
        summary: document.querySelector('[data-step="summary"]'),
    };
    const stepLabel = document.getElementById("stepLabel");
    const continueAddress = document.getElementById("continueAddress");
    const continueShipping = document.getElementById("continueShipping");
    const continueCpf = document.getElementById("continueCpf");
    const shippingStatus = document.getElementById("shippingStatus");
    const shippingOptions = document.getElementById("shippingOptions");
    const cpfInput = document.getElementById("id_checkout_cpf");
    const cpfStatus = document.getElementById("cpfStatus");
    const summaryFrete = document.getElementById("summaryFrete");
    const summaryTotal = document.getElementById("summaryTotal");
    const serviceInput = document.getElementById("shippingServiceInput");
    const submitBtn = document.getElementById("checkoutSubmit");

    const STEP_ORDER = ["address", "shipping", "cpf", "summary"];
    const STEP_LABELS = {
        address: "Endereço",
        shipping: "Frete",
        cpf: "CPF",
        summary: "Resumo",
    };

    const fmt = (value) => `R$ ${value.toFixed(2).replace(".", ",")}`;

    let selectedOption = null;
    let cpfOk = hasCpf;
    let loadingShipping = false;

    const showStep = (name) => {
        Object.entries(steps).forEach(([key, el]) => {
            if (el) el.hidden = key !== name;
        });
        const index = STEP_ORDER.indexOf(name) + 1;
        if (stepLabel) {
            stepLabel.textContent = `Etapa ${index} de ${STEP_ORDER.length} — ${STEP_LABELS[name]}`;
        }
        window.scrollTo({ top: 0, behavior: "smooth" });
    };

    const syncNewForm = () => {
        if (!useNew || !newBox) return;
        const show = radios.some(
            (radio) => radio.checked && radio.value === "new"
        );
        newBox.hidden = !show;
        newBox.querySelectorAll("input").forEach((input) => {
            if (input.name === "complement" || input.name === "is_primary") return;
            input.required = show;
        });
    };

    const addressCep = () => {
        const checked = radios.find((radio) => radio.checked);
        if (checked && checked.value !== "new") {
            const label = checked.closest(".checkout__address");
            return label ? label.dataset.cep : null;
        }
        const cep = newCepInput ? newCepInput.value.replace(/\D/g, "") : "";
        return cep.length === 8 ? cep : null;
    };

    const newFormReady = () => {
        if (!newBox) return true;
        const show = radios.length === 0 || radios.some(
            (radio) => radio.checked && radio.value === "new"
        );
        if (!show) return true;
        const required = ["zip_code", "state", "city", "neighborhood", "street", "number"];
        return required.every((name) => {
            const el = document.getElementById(`id_${name}`);
            return el && el.value.trim() !== "";
        });
    };

    const addressReady = () => Boolean(addressCep()) && newFormReady();

    const updateContinueState = () => {
        continueAddress.disabled = !addressReady();
        continueShipping.disabled = !selectedOption;
        continueCpf.disabled = !cpfOk;
    };

    const renderOptions = (options) => {
        shippingOptions.innerHTML = "";
        options.forEach((option) => {
            const label = document.createElement("label");
            label.className = "checkout__ship";
            label.innerHTML = `
                <input type="radio" name="shipping_choice" value="${option.name}" class="checkout__radio">
                <div class="checkout__ship-body">
                    <span class="checkout__ship-name">${option.name}</span>
                    <span class="checkout__ship-meta">${option.delivery_time} dia(s) útil(is)</span>
                </div>
                <span class="checkout__ship-price">${fmt(option.price)}</span>`;
            label.querySelector("input").addEventListener("change", () => {
                selectedOption = option;
                serviceInput.value = option.name;
                updateContinueState();
            });
            shippingOptions.appendChild(label);
        });
    };

    const loadShipping = async (cep) => {
        loadingShipping = true;
        shippingStatus.textContent = "Calculando frete...";
        shippingOptions.innerHTML = "";
        selectedOption = null;
        serviceInput.value = "";
        continueShipping.disabled = true;
        try {
            const response = await fetch(`/orders/checkout/shipping/?zipcode=${cep}`);
            const data = await response.json();
            if (!response.ok || data.error) {
                shippingStatus.textContent = data.error || "Não foi possível calcular o frete.";
                return;
            }
            if (!data.options || data.options.length === 0) {
                shippingStatus.textContent = "Nenhuma opção de frete disponível para este CEP.";
                return;
            }
            shippingStatus.textContent = "Escolha uma opção de frete:";
            renderOptions(data.options);
        } catch {
            shippingStatus.textContent = "Erro ao calcular o frete. Tente novamente.";
        } finally {
            loadingShipping = false;
        }
    };

    const refreshSummary = () => {
        if (!selectedOption) return;
        summaryFrete.textContent = `${fmt(selectedOption.price)} (${selectedOption.name})`;
        summaryTotal.textContent = fmt(subtotal + selectedOption.price);
        submitBtn.disabled = !(selectedOption && cpfOk);
    };

    const validateCpf = () => {
        const digits = cpfInput ? cpfInput.value.replace(/\D/g, "") : "";
        cpfOk = hasCpf || digits.length === 11;
        if (cpfStatus) {
            cpfStatus.textContent = cpfOk ? "" : "Informe os 11 dígitos do CPF.";
            cpfStatus.classList.toggle("is-error", !cpfOk);
        }
        updateContinueState();
    };

    continueAddress.addEventListener("click", () => {
        if (!addressReady()) return;
        showStep("shipping");
        loadShipping(addressCep());
    });

    continueShipping.addEventListener("click", () => {
        if (!selectedOption) return;
        showStep("cpf");
    });

    continueCpf.addEventListener("click", () => {
        if (!cpfOk) return;
        refreshSummary();
        showStep("summary");
    });

    if (cpfInput) {
        cpfInput.addEventListener("input", validateCpf);
    }

    radios.forEach((radio) => {
        radio.addEventListener("change", () => {
            syncNewForm();
            updateContinueState();
        });
    });

    if (newBox) {
        newBox.querySelectorAll("input, select").forEach((el) => {
            el.addEventListener("input", updateContinueState);
        });
    }

    syncNewForm();
    showStep("address");
    updateContinueState();
});