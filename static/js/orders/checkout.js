document.addEventListener("DOMContentLoaded", () => {
    CEP.init({
        input: document.getElementById("id_zip_code"),
        status: document.getElementById("cepStatus"),
        onEmpty: () => {
            document.getElementById("id_complement").value = "";
        },
    });

    const useNew = document.getElementById("id_use_new");
    const newBox = document.getElementById("newAddressBox");
    const radios = Array.from(
        document.querySelectorAll('input[name="address_id"]')
    );

    if (useNew && newBox) {
        const sync = () => {
            const show = radios.some(
                (radio) => radio.checked && radio.value === "new"
            );
            newBox.hidden = !show;
            newBox.querySelectorAll("input").forEach((input) => {
                if (input.name === "complement" || input.name === "is_primary") return;
                input.required = show;
            });
        };

        radios.forEach((radio) => radio.addEventListener("change", sync));
        sync();
    }
});
