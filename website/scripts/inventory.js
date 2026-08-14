const tab = document.querySelector('.main')
let invItems = []

async function loadInventory() {
    const response = await fetch('https://unikov.v-y-x.xyz/api/inventory', {
        credentials: "include"
    })
    invItems = await response.json()
    container = document.querySelector('.shop-items')

    invItems['items'].forEach(item => {
        const card = document.createElement('div')
        card.className = 'shop-card'

        card.innerHTML = `
            <span id="name">${item.name}</span>
            <img id="image" src="${item.image}" alt="${item.name}">
            <span id="balance">x${item.quantity}</span>
            <button onclick="viewItem('${item.id}')">See more</button>
            `

        container.appendChild(card)
    });
}

loadInventory()
let windowID = 0
let topZ = 0

function viewItem(itemID) {
    const item = invItems['items'].find(i => i.id === itemID);
    if (!item) return;

    windowID++;
    const winID = `window-${item.name}-${windowID}`;

    const window = document.createElement('div');
    window.className = 'item-window window'
    window.id = winID
    window.style.zIndex = ++topZ

    window.innerHTML = `
    <div class="title-bar">
            <div class="title-bar-text">${item.name}</div>
            <div class="title-bar-controls">
                <button aria-label="Close" onclick="closeItem('${winID}')"></button>
            </div>
        </div>
        <div class="window-body item-body">
            <div class="card-main">
                <div class="card-left">
                    <span id="item-name">${item.name}</span>
                    <img id="item-img" src="${item.image}" alt="">
                </div>
                <div class="card-right">
                    <span id="item-desc">${item.description}</span>
                    <div class="divider"></div>
                    <span id="item-price">you currently own ${item.quantity}</span>
                    <button onclick="useItem('${item.id}')">Use</button>
                </div>
            </div>
        </div>
    `

    tab.appendChild(window)

    document.querySelectorAll(".title-bar").forEach(bar => {
        bar.addEventListener("mousedown", startDrag);
    })

    document.querySelectorAll(".window").forEach(win => {
        win.addEventListener("mousedown", () => {
            win.style.zIndex = ++topZ;
        })
    })
}

function closeItem(winID) {
    const window = document.getElementById(winID)
    if (window) window.remove()
}

async function useItem(itemID) {
    const response = await fetch('https://unikov.v-y-x.xyz/api/use', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemID })
    })

    const result = await response.json()

    if (result.success) {
        alert('item has been used!')
        loadInventory()
    } else {
        alert(result.error)
    }
}