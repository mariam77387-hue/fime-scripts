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
                "No script was selected."
            );

            return;

        }


        try {

            const response =
                await fetch(
                    "data/scripts.json"
                );


            if (!response.ok) {
                throw new Error(
                    "Failed to load data"
                );
            }


            const scripts =
                await response.json();


            const script =
                scripts.find(
                    item => item.id === id
                );


            if (!script) {

                showError(
                    container,
                    "Script not found."
                );

                return;

            }


            renderScript(
                container,
                script
            );


        } catch (error) {

            console.error(error);

            showError(
                container,
                "Unable to load this script."
            );

        }

    }
);


function renderScript(
    container,
    script
) {

    const tags =
        (script.tags || [])
            .map(
                tag =>
                    `<span class="tag">
                        ${escapeHTML(tag)}
                    </span>`
            )
            .join("");


    container.innerHTML = `

        <div class="script-detail-header">

            <div class="script-card-top">

                <div class="script-icon">
                    ${script.type?.toLowerCase() === "hack"
                        ? "🧩"
                        : "📜"}
                </div>

                <span class="script-category">
                    ${escapeHTML(
                        script.category || "Other"
                    )}
                </span>

            </div>


            <h1>
                ${escapeHTML(script.name)}
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
                    Script Code
                </span>

                <button
                    class="copy-code-btn"
                    id="copyCodeBtn">

                    Copy Code

                </button>

            </div>


            <pre><code id="scriptCode"></code></pre>

        </div>


        <div class="script-description">

            <h2>
                About this script
            </h2>

            <p>
                ${escapeHTML(
                    script.description || "No description."
                )}
            </p>

        </div>

    `;


    const codeElement =
        document.getElementById(
            "scriptCode"
        );


    codeElement.textContent =
        script.code || "";


    const copyButton =
        document.getElementById(
            "copyCodeBtn"
        );


    copyButton.addEventListener(
        "click",
        async () => {

            try {

                await navigator.clipboard.writeText(
                    script.code || ""
                );


                copyButton.textContent =
                    "Copied!";


                setTimeout(
                    () => {

                        copyButton.textContent =
                            "Copy Code";

                    },
                    1500
                );


            } catch (error) {

                console.error(error);

                copyButton.textContent =
                    "Copy failed";

            }

        }
    );

}


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
                Return to the scripts page and try again.
            </p>

        </div>

    `;

}


function escapeHTML(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}