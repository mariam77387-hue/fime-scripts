(() => {
    "use strict";

    const commands = [
        {
            command: "/search",
            title: "بحث سكربت",
            description: "البحث عن السكربتات",
            action: () => {
                window.location.href = "/scripts";
            }
        },
        {
            command: "/request",
            title: "طلب سكربت",
            description: "إرسال طلب سكربت جديد",
            action: () => {
                window.location.href = "/request";
            }
        },
        {
            command: "/home",
            title: "الرئيسية",
            description: "العودة إلى الصفحة الرئيسية",
            action: () => {
                window.location.href = "/";
            }
        },
        {
            command: "/owner",
            title: "Owner",
            description: "دخول لوحة المالك",
            action: () => {
                openOwnerLogin();
            }
        },
        {
            command: "/commands",
            title: "الأوامر",
            description: "عرض جميع أوامر الموقع",
            action: () => {
                openCommands();
            }
        }
    ];

    function createElement(tag, className, text = "") {
        const element = document.createElement(tag);

        if (className) {
            element.className = className;
        }

        if (text) {
            element.textContent = text;
        }

        return element;
    }

    function injectStyles() {
        if (document.getElementById("fime-command-styles")) {
            return;
        }

        const style = document.createElement("style");
        style.id = "fime-command-styles";

        style.textContent = `
            .fime-command-bar {
                position: fixed;
                left: 18px;
                right: 18px;
                bottom: 18px;
                z-index: 9999;

                display: flex;
                align-items: center;
                gap: 10px;

                max-width: 900px;
                margin: auto;

                padding: 10px;

                background: rgba(10, 12, 20, .88);
                border: 1px solid rgba(255,255,255,.09);
                border-radius: 18px;

                backdrop-filter: blur(18px);
                -webkit-backdrop-filter: blur(18px);

                box-shadow:
                    0 18px 50px rgba(0,0,0,.35);
            }

            .fime-command-input {
                flex: 1;
                min-width: 0;

                border: 0;
                outline: none;

                background: transparent;
                color: #fff;

                font: inherit;
                padding: 11px 13px;

                direction: ltr;
                text-align: left;
            }

            .fime-command-input::placeholder {
                color: rgba(255,255,255,.42);
            }

            .fime-command-button {
                border: 0;
                cursor: pointer;

                padding: 10px 15px;

                border-radius: 12px;

                background: #5865f2;
                color: white;

                font: inherit;
                font-weight: 700;

                transition: .2s ease;
            }

            .fime-command-button:hover {
                transform: translateY(-1px);
                filter: brightness(1.08);
            }

            .fime-command-overlay {
                position: fixed;
                inset: 0;
                z-index: 10000;

                display: flex;
                align-items: center;
                justify-content: center;

                padding: 20px;

                background: rgba(0,0,0,.68);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
            }

            .fime-command-modal {
                width: min(430px, 100%);

                padding: 25px;

                border-radius: 22px;

                background: #10131c;
                border: 1px solid rgba(255,255,255,.09);

                box-shadow: 0 25px 80px rgba(0,0,0,.45);
            }

            .fime-command-modal h2 {
                margin: 0 0 8px;
                color: #fff;
            }

            .fime-command-modal p {
                margin: 0 0 20px;
                color: rgba(255,255,255,.62);
            }

            .fime-owner-password {
                width: 100%;
                box-sizing: border-box;

                padding: 13px 15px;

                border-radius: 13px;
                border: 1px solid rgba(255,255,255,.1);

                outline: none;

                background: #080a10;
                color: #fff;

                font: inherit;
                direction: ltr;
                text-align: left;
            }

            .fime-owner-password:focus {
                border-color: #5865f2;
            }

            .fime-owner-actions {
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }

            .fime-owner-actions button {
                flex: 1;
                padding: 12px;

                border: 0;
                border-radius: 12px;

                cursor: pointer;
                font: inherit;
                font-weight: 700;
            }

            .fime-owner-login {
                background: #5865f2;
                color: white;
            }

            .fime-owner-cancel {
                background: rgba(255,255,255,.07);
                color: white;
            }

            .fime-owner-message {
                min-height: 22px;
                margin-top: 12px;
                color: #ff7777;
                font-size: 14px;
            }

            .fime-command-list {
                display: grid;
                gap: 10px;
                margin-top: 18px;
            }

            .fime-command-item {
                padding: 13px;

                border-radius: 13px;
                background: rgba(255,255,255,.045);
                border: 1px solid rgba(255,255,255,.06);

                cursor: pointer;
            }

            .fime-command-item strong {
                display: block;
                direction: ltr;
                text-align: left;
                color: #fff;
                margin-bottom: 4px;
            }

            .fime-command-item span {
                color: rgba(255,255,255,.55);
                font-size: 13px;
            }

            @media (max-width: 600px) {
                .fime-command-bar {
                    left: 10px;
                    right: 10px;
                    bottom: 10px;
                }

                .fime-command-button {
                    padding: 10px 12px;
                }
            }
        `;

        document.head.appendChild(style);
    }

    function openOverlay() {
        const existing = document.querySelector(".fime-command-overlay");

        if (existing) {
            existing.remove();
        }

        const overlay = createElement("div", "fime-command-overlay");

        overlay.addEventListener("click", (event) => {
            if (event.target === overlay) {
                overlay.remove();
            }
        });

        document.body.appendChild(overlay);

        return overlay;
    }

    function openOwnerLogin() {
        const overlay = openOverlay();

        const modal = createElement("div", "fime-command-modal");

        const title = createElement(
            "h2",
            "",
            "🔐 Fime Owner"
        );

        const description = createElement(
            "p",
            "",
            "أدخل كلمة مرور المالك للدخول إلى لوحة الإدارة."
        );

        const password = document.createElement("input");
        password.className = "fime-owner-password";
        password.type = "password";
        password.placeholder = "كلمة مرور المالك";
        password.autocomplete = "current-password";

        const message = createElement(
            "div",
            "fime-owner-message"
        );

        const actions = createElement(
            "div",
            "fime-owner-actions"
        );

        const cancel = createElement(
            "button",
            "fime-owner-cancel",
            "إلغاء"
        );

        const login = createElement(
            "button",
            "fime-owner-login",
            "دخول"
        );

        actions.appendChild(cancel);
        actions.appendChild(login);

        modal.appendChild(title);
        modal.appendChild(description);
        modal.appendChild(password);
        modal.appendChild(message);
        modal.appendChild(actions);

        overlay.appendChild(modal);

        cancel.addEventListener("click", () => {
            overlay.remove();
        });

        async function loginOwner() {
            const value = password.value;

            if (!value) {
                message.textContent = "اكتب كلمة المرور.";
                password.focus();
                return;
            }

            login.disabled = true;
            login.textContent = "جاري التحقق...";
            message.textContent = "";

            try {
                const response = await fetch(
                    "/api/owner/login",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        credentials: "same-origin",
                        body: JSON.stringify({
                            password: value
                        })
                    }
                );

                const data = await response.json();

                if (!response.ok || !data.success) {
                    message.textContent =
                        data.error ||
                        "كلمة المرور غير صحيحة.";

                    login.disabled = false;
                    login.textContent = "دخول";
                    password.value = "";
                    password.focus();

                    return;
                }

                window.location.href = "/owner";

            } catch (error) {
                console.error(error);

                message.textContent =
                    "تعذر الاتصال بالسيرفر.";

                login.disabled = false;
                login.textContent = "دخول";
            }
        }

        login.addEventListener("click", loginOwner);

        password.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                loginOwner();
            }
        });

        setTimeout(() => password.focus(), 50);
    }

    function openCommands() {
        const overlay = openOverlay();

        const modal = createElement(
            "div",
            "fime-command-modal"
        );

        const title = createElement(
            "h2",
            "",
            "⚡ أوامر Fime"
        );

        const description = createElement(
            "p",
            "",
            "اكتب أي أمر في الشريط الموجود أسفل الموقع."
        );

        const list = createElement(
            "div",
            "fime-command-list"
        );

        for (const item of commands) {
            const commandItem = createElement(
                "div",
                "fime-command-item"
            );

            const command = createElement(
                "strong",
                "",
                item.command
            );

            const text = createElement(
                "span",
                "",
                item.title + " — " + item.description
            );

            commandItem.appendChild(command);
            commandItem.appendChild(text);

            commandItem.addEventListener(
                "click",
                () => {
                    overlay.remove();
                    item.action();
                }
            );

            list.appendChild(commandItem);
        }

        modal.appendChild(title);
        modal.appendChild(description);
        modal.appendChild(list);

        overlay.appendChild(modal);
    }

    function executeCommand(value) {
        const command = value.trim().toLowerCase();

        if (!command) {
            return;
        }

        const found = commands.find(
            item => item.command === command
        );

        if (found) {
            found.action();
            return;
        }

        // لو كتب اسم الأمر بدون /
        const normalized = "/" + command.replace(/^\/+/, "");

        const foundWithoutSlash = commands.find(
            item => item.command === normalized
        );

        if (foundWithoutSlash) {
            foundWithoutSlash.action();
            return;
        }

        // إذا كتب نص بحث عادي
        window.location.href =
            "/scripts?search=" +
            encodeURIComponent(value.trim());
    }

    function createCommandBar() {
        if (document.querySelector(".fime-command-bar")) {
            return;
        }

        const bar = createElement(
            "div",
            "fime-command-bar"
        );

        const input = document.createElement("input");

        input.className = "fime-command-input";

        input.type = "text";
        input.placeholder =
            "اكتب أمرًا مثل /search أو /owner ...";

        input.autocomplete = "off";
        input.spellcheck = false;

        const button = createElement(
            "button",
            "fime-command-button",
            "تنفيذ"
        );

        button.type = "button";

        bar.appendChild(input);
        bar.appendChild(button);

        document.body.appendChild(bar);

        button.addEventListener(
            "click",
            () => executeCommand(input.value)
        );

        input.addEventListener(
            "keydown",
            (event) => {
                if (event.key === "Enter") {
                    executeCommand(input.value);
                }
            }
        );
    }

    function init() {
        injectStyles();
        createCommandBar();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();