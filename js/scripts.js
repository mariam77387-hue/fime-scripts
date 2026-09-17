let allScripts = [];
let currentCategory = "all";

document.addEventListener("DOMContentLoaded", async () => {
    const scriptsGrid = document.getElementById("scriptsGrid");
    const hacksGrid = document.getElementById("hacksGrid");

    if (!scriptsGrid && !hacksGrid) {
        return;
    }

    try {
        const response = await fetch("/api/scripts", {
            method: "GET",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        if (!Array.isArray(data)) {
            throw new Error("Invalid API response");
        }

        allScripts = data;

        if (scriptsGrid) {
            setupScriptsPage();
        }

        if (hacksGrid) {
            setupHacksPage();
        }

    } catch (error) {
        console.error("Failed to load scripts:", error);

        if (scriptsGrid) {
            scriptsGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">!</div>
                    <h3>تعذر تحميل السكربتات</h3>
                    <p>حدث خطأ أثناء الاتصال بالموقع. حاول مرة أخرى لاحقًا.</p>
                </div>
            `;
        }

        if (hacksGrid) {
            hacksGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">!</div>
                    <h3>تعذر تحميل الهاكات</h3>
                    <p>حاول تحديث الصفحة مرة أخرى.</p>
                </div>
            `;
        }
    }
});


/*
 * =========================
 * SCRIPTS PAGE
 * =========================
 */

function setupScriptsPage() {
    const searchInput =
        document.getElementById("scriptSearch");

    const filterContainer =
        document.getElementById("categoryFilters");

    createCategoryFilters(filterContainer);

    renderScripts(
        getFilteredScripts(searchInput?.value || "")
    );

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            renderScripts(
                getFilteredScripts(searchInput.value)
            );
        });
    }
}


/*
 * =========================
 * HACKS PAGE
 * =========================
 */

function setupHacksPage() {
    const hacks = allScripts.filter(script => {
        const type = String(script.type || "").toLowerCase();
        const category = String(script.category || "").toLowerCase();

        return (
            type === "hack" ||
            category === "hacks" ||
            category === "hack"
        );
    });

    const grid =
        document.getElementById("hacksGrid");

    const empty =
        document.getElementById("hacksEmpty");

    if (!hacks.length) {
        if (grid) {
            grid.innerHTML = "";
        }

        if (empty) {
            empty.style.display = "block";
        }

        return;
    }

    if (empty) {
        empty.style.display = "none";
    }

    renderScripts(hacks, grid);
}


/*
 * =========================
 * CATEGORY FILTERS
 * =========================
 */

function createCategoryFilters(container) {
    if (!container) {
        return;
    }

    container.innerHTML = "";

    const allButton =
        document.createElement("button");

    allButton.className =
        "filter-btn active";

    allButton.dataset.category = "all";
    allButton.textContent = "الكل";

    allButton.addEventListener("click", () => {
        currentCategory = "all";

        container
            .querySelectorAll(".filter-btn")
            .forEach(btn =>
                btn.classList.remove("active")
            );

        allButton.classList.add("active");

        const search =
            document.getElementById("scriptSearch");

        renderScripts(
            getFilteredScripts(search?.value || "")
        );
    });

    container.appendChild(allButton);


    const categories = [
        ...new Set(
            allScripts
                .map(script => script.category)
                .filter(category => category)
        )
    ];


    categories.forEach(category => {
        const button =
            document.createElement("button");

        button.className =
            "filter-btn";

        button.dataset.category =
            category;

        button.textContent =
            category;

        button.addEventListener("click", () => {
            currentCategory = category;

            container
                .querySelectorAll(".filter-btn")
                .forEach(btn =>
                    btn.classList.remove("active")
                );

            button.classList.add("active");

            const search =
                document.getElementById("scriptSearch");

            renderScripts(
                getFilteredScripts(search?.value || "")
            );
        });

        container.appendChild(button);
    });
}


/*
 * =========================
 * FILTER
 * =========================
 */

