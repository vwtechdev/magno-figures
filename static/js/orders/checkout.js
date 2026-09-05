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

    const shippingStep = document.querySelector('[data-step="shipping"]');
    const cpfStep = document.querySelector('[data-step="cpf"]');
    const summaryStep = document.querySelector('[data-step="summary"]');
    const shippingStatus = document.getElementById("shippingStatus");
    const shippingOptions = document.getElementById("shippingOptions");
    const cpfInput = document.getElementById("id_checkout_cpf");
    const cpfStatus = document.getElementById("cpfStatus");
    const summaryFrete = document.getElementById("summaryFrete");
    const summaryTotal = document.getElementById("summaryTotal");
    const serviceInput = document.getElementById("shippingServiceInput");
    const submitBtn = document.getElementById("checkoutSubmit");

    const fmt = (value) => `R$ ${value.toFixed(2).replace(".", ",")}`;

    let selectedOption = null;
    let cpfOk = hasCpf;
    let loadingShipping = false;

    const updateSubmit = () => {
        submitBtn.disabled = !(selectedOption && cpfOk);
    };

    const refreshSummary = () => {
        if (!selectedOption) return;
        summaryFrete.textContent = `${fmt(selectedOption.price)} (${selectedOption.name})`;
        summaryTotal.textContent = fmt(subtotal + selectedOption.price);
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
                refreshSummary();
                summaryStep.hidden = false;
                updateSubmit();
                summaryStep.scrollIntoView({ behavior: "smooth", block: "center" });
            });
            shippingOptions.appendChild(label);
        });
        cpfStep.hidden = false;
    };

    const loadShipping = async (cep) => {
        loadingShipping = true;
        shippingStep.hidden = false;
        shippingStatus.textContent = "Calculando frete...";
        shippingOptions.innerHTML = "";
        selectedOption = null;
        serviceInput.value = "";
        updateSubmit();
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
            shippingStatus.textContent = "";
            renderOptions(data.options);
        } catch {
            shippingStatus.textContent = "Erro ao calcular o frete. Tente novamente.";
        } finally {
            loadingShipping = false;
        }
    };

    const maybeLoadShipping = () => {
        if (loadingShipping) return;
        const cep = addressCep();
        if (!cep || !newFormReady()) return;
        loadShipping(cep);
    };

    const validateCpf = () => {
        const digits = cpfInput ? cpfInput.value.replace(/\D/g, "") : "";
        cpfOk = hasCpf || digits.length === 11;
        if (cpfStatus) {
            cpfStatus.textContent = cpfOk ? "" : "Informe os 11 dígitos do CPF.";
            cpfStatus.classList.toggle("is-error", !cpfOk);
        }
        updateSubmit();
    };

    if (cpfInput) {
        cpfInput.addEventListener("input", validateCpf);
    }

    radios.forEach((radio) => {
        radio.addEventListener("change", () => {
            syncNewForm();
            cpfStep.hidden = false;
            maybeLoadShipping();
        });
    });

    if (newBox) {
        newBox.querySelectorAll("input, select").forEach((el) => {
            el.addEventListener("input", maybeLoadShipping);
        });
    }

    syncNewForm();
    maybeLoadShipping();
});