let cart = JSON.parse(localStorage.getItem("cart")) || [];

function fetchRestaurants() {
    fetch("http://localhost:5000/restaurants")
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById("restaurant-list");
            list.innerHTML = "";
            data.forEach(r => {
                const div = document.createElement("div");
                div.innerHTML = `<h3>${r.name}</h3>
                                 <p>${r.cuisine}</p>
                                 <button onclick="goToRestaurant(${r.id}, '${r.name}')">Ver Cardápio</button>`;
                list.appendChild(div);
            });
        });
}

function goToRestaurant(id, name) {
    window.location.href = `restaurant.html?id=${id}`;
}

function fetchMenu(restaurantId) {
    fetch(`http://localhost:5000/restaurants/${restaurantId}/menu`)
        .then(res => res.json())
        .then(data => {
            document.getElementById("restaurant-name").textContent = data.restaurant.name;
            const menuList = document.getElementById("menu-list");
            menuList.innerHTML = "";
            data.menu.forEach(item => {
                const div = document.createElement("div");
                div.innerHTML = `<h4>${item.name} - R$ ${item.price.toFixed(2)}</h4>
                                 <p>${item.description}</p>
                                 <button onclick='addToCart(${JSON.stringify(item)})'>Adicionar</button>`;
                menuList.appendChild(div);
            });
        });
}

function addToCart(item) {
    cart.push(item);
    localStorage.setItem("cart", JSON.stringify(cart));
    alert("Adicionado ao carrinho!");
}

function renderCart() {
    const cartDiv = document.getElementById("cart-items");
    cartDiv.innerHTML = "";
    cart.forEach((item, index) => {
        cartDiv.innerHTML += `<div>${item.name} - R$ ${item.price.toFixed(2)}
                              <button onclick="removeFromCart(${index})">Remover</button></div>`;
    });
}

function removeFromCart(index) {
    cart.splice(index, 1);
    localStorage.setItem("cart", JSON.stringify(cart));
    renderCart();
}

function checkout() {
    fetch("http://localhost:5000/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: cart })
    })
    .then(res => res.json())
    .then(data => {
        alert("Pedido realizado!");
        cart = [];
        localStorage.setItem("cart", JSON.stringify(cart));
        window.location.href = "index.html";
    });
}
