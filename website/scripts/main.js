const ding = new Audio('scripts/sfx/ding.mp3');
const chimes = new Audio('scripts/sfx/chimes.mp3');
const chord = new Audio('scripts/sfx/chord.mp3');

ding.volume = .3
chimes.volume = .3
chord.volume = .3

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
        accountWin.innerHTML = `<button id="loginButton" onclick="cookieWindow()">Connect</button>`
    }
}

loadAccountInfo()

function closeItem(winID) {
    const window = document.getElementById(winID)
    if (window) window.remove()
    }

let alertNum = 0

function createWindow(){
    const window = document.createElement('div')
    window.className = 'window alert-window'
    alertNum++
    
    return window
}

function cookieWindow() {
    const path = window.location.pathname
    const alertID = `alert-${alertNum}`
    cookieWin = createWindow()
    cookieWin.id = alertID
    cookieWin.innerHTML = `
    <div class="title-bar">
    <div class="title-bar-text">Cookie Disclaimer</div>
    </div>
    <div class="window-body alert-body">
        <div id="alert-content">
            <img src="resources/icons/warning.ico">
            <span id="text">this website uses cookies to store your discord data for future sessions. we only save public information about your account. if you're fine with that, proceed with your login!</span>
        </div>
        <div id="acc-login-but">
            <a href="https://unikov.v-y-x.xyz/login?next=${path}"><button>Connect</button></a>
            <button onclick="closeItem('${alertID}')">Close</button>
        </div>  
    `
        
    document.querySelector('body').appendChild(cookieWin)
    ding.play()

    document.querySelectorAll(".title-bar").forEach(bar => {
        bar.addEventListener("mousedown", startDrag);
    })

    cookieWin.addEventListener("mousedown", () => {
        cookieWin.style.zIndex = ++topZ;
    })
}

function successWindow(message) {
    const alertID = `alert-${alertNum}`
    successWin = createWindow()
    successWin.id = alertID
    successWin.innerHTML = `
    <div class="title-bar">
    <div class="title-bar-text">Success</div>
    </div>
    <div class="window-body alert-body">
        <div id="alert-content">
            <img src="resources/icons/info.ico">
            <span id="text">${message}</span>
        </div>
        <div id="acc-login-but">
            <button onclick="closeItem('${alertID}')">Close</button>
        </div>
    </div>
    `
        
    document.querySelector('body').appendChild(successWin)
    chimes.play()

    document.querySelectorAll(".title-bar").forEach(bar => {
        bar.addEventListener("mousedown", startDrag);
    })

    successWin.addEventListener("mousedown", () => {
        successWin.style.zIndex = ++topZ;
    })
}

function errorWindow(message) {
    const alertID = `alert-${alertNum}`
    errorWin = createWindow()
    errorWin.id = alertID
    errorWin.innerHTML = `
    <div class="title-bar">
    <div class="title-bar-text">Error</div>
    </div>
    <div class="window-body alert-body">
        <div id="alert-content">
            <img src="resources/icons/error.ico">
            <span id="text">${message}</span>
        </div>
        <div id="acc-login-but">
            <button onclick="closeItem('${alertID}')">Close</button>
        </div>
    </div>
    `        
    document.querySelector('body').appendChild(errorWin)
    chord.play()

    document.querySelectorAll(".title-bar").forEach(bar => {
        bar.addEventListener("mousedown", startDrag);
    })

    errorWin.addEventListener("mousedown", () => {
        errorWin.style.zIndex = ++topZ;
    })
}