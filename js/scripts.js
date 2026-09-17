/* =========================================================
   Fime Scripts — scripts.js
   Public Scripts Page
   ========================================================= */

(() => {
    "use strict";

    const state = {
        scripts: [],
        categories: [],
        search: "",
        category: "all"
    };

    const elements = {
        grid: document.getElementById("scriptsGrid"),
        search: document.getElementById("searchInput"),
        category: document.getElementById("categoryFilter")
    };

    /* =====================================================
       Helpers
       ===================================================== */

    async function apiFetch(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            credentials: "same-origin",
            cache: "no-store",
            headers: {
                "Accept": "application/json",
                ...(options.headers || {})
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
                `Request failed: ${response.status}`
            );
        }

        return data;
    }

    function escapeHTML(value) {
        const div = document.createElement("div");
        div.textContent = value ?? "";
        return div.innerHTML;
    }

    function normalize(value) {
        return String(value ?? "")
            .toLowerCase()
            .normalize("NFKD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();
    }

    function getScriptTitle(script) {
        return script.title || script.name || "بدون عنوان";
    }

    function getScriptCategory(script) {
        return script.category || "Scripts";
    }

    function getScriptDescription(script) {
        return script.description || "لا يوجد وصف لهذا السكربت.";
    }

    function getScriptGame(script) {
        return script.game || "";
    }

    function getScriptImage(script) {
        return script.image || "";
    }

    function isFeatured(script) {
        return Boolean(script.featured);
    }

    /* =====================================================
       Load Data
       ===================================================== */

    async function loadScripts() {
        try {
            const data = await apiFetch("/api/scripts");

            if (Array.isArray(data)) {
                state.scripts = data;
            } else if (Array.isArray(data.scripts)) {
                state.scripts = data.scripts;
            } else {
                state.scripts = [];
            }

            buildCategories();
            renderCategoryFilter();
            renderScripts();

        } catch (error) {
            console.error("Fime Scripts load error:", error);

            showError(
                "حدث خطأ أثناء تحميل السكربتات. حاول تحديث الصفحة."
            );
        }
    }

    function buildCategories() {
        const categorySet = new Map();

        for (const script of state.scripts) {
            const category = getScriptCategory(script);

            if (!category) continue;

            const key = normalize(category);

            if (!categorySet.has(key)) {
                categorySet.set(key, category);
            }
        }

        state.categories = Array.from(categorySet.values())
            .sort((a, b) => a.localeCompare(b, "ar"));
    }

    /* =====================================================
       Categories
       ===================================================== */

    function renderCategoryFilter() {
        if (!elements.category) return;

        elements.category.innerHTML = "";

        const allOption = document.createElement("option");
        allOption.value = "all";
        allOption.textContent = "كل التصنيفات";
        elements.category.appendChild(allOption);

        for (const category of state.categories) {
            const option = document.createElement("option");

            option.value = category;
            option.textContent = category;

            elements.category.appendChild(option);
        }

        elements.category.value = state.category;
    }

    /* =====================================================
       Search
       ===================================================== */

    function matchesSearch(script) {
        const query = normalize(state.search);

        if (!query) return true;

        const searchableText = [
            getScriptTitle(script),
            getScriptDescription(script),
            getScriptCategory(script),
            getScriptGame(script),
            script.author || "",
            ...(Array.isArray(script.tags) ? script.tags : [])
        ]
            .map(normalize)
            .join(" ");

        return searchableText.includes(query);
    }

    function matchesCategory(script) {
        if (state.category === "all") {
            return true;
        }

        return normalize(getScriptCategory(script)) ===
               normalize(state.category);
    }

    function getFilteredScripts() {
        return state.scripts
            .filter(matchesSearch)
            .filter(matchesCategory)
            .sort((a, b) => {
                // Featured أولاً
                if (isFeatured(a) && !isFeatured(b)) return -1;
                if (!isFeatured(a) && isFeatured(b)) return 1;

                // الأحدث أولاً إذا كان ID موجود
                return Number(b.id || 0) - Number(a.id || 0);
            });
    }

    /* =====================================================
       Render
       ===================================================== */

    function renderScripts() {
        if (!elements.grid) {
            console.error(
                'Fime Scripts: لم يتم العثور على العنصر "scriptsGrid".'
            );
            return;
        }

        const scripts = getFilteredScripts();

        elements.grid.innerHTML = "";

        if (scripts.length === 0) {
            renderEmptyState();
            return;
        }

        const fragment = document.createDocumentFragment();

        for (const script of scripts) {
            fragment.appendChild(createScriptCard(script));
        }

        elements.grid.appendChild(fragment);
    }

    function createScriptCard(script) {
        const card = document.createElement("article");
        card.className = "script-card";

        const title = getScriptTitle(script);
        const description = getScriptDescription(script);
        const category = getScriptCategory(script);
        const game = getScriptGame(script);
        const image = getScriptImage(script);

        if (isFeatured(script)) {
            card.classList.add("featured");
        }

        /* =================================================
           Image
           ================================================= */

        if (image) {
            const imageWrapper = document.createElement("div");
            imageWrapper.className = "script-image";

            const img = document.createElement("img");

            img.src = image;
            img.alt = title;
            img.loading = "lazy";
            img.referrerPolicy = "no-referrer";

            img.onerror = () => {
                imageWrapper.classList.add("image-error");
                imageWrapper.innerHTML = `
                    <div class="script-image-placeholder">
                        <span>⚡</span>
                    </div>
                `;
            };

            imageWrapper.appendChild(img);
            card.appendChild(imageWrapper);
        }

        /* =================================================
           Content
           ================================================= */

        const content = document.createElement("div");
        content.className = "script-card-content";

        /* Featured */
        if (isFeatured(script)) {
            const featured = document.createElement("span");
            featured.className = "featured-badge";
            featured.textContent = "مميز";
            content.appendChild(featured);
        }

        /* Category */
        const categoryBadge = document.createElement("span");
        categoryBadge.className = "script-category";
        categoryBadge.textContent = category;

        content.appendChild(categoryBadge);

        /* Title */
        const heading = document.createElement("h3");
        heading.className = "script-title";
        heading.textContent = title;

        content.appendChild(heading);

        /* Game */
        if (game) {
            const gameElement = document.createElement("div");
            gameElement.className = "script-game";
            gameElement.textContent = `🎮 ${game}`;

            content.appendChild(gameElement);
        }

        /* Description */
        const descriptionElement = document.createElement("p");
        descriptionElement.className = "script-description";
        descriptionElement.textContent = description;

        content.appendChild(descriptionElement);

        /* Author */
        if (script.author) {
            const author = document.createElement("div");
            author.className = "script-author";
            author.textContent = `بواسطة ${script.author}`;

            content.appendChild(author);
        }

        /* Buttons */
        const actions = document.createElement("div");
        actions.className = "script-actions";

        const viewButton = document.createElement("a");
        viewButton.className = "script-view-button";
        viewButton.href = `/script?id=${encodeURIComponent(script.id)}`;
        viewButton.textContent = "عرض السكربت";

        actions.appendChild(viewButton);

        /*
         * Copy button
         * يظهر إذا كان الكود موجوداً
         */
        if (script.code) {
            const copyButton = document.createElement("button");

            copyButton.type = "button";
            copyButton.className = "script-copy-button";
            copyButton.textContent = "نسخ";

            copyButton.addEventListener("click", async () => {
                await copyCode(script.code, copyButton);
            });

            actions.appendChild(copyButton);
        }

        content.appendChild(actions);
        card.appendChild(content);

        return card;
    }

    /* =====================================================
       Empty State
       ===================================================== */

    function renderEmptyState() {
        if (!elements.grid) return;

        const empty = document.createElement("div");
        empty.className = "scripts-empty";

        const icon = document.createElement("div");
        icon.className = "scripts-empty-icon";
        icon.textContent = "🔎";

        const title = document.createElement("h3");
        title.textContent = state.search
            ? "ما لقينا نتائج"
            : "ما فيه سكربتات حالياً";

        const text = document.createElement("p");
        text.textContent = state.search
            ? "جرّب كلمة بحث مختلفة أو غيّر التصنيف."
            : "سيتم إضافة السكربتات هنا قريباً.";

        empty.appendChild(icon);
        empty.appendChild(title);
        empty.appendChild(text);

        elements.grid.appendChild(empty);
    }

    function showError(message) {
        if (!elements.grid) return;

        elements.grid.innerHTML = "";

        const error = document.createElement("div");
        error.className = "scripts-error";

        const icon = document.createElement("div");
        icon.className = "scripts-error-icon";
        icon.textContent = "⚠️";

        const text = document.createElement("p");
        text.textContent = message;

        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "scripts-retry-button";
        retry.textContent = "إعادة المحاولة";

        retry.addEventListener("click", () => {
            loadScripts();
        });

        error.appendChild(icon);
        error.appendChild(text);
        error.appendChild(retry);

        elements.grid.appendChild(error);
    }

    /* =====================================================
       Copy
       ===================================================== */

    async function copyCode(code, button) {
        if (!code) return;

        const originalText = button.textContent;

        try {
            await navigator.clipboard.writeText(code);

            button.textContent = "تم النسخ ✓";
            button.classList.add("copied");

            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove("copied");
            }, 1800);

        } catch (error) {
            console.error("Copy failed:", error);

            /*
             * Fallback للمتصفحات التي لا تدعم Clipboard API
             */
            try {
                const textarea = document.createElement("textarea");

                textarea.value = code;
                textarea.style.position = "fixed";
                textarea.style.opacity = "0";
                textarea.style.pointerEvents = "none";

                document.body.appendChild(textarea);

                textarea.focus();
                textarea.select();

                document.execCommand("copy");

                textarea.remove();

                button.textContent = "تم النسخ ✓";
                button.classList.add("copied");

                setTimeout(() => {
                    button.textContent = originalText;
                    button.classList.remove("copied");
                }, 1800);

            } catch (fallbackError) {
                console.error("Fallback copy failed:", fallbackError);

                button.textContent = "فشل النسخ";

                setTimeout(() => {
                    button.textContent = originalText;
                }, 1800);
            }
        }
    }

    /* =====================================================
       Events
       ===================================================== */

    function setupEvents() {
        if (elements.search) {
            let searchTimer;

            elements.search.addEventListener("input", (event) => {
                clearTimeout(searchTimer);

                searchTimer = setTimeout(() => {
                    state.search = event.target.value;
                    renderScripts();
                }, 120);
            });
        }

        if (elements.category) {
            elements.category.addEventListener("change", (event) => {
                state.category = event.target.value;
                renderScripts();
            });
        }
    }

    /* =====================================================
       Keyboard Shortcuts
       ===================================================== */

    document.addEventListener("keydown", (event) => {
        /*
         * "/" يفتح البحث
         */
        if (
            event.key === "/" &&
            document.activeElement !== elements.search &&
            document.activeElement?.tagName !== "INPUT" &&
            document.activeElement?.tagName !== "TEXTAREA"
        ) {
            event.preventDefault();

            if (elements.search) {
                elements.search.focus();
            }
        }

        /*
         * Escape يمسح البحث
         */
        if (
            event.key === "Escape" &&
            document.activeElement === elements.search
        ) {
            if (elements.search) {
                elements.search.value = "";
                state.search = "";
                renderScripts();
                elements.search.blur();
            }
        }
    });

    /* =====================================================
       Start
       ===================================================== */

    function init() {
        setupEvents();
        loadScripts();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();