function getFilteredScripts(searchText) {
    const query =
        String(searchText || "")
            .trim()
            .toLowerCase();

    return allScripts.filter(script => {
        const matchesCategory =
            currentCategory === "all" ||
            script.category === currentCategory;

        const searchableText = [
            script.title,
            script.name,
            script.description,
            script.category,
            script.game,
            script.type,
            ...(Array.isArray(script.tags)
                ? script.tags
                : [])
        ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();

        const matchesSearch =
            !query ||
            searchableText.includes(query);

        return matchesCategory && matchesSearch;
    });
}


/*
 * =========================
 * RENDER
 * =========================
 */

function renderScripts(
    scripts,
    target = document.getElementById("scriptsGrid")
) {
    if (!target) {
        return;
    }

    const emptyState =
        document.getElementById("emptyState");

    if (!scripts.length) {
        target.innerHTML = "";

        if (emptyState) {
            emptyState.style.display = "block";
        }

        return;
    }

    if (emptyState) {
        emptyState.style.display = "none";
    }

    target.innerHTML =
        scripts
            .map(createScriptCard)
            .join("");

    setupCardButtons(target);
}


/*
 * =========================
 * SCRIPT CARD
 * =========================
 */

function createScriptCard(script) {
    const tags =
        (Array.isArray(script.tags)
            ? script.tags
            : [])
            .slice(0, 4)
            .map(tag => `
                <span class="tag">
                    ${escapeHTML(tag)}
                </span>
            `)
            .join("");


    const scriptName =
        script.title ||
        script.name ||
        "بدون اسم";


    const type =
        String(script.type || "Script")
            .toLowerCase();


    const icon =
        type === "hack"
            ? "🧩"
            : "📜";


    return `
        <article class="script-card">

            <div class="script-card-top">

                <div class="script-icon">
                    ${icon}
                </div>

                <span class="script-category">
                    ${escapeHTML(
                        script.category || "Other"
                    )}
                </span>

            </div>


            <h3>
                ${escapeHTML(scriptName)}
            </h3>


            <p>
                ${escapeHTML(
                    script.description || ""
                )}
            </p>


            ${
                script.game
                    ? `
                        <div class="script-game">
                            🎮 ${escapeHTML(script.game)}
                        </div>
                    `
                    : ""
            }


            <div class="script-tags">
                ${tags}
            </div>


            <div class="script-card-bottom">

                <a
                    class="card-btn primary"
                    href="script.html?id=${encodeURIComponent(script.id)}">

                    عرض السكربت

                </a>

                <button
                    class="card-btn copy-script-btn"
                    type="button"
                    data-script-id="${escapeHTML(script.id)}">

                    نسخ

                </button>

            </div>

        </article>
    `;
}


/*
 * =========================
 * CARD BUTTONS
 * =========================
 */

function setupCardButtons(target) {
    const buttons =
        target.querySelectorAll(
            ".copy-script-btn"
        );

    buttons.forEach(button => {
        button.addEventListener("click", () => {
            copyScript(button.dataset.scriptId);
        });
    });
}


/*
 * =========================
 * COPY
 * =========================
 */

async function copyScript(id) {
    const script =
        allScripts.find(
            item => String(item.id) === String(id)
        );

    if (!script) {
        showToast("السكربت غير موجود.");
        return;
    }

    try {
        await navigator.clipboard.writeText(
            script.code || ""
        );

        showToast("تم نسخ السكربت!");

    } catch (error) {
        console.error("Copy failed:", error);
        showToast("تعذر نسخ السكربت.");
    }
}


/*
 * =========================
 * TOAST
 * =========================
 */

function showToast(message) {
    let toast =
        document.getElementById("fimeToast");

    if (!toast) {
        toast =
            document.createElement("div");

        toast.id = "fimeToast";

        toast.style.position = "fixed";
        toast.style.bottom = "25px";
        toast.style.left = "50%";
        toast.style.transform = "translateX(-50%)";
        toast.style.zIndex = "9999";
        toast.style.padding = "12px 18px";
        toast.style.borderRadius = "10px";
        toast.style.background = "#161923";
        toast.style.border =
            "1px solid rgba(255,255,255,.1)";
        toast.style.color = "white";
        toast.style.fontSize = "14px";
        toast.style.transition = "opacity .2s";

        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.style.opacity = "1";

    clearTimeout(
        window.fimeToastTimeout
    );

    window.fimeToastTimeout =
        setTimeout(() => {
            toast.style.opacity = "0";
        }, 1800);
}


/*
 * =========================
 * SECURITY
 * =========================
 */

function escapeHTML(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}