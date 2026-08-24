const tab = document.querySelector('.main')
let shopItems = []

async function loadShopItmes() {
    const response = await fetch('/api/items', {credentials: "include"});
    shopItems = await response.json();

    container = document.querySelector('.shop-items')

    shopItems.forEach(item => {
        const card = document.createElement('div')
        card.className = 'shop-card'

        card.innerHTML = `
            <span id="name">${item.name}</span>
            <img id="image" src="${item.image}" alt="${item.name}">
            <span id="balance">${item.price} coins</span>
            <button onclick="viewItem('${item.id}')">See more</button>
            `

        container.appendChild(card)
    });
}

loadShopItmes()

let windowID = 0

function viewItem(itemID) {
    const item = shopItems.find(i => i.id === itemID);
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
                    <span id="item-price">${item.price} coins</span>
                    <button onclick="buyItem('${item.id}')">Buy</button>
                </div>
            </div>
        </div>
    `
    
    tab.appendChild(window)
    
    document.querySelectorAll(".title-bar").forEach(bar => {
        bar.addEventListener("mousedown", startDrag);
    })

    window.addEventListener("mousedown", () => {
        window.style.zIndex = ++topZ;
    })
}

async function buyItem(itemId) {
    const response = await fetch('https://unikov.v-y-x.xyz/api/buy', {
        method: "POST",
        credentials: "include",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId })
    })

    const result = await response.json();

    if (result.success) {
        let message = `success! your new balance is ${result.new_balance}` 
        successWindow(message)
        loadAccountInfo()
    } else {
        let message = `error: ${result.error}` 
        errorWindow(message)
    }

    loadAccountInfo()
}
