// ==============================
// CONFIG
// ==============================
const API_BASE = "http://localhost:8000";
const params = new URLSearchParams(window.location.search);
const AUCTION_ID = params.get("auction_id");

if (!AUCTION_ID) {
    alert("Auction ID missing in URL");
    window.location.href = "auctions.html";
}

let ws = null;
let reconnectAttempts = 0;
let reconnectTimeout = null;

// ==============================
// TOAST
// ==============================
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.innerText = message;

    toast.style.position = "fixed";
    toast.style.bottom = "20px";
    toast.style.right = "20px";
    toast.style.padding = "12px 20px";
    toast.style.borderRadius = "6px";
    toast.style.color = "white";
    toast.style.zIndex = "1000";
    toast.style.fontWeight = "bold";

    if (type === "success") toast.style.backgroundColor = "#22c55e";
    else if (type === "error") toast.style.backgroundColor = "#ef4444";
    else toast.style.backgroundColor = "#64748b";

    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ==============================
// FETCH AUCTION STATE
// ==============================
async function syncAuctionState() {
    try {
        const res = await fetch(`${API_BASE}/auction/${AUCTION_ID}`);
        if (!res.ok) return;

        const data = await res.json();

        document.getElementById("price").innerText =
            "Current Price: ₹" + data.current_price;

        document.getElementById("status").innerText =
            "Status: " + data.status;

    } catch (err) {
        console.error("State sync failed", err);
    }
}

// ==============================
// COUNTDOWN TIMER
// ==============================
async function startCountdown() {
    try {
        const res = await fetch(`${API_BASE}/auction/${AUCTION_ID}`);
        const data = await res.json();

        if (!data.end_time) return;

        const endTime = new Date(data.end_time).getTime();

        setInterval(() => {
            const now = new Date().getTime();
            const diff = endTime - now;

            if (diff <= 0) {
                document.getElementById("timer").innerText = "Auction Closed";
                return;
            }

            const mins = Math.floor(diff / 60000);
            const secs = Math.floor((diff % 60000) / 1000);

            document.getElementById("timer").innerText =
                `Time Remaining: ${mins}m ${secs}s`;

        }, 1000);

    } catch (err) {
        console.error("Timer failed", err);
    }
}

// ==============================
// WEBSOCKET
// ==============================
function connectWebSocket() {
    const token = localStorage.getItem("token");

    if (!token) {
        showToast("Please login first", "error");
        window.location.href = "login.html";
        return;
    }

    const wsUrl = `ws://localhost:8000/ws/${AUCTION_ID}?token=${token}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        reconnectAttempts = 0;
        showToast("Connected", "success");
        syncAuctionState();
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

            if (data.price !== undefined) {
                const priceElement = document.getElementById("price");

                priceElement.innerText =
                    "Current Price: ₹" + data.price;

                priceElement.style.transform = "scale(1.15)";
                priceElement.style.color = "#f97316";

                setTimeout(() => {
                    priceElement.style.transform = "scale(1)";
                    priceElement.style.color = "#22c55e";
                }, 300);
            }

            if (data.dealer_id !== undefined && data.dealer_id !== null) {
                document.getElementById("leader").innerText =
                    "Leading Bidder: Dealer #" + data.dealer_id;

                const history = document.getElementById("bidHistory");
                const li = document.createElement("li");
                li.innerText =
                    `Dealer #${data.dealer_id} → ₹${data.price}`;
                history.prepend(li);

                if (history.children.length > 15) {
                    history.removeChild(history.lastChild);
                }
            }

        } catch (err) {
            console.error("Invalid WS message", err);
        }
    };

    ws.onclose = () => {
        showToast("Connection lost. Reconnecting...", "error");

        reconnectAttempts++;
        const delay = Math.min(2000 * reconnectAttempts, 10000);

        reconnectTimeout = setTimeout(() => {
            connectWebSocket();
        }, delay);
    };

    ws.onerror = () => ws.close();
}

// ==============================
// PLACE BID
// ==============================
async function placeBid() {
    const token = localStorage.getItem("token");

    if (!token) {
        showToast("Please login first", "error");
        window.location.href = "login.html";
        return;
    }

    const bidInput = document.getElementById("bidAmount");
    const button = document.getElementById("bidBtn");

    const amount = parseFloat(bidInput.value);

    if (!amount || amount <= 0) {
        showToast("Enter valid bid amount", "error");
        return;
    }

    button.disabled = true;
    button.innerText = "Placing...";

    const idempotencyKey = "bid_" + Date.now();

    try {
        const response = await fetch(`${API_BASE}/bid`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            },
            body: JSON.stringify({
                auction_id: Number(AUCTION_ID),
                amount: Number(amount),
                idempotency_key: idempotencyKey
            })
        });

        const data = await response.json();

        if (!response.ok) {
            showToast(data.detail || "Bid failed", "error");
        } else {
            showToast("Bid placed!", "success");
            bidInput.value = "";
        }

    } catch {
        showToast("Network error", "error");
    }

    button.disabled = false;
    button.innerText = "Place Bid";
}

// ==============================
// LOGOUT
// ==============================
function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

// ==============================
// INIT
// ==============================
window.onload = () => {
    connectWebSocket();
    startCountdown();
};