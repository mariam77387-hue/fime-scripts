const loginBox = document.getElementById("loginBox");
const dashboard = document.getElementById("dashboard");

const loginForm = document.getElementById("loginForm");
const loginMessage = document.getElementById("loginMessage");

const scriptForm = document.getElementById("scriptForm");
const scriptMessage = document.getElementById("scriptMessage");

const scriptsList = document.getElementById("scriptsList");
const logoutButton = document.getElementById("logoutButton");


async function checkOwner() {
    try {
        const response = await fetch("/api/owner/me");

        const data = await response.json();

        if (data.authenticated) {
            showDashboard();
            await loadOwnerScripts();
        }
    } catch (error) {
        console.error(error);
    }
}


function showDashboard() {
    loginBox.hidden = true;
    dashboard.hidden = false;
}


function showLogin() {
    loginBox.hidden = false;
    dashboard.hidden = true;
}


loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    loginMessage.textContent = "جارٍ تسجيل الدخول...";

    const username =
        document.getElementById("username").value;

    const password =
        document.getElementById("password").value;

    try {
        const response = await fetch("/api/owner/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username,
                password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            loginMessage.textContent =
                data.error || "فشل تسجيل الدخول.";

            return;
        }

        loginForm.reset();

        showDashboard();

        await loadOwnerScripts();

    } catch (error) {
        console.error(error);

        loginMessage.textContent =
            "حدث خطأ في الاتصال.";
    }
});


logoutButton.addEventListener("click", async () => {

    await fetch("/api/owner/logout", {
        method: "POST"
    });

    showLogin();

});


scriptForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    scriptMessage.textContent =
        "جاري نشر السكربت...";

    const payload = {
        title: document.getElementById("title").value.trim(),

        description:
            document.getElementById("description").value.trim(),

        game:
            document.getElementById("game").value.trim(),

        category:
            document.getElementById("category").value,

        image:
            document.getElementById("image").value.trim(),

        code:
            document.getElementById("code").value,

        featured:
            document.getElementById("featured").checked
    };


    try {

        const response = await fetch(
            "/api/owner/scripts",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(payload)
            }
        );


        const data = await response.json();


        if (!response.ok) {

            scriptMessage.textContent =
                data.error || "فشل نشر السكربت.";

            return;
        }


        scriptForm.reset();

        scriptMessage.textContent =
            "✅ تم نشر السكربت بنجاح.";

        await loadOwnerScripts();


    } catch (error) {

        console.error(error);

        scriptMessage.textContent =
            "حدث خطأ في الاتصال.";
    }
});


async function loadOwnerScripts() {

    scriptsList.textContent =
        "جاري تحميل السكربتات...";


    try {

        const response =
            await fetch("/api/scripts");

        const scripts =
            await response.json();


        scriptsList.textContent = "";


        if (!scripts.length) {

            scriptsList.textContent =
                "لا توجد سكربتات حتى الآن.";

            return;
        }


        for (const script of scripts) {

            const item =
                document.createElement("div");

            item.className =
                "owner-script";


            const info =
                document.createElement("div");


            const title =
                document.createElement("strong");

            title.textContent =
                script.title;


            const game =
                document.createElement("div");

            game.textContent =
                script.game || "بدون لعبة";


            info.appendChild(title);

            info.appendChild(game);


            const actions =
                document.createElement("div");


            const deleteButton =
                document.createElement("button");

            deleteButton.className =
                "btn btn-secondary";

            deleteButton.textContent =
                "حذف";


            deleteButton.addEventListener(
                "click",
                () => deleteScript(script.id)
            );


            actions.appendChild(deleteButton);


            item.appendChild(info);

            item.appendChild(actions);


            scriptsList.appendChild(item);
        }


    } catch (error) {

        console.error(error);

        scriptsList.textContent =
            "تعذر تحميل السكربتات.";
    }
}


async function deleteScript(id) {

    const confirmed =
        window.confirm(
            "هل أنت متأكد من حذف هذا السكربت؟"
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/api/owner/scripts/${id}`,
                {
                    method: "DELETE"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            alert(
                data.error ||
                "فشل حذف السكربت."
            );

            return;
        }


        await loadOwnerScripts();


    } catch (error) {

        console.error(error);

        alert(
            "حدث خطأ أثناء حذف السكربت."
        );
    }
}


checkOwner();