document.addEventListener(
    "DOMContentLoaded",
    async () => {

        const container =
            document.getElementById(
                "scriptDetails"
            );

        if (!container) {
            return;
        }

        const params =
            new URLSearchParams(
                window.location.search
            );

        const id =
            params.get("id");

        if (!id) {
            showError(
                container,
                "لم يتم تحديد أي سكربت."
            );

            return;
        }

        try {

            const response =
                await fetch(
                    "data/scripts.json",
                    {
                        cache: "no-cache"
                    }
                );

            if (!response.ok) {
                throw new Error(
                    "Failed to load data"
                );
            }

            const scripts =
                await response.json();

            if (!Array.isArray(scripts)) {
                throw new Error(
                    "Invalid scripts data"
                );
            }

            const script =
                scripts.find(
                    item => item.id === id
                );

            if (!script) {

                showError(
                    container,
                    "السكربت غير موجود."
                );

                return;
            }

            renderScript(
                container,
                script
            );

        } catch (error) {

            console.error(
                "Fime Script Page:",
                error
            );

            showError(
                container,
                "تعذر تحميل هذا السكربت."
            );
        }
    }
);


/*
 * RENDER SCRIPT
 */

function renderScript(
    container,
    script
) {

    const tags =
        (
            Array.isArray(script.tags)
                ? script.tags
                : []
        )
            .map(tag => {
                return `
                    <span class="tag">
                        ${escapeHTML(tag)}
                    </span>
                `;
            })
            .join("");


    const isHack =
        String(script.type || "")
            .toLowerCase() === "hack";


    container.innerHTML = `

        <div class="script-detail-header">

            <div class="script-card-top">

                <div class="script-icon">
                    ${isHack ? "🧩" : "📜"}
                </div>

                <span class="script-category">
                    ${escapeHTML(
                        script.category || "Other"
                    )}
                </span>

            </div>


            <h1>
                ${escapeHTML(
                    script.name || "بدون اسم"
                )}
            </h1>


            <p>
                ${escapeHTML(
                    script.description || ""
                )}
            </p>


            <div class="detail-meta">
                ${tags}
            </div>

        </div>


        <div class="code-container">

            <div class="code-header">

                <span>
                    كود السكربت
                </span>

                <button
                    class="copy-code-btn"
                    id="copyCodeBtn"
                    type="button"
                >
                    نسخ الكود
                </button>

            </div>


            <pre><code id="scriptCode"></code></pre>

        </div>


        <div class="script-description">

            <h2>
                عن هذا السكربت
            </h2>

            <p>
                ${escapeHTML(
                    script.description ||
                    "لا يوجد وصف لهذا السكربت."
                )}
            </p>

        </div>

    `;


    /*
     * CODE
     *
     * نستخدم textContent بدل innerHTML
     * حتى يتم عرض الكود كنص وليس كـ HTML.
     */

    const codeElement =
        document.getElementById(
            "scriptCode"
        );

    if (codeElement) {

        codeElement.textContent =
            script.code || "";

    }


    /*
     * COPY
     */

    const copyButton =
        document.getElementById(
            "copyCodeBtn"
        );

    if (!copyButton) {
        return;
    }


    copyButton.addEventListener(
        "click",
        async () => {

            const code =
                script.code || "";


            if (!code) {

                copyButton.textContent =
                    "لا يوجد كود";

                resetCopyButton(
                    copyButton,
                    "نسخ الكود",
                    1500
                );

                return;
            }


            try {

                await navigator.clipboard.writeText(
                    code
                );


                copyButton.textContent =
                    "تم النسخ ✓";


                resetCopyButton(
                    copyButton,
                    "نسخ الكود",
                    1500
                );


            } catch (error) {

                console.error(
                    "Copy error:",
                    error
                );


                copyButton.textContent =
                    "فشل النسخ";


                resetCopyButton(
                    copyButton,
                    "نسخ الكود",
                    1800
                );
            }

        }
    );

}


/*
 * RESET COPY BUTTON
 */

function resetCopyButton(
    button,
    text,
    delay
) {

    setTimeout(
        () => {
            button.textContent = text;
        },
        delay
    );

}


/*
 * ERROR
 */

function showError(
    container,
    message
) {

    container.innerHTML = `

        <div class="empty-state">

            <div class="empty-icon">
                !
            </div>

            <h3>
                ${escapeHTML(message)}
            </h3>

            <p>
                ارجع إلى صفحة السكربتات وحاول مرة أخرى.
            </p>

            <a
                href="scripts.html"
                class="card-btn primary"
            >
                العودة للسكربتات
            </a>

        </div>

    `;

}


/*
 * SECURITY
 */

function escapeHTML(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}