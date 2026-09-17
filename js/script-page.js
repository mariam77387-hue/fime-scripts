(() => {
    "use strict";

    /* =========================================================
       Fime — script-page.js
       صفحة عرض السكربت
       متوافق مع:
       GET /api/scripts/<script_id>
       ========================================================= */

    const details = document.getElementById("scriptDetails");

    /* =========================================================
       Helpers
       ========================================================= */

    async function apiFetch(url) {
        const response = await fetch(url, {
            method: "GET",
            credentials: "same-origin",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        let data = null;

        try {
            data = await response.json();
        } catch {
            data = null;
        }

        if (!response.ok) {
            throw new Error(
                data?.error ||
                data?.message ||
                `HTTP ${response.status}`
            );
        }

        return data;
    }


    function getScriptId() {
        const params = new URLSearchParams(window.location.search);
        return params.get("id");
    }


    function text(value, fallback = "") {
        if (value === null || value === undefined) {
            return fallback;
        }

        return String(value);
    }


    function updatePageTitle(script) {
        const title =
            script.title ||
            script.name ||
            "Script";

        document.title = `${title} — Fime`;
    }


    /* =========================================================
       Loading
       ========================================================= */

    function showLoading() {
        if (!details) return;

        details.innerHTML = "";

        const wrapper = document.createElement("div");
        wrapper.className = "script-loading";

        const spinner = document.createElement("div");
        spinner.className = "loading-spinner";

        const message = document.createElement("p");
        message.textContent = "جاري تحميل السكربت...";

        wrapper.appendChild(spinner);
        wrapper.appendChild(message);

        details.appendChild(wrapper);
    }


    /* =========================================================
       Error
       ========================================================= */

    function showError(message = "تعذر تحميل السكربت.") {
        if (!details) return;

        details.innerHTML = "";

        const error = document.createElement("div");
        error.className = "script-error";

        const icon = document.createElement("div");
        icon.className = "script-error-icon";
        icon.textContent = "⚠️";

        const title = document.createElement("h2");
        title.textContent = "حدث خطأ";

        const paragraph = document.createElement("p");
        paragraph.textContent = message;

        const back = document.createElement("a");
        back.href = "/scripts";
        back.className = "script-back-button";
        back.textContent = "العودة إلى السكربتات";

        error.appendChild(icon);
        error.appendChild(title);
        error.appendChild(paragraph);
        error.appendChild(back);

        details.appendChild(error);
    }


    /* =========================================================
       Not Found
       ========================================================= */

    function showNotFound() {
        if (!details) return;

        details.innerHTML = "";

        const wrapper = document.createElement("div");
        wrapper.className = "script-not-found";

        const icon = document.createElement("div");
        icon.className = "script-not-found-icon";
        icon.textContent = "🔎";

        const title = document.createElement("h2");
        title.textContent = "السكربت غير موجود";

        const paragraph = document.createElement("p");
        paragraph.textContent =
            "يمكن أن يكون السكربت قد تم حذفه أو أن الرابط غير صحيح.";

        const back = document.createElement("a");
        back.href = "/scripts";
        back.className = "script-back-button";
        back.textContent = "تصفح السكربتات";

        wrapper.appendChild(icon);
        wrapper.appendChild(title);
        wrapper.appendChild(paragraph);
        wrapper.appendChild(back);

        details.appendChild(wrapper);
    }


    /* =========================================================
       Copy
       ========================================================= */

    async function copyCode(code, button) {
        if (!code || !button) return;

        const originalText = button.textContent;

        try {
            if (
                navigator.clipboard &&
                window.isSecureContext
            ) {
                await navigator.clipboard.writeText(code);
            } else {
                fallbackCopy(code);
            }

            button.textContent = "تم النسخ ✓";
            button.classList.add("copied");

            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove("copied");
            }, 1800);

        } catch (error) {
            console.error("Copy error:", error);

            try {
                fallbackCopy(code);

                button.textContent = "تم النسخ ✓";
                button.classList.add("copied");

                setTimeout(() => {
                    button.textContent = originalText;
                    button.classList.remove("copied");
                }, 1800);

            } catch (fallbackError) {
                console.error(
                    "Fallback copy error:",
                    fallbackError
                );

                button.textContent = "فشل النسخ";

                setTimeout(() => {
                    button.textContent = originalText;
                }, 1800);
            }
        }
    }


    function fallbackCopy(code) {
        const textarea = document.createElement("textarea");

        textarea.value = code;

        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.top = "0";
        textarea.style.left = "0";
        textarea.style.width = "1px";
        textarea.style.height = "1px";
        textarea.style.opacity = "0";
        textarea.style.pointerEvents = "none";

        document.body.appendChild(textarea);

        textarea.focus();
        textarea.select();
        textarea.setSelectionRange(
            0,
            textarea.value.length
        );

        const successful =
            document.execCommand("copy");

        textarea.remove();

        if (!successful) {
            throw new Error("Copy command failed.");
        }
    }


    /* =========================================================
       Code actions
       ========================================================= */

    function setupCodeActions(code, copyButton, codeElement) {

        if (copyButton) {
            copyButton.addEventListener(
                "click",
                () => copyCode(code, copyButton)
            );
        }

        /*
         * تحديد الكود عند الضغط عليه
         */
        if (codeElement) {
            codeElement.addEventListener(
                "dblclick",
                () => {
                    const selection = window.getSelection();
                    const range = document.createRange();

                    range.selectNodeContents(codeElement);

                    selection.removeAllRanges();
                    selection.addRange(range);
                }
            );
        }
    }


    /* =========================================================
       Render Script
       ========================================================= */

    function renderScript(script) {
        if (!details) return;

        details.innerHTML = "";

        const title =
            text(
                script.title || script.name,
                "بدون عنوان"
            );

        const description =
            text(
                script.description,
                "لا يوجد وصف لهذا السكربت."
            );

        const category =
            text(
                script.category,
                "Scripts"
            );

        const game =
            text(
                script.game,
                ""
            );

        const author =
            text(
                script.author,
                ""
            );

        const code =
            text(
                script.code,
                ""
            );

        const image =
            text(
                script.image,
                ""
            );


        /* =====================================================
           Main wrapper
           ===================================================== */

        const wrapper =
            document.createElement("article");

        wrapper.className =
            "script-detail-card";


        /* =====================================================
           Featured badge
           ===================================================== */

        if (script.featured) {
            const featured =
                document.createElement("div");

            featured.className =
                "script-featured-badge";

            featured.textContent =
                "مميز ⭐";

            wrapper.appendChild(featured);
        }


        /* =====================================================
           Image
           ===================================================== */

        if (image) {
            const imageWrapper =
                document.createElement("div");

            imageWrapper.className =
                "script-detail-image";

            const img =
                document.createElement("img");

            img.src = image;
            img.alt = title;
            img.loading = "eager";
            img.referrerPolicy = "no-referrer";

            img.addEventListener(
                "error",
                () => {
                    imageWrapper.remove();
                },
                { once: true }
            );

            imageWrapper.appendChild(img);
            wrapper.appendChild(imageWrapper);
        }


        /* =====================================================
           Header
           ===================================================== */

        const header =
            document.createElement("div");

        header.className =
            "script-detail-header";


        /* Category */

        const categoryBadge =
            document.createElement("span");

        categoryBadge.className =
            "script-detail-category";

        categoryBadge.textContent =
            category;

        header.appendChild(categoryBadge);


        /* Title */

        const heading =
            document.createElement("h1");

        heading.className =
            "script-detail-title";

        heading.textContent =
            title;

        header.appendChild(heading);


        /* Game */

        if (game) {
            const gameElement =
                document.createElement("div");

            gameElement.className =
                "script-detail-game";

            gameElement.textContent =
                `🎮 ${game}`;

            header.appendChild(gameElement);
        }


        /* Author */

        if (author) {
            const authorElement =
                document.createElement("div");

            authorElement.className =
                "script-detail-author";

            authorElement.textContent =
                `بواسطة ${author}`;

            header.appendChild(authorElement);
        }


        wrapper.appendChild(header);


        /* =====================================================
           Description
           ===================================================== */

        const descriptionBox =
            document.createElement("div");

        descriptionBox.className =
            "script-detail-description";


        const descriptionTitle =
            document.createElement("h2");

        descriptionTitle.textContent =
            "الوصف";

        const descriptionText =
            document.createElement("p");

        descriptionText.textContent =
            description;


        descriptionBox.appendChild(
            descriptionTitle
        );

        descriptionBox.appendChild(
            descriptionText
        );

        wrapper.appendChild(
            descriptionBox
        );


        /* =====================================================
           Code section
           ===================================================== */

        if (code) {

            const codeSection =
                document.createElement("section");

            codeSection.className =
                "script-code-section";


            /* Code header */

            const codeHeader =
                document.createElement("div");

            codeHeader.className =
                "script-code-header";


            const codeTitle =
                document.createElement("h2");

            codeTitle.textContent =
                "الكود";


            const copyButton =
                document.createElement("button");

            copyButton.type =
                "button";

            copyButton.className =
                "script-copy-button";

            copyButton.textContent =
                "نسخ";


            codeHeader.appendChild(
                codeTitle
            );

            codeHeader.appendChild(
                copyButton
            );


            /* Code */

            const codeWrapper =
                document.createElement("div");

            codeWrapper.className =
                "script-code-wrapper";


            const pre =
                document.createElement("pre");

            pre.className =
                "script-code";


            const codeElement =
                document.createElement("code");

            /*
             * textContent مهم جداً:
             * يمنع تنفيذ HTML/JS الموجود داخل السكربت.
             */
            codeElement.textContent =
                code;


            pre.appendChild(
                codeElement
            );

            codeWrapper.appendChild(
                pre
            );


            codeSection.appendChild(
                codeHeader
            );

            codeSection.appendChild(
                codeWrapper
            );


            wrapper.appendChild(
                codeSection
            );


            setupCodeActions(
                code,
                copyButton,
                codeElement
            );
        }


        /* =====================================================
           Bottom actions
           ===================================================== */

        const actions =
            document.createElement("div");

        actions.className =
            "script-detail-actions";


        const back =
            document.createElement("a");

        back.href =
            "/scripts";

        back.className =
            "script-back-button";

        back.textContent =
            "← العودة إلى السكربتات";


        actions.appendChild(
            back
        );

        wrapper.appendChild(
            actions
        );


        /* =====================================================
           Insert
           ===================================================== */

        details.appendChild(
            wrapper
        );
    }


    /* =========================================================
       Load Script
       ========================================================= */

    async function loadScript() {

        if (!details) {
            console.error(
                'Fime: العنصر "scriptDetails" غير موجود.'
            );

            return;
        }


        const scriptId =
            getScriptId();


        if (!scriptId) {
            showNotFound();
            return;
        }


        /*
         * ID يجب أن يكون رقمياً
         */
        if (!/^\d+$/.test(scriptId)) {
            showNotFound();
            return;
        }


        showLoading();


        try {

            const script =
                await apiFetch(
                    `/api/scripts/${encodeURIComponent(scriptId)}`
                );


            if (!script || !script.id) {
                showNotFound();
                return;
            }


            updatePageTitle(
                script
            );


            renderScript(
                script
            );


        } catch (error) {

            console.error(
                "Fime Script API error:",
                error
            );


            /*
             * إذا كان السكربت غير موجود
             */
            if (
                error.message &&
                (
                    error.message.includes("404") ||
                    error.message.includes("غير موجود")
                )
            ) {
                showNotFound();
                return;
            }


            showError(
                "تعذر الاتصال بالخادم. حاول تحديث الصفحة."
            );
        }
    }


    /* =========================================================
       Start
       ========================================================= */

    function init() {
        loadScript();
    }


    if (
        document.readyState === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            init
        );
    } else {
        init();
    }

})();