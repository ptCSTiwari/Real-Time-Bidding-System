const API_BASE = "http://localhost:8000";
let selectedAuctionId = null;

async function fetchAuctions() {
    const token = localStorage.getItem("token");

    const res = await fetch(`${API_BASE}/admin/all-auctions`, {
        headers: { "Authorization": "Bearer " + token }
    });

    if (!res.ok) {
        alert("Not authorized");
        window.location.href = "login.html";
        return;
    }

    const auctions = await res.json();
    const select = document.getElementById("auctionSelect");

    select.innerHTML = "";

    auctions.forEach(a => {
        const option = document.createElement("option");
        option.value = a.id;
        option.innerText = `${a.product_name} (ID: ${a.id})`;
        select.appendChild(option);
    });
}

async function loadAuctionStats() {
    const token = localStorage.getItem("token");
    selectedAuctionId = document.getElementById("auctionSelect").value;

    const res = await fetch(`${API_BASE}/admin/auction-stats/${selectedAuctionId}`, {
        headers: { "Authorization": "Bearer " + token }
    });

    const data = await res.json();

    document.getElementById("adminStatus").innerText =
        "Status: " + data.status;

    document.getElementById("adminPrice").innerText =
        "Current Price: ₹" + data.current_price;

    document.getElementById("adminTotalBids").innerText =
        "Total Bids: " + data.total_bids;
}

async function pauseAuction() {
    await adminAction("pause-auction");
}

async function resumeAuction() {
    await adminAction("resume-auction");
}

async function closeAuction() {
    await adminAction("close-auction");
}

async function extendAuction() {
    const token = localStorage.getItem("token");
    const minutes = document.getElementById("extendMinutes").value;

    await fetch(`${API_BASE}/admin/extend-auction/${selectedAuctionId}?extra_minutes=${minutes}`, {
        method: "POST",
        headers: { "Authorization": "Bearer " + token }
    });

    loadAuctionStats();
}

async function adminAction(action) {
    const token = localStorage.getItem("token");

    await fetch(`${API_BASE}/admin/${action}/${selectedAuctionId}`, {
        method: "POST",
        headers: { "Authorization": "Bearer " + token }
    });

    loadAuctionStats();
}

function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

window.onload = fetchAuctions;