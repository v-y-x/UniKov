document.querySelectorAll(".title-bar").forEach(bar => {
    bar.addEventListener("mousedown", startDrag);
})

function startDrag(e) {
    const windowE = e.target.parentElement;
    const startX = e.clientX;
    const startY = e.clientY;
    const startLeft = windowE.offsetLeft;
    const startTop = windowE.offsetTop;

    function onMouseMove(e) {
        let currentX = e.clientX;
        let currentY = e.clientY;

        let dx = currentX - startX;
        let dy = currentY - startY;

        windowE.style.left = startLeft + dx + "px";
        windowE.style.top = startTop + dy + "px";
    }

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", () => {
        document.removeEventListener("mousemove", onMouseMove);
    })
}


async function loadAccountInfo() {
    const response = await fetch('https://unikov.v-y-x.xyz/api/me', {
        credentials: "include"  
    })
    const data = await response.json()
    
    const path = window.location.pathname
    const accountWin = document.querySelector('.account-body')
    
    if (data.logged_in) {
        accountWin.innerHTML = `
            <img src="${data.avatar}" alt="Avatar">
            <div>
                <span>${data.username}</span><span>${data.balance} coins</span>
            </div>
        `
    }
    else {
        accountWin.innerHTML = `<a href="https://unikov.v-y-x.xyz/login?next=${path}"><button id="loginButton">Connect</button></a>`
    }
}

loadAccountInfo()
