(function () {
    var form = document.getElementById("newsletterForm");
    var msg = document.getElementById("newsletterMsg");
    if (!form) {
        return;
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (msg) {
            msg.textContent = "";
        }
        var data = new FormData(form);
        fetch(form.action, {
            method: "POST",
            headers: {"X-Requested-With": "XMLHttpRequest"},
            body: data,
        })
            .then(function (response) {
                return response.json().then(function (payload) {
                    return {status: response.status, payload: payload};
                });
            })
            .then(function (result) {
                if (msg) {
                    msg.textContent = result.payload.message || "";
                }
                if (result.status < 400) {
                    form.reset();
                }
            })
            .catch(function () {
                form.submit();
            });
    });
})();
